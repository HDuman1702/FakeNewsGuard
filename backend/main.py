from fastapi import FastAPI, Query
from rss_scheduler import start_scheduler
from analysis_service import analyze_url
from db import SessionLocal
from models import Article, Analysis
import json
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import urlparse
from sqlalchemy import func


app = FastAPI(title="FakeNewsGuard Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js Frontend
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



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



@app.get("/dashboard")
def dashboard(
    q: str | None = Query(None),
    categories: str | None = Query(None),
    min_conf: int = Query(0),
    only_failed: bool = Query(False),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    limit: int = Query(50),
):

    db = SessionLocal()
    try:
        query = (
            db.query(Analysis, Article)
            .join(Article, Analysis.article_id == Article.id)
        )

        #  Suche
        if q:
            query = query.filter(
            Article.title.ilike(f"%{q}%") |
            Article.url.ilike(f"%{q}%")
        )

        #  Min Confidence
        if min_conf:
            query = query.filter(Analysis.confidence >= min_conf)

        #  Nur fehlerhafte
        if only_failed:
            query = query.filter(Analysis.label != "likely_real")

        # Kategorien
        if categories:
            cat_list = [c.strip() for c in categories.split(",")]
            query = query.filter(Analysis.category.in_(cat_list))

        #  Sortierung
        sort_col = Analysis.created_at
        if sort == "confidence":
            sort_col = Analysis.confidence
        elif sort == "word_count":
            sort_col = Article.word_count
        else:
            sort_col = Analysis.created_at

       

        if order == "desc":
            sort_col = sort_col.desc()
        else:
            sort_col = sort_col.asc()

        rows = query.order_by(sort_col).limit(limit).all()


        

        result = []
        for analysis, article in rows:
            result.append({
                "url": article.url,
                "analyzed_at": analysis.created_at.isoformat(),
                "source_domain": urlparse(article.url).netloc,
                "result": {
                    "label": analysis.label,
                    "confidence": int(analysis.confidence),
                    "category": analysis.category,
                    "reasoning_summary": analysis.reasoning_summary,
                    "red_flags": json.loads(analysis.red_flags) if analysis.red_flags else [],
                    "title": article.title,
                    "word_count": article.word_count,
                    "excerpt": article.text[:280] if article.text else "",
                 }
            })

        return result

    finally:
        db.close()

@app.on_event("startup")
async def startup():
    start_scheduler()

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


