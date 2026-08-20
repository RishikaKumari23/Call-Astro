import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Dict
from app.utils.logger import logger
from app.config.settings import settings

FUNCTION_URL = settings.KUNDLI_LAMBDA_URL

DASHA_SEQUENCE = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17
}
NAKSHATRA_LORDS = (
    ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"] * 3
)

SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

ZODIAC_SIGNS_ORDER = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]


def get_house_lord(house_number: int, ascendant_sign: str) -> Optional[str]:
    try:
        asc_idx = ZODIAC_SIGNS_ORDER.index(ascendant_sign)
        house_sign = ZODIAC_SIGNS_ORDER[(asc_idx + house_number - 1) % 12]
        return SIGN_LORDS.get(house_sign)
    except (ValueError, KeyError):
        return None


def _parse_dob_to_age(dob: Optional[str]) -> float:
    if not dob:
        return 0.0
    for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]:
        try:
            dt = datetime.strptime(dob.strip(), fmt)
            age_days = (datetime.now() - dt).days
            return max(0.0, age_days / 365.25)
        except Exception:
            continue
    return 0.0


def calculate_vimshottari_dasha(moon_degree: float, moon_star_lord: str, moon_pada: int, dob: Optional[str] = None) -> Optional[Dict]:
    try:
        NAKSHATRA_ARC = 360.0 / 27.0  # precise float — 13.3333...° per nakshatra

        nakshatra_num = int(moon_degree / NAKSHATRA_ARC) + 1
        nakshatra_lord = NAKSHATRA_LORDS[nakshatra_num - 1]

        if nakshatra_lord != moon_star_lord:
            logger.warning(f"Dasha lord mismatch: calculated {nakshatra_lord} vs API {moon_star_lord} — using API value")
            nakshatra_lord = moon_star_lord

        position_in_nakshatra = moon_degree % NAKSHATRA_ARC
        fraction_passed = position_in_nakshatra / NAKSHATRA_ARC

        start_lord_idx = DASHA_SEQUENCE.index(nakshatra_lord)
        start_dasha_years = DASHA_YEARS[nakshatra_lord]
        balance_years = start_dasha_years * (1 - fraction_passed)

        dasha_timeline = []
        current_year = 0.0
        # 18 periods = 2 full 120-year cycles to cover users of all ages without truncation
        for i in range(18):
            lord_idx = (start_lord_idx + i) % 9
            lord = DASHA_SEQUENCE[lord_idx]
            years = balance_years if i == 0 else DASHA_YEARS[lord]

            dasha_timeline.append({
                "lord": lord,
                "years": round(years, 2),
                "start_year": round(current_year, 2),
                "end_year": round(current_year + years, 2),
            })
            current_year += years

        age_years = _parse_dob_to_age(dob)
        current_maha = dasha_timeline[0]
        for maha in dasha_timeline:
            if maha["start_year"] <= age_years < maha["end_year"]:
                current_maha = maha
                break

        return {
            "birth_nakshatra": nakshatra_num,
            "nakshatra_lord": nakshatra_lord,
            "moon_pada": moon_pada,
            "balance_of_dasha_at_birth": round(balance_years, 2),
            "dasha_sequence": dasha_timeline,
            "current_mahadasha": current_maha,
            "age_years": age_years,
        }
    except Exception as e:
        logger.error(f"Dasha calculation failed: {e}")
        return None


def calculate_full_dasha_periods(moon_degree: float, moon_star_lord: str, moon_pada: int, dob: Optional[str] = None) -> Optional[Dict]:
    mahadasha_info = calculate_vimshottari_dasha(moon_degree, moon_star_lord, moon_pada, dob=dob)
    if not mahadasha_info:
        return None

    try:
        current_maha = mahadasha_info["current_mahadasha"]
        maha_lord = current_maha["lord"]
        maha_start_year = current_maha["start_year"]
        maha_total_years = DASHA_YEARS[maha_lord]
        maha_lord_idx = DASHA_SEQUENCE.index(maha_lord)
        age_years = mahadasha_info.get("age_years", 0.0)

        antardasha_sequence = []
        elapsed = maha_start_year
        current_antar = None

        for i in range(9):
            antar_lord_idx = (maha_lord_idx + i) % 9
            antar_lord = DASHA_SEQUENCE[antar_lord_idx]
            antar_years = (maha_total_years * DASHA_YEARS[antar_lord]) / 120
            antar_entry = {
                "lord": antar_lord,
                "years": round(antar_years, 3),
                "start_year": round(elapsed, 3),
                "end_year": round(elapsed + antar_years, 3),
            }
            antardasha_sequence.append(antar_entry)
            if elapsed <= age_years < (elapsed + antar_years):
                current_antar = antar_entry
            elapsed += antar_years

        if not current_antar and antardasha_sequence:
            current_antar = antardasha_sequence[0]

        mahadasha_info["antardasha_sequence"] = antardasha_sequence
        mahadasha_info["current_antardasha"] = current_antar

        antar_lord = current_antar["lord"]
        antar_total_years = (maha_total_years * DASHA_YEARS[antar_lord]) / 120
        antar_start_year = current_antar["start_year"]
        antar_lord_idx2 = DASHA_SEQUENCE.index(antar_lord)

        pratyantar_sequence = []
        elapsed2 = antar_start_year
        current_praty = None

        for i in range(9):
            praty_lord_idx = (antar_lord_idx2 + i) % 9
            praty_lord = DASHA_SEQUENCE[praty_lord_idx]
            praty_years = (antar_total_years * DASHA_YEARS[praty_lord]) / 120
            praty_entry = {
                "lord": praty_lord,
                "years": round(praty_years, 4),
                "start_year": round(elapsed2, 4),
                "end_year": round(elapsed2 + praty_years, 4),
            }
            pratyantar_sequence.append(praty_entry)
            if elapsed2 <= age_years < (elapsed2 + praty_years):
                current_praty = praty_entry
            elapsed2 += praty_years

        if not current_praty and pratyantar_sequence:
            current_praty = pratyantar_sequence[0]

        mahadasha_info["pratyantardasha_sequence"] = pratyantar_sequence
        mahadasha_info["current_pratyantardasha"] = current_praty

        return mahadasha_info
    except Exception as e:
        logger.error(f"Antardasha/Pratyantardasha calculation failed: {e}")
        return mahadasha_info


class KundliService:
    def fetch_kundli(self, name: str, date: str, time: str, latitude: float, longitude: float,
                      timezone_name: str = "Asia/Kolkata", language: str = "English",
                      max_retries: int = 2) -> Optional[Dict]:
        payload = {
            "requirements": ["KundliDetails", "AscendantPrediction"],
            "date": date, "time": time,
            "latitude": str(latitude), "longitude": str(longitude),
            "timezone_name": timezone_name, "language": language, "name": name,
        }
        req = urllib.request.Request(
            FUNCTION_URL, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )

        last_error = None
        for attempt in range(1, max_retries + 2):
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    response = json.loads(resp.read().decode("utf-8"))
                logger.info(f"Kundli data fetched successfully (attempt {attempt})")
                return response
            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8")
                logger.warning(f"Kundli fetch HTTP error {e.code} on attempt {attempt}: {error_body}")
                last_error = e
            except Exception as e:
                logger.warning(f"Kundli fetch failed on attempt {attempt}: {e}")
                last_error = e

        logger.error(f"Kundli fetch failed after {max_retries + 1} attempts: {last_error}")
        return None

    def get_ascendant_data(self, kundli_data: Dict) -> Optional[Dict]:
        """Extract the raw Ascendant planet object from planetary_positions —
        required as input for the separate Dasha Lambda's ascendant_data field
        ('Missing required parameters: ascendant_data' otherwise)."""
        try:
            for p in kundli_data.get("planetary_positions", []):
                if p.get("name") == "Ascendant":
                    return p
        except Exception as e:
            logger.error(f"Failed to extract ascendant_data: {e}")
        return None

    def _get_dasha_for_kundli(self, kundli_data: Dict, dob: Optional[str] = None) -> Optional[Dict]:
        try:
            moon_lord_data = kundli_data.get("planet_lords", {}).get("Moon", {})
            moon_degree = moon_lord_data.get("degree")
            moon_star_lord = moon_lord_data.get("star_lord")
            moon_pada = moon_lord_data.get("pada")

            if moon_degree is None or not moon_star_lord or moon_pada is None:
                logger.warning("Missing Moon degree/star_lord/pada — cannot calculate dasha")
                return None

            return calculate_full_dasha_periods(float(moon_degree), moon_star_lord, int(moon_pada), dob=dob)
        except Exception as e:
            logger.error(f"Failed to derive dasha inputs: {e}")
            return None

    def summarize_kundli(self, kundli_data: Dict, dob: Optional[str] = None, dasha_info: Optional[Dict] = None) -> str:
        try:
            lines = []
            positions = kundli_data.get("planetary_positions", [])

            ZODIAC = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
            NAKSHATRAS = [
                "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha",
                "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
                "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
            ]
            
            ascendant_sign = None
            moon_sign = None
            
            for p in positions:
                if p.get("name") == "Ascendant":
                    ascendant_sign = p.get("sign_name", "")
                    break
            
            asc_index = ZODIAC.index(ascendant_sign) if ascendant_sign in ZODIAC else 0

            planet_lords = kundli_data.get("planet_lords", {})

            planet_lines = []
            for p in positions:
                name = p.get("name", "Unknown")
                sign = p.get("sign_name", "")
                is_retro = str(p.get("isRetro", "")).lower() == "true"

                if name == "Ascendant":
                    continue
                if name == "Moon":
                    moon_sign = sign
                
                house_str = ""
                if sign in ZODIAC and ascendant_sign in ZODIAC:
                    sign_idx = ZODIAC.index(sign)
                    house_num = (sign_idx - asc_index + 12) % 12 + 1
                    def _ordinal(n):
                        return ("st" if n % 10 == 1 and n % 100 != 11
                                else "nd" if n % 10 == 2 and n % 100 != 12
                                else "rd" if n % 10 == 3 and n % 100 != 13
                                else "th")
                    house_str = f" ({house_num}{_ordinal(house_num)} House)"
                
                lord_data = planet_lords.get(name, {})
                star_lord = lord_data.get("star_lord")
                pada = lord_data.get("pada")
                degree = lord_data.get("degree")
                
                nak_name_str = ""
                if degree is not None:
                    try:
                        nak_idx = int(float(degree) / (360.0 / 27.0)) % 27
                        nak_name_str = f"{NAKSHATRAS[nak_idx]} Nakshatra, "
                    except Exception:
                        pass
                
                nak_str = f" [{nak_name_str}Nakshatra Lord: {star_lord}, Pada: {pada}]" if star_lord else ""

                retro_marker = " (retrograde)" if is_retro else ""
                planet_lines.append(f"{name} in {sign}{house_str}{nak_str}{retro_marker}")

            if ascendant_sign:
                lines.append(f"Ascendant (Lagna): {ascendant_sign}")
            if moon_sign:
                lines.append(f"Moon Sign (Rashi): {moon_sign}")
            if planet_lines:
                lines.append("Planetary positions: " + ", ".join(planet_lines))

            if ascendant_sign and ascendant_sign in ZODIAC:
                ZODIAC_LORDS = {
                    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
                    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
                    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"
                }
                house_rulerships = []
                for h in range(1, 13):
                    sign_idx = (asc_index + h - 1) % 12
                    sign_name = ZODIAC[sign_idx]
                    house_rulerships.append(f"{h}{_ordinal(h)} House ({sign_name}, ruled by {ZODIAC_LORDS[sign_name]})")
                lines.append("House Rulerships: " + ", ".join(house_rulerships))

            chart_positions = kundli_data.get("chart_planet_positions", {})
            d9 = chart_positions.get("D9", {}) if chart_positions else {}
            d9_asc = d9.get("Ascendant", {}).get("sign_name") if d9 else None
            if d9_asc:
                lines.append(f"Navamsa (D9) Ascendant: {d9_asc}")
            else:
                lines.append("Navamsa (D9) Ascendant: Not available in birth data")

            if not dasha_info:
                dasha_info = self._get_dasha_for_kundli(kundli_data)
            
            if dasha_info:
                maha = dasha_info["current_mahadasha"]
                antar = dasha_info.get("current_antardasha")
                praty = dasha_info.get("current_pratyantardasha")

                dasha_source = dasha_info.get("source", "calculated")
                dasha_label = "Real API" if dasha_source == "real_api" else "approximate, calculated"
                dasha_line = f"Current Dasha Period ({dasha_label}): Mahadasha={maha['lord']}"
                if antar:
                    dasha_line += f", Antardasha={antar['lord']}"
                if praty:
                    dasha_line += f", Pratyantardasha={praty['lord']}"
                lines.append(dasha_line)

                if "dasha_sequence" in dasha_info and len(dasha_info["dasha_sequence"]) > 1:
                    nxt = dasha_info["dasha_sequence"][1]
                    if dob:
                        try:
                            from datetime import datetime as _dt
                            birth_dt = None
                            for _fmt in ["%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]:
                                try:
                                    birth_dt = _dt.strptime(dob.strip(), _fmt)
                                    break
                                except ValueError:
                                    continue
                            if birth_dt:
                                approx_year = birth_dt.year + int(nxt["start_year"])
                                lines.append(f"Next Mahadasha: {nxt['lord']} (approx. begins around {approx_year})")
                        except (ValueError, TypeError):
                            pass

            ascendant_pred = kundli_data.get("ascendant_sign_prediction", "")
            if ascendant_pred:
                lines.append(f"Ascendant reading: {str(ascendant_pred)[:400]}")

            bhagyodaya = kundli_data.get("bhagyodaya", "")
            if bhagyodaya:
                lines.append(f"Prosperity period: {str(bhagyodaya)[:300]}")

            if not lines:
                logger.warning(f"summarize_kundli found nothing usable. Raw keys: {list(kundli_data.keys())}")
                return "No structured chart data available."
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Failed to summarize kundli data: {e}")
            return "No structured chart data available."

    def extract_chart_data(self, kundli_data: Dict) -> Optional[Dict]:
        if not kundli_data:
            return None
        try:
            positions = kundli_data.get("planetary_positions", [])
            planets = []
            ascendant_sign = None
            for p in positions:
                name = p.get("name", "Unknown")
                sign = p.get("sign_name", "")
                is_retro = "true" if str(p.get("isRetro", "")).lower() == "true" else "false"
                if name == "Ascendant":
                    ascendant_sign = sign
                    continue
                planets.append({"name": name, "sign_name": sign, "isRetro": is_retro})
            return {"planets": planets, "ascendant_sign": ascendant_sign}
        except Exception as e:
            logger.error(f"Failed to extract chart data: {e}")
            return None

    def extract_divisional_chart(self, kundli_data: Dict, chart_code: str) -> Optional[Dict]:
        try:
            chart_positions = kundli_data.get("chart_planet_positions", {})
            chart = chart_positions.get(chart_code)
            if not chart:
                return None

            ascendant_sign = chart.get("Ascendant", {}).get("sign_name")
            planets = {}
            for planet_name, planet_data in chart.items():
                if planet_name == "Ascendant":
                    continue
                planets[planet_name] = planet_data.get("sign_name")

            return {"ascendant_sign": ascendant_sign, "planets": planets}
        except Exception as e:
            logger.error(f"Failed to extract {chart_code} chart: {e}")
            return None

    def summarize_divisional_chart(self, kundli_data: Dict, chart_code: str, purpose: str) -> str:
        chart = self.extract_divisional_chart(kundli_data, chart_code)
        if not chart or not chart.get("ascendant_sign"):
            return f"{chart_code} Chart (for {purpose}): Data not available in current chart"

        lines = [f"{chart_code} Chart (for {purpose}): Ascendant is {chart['ascendant_sign']}"]
        planet_strs = [f"{name} in {sign}" for name, sign in chart.get("planets", {}).items() if sign]
        if planet_strs:
            lines.append(", ".join(planet_strs))
        return " — ".join(lines)

    def get_moon_sign(self, kundli_data: Dict) -> Optional[str]:
        try:
            for p in kundli_data.get("planetary_positions", []):
                if p.get("name") == "Moon":
                    return p.get("sign_name")
        except Exception as e:
            logger.error(f"Failed to extract moon sign: {e}")
        return None

    def get_full_chart_bundle(self, kundli_data: Dict) -> Dict:
        return {
            "summary": self.summarize_kundli(kundli_data),
            "chart": self.extract_chart_data(kundli_data),
            "dasha": self._get_dasha_for_kundli(kundli_data),
            "divisional": {
                "D9": self.extract_divisional_chart(kundli_data, "D9"),
                "D10": self.extract_divisional_chart(kundli_data, "D10"),
                "D24": self.extract_divisional_chart(kundli_data, "D24"),
            },
        }

    def get_real_or_calculated_dasha(self, kundli_data: Dict, dob: str, birth_time_24h: str,
                                       latitude: float, longitude: float) -> Optional[Dict]:
        """Try the REAL dasha API first (actual calendar dates, authoritative).
        Falls back to the hand-calculated Vimshottari math only if the real
        API is unavailable, misconfigured, or missing required data."""
        from app.services.dasha_api_service import dasha_api_service

        try:
            ascendant_data = self.get_ascendant_data(kundli_data)
            if not ascendant_data:
                logger.warning("No ascendant_data available — skipping real dasha API, using calculated fallback")
            elif dob:
                # dob is already DD-MM-YYYY — exactly what this Lambda's
                # dateOfBirth field expects. DO NOT convert to slashes here;
                # that was the bug that caused this to silently fail before.
                dasha_tree = dasha_api_service.fetch_dasha_tree(
                    date=dob, time=birth_time_24h,
                    latitude=latitude, longitude=longitude,
                    ascendant_data=ascendant_data,
                )
                if dasha_tree:
                    current_period = dasha_api_service.find_current_period(dasha_tree)
                    if current_period:
                        logger.info("Using REAL dasha API data (with actual calendar dates)")
                        current_period["source"] = "real_api"  # flag so summarize_kundli labels it correctly
                        return current_period
        except Exception as e:
            logger.warning(f"Real dasha API failed, falling back to calculated dasha: {e}")

        logger.info("Falling back to calculated Vimshottari dasha (years-from-birth)")
        return self._get_dasha_for_kundli(kundli_data)

kundli_service = KundliService()