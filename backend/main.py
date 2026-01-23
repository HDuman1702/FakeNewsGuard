from fastapi import FastAPI, Query
#from backend.Arss_scheduler import start_scheduler
from analysis_service import analyze_url
from db import SessionLocal, engine
from models import Article, Analysis
import models
import logging
log = logging.getLogger(__name__)
import json
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import urlparse
from sqlalchemy import func
from sample_urls import SAMPLE_URLS
from datetime import datetime
import os

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="FakeNewsGuard Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://fakenewsguard-ui.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


LLM_ENABLED = os.getenv("LLM_ENABLED", "false").lower() == "true"
LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL")  # z. B. http://host:8001



@app.post("/analyze")
async def analyze(req: dict):
    db = SessionLocal()

    try:
        return await analyze_and_store(req["url"], db)
    finally:
        db.close()
    
async def analyze_and_store(url: str, db):
    
        result = await analyze_url(url)

       # --- Article (robust) ---
        article = (
            db.query(Article)
            .filter(Article.url == url)
            .first()
        )

        if not article:
            article = Article(
                url=url,
                title=result.get("title"),
                text=result.get("analysis_text", ""),
                word_count=result.get("word_count", 0),
            )
            db.add(article)
            db.commit()
            db.refresh(article)

        # --- Analysis ---
        analysis = Analysis(
            article_id=article.id,
            label=result["label"],
            confidence=result["confidence"],
            category=result.get("category"),
            red_flags=json.dumps(result.get("red_flags", [])),
            reasoning_summary=result.get("reasoning_summary"),
        )
        db.add(analysis)
        db.commit()

        return result



@app.get("/health")
def health():
    return {"status": "ok"}



from sample_urls import SAMPLE_URLS

@app.get("/dashboard")
async def dashboard(limit: int = 5):
    urls = SAMPLE_URLS[:limit]
    now = datetime.utcnow().isoformat()

    results = []
    for url in urls:
        res = await analyze_url(url)
        results.append({
            "url": url,
            "analyzed_at": now,
            "source_domain": urlparse(url).netloc,
            "result": res
        })

    return results




#@app.on_event("startup")
#async def startup():
 #   start_scheduler()

@app.get("/topics/trending")
def trending_topics(days: int = 3, min_conf: int = 70, limit: int = 10):
    db = SessionLocal()
    try:
        rows = (
            db.query(Analysis.category, func.count(Analysis.id).label("count"))
            .filter(Analysis.confidence >= min_conf)
            .group_by(Analysis.category)
            .order_by(func.count(Analysis.id).desc())
            .limit(limit)
            .all()
        )

        return [
            {"topic": category or "Unbekannt", "count": count}
            for category, count in rows
        ]
    finally:
        db.close()


