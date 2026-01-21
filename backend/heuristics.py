import re
from urllib.parse import urlparse

CATEGORIES = [
    "Satire / Parodie",
    "Propaganda",
    "Clickbait",
    "Irreführende Inhalte",
    "Falschmeldung",
    "Manipulation",
    "Seriöse Nachricht",
]

SATIRE_DOMAINS = [
    "der-postillon.com",
    "theonion.com",
    "titanic-magazin.de",
]

FAKE_TRIGGERS = [
    "die wahrheit", "keiner sagt", "sie verschweigen",
    "100% wahr", "niemand berichtet", "geheim"
]

UNCERTAINTY_WORDS = [
    "angeblich", "vermutlich", "soll", "möglicherweise"
]

EMOTION_WORDS = [
    "schockierend", "skandal", "unfassbar", "krass"
]


def extract_features(text: str, url: str) -> dict:
    text_l = text.lower()
    domain = urlparse(url).netloc.replace("www.", "")

    return {
        "word_count": len(text.split()),
        "source_domain": domain,
        "is_satire_domain": domain in SATIRE_DOMAINS,
        "fake_trigger_hits": sum(text_l.count(w) for w in FAKE_TRIGGERS),
        "uncertainty_hits": sum(text_l.count(w) for w in UNCERTAINTY_WORDS),
        "emotion_hits": sum(text_l.count(w) for w in EMOTION_WORDS),
        "has_enough_text": len(text.split()) >= 150,
    }
