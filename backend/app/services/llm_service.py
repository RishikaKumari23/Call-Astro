import json
import requests
import re
from datetime import datetime
from typing import Dict, Any, Optional
from backend.app.config.settings import settings
from backend.app.utils.logger import logger

class LLMService:
    def __init__(self):
        self.host = settings.OLLAMA_HOST
        self.model = settings.OLLAMA_LLM_MODEL
        logger.info(f"LLM Service initialised targeting Ollama host: {self.host}, model: {self.model}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None, json_format: bool = False, temperature: float = 0.3) -> str:
        """Call Ollama generation endpoint with options."""
        url = f"{self.host}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        if json_format:
            payload["format"] = "json"
            
        try:
            logger.debug(f"Sending prompt to Ollama model {self.model} (JSON Mode={json_format})...")
            response = requests.post(url, json=payload, timeout=45)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            elif response.status_code == 404:
                # Often model not found error
                logger.error(f"Ollama returned 404: Model '{self.model}' not found. Please run 'ollama pull {self.model}'.")
                raise RuntimeError(
                    f"Ollama model '{self.model}' is not pulled or running. "
                    f"Please open terminal and run: `ollama pull {self.model}`"
                )
            else:
                logger.error(f"Ollama returned status code {response.status_code}: {response.text}")
                raise RuntimeError(f"Ollama server error ({response.status_code}): {response.text}")
                
        except requests.exceptions.ConnectionError as ce:
            logger.error(f"Failed to connect to Ollama server at {self.host}. Is Ollama service running?")
            raise RuntimeError(
                f"Cannot connect to Ollama server at {self.host}. "
                f"Please ensure Ollama is installed and running locally."
            ) from ce
        except Exception as e:
            logger.error(f"Error communicating with Ollama LLM: {e}")
            raise

    def _extract_date_regex(self, text: str) -> Optional[str]:
        """Extract date from text using regex patterns. Supports multiple formats."""
        text_lower = text.lower()
        
        # Month name to number mapping (including Hindi)
        months = {
            'january': '01', 'jan': '01', 'जनवरी': '01',
            'february': '02', 'feb': '02', 'फरवरी': '02',
            'march': '03', 'mar': '03', 'मार्च': '03',
            'april': '04', 'apr': '04', 'अप्रैल': '04',
            'may': '05', 'मई': '05',
            'june': '06', 'jun': '06', 'जून': '06',
            'july': '07', 'jul': '07', 'जुलाई': '07',
            'august': '08', 'aug': '08', 'अगस्त': '08',
            'september': '09', 'sep': '09', 'सितंबर': '09',
            'october': '10', 'oct': '10', 'अक्टूबर': '10',
            'november': '11', 'nov': '11', 'नवंबर': '11',
            'december': '12', 'dec': '12', 'दिसंबर': '12'
        }
        
        # Pattern 1: DD Month YYYY (e.g., "15 july 2005", "15-july-2005")
        pattern1 = r'(\d{1,2})\s*[-/.]?\s*(january|february|march|april|may|june|july|august|september|october|november|december|जनवरी|फरवरी|मार्च|अप्रैल|मई|जून|जुलाई|अगस्त|सितंबर|अक्टूबर|नवंबर|दिसंबर|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s*[-/.]?\s*(\d{4})'
        match = re.search(pattern1, text_lower)
        if match:
            day, month_name, year = match.groups()
            month_num = months.get(month_name.lower(), '00')
            dob = f"{day.zfill(2)}-{month_num}-{year}"
            logger.info(f"Extracted date via pattern1 (DD-MMM-YYYY): {dob}")
            return dob
        
        # Pattern 2: Month DD YYYY (e.g., "july 15 2005", "July 15, 2005")
        pattern2 = r'(january|february|march|april|may|june|july|august|september|october|november|december|जनवरी|फरवरी|मार्च|अप्रैल|मई|जून|जुलाई|अगस्त|सितंबर|अक्टूबर|नवंबर|दिसंबर|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2})\s*[-,.]?\s*(\d{4})'
        match = re.search(pattern2, text_lower)
        if match:
            month_name, day, year = match.groups()
            month_num = months.get(month_name.lower(), '00')
            dob = f"{day.zfill(2)}-{month_num}-{year}"
            logger.info(f"Extracted date via pattern2 (MMM-DD-YYYY): {dob}")
            return dob
        
        # Pattern 3: DD/MM/YYYY or DD-MM-YYYY (e.g., "15/07/2005", "15-07-2005")
        pattern3 = r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{4})'
        match = re.search(pattern3, text_lower)
        if match:
            day, month, year = match.groups()
            dob = f"{day.zfill(2)}-{month.zfill(2)}-{year}"
            logger.info(f"Extracted date via pattern3 (DD-MM-YYYY): {dob}")
            return dob
        
        # Pattern 4: YYYY-MM-DD format
        pattern4 = r'(\d{4})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{1,2})'
        match = re.search(pattern4, text_lower)
        if match:
            year, month, day = match.groups()
            dob = f"{day.zfill(2)}-{month.zfill(2)}-{year}"
            logger.info(f"Extracted date via pattern4 (YYYY-MM-DD): {dob}")
            return dob
        
        logger.debug("No date pattern matched in text")
        return None

    def _extract_time_regex(self, text: str) -> Optional[str]:
        """Extract birth time from text using regex patterns."""
        text_lower = text.lower()
        
        # Pattern 1: HH:MM AM/PM (e.g., "11:30 PM", "3:45 am")
        pattern1 = r'(\d{1,2})\s*[:.]?\s*(\d{2})\s*(am|pm|AM|PM)'
        match = re.search(pattern1, text_lower)
        if match:
            hour, minute, period = match.groups()
            time_str = f"{hour}:{minute} {period.upper()}"
            logger.info(f"Extracted time via pattern1: {time_str}")
            return time_str
        
        # Pattern 2: HH AM/PM without minutes (e.g., "11 PM", "3 am")
        pattern2 = r'(\d{1,2})\s*(am|pm|AM|PM)'
        match = re.search(pattern2, text_lower)
        if match:
            hour, period = match.groups()
            time_str = f"{hour}:00 {period.upper()}"
            logger.info(f"Extracted time via pattern2: {time_str}")
            return time_str
        
        return None

    def _extract_place_regex(self, text: str) -> Optional[str]:
        """Extract birth place from text using regex patterns."""
        text_lower = text.lower()
        
        # Patterns for place: "place is X", "place: X", "born in X", "से X"
        patterns = [
            r'place\s*(?:is|:)\s*([A-Za-z\s]+?)(?:\.|,|$)',
            r'born\s+in\s+([A-Za-z\s]+?)(?:\.|,|$)',
            r'से\s+([A-Za-z\s०-९]+?)(?:\.|,|$)',
            r'जगह\s*(?:है|:)\s*([A-Za-z\s०-९]+?)(?:\.|,|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                place = match.group(1).strip()
                if place and len(place) > 1:
                    logger.info(f"Extracted place via regex: {place}")
                    return place
        
        return None

    def extract_profile_details(self, message: str, history: str) -> Dict[str, Any]:
        """Extract birth details from chat input using LLM + regex fallback."""
        from backend.app.prompts.templates import EXTRACTION_PROMPT
        
        result = {
            "dob": None,
            "birth_time": None,
            "birth_place": None,
            "language": "Hinglish",
            "is_astrology_query": True
        }
        
        prompt = EXTRACTION_PROMPT.format(history=history, message=message)
        
        try:
            # Try LLM extraction first
            raw_response = self.generate(prompt=prompt, json_format=True, temperature=0.0)
            logger.debug(f"Raw extraction output: {raw_response[:200]}")
            
            # Clean up response - remove markdown code blocks
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    # Use LLM results where available
                    if parsed.get("dob") not in ["null", "", None, "N/A"]:
                        result["dob"] = parsed.get("dob")
                    if parsed.get("birth_time") not in ["null", "", None, "N/A"]:
                        result["birth_time"] = parsed.get("birth_time")
                    if parsed.get("birth_place") not in ["null", "", None, "N/A"]:
                        result["birth_place"] = parsed.get("birth_place")
                    if parsed.get("language"):
                        result["language"] = parsed.get("language")
                    if "is_astrology_query" in parsed:
                        result["is_astrology_query"] = bool(parsed.get("is_astrology_query", True))
            except json.JSONDecodeError:
                logger.debug("LLM JSON parsing failed, using regex fallback")
        except Exception as llm_err:
            logger.debug(f"LLM extraction failed: {llm_err}, using regex fallback")
        
        # Regex fallback: Extract any missing fields using patterns
        combined_text = f"{history}\n{message}"
        
        if not result["dob"]:
            extracted_dob = self._extract_date_regex(combined_text)
            if extracted_dob:
                result["dob"] = extracted_dob
                logger.info(f"Filled DOB via regex: {extracted_dob}")
        
        if not result["birth_time"]:
            extracted_time = self._extract_time_regex(combined_text)
            if extracted_time:
                result["birth_time"] = extracted_time
                logger.info(f"Filled birth_time via regex: {extracted_time}")
        
        if not result["birth_place"]:
            extracted_place = self._extract_place_regex(combined_text)
            if extracted_place:
                result["birth_place"] = extracted_place
                logger.info(f"Filled birth_place via regex: {extracted_place}")
        
        logger.info(f"Final extracted profile: dob={result['dob']}, time={result['birth_time']}, place={result['birth_place']}")
        return result

# Instantiate global LLM service
llm_service = LLMService()
