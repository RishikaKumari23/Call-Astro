from typing import List, Dict, Optional
from app.services.topic_service import get_house_for_sign, get_sign_for_house

SPECIAL_ASPECTS = {
    "Mars": [4, 8],
    "Jupiter": [5, 9],
    "Saturn": [3, 10],
}


def get_planets_aspecting_house(target_house: int, planets: List[dict], ascendant_sign: str) -> List[str]:
    aspecting = []
    for p in planets:
        name = p.get("name")
        sign = p.get("sign_name", "")
        planet_house = get_house_for_sign(sign, ascendant_sign)
        if not planet_house:
            continue

        aspected_houses = [((planet_house + 7 - 1 - 1) % 12) + 1]
        if name in SPECIAL_ASPECTS:
            for offset in SPECIAL_ASPECTS[name]:
                aspected_houses.append(((planet_house + offset - 1 - 1) % 12) + 1)

        if target_house in aspected_houses:
            aspecting.append(name)

    return aspecting