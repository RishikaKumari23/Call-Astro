"""
Event Timing Engine — generic, topic-pluggable hierarchical Dasha-window
search. The engine itself is topic-agnostic; each topic supplies its own
candidate-planet hierarchy and match-mode via TOPIC_RULES below.

STILL UNCONFIRMED (do not present these as final until your professor
confirms them):
  - Whether Mahadasha+Antardasha BOTH need to be candidates ("and") or
    EITHER is sufficient ("or"). Defaulting to "and" per his quoted wording,
    but this is a guess pending his explicit answer.
  - What exactly makes a found window "valid" (currently: any window found
    counts as valid — no additional filter applied yet).
  - Early/late marriage bias weighting — not implemented.
  - Career hierarchy — explicitly a placeholder, not his rules.

TRANSIT LAYER NOT IMPLEMENTED: no live transit data source confirmed.
Windows returned here are Dasha-based candidates only, not final predictions.
"""
from typing import List, Dict, Optional, Callable
from app.services.kundli_service import get_house_lord
from app.services.topic_service import get_house_for_sign
from app.services.aspect_service import get_planets_aspecting_house
from app.utils.logger import logger


# ---------------------------------------------------------------------------
# Per-topic candidate-planet hierarchy builders.
# Each returns a list of levels, tried in order. Each level is a dict:
#   {"level": int, "label": str, "planets": set}
# ---------------------------------------------------------------------------

def _get_marriage_candidate_levels(planets: List[dict], ascendant_sign: str) -> List[Dict]:
    """CONFIRMED hierarchy (per professor, marriage only):
    Level 1: 7th lord, Venus (significator), 7th occupants, 7th aspects
    Level 2 (fallback): 1st lord
    Level 3 (fallback): 9th lord
    """
    lord_7 = get_house_lord(7, ascendant_sign)
    occupants_7 = [p.get("name") for p in planets if get_house_for_sign(p.get("sign_name", ""), ascendant_sign) == 7]
    aspects_7 = get_planets_aspecting_house(7, planets, ascendant_sign)

    level1 = set(filter(None, [lord_7, "Venus"] + occupants_7 + aspects_7))
    level2 = set(filter(None, [get_house_lord(1, ascendant_sign)]))
    level3 = set(filter(None, [get_house_lord(9, ascendant_sign)]))

    return [
        {"level": 1, "label": "7th house factors (lord, significator, occupants, aspects)", "planets": level1},
        {"level": 2, "label": "1st house lord (fallback)", "planets": level2 - level1},
        {"level": 3, "label": "9th house lord (fallback)", "planets": level3 - level1 - level2},
    ]


def _get_career_candidate_levels(planets: List[dict], ascendant_sign: str) -> List[Dict]:
    """PLACEHOLDER — NOT confirmed by professor. Analogous structure to the
    marriage hierarchy, our own reasonable guess only. Ask him for the real
    career rules before treating any output from this as final:
      - which house lord/significator comes first
      - what fallback factors apply
      - what counts as a valid career Dasha window
    """
    lord_10 = get_house_lord(10, ascendant_sign)
    occupants_10 = [p.get("name") for p in planets if get_house_for_sign(p.get("sign_name", ""), ascendant_sign) == 10]
    aspects_10 = get_planets_aspecting_house(10, planets, ascendant_sign)

    level1 = set(filter(None, [lord_10, "Saturn", "Sun"] + occupants_10 + aspects_10))
    level2 = set(filter(None, [get_house_lord(6, ascendant_sign)]))
    level3 = set(filter(None, [get_house_lord(11, ascendant_sign)]))

    return [
        {"level": 1, "label": "10th house factors (lord, significators, occupants, aspects) — UNCONFIRMED", "planets": level1},
        {"level": 2, "label": "6th house lord (fallback) — UNCONFIRMED", "planets": level2 - level1},
        {"level": 3, "label": "11th house lord (fallback) — UNCONFIRMED", "planets": level3 - level1 - level2},
    ]


# ---------------------------------------------------------------------------
# Per-topic configuration — this is the pluggable registry. Adding a new
# topic (education, finance, etc.) means adding one entry here, once you
# have confirmed rules for it — nothing else in the engine changes.
# ---------------------------------------------------------------------------

TOPIC_RULES: Dict[str, Dict] = {
    "marriage": {
        "candidate_builder": _get_marriage_candidate_levels,
        "match_mode": "and",  # UNCONFIRMED — see module docstring. "and" = stricter guess.
        "confirmed": True,
    },
    "career": {
        "candidate_builder": _get_career_candidate_levels,
        "match_mode": "and",
        "confirmed": False,  # placeholder rules — flag this in any output/UI
    },
}


def get_candidate_levels(topic: str, planets: List[dict], ascendant_sign: str) -> List[Dict]:
    rule = TOPIC_RULES.get(topic)
    if not rule:
        return []
    return rule["candidate_builder"](planets, ascendant_sign)


def _is_topic_confirmed(topic: str) -> bool:
    rule = TOPIC_RULES.get(topic)
    return bool(rule and rule.get("confirmed"))


def _get_match_mode(topic: str) -> str:
    rule = TOPIC_RULES.get(topic)
    return rule.get("match_mode", "and") if rule else "and"


# ---------------------------------------------------------------------------
# Dasha window search
# ---------------------------------------------------------------------------

def find_dasha_windows(candidate_planets: set, flattened_periods: List[Dict], match_mode: str = "and") -> List[Dict]:
    """
    match_mode="and": BOTH Mahadasha and Antardasha lords must be in the
      candidate set for a period to count as a window. This is the current
      best guess of the professor's rule ("इसमें ही महाराशा होनी चाहिए,
      इसी लिस्ट में ही अंतर दशा होनी चाहिए") — CONFIRM WITH HIM.
    match_mode="or": either lord being a candidate is sufficient (looser,
      original behavior — kept available in case "and" is confirmed wrong).
    """
    windows = []
    for period in flattened_periods:
        maha = period.get("mahadasha")
        antar = period.get("antardasha")

        if match_mode == "and":
            if maha in candidate_planets and antar in candidate_planets:
                windows.append({**period, "match_score": 3})  # both matched — strongest signal
        else:  # "or"
            score = 0
            if maha in candidate_planets:
                score += 2
            if antar in candidate_planets:
                score += 1
            if score > 0:
                windows.append({**period, "match_score": score})

    windows.sort(key=lambda w: w["match_score"], reverse=True)
    return windows


def _filter_valid_windows(windows: List[Dict], topic: str) -> List[Dict]:
    """Placeholder for the 'what makes a window VALID, not just found' rule
    your professor described. Currently a no-op (every found window is
    treated as valid) — this is the one-line change point once his exact
    validity rules are confirmed, without needing to restructure the
    hierarchy-search logic that calls this."""
    return windows


def find_candidate_windows(topic: str, planets: List[dict], ascendant_sign: str,
                             flattened_periods: List[Dict]) -> Dict:
    """
    Hierarchical search: tries Level 1 first. Only proceeds to Level 2/3 if
    Level 1 produces NO VALID windows (not just "no windows found" — those
    are now distinct checks, per the fix below).
    """
    levels = get_candidate_levels(topic, planets, ascendant_sign)
    if not levels:
        return {"windows": [], "level_used": None, "candidate_planets": [], "supported": False, "topic_confirmed": _is_topic_confirmed(topic)}

    match_mode = _get_match_mode(topic)

    for level_info in levels:
        candidates = level_info["planets"]
        if not candidates:
            continue

        found_windows = find_dasha_windows(candidates, flattened_periods, match_mode)
        valid_windows = _filter_valid_windows(found_windows, topic)

        if valid_windows:
            logger.info(
                f"Event timing: found {len(valid_windows)} valid window(s) at level "
                f"{level_info['level']} ({level_info['label']}) for candidates {candidates}, "
                f"match_mode={match_mode}"
            )
            return {
                "windows": valid_windows,
                "level_used": level_info["level"],
                "level_label": level_info["label"],
                "candidate_planets": list(candidates),
                "supported": True,
                "topic_confirmed": _is_topic_confirmed(topic),
            }

    logger.info(f"Event timing: no supported window found for topic '{topic}' at any hierarchy level")
    return {"windows": [], "level_used": None, "candidate_planets": [], "supported": False, "topic_confirmed": _is_topic_confirmed(topic)}


def format_event_timing_for_prompt(result: Dict, topic: str, language: str = "Hinglish") -> str:
    if not result.get("supported"):
        return (
            f"Event Timing Analysis for {topic}: No sufficiently supported Dasha "
            f"window was found using the standard hierarchy of chart factors for "
            f"this topic. If asked about specific timing, be honest that the "
            f"current period does not show a strong, specific indication — do NOT "
            f"invent a timeframe. You may still discuss general chart potential."
        )

    confirmation_note = "" if result.get("topic_confirmed") else " [NOTE: this topic's rule hierarchy is a placeholder, not yet confirmed against classical sources — treat with extra caution]"

    lines = [
        f"Event Timing Analysis for {topic} (based on {result['level_label']}, "
        f"candidate planets: {', '.join(result['candidate_planets'])}){confirmation_note}:"
    ]
    for w in result["windows"][:5]:
        start = w.get("start", "").split(" ")[0]
        end = w.get("end", "").split(" ")[0]
        lines.append(f"- {w.get('mahadasha')}/{w.get('antardasha')}: {start} to {end} (match strength: {w['match_score']})")

    lines.append(
        "These are candidate Dasha windows based on real chart factors and Dasha timing — "
        "NOT confirmed by planetary transits (transit data is not available). Present them "
        "as the strongest indicated periods, not as certainties."
    )
    return "\n".join(lines)