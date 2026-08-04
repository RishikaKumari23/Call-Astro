import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Dict, List

from app.utils.logger import logger

DATE_FORMAT = "%d/%m/%Y %H:%M:%S"

DASHA_LAMBDA_URL = "https://bivrov2febq5ued37psv2hcxyi0wlxet.lambda-url.ap-south-1.on.aws/"
DASHA_LAMBDA_BEARER_TOKEN = "f83c6105-1731-4cd9-9d94-9543ff01bfe1"

# Confirmed working value — casing matters ("Mahadasha", not "MahaDasha").
FEATURE = "Mahadasha"


def _parse_dt(date_str: str) -> Optional[datetime]:
    try:
        return datetime.strptime(date_str, DATE_FORMAT)
    except (ValueError, TypeError):
        return None


class DashaApiService:

    def fetch_dasha_tree(
        self,
        date: str,           # expects DD-MM-YYYY, same as your other services
        time: str,           # expects HH:MM 24h
        latitude: float,
        longitude: float,
        timezone_name: str = "Asia/Kolkata",
        language: str = "english",
        max_retries: int = 2,
    ) -> Optional[List[Dict]]:
        payload = {
            "requirements": [FEATURE],
            # NOTE: this Lambda uses different field names than kundli_service.py's Lambda
            "dateOfBirth": date,
            "time_of_birth": time,
            "latitude": str(latitude),
            "longitude": str(longitude),
            "timezone_name": timezone_name,
            "language": language,
        }

        req = urllib.request.Request(
            DASHA_LAMBDA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DASHA_LAMBDA_BEARER_TOKEN}",
            },
            method="POST",
        )

        for attempt in range(1, max_retries + 2):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    response = json.loads(resp.read().decode("utf-8"))

                logger.info(f"Dasha API response fetched successfully (attempt {attempt})")

                # Handle API Gateway envelope: {"body": "...json string..."}
                if isinstance(response, dict) and "body" in response:
                    body_value = response["body"]
                    response = json.loads(body_value) if isinstance(body_value, str) else body_value
                
                if isinstance(response, list):
                    return response

                if isinstance(response, dict) and FEATURE in response:
                    feature_value = response[FEATURE]
                    if isinstance(feature_value, str):
                        try:
                            feature_value = json.loads(feature_value)
                        except json.JSONDecodeError:
                            logger.error(f"Dasha API '{FEATURE}' value was an unparseable string: {feature_value[:200]}")
                            return None
                    if isinstance(feature_value, list):
                        return feature_value
                    logger.warning(f"Dasha API '{FEATURE}' value has unexpected type: {type(feature_value)}")
                    return None

                logger.warning(f"Dasha API returned unexpected shape: {type(response)}")
                return None
                
            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8")
                if 400 <= e.code < 500:
                    logger.error(f"Dasha API rejected request (HTTP {e.code}): {error_body}")
                    return None  # 4xx won't fix itself on retry
                logger.warning(f"Dasha API HTTP error {e.code} on attempt {attempt}: {error_body}")

            except Exception as e:
                logger.warning(f"Dasha API request failed on attempt {attempt}: {e}")

        logger.error(f"Dasha API fetch failed after {max_retries + 1} attempts")
        return None

    def find_current_period(self, dasha_tree: List[Dict]) -> Optional[Dict]:
        now = datetime.now()

        current_maha = None
        for maha in dasha_tree:
            maha_start = _parse_dt(maha.get("start", ""))
            maha_end = _parse_dt(maha.get("end", ""))
            if maha_start and maha_end and maha_start <= now <= maha_end:
                current_maha = maha
                break

        if not current_maha:
            logger.warning("Could not find a Mahadasha period containing the current date")
            return None

        current_antar = None
        for antar in current_maha.get("antardasha", []):
            antar_start = _parse_dt(antar.get("start", ""))
            antar_end = _parse_dt(antar.get("end", ""))
            if antar_start and antar_end and antar_start <= now <= antar_end:
                current_antar = antar
                break

        current_praty = None
        if current_antar:
            for praty in current_antar.get("pratyantar", []):
                praty_start = _parse_dt(praty.get("start", ""))
                praty_end = _parse_dt(praty.get("end", ""))
                if praty_start and praty_end and praty_start <= now <= praty_end:
                    current_praty = praty
                    break

        result = {
            "current_mahadasha": {
                "lord": current_maha.get("mahadasha") or current_maha.get("mahadasha_display"),
                "start": current_maha.get("start"),
                "end": current_maha.get("end"),
            }
        }
        if current_antar:
            result["current_antardasha"] = {
                "lord": current_antar.get("antardasha") or current_antar.get("antardasha_display"),
                "start": current_antar.get("start"),
                "end": current_antar.get("end"),
            }
        if current_praty:
            result["current_pratyantardasha"] = {
                "lord": current_praty.get("pratyantar") or current_praty.get("pratyantar_display"),
                "start": current_praty.get("start"),
                "end": current_praty.get("end"),
            }

        return result


dasha_api_service = DashaApiService()