"""import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Dict, List
from app.config.settings import settings
from app.utils.logger import logger

DATE_FORMAT = "%d/%m/%Y %H:%M:%S"  # matches "17/01/2100 16:17:02" style timestamps
DASHA_LAMBDA_URL: str = "https://bivrov2febq5ued37psv2hcxyi0wlxet.lambda-url.ap-south-1.on.aws/"
DASHA_LAMBDA_BEARER_TOKEN: str = "f83c6105-1731-4cd9-9d94-9543ff01bfe1"

def _parse_dt(date_str: str) -> Optional[datetime]:
    try:
        return datetime.strptime(date_str, DATE_FORMAT)
    except (ValueError, TypeError):
        return None


class DashaApiService:
    def fetch_dasha_tree(self, date: str, time: str, latitude: float, longitude: float,
                          timezone_name: str = "Asia/Kolkata", language: str = "English") -> Optional[List[Dict]]:
        
        if not settings.DASHA_LAMBDA_URL or not settings.DASHA_LAMBDA_BEARER_TOKEN:
            logger.warning("DASHA_LAMBDA_URL or DASHA_LAMBDA_BEARER_TOKEN not configured — skipping real dasha API")
            return None

        payload = {
            "date": date, "time": time,
            "latitude": str(latitude), "longitude": str(longitude),
            "timezone_name": timezone_name, "language": language,
        }
        req = urllib.request.Request(
            settings.DASHA_LAMBDA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.DASHA_LAMBDA_BEARER_TOKEN}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                response = json.loads(resp.read().decode("utf-8"))
            logger.info("Dasha API response fetched successfully")

            # Defensive unwrapping — response might be a bare list, or
            # wrapped under a key. Log what we actually got so we can
            # confirm the exact shape from real output.
            if isinstance(response, list):
                return response
            if isinstance(response, dict):
                for key in ("mahadasha", "dasha", "vimshottari", "data", "result"):
                    if key in response and isinstance(response[key], list):
                        return response[key]
                logger.warning(f"Dasha API returned a dict with unexpected keys: {list(response.keys())} — could not locate the mahadasha list")
                return None

            logger.warning(f"Dasha API returned unexpected type: {type(response)}")
            return None
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.error(f"Dasha API HTTP error {e.code}: {error_body}")
            return None
        except Exception as e:
            logger.error(f"Dasha API fetch failed: {e}")
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


dasha_api_service = DashaApiService()"""



import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Dict, List

from app.utils.logger import logger

DATE_FORMAT = "%d/%m/%Y %H:%M:%S"

DASHA_LAMBDA_URL = "https://bivrov2febq5ued37psv2hcxyi0wlxet.lambda-url.ap-south-1.on.aws/"
DASHA_LAMBDA_BEARER_TOKEN = "f83c6105-1731-4cd9-9d94-9543ff01bfe1"

# Candidate values to try for the "requirements" field, in priority order.
# The Lambda rejects requests without this field ("requirements must be a
# non-empty list"), but we don't know the exact accepted value(s) yet — so
# we try the most likely ones and lock in whichever succeeds first.
REQUIREMENTS_CANDIDATES = [ "MahaDasha"]


def _parse_dt(date_str: str) -> Optional[datetime]:
    try:
        return datetime.strptime(date_str, DATE_FORMAT)
    except (ValueError, TypeError):
        return None


class DashaApiService:

    def _try_fetch(self, payload: Dict, max_retries: int) -> Optional[List[Dict]]:
        """Attempt a single payload (one requirements candidate), retrying on
        transient failures (timeouts, connection errors) but NOT retrying on
        a 400-style rejection — that means this candidate value is just wrong,
        so we should move on to the next candidate instead of retrying it."""
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
                with urllib.request.urlopen(req, timeout=45) as resp:
                    response = json.loads(resp.read().decode("utf-8"))

                logger.info(
                    f"Dasha API response fetched successfully "
                    f"(requirements={payload.get('requirements')}, attempt {attempt})"
                )

                if isinstance(response, list):
                    return response

                if isinstance(response, dict):
                    for key in ("mahadasha", "dasha", "vimshottari", "data", "result"):
                        if key in response and isinstance(response[key], list):
                            return response[key]

                    logger.warning(
                        f"Dasha API returned unexpected keys "
                        f"(requirements={payload.get('requirements')}): {list(response.keys())}"
                    )
                    return None

                logger.warning(
                    f"Dasha API returned unexpected response type {type(response)} "
                    f"(requirements={payload.get('requirements')})"
                )
                return None

            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8")
                # 4xx errors (bad request, invalid requirements value) won't fix
                # themselves on retry — stop retrying THIS candidate immediately
                # and let the caller move on to the next one.
                if 400 <= e.code < 500:
                    logger.warning(
                        f"Dasha API rejected requirements={payload.get('requirements')!r} "
                        f"(HTTP {e.code}): {error_body}"
                    )
                    return None
                # 5xx errors might be transient — worth retrying
                logger.warning(
                    f"Dasha API HTTP error {e.code} on attempt {attempt} "
                    f"(requirements={payload.get('requirements')}): {error_body}"
                )

            except Exception as e:
                logger.warning(
                    f"Dasha API request failed on attempt {attempt} "
                    f"(requirements={payload.get('requirements')}): {e}"
                )

        logger.error(
            f"Dasha API fetch failed after {max_retries + 1} attempts "
            f"(requirements={payload.get('requirements')})"
        )
        return None

    def fetch_dasha_tree(
        self,
        date: str,
        time: str,
        latitude: float,
        longitude: float,
        timezone_name: str = "Asia/Kolkata",
        language: str = "English",
        max_retries: int = 2,
    ) -> Optional[List[Dict]]:
        """Tries each candidate 'requirements' value in turn (with retry-on-
        transient-failure for each) until one succeeds. Once you confirm which
        candidate actually works, you can trim REQUIREMENTS_CANDIDATES down to
        just that value to skip the trial-and-error on every future call."""

        for req_value in REQUIREMENTS_CANDIDATES:
            payload = {
                "requirements": [req_value],
                "date": date,
                "time": time,
                "latitude": str(latitude),
                "longitude": str(longitude),
                "timezone_name": timezone_name,
                "language": language,
            }

            result = self._try_fetch(payload, max_retries)
            if result is not None:
                logger.info(f"Dasha API succeeded with requirements=['{req_value}'] — locking this in for future calls")
                # Move the winning candidate to the front so future calls try it first
                if req_value in REQUIREMENTS_CANDIDATES:
                    REQUIREMENTS_CANDIDATES.remove(req_value)
                    REQUIREMENTS_CANDIDATES.insert(0, req_value)
                return result

        logger.error(f"Dasha API failed for all requirements candidates: {REQUIREMENTS_CANDIDATES}")
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