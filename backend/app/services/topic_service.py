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