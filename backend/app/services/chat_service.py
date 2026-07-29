from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from app.memory.database import db
from app.services.llm_service import llm_service
from app.services.geocoding_service import geocoding_service
from app.services.kundli_service import kundli_service
from app.rag.vector_store import vector_store
from app.rag.embeddings import EmbeddingsProvider
from app.prompts.templates import ASTROLOGER_PROMPT, MISSING_INFO_PROMPT
from app.config.settings import settings
from app.utils.logger import logger
from app.services.topic_service import (
    classify_topic, build_topic_emphasis, get_search_bias,
    build_explanation_footer, TOPIC_CHART_FACTORS
)


class ChatService:
    def __init__(self):
        self.embeddings_provider = EmbeddingsProvider()

    def _format_history_for_llm(self, history: List[Dict[str, str]]) -> str:
        formatted = []
        for msg in history:
            if msg["role"] == "system":
                continue  # don't feed system divider messages into the LLM prompt
            role_name = "User" if msg["role"] == "user" else "Astrologer"
            formatted.append(f"{role_name}: {msg['content']}")
        return "\n".join(formatted)

    def _to_24h(self, time_str: str) -> str:
        if not time_str:
            return ""
        try:
            from dateutil import parser as dateutil_parser
            parsed = dateutil_parser.parse(time_str.strip(), fuzzy=True)
            return parsed.strftime("%H:%M")
        except Exception:
            try:
                parsed_time = datetime.strptime(time_str.strip(), "%I:%M %p")
                return parsed_time.strftime("%H:%M")
            except ValueError:
                return time_str

    def _fetch_and_cache_kundli(self, session_id: str, session: Dict) -> str:
        """Fetch Kundli data once, cache the text summary (for the LLM prompt),
        structured chart data (for the frontend chart), and dasha info (for
        the explainability footer) — all on the session."""
        try:
            coords = geocoding_service.geocode(session.get("birth_place"))
            if not coords:
                logger.warning(f"Could not geocode birth_place: {session.get('birth_place')}")
                return "No chart data available."

            lat, lon = coords
            time_24h = self._to_24h(session.get("birth_time", ""))

            kundli_data = kundli_service.fetch_kundli(
                name=session.get("name") or "User",
                date=session.get("dob"), time=time_24h, latitude=lat, longitude=lon,
            )
            if kundli_data:
                bundle = kundli_service.get_full_chart_bundle(kundli_data)
                kundli_str = bundle["summary"]
                chart_json = json.dumps(bundle["chart"]) if bundle["chart"] else None
                dasha_json = json.dumps(bundle["dasha"]) if bundle["dasha"] else None
                divisional_json = json.dumps(bundle["divisional"]) if bundle.get("divisional") else None

                db.update_session(session_id, {
                    "kundli_data": kundli_str,
                    "kundli_raw": chart_json,
                    "kundli_dasha": dasha_json,
                    "kundli_divisional": divisional_json,
                })
                session["kundli_data"] = kundli_str
                session["kundli_raw"] = chart_json
                session["kundli_dasha"] = dasha_json
                logger.info("Kundli data fetched and cached (summary + chart + dasha)")
                return kundli_str
        except Exception as kundli_err:
            logger.error(f"Kundli fetch failed: {kundli_err}")

        return "No chart data available."

    def _fetch_and_cache_kundli(self, session_id: str, session: Dict) -> str:
        try:
            coords = geocoding_service.geocode(session.get("birth_place"))
            if not coords:
                logger.warning(f"Could not geocode birth_place: {session.get('birth_place')}")
                return "No chart data available."

            lat, lon = coords
            time_24h = self._to_24h(session.get("birth_time", ""))

            kundli_data = kundli_service.fetch_kundli(
                name=session.get("name") or "User",
                date=session.get("dob"), time=time_24h, latitude=lat, longitude=lon,
            )
            if kundli_data:
                # Try real dasha API first, fall back to calculated version
                dasha_info = kundli_service.get_real_or_calculated_dasha(
                    kundli_data, session.get("dob"), time_24h, lat, lon
                )

                kundli_str = kundli_service.summarize_kundli(kundli_data)
                chart_data = kundli_service.extract_chart_data(kundli_data)
                chart_json = json.dumps(chart_data) if chart_data else None
                dasha_json = json.dumps(dasha_info) if dasha_info else None

                db.update_session(session_id, {
                    "kundli_data": kundli_str,
                    "kundli_raw": chart_json,
                    "kundli_dasha": dasha_json,
                })
                session["kundli_data"] = kundli_str
                session["kundli_raw"] = chart_json
                session["kundli_dasha"] = dasha_json
                logger.info("Kundli data fetched and cached (summary + chart + dasha)")
                return kundli_str
        except Exception as kundli_err:
            logger.error(f"Kundli fetch failed: {kundli_err}")

        return "No chart data available."

    def _get_rag_context(self, message_text: str, topic: Optional[str] = None) -> str:
        """Shared RAG retrieval logic, with optional topic-biased search query."""
        try:
            search_query = message_text
            if topic:
                bias = get_search_bias(topic)
                if bias:
                    search_query = f"{message_text} {bias}"
                    logger.info(f"Classified topic: {topic} — biasing search query")

            query_vector = self.embeddings_provider.get_embedding(search_query)
            hits = vector_store.hybrid_search(
                query=search_query, query_vector=query_vector,
                top_k=settings.TOP_K_RETRIEVAL, alpha=settings.HYBRID_ALPHA
            )
            context_chunks = [
                f"--- Context {i+1} [Source: {hit['metadata'].get('source', 'Unknown')}] ---\n{hit['text']}\n"
                for i, hit in enumerate(hits)
            ]
            logger.info(f"Retrieved {len(hits)} chunks for query")
            return "\n".join(context_chunks)
        except Exception as rag_err:
            logger.error(f"RAG failed: {rag_err}")
            return "No reference available."

    def _get_topic_emphasis(self, session: Dict, topic: Optional[str]) -> str:
        """Build the topic-targeted chart-facts emphasis block, using the
        cached structured chart data (kundli_raw)."""
        if not topic:
            return ""
        try:
            cached_raw = session.get("kundli_raw")
            if not cached_raw:
                return ""
            parsed = json.loads(cached_raw)
            planets = parsed.get("planets", [])
            ascendant_sign = parsed.get("ascendant_sign")
            if planets and ascendant_sign:
                return build_topic_emphasis(topic, planets, ascendant_sign, None)
        except Exception as topic_err:
            logger.error(f"Topic emphasis build failed: {topic_err}")
        return ""

    def _get_divisional_chart_text(self, session: Dict, topic: Optional[str]) -> str:
        """If the topic has a relevant divisional chart (D9 for marriage,
        D10 for career, etc.), fetch it and summarize. This data is already
        present in every Kundli API response under chart_planet_positions —
        just previously unused. Not cached separately (re-fetches the Lambda
        once per topic switch within a session) to avoid a schema change."""
        if not topic:
            return ""
        config = TOPIC_CHART_FACTORS.get(topic, {})
        chart_code = config.get("divisional_chart")
        if not chart_code:
            return ""

        try:
            coords = geocoding_service.geocode(session.get("birth_place"))
            if not coords:
                return ""
            lat, lon = coords
            time_24h = self._to_24h(session.get("birth_time", ""))
            kundli_data = kundli_service.fetch_kundli(
                name=session.get("name") or "User",
                date=session.get("dob"), time=time_24h, latitude=lat, longitude=lon,
            )
            if not kundli_data:
                return ""

            purpose_map = {"D9": "marriage", "D10": "career", "D24": "education", "D7": "children"}
            purpose = purpose_map.get(chart_code, chart_code)
            return kundli_service.summarize_divisional_chart(kundli_data, chart_code, purpose)
        except Exception as e:
            logger.error(f"Divisional chart fetch failed: {e}")
            return ""

    def _build_footer(self, session: Dict, topic: Optional[str], language: str) -> str:
        """Build the honest, deterministic explainability footer from cached
        chart + dasha data. Every item shown here is something we actually
        fed the LLM — not an LLM self-report — so it's truthful by construction."""
        try:
            ascendant_sign = None
            cached_raw = session.get("kundli_raw")
            if cached_raw:
                parsed = json.loads(cached_raw)
                ascendant_sign = parsed.get("ascendant_sign")

            dasha_info = None
            cached_dasha = session.get("kundli_dasha")
            if cached_dasha:
                dasha_info = json.loads(cached_dasha)

            return build_explanation_footer(topic, ascendant_sign, dasha_info, language)
        except Exception as e:
            logger.error(f"Footer build failed: {e}")
            return ""

    def _build_final_kundli_data(self, kundli_str: str, topic_emphasis: str, divisional_text: str) -> str:
        """Combine base summary + topic emphasis + divisional chart into one
        block for the prompt, skipping any empty parts cleanly."""
        parts = [p for p in [kundli_str, topic_emphasis, divisional_text] if p]
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # NON-STREAMING — POST /api/chat
    # ------------------------------------------------------------------
    def process_chat_message(self, session_id: str, message_text: str) -> Dict[str, Any]:
        logger.info(f"Processing chat message for session: {session_id}")
        try:
            session = db.get_or_create_session(session_id)
            history = db.get_history(session_id, limit=10)
            history_text = self._format_history_for_llm(history)

            profile_complete = bool(session.get("dob") and session.get("birth_time") and session.get("birth_place"))

            if profile_complete:
                logger.info("Profile already complete — skipping extraction step")
                is_astrology = True
                language = session.get("language", "Hinglish")
                db.add_message(session_id, "user", message_text)
                missing_fields = []
            else:
                try:
                    extracted = llm_service.extract_profile_details(message_text, history_text)
                except Exception as extract_err:
                    logger.error(f"Profile extraction failed: {extract_err}")
                    extracted = {"dob": None, "birth_time": None, "birth_place": None, "language": "Hinglish", "is_astrology_query": True}

                updates = {}
                for key in ["dob", "birth_time", "birth_place"]:
                    if extracted.get(key):
                        updates[key] = extracted[key]
                        session[key] = extracted[key]
                if extracted.get("language"):
                    updates["language"] = extracted["language"]
                    session["language"] = extracted["language"]
                if updates:
                    db.update_session(session_id, updates)

                language = session.get("language", "Hinglish")
                db.add_message(session_id, "user", message_text)

                is_astrology = extracted.get("is_astrology_query", True)
                missing_fields = []
                if not session.get("dob"):
                    missing_fields.append(("Date of Birth", "dob"))
                if not session.get("birth_time"):
                    missing_fields.append(("Birth Time", "birth_time"))
                if not session.get("birth_place"):
                    missing_fields.append(("Birth Place", "birth_place"))

                if is_astrology and missing_fields:
                    next_missing_name, _ = missing_fields[0]
                    try:
                        prompt = MISSING_INFO_PROMPT.format(missing_detail=next_missing_name, language=language)
                        response_text = llm_service.generate(prompt=prompt, temperature=0.3)
                    except Exception as llm_err:
                        logger.error(f"LLM failed: {llm_err}")
                        response_text = f"Kripya apna {next_missing_name} batayein."
                    db.add_message(session_id, "assistant", response_text)
                    return {
                        "session_id": session_id, "message": response_text,
                        "dob": session.get("dob"), "birth_time": session.get("birth_time"),
                        "birth_place": session.get("birth_place"), "language": language
                    }

            # Topic classification — drives RAG bias, chart emphasis, divisional chart, and footer
            topic = classify_topic(message_text) if (is_astrology and not missing_fields) else None

            context_str = ""
            if is_astrology and not missing_fields:
                context_str = self._get_rag_context(message_text, topic)

            kundli_str = "No chart data available."
            if is_astrology and not missing_fields:
                cached_kundli = session.get("kundli_data")
                kundli_str = cached_kundli if cached_kundli else self._fetch_and_cache_kundli(session_id, session)

            topic_emphasis = ""
            divisional_text = ""
            if is_astrology and not missing_fields and topic:
                topic_emphasis = self._get_topic_emphasis(session, topic)
                divisional_text = self._get_divisional_chart_text(session, topic)

            final_kundli_data = self._build_final_kundli_data(kundli_str, topic_emphasis, divisional_text)

            try:
                astrologer_prompt = ASTROLOGER_PROMPT.format(
                    language=language, dob=session.get("dob") or "Not provided",
                    birth_time=session.get("birth_time") or "Not provided",
                    birth_place=session.get("birth_place") or "Not provided",
                    context=context_str or "No book context.", kundli_data=final_kundli_data,
                    history=history_text, query=message_text
                )
                response_text = llm_service.generate(prompt=astrologer_prompt, temperature=0.6)

                
            except Exception as gen_err:
                logger.error(f"Generation failed: {gen_err}")
                response_text = "Mujhe samajhne mein kuch pareshani ho gayi."

            db.add_message(session_id, "assistant", response_text)
            return {
                "session_id": session_id, "message": response_text,
                "dob": session.get("dob"), "birth_time": session.get("birth_time"),
                "birth_place": session.get("birth_place"), "language": language
            }
        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            return {"session_id": session_id, "message": "Kripya dobara koshish karein.",
                    "dob": None, "birth_time": None, "birth_place": None, "language": "Hinglish"}

    
    # STREAMING — POST /api/chat/stream
     
    def process_chat_message_stream(self, session_id: str, message_text: str):
        logger.info(f"Processing chat message (stream) for session: {session_id}")
        try:
            session = db.get_or_create_session(session_id)
            history = db.get_history(session_id, limit=10)
            history_text = self._format_history_for_llm(history)

            profile_complete = bool(session.get("dob") and session.get("birth_time") and session.get("birth_place"))

            if profile_complete:
                logger.info("Profile already complete — skipping extraction step")
                is_astrology = True
                language = session.get("language", "Hinglish")
                db.add_message(session_id, "user", message_text)
                missing_fields = []
            else:
                try:
                    extracted = llm_service.extract_profile_details(message_text, history_text)
                except Exception as extract_err:
                    logger.error(f"Profile extraction failed: {extract_err}")
                    extracted = {"dob": None, "birth_time": None, "birth_place": None, "language": "Hinglish", "is_astrology_query": True}

                updates = {}
                for key in ["dob", "birth_time", "birth_place"]:
                    if extracted.get(key):
                        updates[key] = extracted[key]
                        session[key] = extracted[key]
                if extracted.get("language"):
                    updates["language"] = extracted["language"]
                    session["language"] = extracted["language"]
                if updates:
                    db.update_session(session_id, updates)

                language = session.get("language", "Hinglish")
                db.add_message(session_id, "user", message_text)

                is_astrology = extracted.get("is_astrology_query", True)
                missing_fields = []
                if not session.get("dob"):
                    missing_fields.append(("Date of Birth", "dob"))
                if not session.get("birth_time"):
                    missing_fields.append(("Birth Time", "birth_time"))
                if not session.get("birth_place"):
                    missing_fields.append(("Birth Place", "birth_place"))

                if is_astrology and missing_fields:
                    next_missing_name, _ = missing_fields[0]
                    prompt = MISSING_INFO_PROMPT.format(missing_detail=next_missing_name, language=language)
                    full_text = ""
                    try:
                        for token in llm_service.generate_stream(prompt=prompt, temperature=0.3):
                            full_text += token
                            yield {"type": "chunk", "text": token}
                    except Exception as llm_err:
                        logger.error(f"LLM stream failed: {llm_err}")
                        full_text = f"Kripya apna {next_missing_name} batayein."
                        yield {"type": "chunk", "text": full_text}

                    db.add_message(session_id, "assistant", full_text)
                    yield {"type": "done", "session_id": session_id, "message": full_text,
                           "dob": session.get("dob"), "birth_time": session.get("birth_time"),
                           "birth_place": session.get("birth_place"), "language": language}
                    return

            # Topic classification — drives RAG bias, chart emphasis, divisional chart, and footer
            topic = classify_topic(message_text) if (is_astrology and not missing_fields) else None

            context_str = ""
            if is_astrology and not missing_fields:
                context_str = self._get_rag_context(message_text, topic)

            kundli_str = "No chart data available."
            if is_astrology and not missing_fields:
                cached_kundli = session.get("kundli_data")
                kundli_str = cached_kundli if cached_kundli else self._fetch_and_cache_kundli(session_id, session)

            topic_emphasis = ""
            divisional_text = ""
            if is_astrology and not missing_fields and topic:
                topic_emphasis = self._get_topic_emphasis(session, topic)
                divisional_text = self._get_divisional_chart_text(session, topic)

            final_kundli_data = self._build_final_kundli_data(kundli_str, topic_emphasis, divisional_text)

            astrologer_prompt = ASTROLOGER_PROMPT.format(
                language=language, dob=session.get("dob") or "Not provided",
                birth_time=session.get("birth_time") or "Not provided",
                birth_place=session.get("birth_place") or "Not provided",
                context=context_str or "No book context.", kundli_data=final_kundli_data,
                history=history_text, query=message_text
            )

            full_text = ""
            try:
                for token in llm_service.generate_stream(prompt=astrologer_prompt, temperature=0.6):
                    full_text += token
                    yield {"type": "chunk", "text": token}

                
            except Exception as gen_err:
                logger.error(f"Streaming generation failed: {gen_err}")
                full_text = "Mujhe samajhne mein kuch pareshani ho gayi."
                yield {"type": "chunk", "text": full_text}

            db.add_message(session_id, "assistant", full_text)
            yield {"type": "done", "session_id": session_id, "message": full_text,
                   "dob": session.get("dob"), "birth_time": session.get("birth_time"),
                   "birth_place": session.get("birth_place"), "language": language}

        except Exception as e:
            logger.error(f"Chat streaming error: {e}")
            fallback = "Kripya dobara koshish karein."
            yield {"type": "chunk", "text": fallback}
            yield {"type": "done", "session_id": session_id, "message": fallback,
                   "dob": None, "birth_time": None, "birth_place": None, "language": "Hinglish"}


chat_service = ChatService()