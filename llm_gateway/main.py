import json
import os
import re
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="FakeNewsGuard LLM Gateway", version="0.3.0")

LLM_MODE = (os.environ.get("LLM_MODE") or "ollama").lower()
LLM_BASE_URL = (os.environ.get("LLM_BASE_URL") or "http://10.10.10.201:11434").rstrip("/")
LLM_MODEL = os.environ.get("LLM_MODEL") or "llama3"

HTTP_TIMEOUT = httpx.Timeout(300.0, connect=20.0, read=300.0, write=60.0)

SYSTEM_PROMPT = """Du bist FakeNewsGuard, ein Tool zur Einschätzung von Desinformation.

Du bekommst:
1) FEATURES (messbar, regelbasiert, NICHT interpretieren als Wahrheit, sondern als Hinweise)
2) META (Titel, URL)
3) TEXT (Artikeltext oder Kurztext)

WICHTIG: Fake News vs. Satire vs. Meinung
- Satire (z.B. Postillon) ist KEINE Fake News. Sie ist absichtlich erfunden und humoristisch.
- Meinung ist KEINE Fake News, kann aber irreführend sein.
- Fake News sind grob irreführende oder falsche Tatsachenbehauptungen, oft ohne belastbare Quellen.

REGELN FÜR DEIN URTEIL:
- Wenn word_count < 150 oder has_enough_text=false:
  -> label MUSS "uncertain" sein und confidence <= 60.
  -> Begründe: Text zu kurz / nur Teaser / zu wenig Kontext.
- Wenn source_type = "satire":
  -> label sollte i.d.R. "likely_real" oder "uncertain" sein (aber NICHT "likely_fake"),
     und red_flags sollte "satire" enthalten.
- Nutze fake_trigger_hits, uncertainty_hits, emotion_hits als Stil-Indikatoren,
  aber entscheide NICHT allein aufgrund dieser Zahlen.

Gib ausschließlich gültiges JSON zurück, ohne Markdown, ohne Text davor oder danach.

Schema:
{
  "label": "likely_fake" | "uncertain" | "likely_real",
  "confidence": 0-100,
  "red_flags": [string, ...],
  "claims": [],
  "reasoning_summary": string,
  "suggested_counter_sources": [string, ...]
}

WICHTIG:
- Wenn FAKE_SIGNAL_SCORE >= 10 UND der Text konkrete Tatsachenbehauptungen enthält,
  darf und soll "likely_fake" verwendet werden.
- Begründe die Entscheidung anhand der FEATURES.
- Verwende "uncertain" nur, wenn die Hinweise widersprüchlich sind.


ENTSCHEIDUNGSREGELN:
- Wenn Verschwörungstheorie, Falschmeldung oder Propaganda dominant sind
  UND der Text Tatsachenbehauptungen enthält → likely_fake
- Wenn Satire / Parodie dominiert → likely_real + red_flag "satire"
- Wenn Clickbait oder Irreführend dominiert → uncertain
- Seriöse Nachricht → likely_real

ANTWORTE AUSSCHLIESSLICH MIT GÜLTIGEM JSON.
KEIN TEXT, KEINE ERKLÄRUNG, KEIN MARKDOWN.

"""


class LLMRequest(BaseModel):
    text: str


class LLMResponse(BaseModel):
    raw: str
    parsed: Optional[Dict[str, Any]] = None


def _extract_json_from_text(s: str) -> Optional[Dict[str, Any]]:
    s = (s or "").strip()
    if not s:
        return None

    # fenced ```json {...} ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, flags=re.DOTALL | re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # Strip fences if whole response is fenced
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()

    # direct json
    if s.startswith("{") and s.endswith("}"):
        try:
            return json.loads(s)
        except Exception:
            return None

    # fallback: first {...}
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = s[start : end + 1]
        try:
            return json.loads(snippet)
        except Exception:
            return None

    return None


async def _call_ollama(text: str) -> str:
    url = f"{LLM_BASE_URL}/api/generate"
    payload = {
    "model": LLM_MODEL,
    "prompt": f"{SYSTEM_PROMPT}\n\nANTWORT NUR ALS JSON!\n\n{text}",
    "stream": False,
    "options": {
        "temperature": 0.2,
        "num_predict": 300,
    },
}

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        return (data.get("response") or "").strip()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": LLM_MODE,
        "base_url": LLM_BASE_URL,
        "model": LLM_MODEL,
    }


@app.post("/classify", response_model=LLMResponse)
async def classify(req: LLMRequest):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text ist leer")

    try:
        if LLM_MODE != "ollama":
            raise HTTPException(status_code=400, detail="Nur LLM_MODE=ollama ist in diesem Prototyp aktiviert")
        raw = await _call_ollama(text)
    except httpx.HTTPStatusError as e:
        body = ""
        try:
            body = e.response.text[:500]
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"LLM HTTP {e.response.status_code}: {body}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {type(e).__name__}")

    parsed = _extract_json_from_text(raw)
    return LLMResponse(raw=raw, parsed=parsed)
