from typing import Optional, List, Dict
from app.services.kundli_service import get_house_lord

# Simplified but reasonable chart-factor mapping per life topic.
TOPIC_CHART_FACTORS = {
    "career": {
        "house": 10, "planets": ["Saturn", "Sun"],
        "keywords": ["career", "job", "profession", "naukri", "business", "work", "kaam"],
        "search_bias": "career job profession 10th house Saturn Sun",
        "divisional_chart": "D10",
    },
    "marriage": {
        "house": 7, "planets": ["Venus", "Jupiter"],
        "keywords": ["marriage", "shaadi", "spouse", "wife", "husband", "partner", "relationship"],
        "search_bias": "marriage spouse 7th house Venus Jupiter Navamsa",
        "divisional_chart": "D9",
    },
    "health": {
        "house": 6, "planets": ["Saturn", "Mars"],
        "keywords": ["health", "sehat", "illness", "disease", "body"],
        "search_bias": "health disease 6th house Saturn Mars",
        "divisional_chart": None,
    },
    "finance": {
        "house": 2, "planets": ["Jupiter", "Venus"],
        "keywords": ["money", "finance", "paisa", "wealth", "income", "dhan"],
        "search_bias": "wealth money finance 2nd house 11th house Jupiter Venus",
        "divisional_chart": None,
    },
    "education": {
        "house": 5, "planets": ["Mercury", "Jupiter"],
        "keywords": ["education", "study", "padhai", "exam", "school", "college"],
        "search_bias": "education study 5th house Mercury Jupiter",
        "divisional_chart": "D24",
    },
}

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]
TOPIC_RELEVANT_BOOKS = {
    "career": [
        "Jyotish_AIFAS_Timing of events through Dasha and transit",
        "Timing of Events through Dasha and Transit",
        "Dasa Lord Transit _PVR Rao (1)",
        "Dasha-Transit (1)",
        "J_KP reader_5_transits",
        "Important Planetary Transits",
        "Gochar Vichar AIFAS (1)",
    ],
    "marriage": [
        "Timing of Marriage by Transits and Jaimini Astrology (2)",
        "Timing marriage",
        "Jupiter_Transits_paryaya",  # from Jyotish_2015_Parthasarathy_Vinukonda_Jupiter_Transits_paryaya
    ],
    "health": [
        "Cancer timing Through Transits_S.Rath (1)",
    ],
    "finance": [
        "Dasa Lord Transit _PVR Rao (1)",
        "Transit Conjunctions on Natal Points_PVR Rao (2)",
    ],
    "education": [
        "Jyotish_AIFAS_Timing of events through Dasha and transit",
        "Stars_Days_&_Transit_In_Vedic_Astrology",  # from Jyotish_2017_S_P_Bhagat
    ],
    "timing_general": [
        "Transit short cuts",
        "Transit Short-Cuts_A Practical Tool_Bepin Behari (2)",
        "Importance of TRANSIT Astrology",
        "Microscopy_of_Transiting_Planets",  # matches all 4 Baldev_Bhatia volumes
        "Celestial_Transits_Or_Grah_Gochar",  # Jyotish_2024_Madhusudan_Dusi
        "Transit of Nakshatra Dasa Lord",
        "Transit of Rahu-Ketu & the Fortunes",
        "Saturn transit in Square houses",
        "Stationary Planets in Transit",
        "Tertiary Progression And Trigger Transits",
    ],
}
NATURAL_BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
NATURAL_MALEFICS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}

KENDRA_TRIKONA_HOUSES = {1, 4, 5, 7, 9, 10, 11}   # strong/supportive houses
DUSTHANA_HOUSES = {6, 8, 12}                       # weak/challenging houses

def classify_topic(message: str) -> Optional[str]:
    """Simple keyword-based topic classifier."""
    text_lower = message.lower()
    for topic, config in TOPIC_CHART_FACTORS.items():
        for kw in config["keywords"]:
            if kw in text_lower:
                return topic
    return None


def get_house_for_sign(sign_name: str, ascendant_sign: str) -> Optional[int]:
    """House 1 = ascendant's own sign; houses count forward from there."""
    try:
        asc_idx = ZODIAC_SIGNS.index(ascendant_sign)
        sign_idx = ZODIAC_SIGNS.index(sign_name)
        return ((sign_idx - asc_idx) % 12) + 1
    except ValueError:
        return None


def get_sign_for_house(house_number: int, ascendant_sign: str) -> Optional[str]:
    """Inverse — which sign occupies a given house number."""
    try:
        asc_idx = ZODIAC_SIGNS.index(ascendant_sign)
        return ZODIAC_SIGNS[(asc_idx + house_number - 1) % 12]
    except ValueError:
        return None


def build_topic_emphasis(topic: str, planets: List[dict], ascendant_sign: str, dasha_info: Optional[dict]) -> str:
    """Build a short, explicit 'pay attention to these facts' block for the
    prompt — includes house, house LORD, significator planets, and timing."""
    config = TOPIC_CHART_FACTORS.get(topic)
    if not config:
        return ""

    lines = [f"--- Key factors for this {topic} question ---"]

    house_num = config["house"]
    house_sign = get_sign_for_house(house_num, ascendant_sign)
    house_lord_name = get_house_lord(house_num, ascendant_sign)

    if house_sign:
        lord_str = f", ruled by {house_lord_name}" if house_lord_name else ""
        lines.append(f"{house_num}th House (governs {topic}): occupied by {house_sign}{lord_str}")

    if house_lord_name:
        lord_match = next((p for p in planets if p.get("name") == house_lord_name), None)
        if lord_match:
            lord_sign = lord_match.get("sign_name", "")
            lord_house = get_house_for_sign(lord_sign, ascendant_sign)
            lord_house_str = f", in the {lord_house}th house" if lord_house else ""
            lines.append(f"{house_lord_name} ({house_num}th Lord): placed in {lord_sign}{lord_house_str}")

    for planet_name in config["planets"]:
        match = next((p for p in planets if p.get("name") == planet_name), None)
        if match:
            sign = match.get("sign_name", "")
            house = get_house_for_sign(sign, ascendant_sign)
            house_str = f", in the {house}th house" if house else ""
            retro = " (retrograde)" if str(match.get("isRetro", "")).lower() == "true" else ""
            lines.append(f"{planet_name} (significator for {topic}): in {sign}{house_str}{retro}")

    if dasha_info:
        maha = dasha_info.get("current_mahadasha", {})
        antar = dasha_info.get("current_antardasha", {})
        if maha:
            timing_line = f"Current timing relevant to {topic}: Mahadasha={maha.get('lord')}"
            if antar:
                timing_line += f", Antardasha={antar.get('lord')}"
            lines.append(timing_line)

    return "\n".join(lines) if len(lines) > 1 else ""


def get_search_bias(topic: Optional[str]) -> str:
    """Extra search terms to append to the RAG query for topic-targeted book retrieval."""
    if not topic:
        return ""
    return TOPIC_CHART_FACTORS.get(topic, {}).get("search_bias", "")


def build_explanation_footer(topic: Optional[str], ascendant_sign: Optional[str], dasha_info: Optional[dict], language: str = "Hinglish") -> str:
    """Build a short, honest footer listing the real factors that grounded
    this response. Every item here is something actually fed to the LLM."""
    if not topic and not dasha_info:
        return ""

    factors = []

    config = TOPIC_CHART_FACTORS.get(topic) if topic else None
    if config and ascendant_sign:
        house_num = config["house"]
        house_lord = get_house_lord(house_num, ascendant_sign)
        if house_lord:
            factors.append(f"{house_num}th House ({house_lord})")
        else:
            factors.append(f"{house_num}th House")
        for planet in config["planets"]:
            factors.append(planet)

    if dasha_info:
        maha = dasha_info.get("current_mahadasha", {})
        antar = dasha_info.get("current_antardasha", {})
        if maha:
            dasha_str = maha.get("lord", "")
            if antar:
                dasha_str += f"–{antar.get('lord', '')}"
            dasha_str += " Dasha"
            factors.append(dasha_str)

    if not factors:
        return ""

    seen = set()
    unique_factors = []
    for f in factors:
        if f not in seen:
            seen.add(f)
            unique_factors.append(f)

    factors_str = ", ".join(unique_factors)

    labels = {
        "English": f"\n\n📍 Based on: {factors_str}",
        "Hindi": f"\n\n📍 आधारित: {factors_str}",
        "Hinglish": f"\n\n📍 Based on: {factors_str}",
    }
    return labels.get(language, labels["Hinglish"])



def _score_dasha_signal(dasha_info: Optional[dict]) -> int:
    """+1 if current Dasha lord(s) are naturally benefic, -1 if malefic, 0 if mixed/unknown."""
    if not dasha_info:
        return 0
    maha_lord = dasha_info.get("current_mahadasha", {}).get("lord")
    antar_lord = dasha_info.get("current_antardasha", {}).get("lord")

    score = 0
    for lord in [maha_lord, antar_lord]:
        if not lord:
            continue
        if lord in NATURAL_BENEFICS:
            score += 1
        elif lord in NATURAL_MALEFICS:
            score -= 1
    # Clamp to -1/0/+1 so Mahadasha+Antardasha don't just double-count the same direction
    return (score > 0) - (score < 0)


def _score_chart_signal(topic: str, planets: List[dict], ascendant_sign: str) -> int:
    """+1 if topic's house lord / significators are well-placed, -1 if in dusthana or retrograde, 0 if mixed."""
    config = TOPIC_CHART_FACTORS.get(topic)
    if not config:
        return 0

    house_num = config["house"]
    house_lord_name = get_house_lord(house_num, ascendant_sign)

    score = 0
    checked = 0

    candidates = [house_lord_name] + config["planets"]
    seen = set()
    for planet_name in candidates:
        if not planet_name or planet_name in seen:
            continue
        seen.add(planet_name)
        match = next((p for p in planets if p.get("name") == planet_name), None)
        if not match:
            continue

        sign = match.get("sign_name", "")
        placed_house = get_house_for_sign(sign, ascendant_sign)
        is_retro = str(match.get("isRetro", "")).lower() == "true"

        checked += 1
        if placed_house in DUSTHANA_HOUSES or is_retro:
            score -= 1
        elif placed_house in KENDRA_TRIKONA_HOUSES:
            score += 1

    if checked == 0:
        return 0
    return (score > 0) - (score < 0)


def build_consistency_check(topic: Optional[str], planets: List[dict], ascendant_sign: Optional[str],
                             dasha_info: Optional[dict]) -> Optional[dict]:
    """Compare Dasha timing vs. chart placement for this topic. Returns None
    if there isn't enough data to check (no topic, no chart, etc.)."""
    if not topic or not planets or not ascendant_sign:
        return None

    dasha_score = _score_dasha_signal(dasha_info)
    chart_score = _score_chart_signal(topic, planets, ascendant_sign)

    if dasha_score == 0 and chart_score == 0:
        return None  # not enough signal either way to say anything meaningful

    if dasha_score > 0 and chart_score > 0:
        alignment = "aligned_positive"
    elif dasha_score < 0 and chart_score < 0:
        alignment = "aligned_negative"
    elif (dasha_score > 0 and chart_score < 0) or (dasha_score < 0 and chart_score > 0):
        alignment = "mixed"
    else:
        alignment = "leaning"  # one signal neutral, other has a direction

    return {
        "alignment": alignment,
        "dasha_score": dasha_score,
        "chart_score": chart_score,
    }


def build_consistency_note(check: Optional[dict], topic: Optional[str]) -> str:
    """Turn the consistency check result into an explicit instruction block
    for the LLM prompt — this is what actually changes the model's behavior."""
    if not check or not topic:
        return ""

    alignment = check["alignment"]

    if alignment == "aligned_positive":
        return (f"Signal check for {topic}: Dasha timing AND chart placement both point favorably. "
                f"You may speak with full confidence — the signals agree.")
    if alignment == "aligned_negative":
        return (f"Signal check for {topic}: Dasha timing AND chart placement both indicate challenges. "
                f"Speak honestly about the difficulty, still with a constructive/encouraging tone — don't manufacture false optimism.")
    if alignment == "mixed":
        return (f"Signal check for {topic}: Dasha timing and chart placement point in DIFFERENT directions "
                f"(one supportive, one challenging). Do NOT force a single confident verdict — acknowledge both "
                f"sides honestly in your own natural voice, e.g. 'is supported by X but a bit delayed by Y'. "
                f"This is genuine nuance in the chart, not uncertainty on your part.")
    # "leaning"
    return (f"Signal check for {topic}: One signal (Dasha or chart) leans positive/negative, the other is neutral. "
            f"You may lean toward that direction but keep slightly softer certainty than a fully aligned reading.")
    
    # ---------------------------------------------------------------------------
# Explainable AI — Step-by-Step Reasoning Trace
# ---------------------------------------------------------------------------
def build_reasoning_trace(
    topic: Optional[str],
    ascendant_sign: Optional[str],
    planets: List[dict],
    dasha_info: Optional[dict],
    consistency_check: Optional[dict],
    rag_sources: Optional[List[str]] = None,
) -> List[dict]:
    """Assemble a numbered, inspectable reasoning chain from data already
    computed elsewhere in the pipeline. Each step is {step, title, detail} —
    purely structural, no LLM call, so it's fast and 100% traceable to real
    inputs rather than an LLM's self-report of its own reasoning."""
    if not topic or not ascendant_sign:
        return []

    steps = []
    step_num = 1

    # Step 1 — current timing
    if dasha_info:
        maha = dasha_info.get("current_mahadasha", {})
        antar = dasha_info.get("current_antardasha", {})
        detail = f"Mahadasha: {maha.get('lord', 'Unknown')}"
        if antar:
            detail += f", Antardasha: {antar.get('lord', 'Unknown')}"
        steps.append({"step": step_num, "title": "Current Dasha Period", "detail": detail})
        step_num += 1

    # Step 2 — relevant house
    config = TOPIC_CHART_FACTORS.get(topic, {})
    house_num = config.get("house")
    if house_num:
        house_sign = get_sign_for_house(house_num, ascendant_sign)
        house_lord = get_house_lord(house_num, ascendant_sign)
        detail = f"{house_num}th House governs {topic}"
        if house_sign:
            detail += f" — occupied by {house_sign}"
        if house_lord:
            detail += f", ruled by {house_lord}"
        steps.append({"step": step_num, "title": f"Relevant House ({house_num}th)", "detail": detail})
        step_num += 1

    # Step 3 — significator planets and their placement
    sig_planets = config.get("planets", [])
    if sig_planets and planets:
        placements = []
        for pname in sig_planets:
            match = next((p for p in planets if p.get("name") == pname), None)
            if match:
                sign = match.get("sign_name", "")
                house = get_house_for_sign(sign, ascendant_sign)
                retro = " (retrograde)" if str(match.get("isRetro", "")).lower() == "true" else ""
                placements.append(f"{pname} in {sign} ({house}th house){retro}")
        if placements:
            steps.append({
                "step": step_num, "title": "Significator Planets",
                "detail": "; ".join(placements)
            })
            step_num += 1

    # Step 4 — divisional chart used
    div_chart = config.get("divisional_chart")
    if div_chart:
        purpose_map = {"D9": "marriage", "D10": "career", "D24": "education", "D7": "children"}
        steps.append({
            "step": step_num, "title": "Divisional Chart Consulted",
            "detail": f"{div_chart} chart (used specifically for {purpose_map.get(div_chart, topic)} analysis)"
        })
        step_num += 1

    # Step 5 — consistency/signal check
    if consistency_check:
        alignment = consistency_check.get("alignment")
        alignment_labels = {
            "aligned_positive": "Dasha timing and chart placement both support a favorable reading",
            "aligned_negative": "Dasha timing and chart placement both indicate challenges",
            "mixed": "Dasha timing and chart placement point in different directions — genuine mixed signals",
            "leaning": "One signal (Dasha or chart) leans in a direction, the other is neutral",
        }
        steps.append({
            "step": step_num, "title": "Signal Consistency Check",
            "detail": alignment_labels.get(alignment, "Signals evaluated")
        })
        step_num += 1

    # Step 6 — classical sources referenced
    if rag_sources:
        unique_sources = list(dict.fromkeys(rag_sources))[:3]  # dedupe, cap at 3
        steps.append({
            "step": step_num, "title": "Classical References Consulted",
            "detail": ", ".join(unique_sources)
        })
        step_num += 1

    return steps


def format_reasoning_trace_text(steps: List[dict], language: str = "Hinglish") -> str:
    """Render the trace as readable text for display (not for the LLM prompt —
    this is shown directly in the UI when the user clicks 'Explain this')."""
    if not steps:
        labels = {
            "English": "No detailed reasoning trace available for this response.",
            "Hindi": "इस उत्तर के लिए विस्तृत तर्क उपलब्ध नहीं है।",
            "Hinglish": "Is jawab ke liye detailed reasoning available nahi hai.",
        }
        return labels.get(language, labels["Hinglish"])

    lines = []
    for s in steps:
        lines.append(f"{s['step']}. {s['title']}\n   {s['detail']}")
    return "\n\n".join(lines)

def rank_favorable_periods(upcoming_periods: List[dict], topic: str, top_n: int = 3) -> List[dict]:
    """Ranks upcoming Antardasha periods by how many of the topic's
    significator planets are involved (Mahadasha lord + Antardasha lord).
    A period where BOTH lords are significators for this topic ranks
    highest — e.g. Venus Mahadasha + Jupiter Antardasha for a marriage
    question, since both are marriage significators."""
    config = TOPIC_CHART_FACTORS.get(topic)
    if not config or not upcoming_periods:
        return []

    significators = set(config["planets"])
    scored = []
    for period in upcoming_periods:
        score = 0
        if period.get("mahadasha") in significators:
            score += 2  # Mahadasha match weighted higher — it's the dominant influence
        if period.get("antardasha") in significators:
            score += 1
        if score > 0:
            scored.append({**period, "favorability_score": score})

    scored.sort(key=lambda p: p["favorability_score"], reverse=True)
    return scored[:top_n]


def format_dasha_timeline_for_prompt(upcoming_periods: List[dict], favorable_periods: List[dict], language: str = "Hinglish") -> str:
    """Formats the upcoming dasha timeline + ranked favorable periods into
    short plain text for the LLM prompt — not raw JSON."""
    if not upcoming_periods:
        return ""

    lines = ["Upcoming Dasha Periods (next few years):"]
    for p in upcoming_periods[:8]:  # cap to keep prompt size reasonable
        maha = p.get("mahadasha", "")
        antar = p.get("antardasha", "")
        start = p.get("start", "").split(" ")[0]  # date only, drop time
        end = p.get("end", "").split(" ")[0]
        lines.append(f"- {maha} Mahadasha / {antar} Antardasha: {start} to {end}")

    if favorable_periods:
        lines.append("\nMost favorable upcoming periods for this topic:")
        for p in favorable_periods:
            maha = p.get("mahadasha", "")
            antar = p.get("antardasha", "")
            start = p.get("start", "").split(" ")[0]
            lines.append(f"- {maha}/{antar}: starting {start} (strong match for this question)")

    return "\n".join(lines)