from datetime import date
from typing import Optional
from app.services.llm_service import llm_service
from app.utils.logger import logger

MOON_SIGN_COLORS = {
    "Aries": "Red", "Taurus": "Green", "Gemini": "Yellow",
    "Cancer": "White", "Leo": "Gold", "Virgo": "Emerald Green",
    "Libra": "Sky Blue", "Scorpio": "Maroon", "Sagittarius": "Purple",
    "Capricorn": "Navy Blue", "Aquarius": "Turquoise", "Pisces": "Sea Green",
}

DAILY_PREDICTION_PROMPT = """You are a warm, experienced Indian Vedic Astrologer writing a short daily
reflection for a client, based on their birth chart.

Rules:
1. Respond in {language}.
2. Length: 2-3 short sentences, max 50 words. WhatsApp-style, warm and encouraging.
3. Frame this as general daily guidance rooted in their natal chart, NOT a precise transit calculation.
4. Do NOT mention specific times, hours, or numeric scores.
5. Do NOT reference any technical process.

Birth Chart Summary:
{kundli_summary}

Today's Date: {today}

Write today's short reflection:
"""

def get_lucky_color(moon_sign: Optional[str]) -> str:
    if not moon_sign:
        return "Not available"
    return MOON_SIGN_COLORS.get(moon_sign, "Not available")

def generate_daily_prediction(kundli_summary: str, language: str) -> Optional[str]:
    """Returns the generated prediction, or None if generation failed —
    callers should NOT cache a None result, so a transient Ollama failure
    doesn't lock in a generic fallback for the rest of the day."""
    try:
        prompt = DAILY_PREDICTION_PROMPT.format(
            language=language,
            kundli_summary=kundli_summary or "No chart data available.",
            today=date.today().strftime("%d %B %Y"),
        )
        result = llm_service.generate(prompt=prompt, temperature=0.7).strip()
        if not result:
            logger.warning("Daily prediction generation returned empty response")
            return None
        return result
    except Exception as e:
        logger.error(f"Daily prediction generation failed: {e}")
        return None