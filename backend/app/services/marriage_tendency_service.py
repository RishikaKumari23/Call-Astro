
from typing import List, Dict, Optional
from app.services.kundli_service import get_house_lord
from app.services.topic_service import get_house_for_sign
from app.utils.logger import logger

TENDENCY_CONFIRMED = False  # flip to True once professor's real rules are substituted


def classify_marriage_tendency(planets: List[dict], ascendant_sign: str) -> Dict:
    """
    Returns {"tendency": "early"|"normal"|"late", "confirmed": bool, "reasoning": str}

    PLACEHOLDER LOGIC (not confirmed):
    - 7th lord in houses 1, 5, 7, 9, 11 (kendra/trikona-ish, "strong" placement) → leans early
    - 7th lord in houses 6, 8, 12 (dusthana, "weak" placement) → leans late
    - Otherwise → normal
    This is a simplistic placeholder standing in for whatever real rule
    the professor specifies — do not treat this mapping as authoritative.
    """
    try:
        lord_7 = get_house_lord(7, ascendant_sign)
        if not lord_7:
            return {"tendency": "normal", "confirmed": TENDENCY_CONFIRMED, "reasoning": "Could not determine 7th lord — defaulting to normal."}

        lord_7_planet = next((p for p in planets if p.get("name") == lord_7), None)
        if not lord_7_planet:
            return {"tendency": "normal", "confirmed": TENDENCY_CONFIRMED, "reasoning": f"{lord_7} (7th lord) position not found — defaulting to normal."}

        lord_7_house = get_house_for_sign(lord_7_planet.get("sign_name", ""), ascendant_sign)
        if not lord_7_house:
            return {"tendency": "normal", "confirmed": TENDENCY_CONFIRMED, "reasoning": "Could not determine 7th lord's house — defaulting to normal."}

        EARLY_LEANING_HOUSES = {1, 5, 7, 9, 11}
        LATE_LEANING_HOUSES = {6, 8, 12}

        if lord_7_house in EARLY_LEANING_HOUSES:
            tendency = "early"
            reasoning = f"{lord_7} (7th lord) is in house {lord_7_house} — a placement leaning toward earlier timing (placeholder rule)."
        elif lord_7_house in LATE_LEANING_HOUSES:
            tendency = "late"
            reasoning = f"{lord_7} (7th lord) is in house {lord_7_house} — a placement leaning toward delayed timing (placeholder rule)."
        else:
            tendency = "normal"
            reasoning = f"{lord_7} (7th lord) is in house {lord_7_house} — a neutral placement (placeholder rule)."

        return {"tendency": tendency, "confirmed": TENDENCY_CONFIRMED, "reasoning": reasoning}
    except Exception as e:
        logger.error(f"Marriage tendency classification failed: {e}")
        return {"tendency": "normal", "confirmed": TENDENCY_CONFIRMED, "reasoning": "Classification error — defaulting to normal."}


def rank_windows_by_tendency(windows: List[Dict], tendency: str) -> List[Dict]:
    """Reorders candidate windows based on classified tendency —
    early tendency prioritizes chronologically-first windows, late
    tendency prioritizes chronologically-last windows, normal keeps
    the existing match-strength order (from find_dasha_windows)."""
    if tendency == "early":
        return sorted(windows, key=lambda w: w.get("start", ""))
    elif tendency == "late":
        return sorted(windows, key=lambda w: w.get("start", ""), reverse=True)
    else:
        return windows  # normal — keep match_score order as-is


def format_tendency_for_prompt(tendency_result: Dict) -> str:
    confirmation_note = "" if tendency_result.get("confirmed") else " [PLACEHOLDER rule — not yet confirmed against classical sources]"
    return (
        f"Marriage Tendency: {tendency_result['tendency'].upper()}{confirmation_note}. "
        f"{tendency_result['reasoning']}"
    )