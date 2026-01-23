import os
import httpx
from typing import Optional, Dict, Any, Tuple

LLM_ENABLED = os.getenv("LLM_ENABLED", "false").lower() == "true"
LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL")
LLM_TIMEOUT = httpx.Timeout(60.0)

async def call_llm_gateway(prompt: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Returns: (parsed_result_or_None, status_message)
    """
    if not LLM_ENABLED:
        return None, "llm_disabled"

    if not LLM_GATEWAY_URL:
        return None, "llm_url_missing"

    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            r = await client.post(
                f"{LLM_GATEWAY_URL}/classify",
                json={"text": prompt}
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return None, f"llm_unreachable: {type(e).__name__}"

    parsed = data.get("parsed")
    if isinstance(parsed, dict):
        return parsed, "llm_ok"

    return None, "llm_no_parseable_output"
