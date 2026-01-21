
from typing import Dict, Any, Tuple, Optional
import httpx
import json
import re
import os
from sqlalchemy.exc import IntegrityError
from models import Article, Analysis
from heuristics import extract_features, CATEGORIES
from scraper import fetch_html, extract_article

LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://127.0.0.1:8001").rstrip("/")
LLM_TIMEOUT = httpx.Timeout(180.0)

DEFAULT_COUNTER_SOURCES = [
    "https://www.tagesschau.de/faktenfinder/",
    "https://correctiv.org/faktencheck/",
]

CATEGORY_MAP = {
    "likely_real": "Seriöse Nachricht",
    "uncertain": "Irreführende Inhalte",
    "likely_fake": "Falschmeldung",
}

def determine_category(label: str, features: dict) -> str:
    # 1. Harte Regeln zuerst
    if features.get("is_satire_domain"):
        return "Satire / Parodie"

    if features.get("fake_trigger_hits", 0) >= 2:
        return "Propaganda"

    if features.get("emotion_hits", 0) >= 2:
        return "Manipulation"

    # 2. Fallback: Label → Kategorie
    return CATEGORY_MAP.get(label, "Unbekannt")


# ---------- LLM Call ----------
async def call_llm(prompt: str) -> Tuple[Optional[Dict[str, Any]], str]:
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            r = await client.post(f"{LLM_GATEWAY_URL}/classify", json={"text": prompt})
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return None, f"LLM error: {e}"

    if isinstance(data.get("parsed"), dict):
        return data["parsed"], "parsed-ok"

    return None, "no-parseable-json"

#Kategorie im Backend ableiten
def map_label_to_category(label: str, features: dict) -> str:
    if features.get("is_satire_domain"):
        return "Satire / Parodie"
    if label == "likely_real":
        return "Seriöse Nachricht"
    if label == "likely_fake":
        return "Falschmeldung"
    return "Unbekannt"




# ---------- Prompt ----------
def build_prompt(title: str, url: str, text: str, features: dict) -> str:
    return f"""
Du bist FakeNewsGuard.

KATEGORIEN:
{", ".join(CATEGORIES)}

REGELN:
- Satire ≠ Fake News
- Propaganda, Falschmeldung, Manipulation → Fake
- Clickbait/Irreführend → Unsicher

MESSWERTE:
- word_count: {features['word_count']}
- fake_trigger_hits: {features['fake_trigger_hits']}
- uncertainty_hits: {features['uncertainty_hits']}
- emotion_hits: {features['emotion_hits']}
- is_satire_domain: {features['is_satire_domain']}

ANTWORTFORMAT (NUR JSON):
{{
  "label": "likely_fake | uncertain | likely_real",
  "confidence": 0-100,
  "category": "...",
  "red_flags": [string],
  "reasoning_summary": string,
  "suggested_counter_sources": [string]
}}

TEXT:
{text[:8000]}
""".strip()


# ---------- Hauptanalyse ----------
async def analyze_url(url: str) -> Dict[str, Any]:
    html = await fetch_html(url)
    title, text, excerpt = extract_article(html, url)
    features = extract_features(text, url)

    #  Harte Satire-Regel (ohne LLM)
    if features.get("is_satire_domain"):
        return {
            "label": "uncertain",
            "confidence": 40,
            "category": "Satire / Parodie",
            "red_flags": ["satire_domain"],
            "analysis_text": "Bekannte Satire-Seite.",
            "reasoning_summary": "Satire ist keine Fake News im engeren Sinne.",
            "suggested_counter_sources": [],
            "title": title,
            "word_count": features.get("word_count", 0),
            "excerpt": excerpt,
        }

    prompt = build_prompt(title, url, text, features)
    parsed, debug = await call_llm(prompt)

    #  LLM-Fallback
    if not isinstance(parsed, dict):
        return {
            "label": "uncertain",
            "confidence": 50,
            "category": determine_category("uncertain", features),
            "analysis_text": "LLM-Fallback",
            "red_flags": ["llm_fallback"],
            "reasoning_summary": debug,
            "suggested_counter_sources": DEFAULT_COUNTER_SOURCES,
            "title": title,
            "word_count": features["word_count"],
            "excerpt": excerpt,
        }

    label = parsed.get("label", "uncertain")
    category = determine_category(label, features)

    return {
        "label": label,
        "confidence": parsed.get("confidence", 50),
        "category": category,
        "analysis_text": parsed.get("reasoning_summary", ""),
        "red_flags": parsed.get("red_flags", []),
        "reasoning_summary": parsed.get("reasoning_summary", ""),
        "suggested_counter_sources": parsed.get("suggested_counter_sources", []),
        "title": title,
        "word_count": features["word_count"],
        "excerpt": excerpt,
    }



async def analyze_and_store(url: str, db):
    result = await analyze_url(url)

    # 🔹 1. Article holen oder neu anlegen
    article = db.query(Article).filter(Article.url == url).first()

    if not article:
        article = Article(
            url=url,
            title=result.get("title"),
            text=result.get("analysis_text", ""),
            word_count=result.get("word_count", 0),
        )
        db.add(article)
        try:
            db.commit()
            db.refresh(article)
        except IntegrityError:
            db.rollback()
            if not isinstance(url, str):
                return None

            article = db.query(Article).filter(Article.url == url).first()

    # 🔹 2. Neue Analysis IMMER anlegen
    analysis = Analysis(
        article_id=article.id,
        label=result["label"],
        confidence=result["confidence"],
        category=result.get("category"),
        reasoning_summary=result.get("reasoning_summary"),
        red_flags=json.dumps(result.get("red_flags", [])),
    )

    db.add(analysis)
    db.commit()

    return result

