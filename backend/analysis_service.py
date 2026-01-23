
from typing import Dict, Any, Tuple, Optional
import httpx
import json
import re
import os
from sqlalchemy.exc import IntegrityError
from models import Article, Analysis
from heuristics import extract_features, CATEGORIES
from scraper import fetch_html, extract_article
from llm_adapter import call_llm_gateway

def count_words_safe(text: str, excerpt: str, title: str) -> int:
    base = text or excerpt or title or ""
    return len(base.split())




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
- "word_count": word_count,

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
    word_count = count_words_safe(text, excerpt, title)
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

  

    # ---------- Regelbasierte Basis ----------
    label = "uncertain"
    confidence = 50
    red_flags = []
    reasoning = "Regelbasierte Analyse."

    if features.get("fake_trigger_hits", 0) >= 2:
        label = "likely_fake"
        confidence = 70
        red_flags.append("typische Fake-News-Schlüsselbegriffe")

    if features.get("emotion_hits", 0) >= 2:
        confidence = max(confidence, 65)
        red_flags.append("stark emotionalisierte Sprache")

    if features.get("uncertainty_hits", 0) >= 2:
        label = "uncertain"
        red_flags.append("vage oder spekulative Formulierungen")

    category = determine_category(label, features)

    result = {
        "label": label,
        "confidence": confidence,
        "category": category,
        "red_flags": red_flags,
        "reasoning_summary": reasoning,
        "suggested_counter_sources": DEFAULT_COUNTER_SOURCES,
        "title": title,
        "word_count": word_count,

        "excerpt": excerpt,
        "method": "rule-based",
        "llm_used": False,
        "llm_status": "not_called",
    }

        # ---------- Feed / Teaser Fallback (leichte Regelbasis) ----------
    if word_count < 50:
        label = "uncertain"
        confidence = 40
        red_flags = ["feed_only"]

    if features.get("fake_trigger_hits", 0) >= 1:
        label = "likely_fake"
        confidence = 55
        red_flags.append("reisserischer_titel")

    return {
        "label": label,
        "confidence": confidence,
        "category": "Feed / Teaser",
        "analysis_text": "Analyse basiert nur auf Titel/Teaser.",
        "red_flags": red_flags,
        "reasoning_summary": "Kein vollständiger Artikeltext vorhanden.",
        "suggested_counter_sources": DEFAULT_COUNTER_SOURCES,
        "title": title,
        "word_count": word_count,
        "excerpt": excerpt,
    }




    # ---------- Optionaler LLM-Call ----------
    prompt = build_prompt(title, url, text, features)
    llm_parsed, llm_status = await call_llm_gateway(prompt)

    if isinstance(llm_parsed, dict):
        result.update({
            "label": llm_parsed.get("label", result["label"]),
            "confidence": llm_parsed.get("confidence", result["confidence"]),
            "category": llm_parsed.get("category", result["category"]),
            "red_flags": llm_parsed.get("red_flags", result["red_flags"]),
            "reasoning_summary": llm_parsed.get(
            "reasoning_summary", result["reasoning_summary"]
            ),
            "suggested_counter_sources": llm_parsed.get(
            "suggested_counter_sources", result["suggested_counter_sources"]
            ),
            "method": "hybrid",
            "llm_used": True,
            "llm_status": "ok",
        })
    else:
        result["llm_status"] = llm_status

   



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

