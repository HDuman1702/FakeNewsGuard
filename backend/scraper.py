import asyncio
import re
from dataclasses import dataclass
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from readability import Document


@dataclass
class ScrapedPage:
    url: str
    title: str
    text: str
    html: str


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Connection": "close",
}


def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


async def fetch_html(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"Ungültige URL: {url}")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "de-DE,de;q=0.9",
    }

    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=20
    ) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text



def extract_main_text(url: str, html: str) -> ScrapedPage:
    title = ""
    main_text = ""

    # 1) Readability
    try:
        doc = Document(html)
        title = (doc.short_title() or "").strip()
        summary_html = doc.summary()

        soup = BeautifulSoup(summary_html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        main_text = soup.get_text("\n", strip=True)
        main_text = _clean_text(main_text)
    except Exception:
        main_text = ""

    # 2) Fallback: body text
    if len(main_text.split()) < 50:
        soup_full = BeautifulSoup(html, "lxml")
        for tag in soup_full(["script", "style", "noscript", "header", 
                              "footer", "nav", "form", "aside"]):
            tag.decompose()

        body_text = soup_full.get_text("\n", strip=True)
        body_text = _clean_text(body_text)

        if len(body_text.split()) > len(main_text.split()):
            main_text = body_text

    # Title fallback
    if not title:
        try:
            soup_head = BeautifulSoup(html, "lxml")
            if soup_head.title and soup_head.title.string:
                title = soup_head.title.string.strip()
        except Exception:
            title = ""

    if not title:
        title = "Unbekannter Titel"

    return ScrapedPage(url=url, title=title, text=main_text, html=html)

def extract_article(html: str, url: str):
    soup = BeautifulSoup(html, "html.parser")

    # -------------------------
    # 1. Störende Layout-Elemente entfernen
    # -------------------------
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    # -------------------------
    # 2. Titel-Extraktion (Prioritäten!)
    # -------------------------
    title = ""

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    else:
        twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
        if twitter_title and twitter_title.get("content"):
            title = twitter_title["content"].strip()
        else:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)
            elif soup.title:
                title = soup.title.get_text(strip=True)

    # -------------------------
    # 3. Text-Extraktion (Artikel bevorzugen)
    # -------------------------
    article_tag = soup.find("article")

    if article_tag:
        text = article_tag.get_text(" ", strip=True)
    else:
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = " ".join(paragraphs)

    # Whitespace normalisieren
    text = re.sub(r"\s+", " ", text).strip()

    # -------------------------
    # 4. Fallback: Meta-Description
    # -------------------------
    if len(text.split()) < 40:
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            text = meta_desc["content"].strip()

    # -------------------------
    # 5. Excerpt erzeugen
    # -------------------------
    excerpt = text[:300]

    return title, text, excerpt

   

