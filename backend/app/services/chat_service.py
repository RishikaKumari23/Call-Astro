import json
from typing import Dict, Any, List
from backend.app.memory.database import db
from backend.app.services.llm_service import llm_service
from backend.app.rag.vector_store import vector_store
from backend.app.rag.embeddings import EmbeddingsProvider
from backend.app.prompts.templates import ASTROLOGER_PROMPT, MISSING_INFO_PROMPT, SUGGESTIONS_PROMPT
from backend.app.config.settings import settings
from backend.app.utils.logger import logger

class ChatService:
    def __init__(self):
        self.embeddings_provider = EmbeddingsProvider()

    def _format_history_for_llm(self, history: List[Dict[str, str]]) -> str:
        """Format SQLite message rows into a readable prompt history transcript."""
        formatted = []
        for msg in history:
            role_name = "User" if msg["role"] == "user" else "Astrologer"
            formatted.append(f"{role_name}: {msg['content']}")
        return "\n".join(formatted)

    def process_chat_message(self, session_id: str, message_text: str) -> Dict[str, Any]:
        """Core state machine flow for handling a user message, updating state, and executing predictions."""
        logger.info(f"Processing chat message for session: {session_id}")
        logger.info(f"User message: {message_text}")
        
        try:
            # 1. Fetch current profile and chat history
            session = db.get_or_create_session(session_id)
            history = db.get_history(session_id, limit=10)
            history_text = self._format_history_for_llm(history)
            logger.info(f"Session before extraction: dob={session.get('dob')}, birth_time={session.get('birth_time')}, birth_place={session.get('birth_place')}")
            
            # 2. Extract profile details safely
            try:
                extracted = llm_service.extract_profile_details(message_text, history_text)
                logger.info(f"Extracted details from message: dob={extracted.get('dob')}, time={extracted.get('birth_time')}, place={extracted.get('birth_place')}")
            except Exception as extract_err:
                logger.error(f"Profile extraction failed: {extract_err}")
                extracted = {"dob": None, "birth_time": None, "birth_place": None, "language": "Hinglish", "is_astrology_query": True}
            
            # 3. Update session with extracted data
            updates = {}
            for key in ["dob", "birth_time", "birth_place"]:
                if extracted.get(key):
                    updates[key] = extracted[key]
                    session[key] = extracted[key]
                    logger.info(f"Updated session[{key}] = {extracted[key]}")
            if extracted.get("language"):
                updates["language"] = extracted["language"]
                session["language"] = extracted["language"]
            
            if updates:
                db.update_session(session_id, updates)
                logger.info(f"Database updated with: {updates}")
            
            language = session.get("language", "Hinglish")
            db.add_message(session_id, "user", message_text)
            
            # 4. Check if missing birth details
            is_astrology = extracted.get("is_astrology_query", True)
            missing_fields = []
            if not session.get("dob"):
                missing_fields.append(("Date of Birth", "dob"))
            if not session.get("birth_time"):
                missing_fields.append(("Birth Time", "birth_time"))
            if not session.get("birth_place"):
                missing_fields.append(("Birth Place", "birth_place"))
            
            logger.info(f"Missing fields: {[f[0] for f in missing_fields]}, is_astrology={is_astrology}")
            
            # 5. If ANY birth details are missing, always ask for them first
            if missing_fields:
                next_missing_name, _ = missing_fields[0]
                logger.info(f"Asking for missing field: {next_missing_name}")
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
                    "birth_place": session.get("birth_place"), "language": language,
                    "suggestions": []
                }
            
            # 6. Get context if needed
            context_str = ""
            if is_astrology and not missing_fields:
                try:
                    query_vector = self.embeddings_provider.get_embedding(message_text)
                    hits = vector_store.hybrid_search(query=message_text, query_vector=query_vector, top_k=settings.TOP_K_RETRIEVAL, alpha=settings.HYBRID_ALPHA)
                    context_chunks = [f"--- Context {i+1} [Source: {hit['metadata'].get('source', 'Unknown')}] ---\n{hit['text']}\n" for i, hit in enumerate(hits)]
                    context_str = "\n".join(context_chunks)
                    logger.info(f"Retrieved {len(hits)} chunks for query")
                except Exception as rag_err:
                    logger.error(f"RAG failed: {rag_err}")
                    context_str = "No reference available."
            
            # 7a. Generate prediction as plain text (simpler = more accurate with llama3)
            suggestions = []
            try:
                astrologer_prompt = ASTROLOGER_PROMPT.format(
                    language=language,
                    dob=session.get("dob") or "Not provided",
                    birth_time=session.get("birth_time") or "Not provided",
                    birth_place=session.get("birth_place") or "Not provided",
                    context=context_str or "No book context.",
                    history=history_text,
                    query=message_text
                )
                response_text = llm_service.generate(prompt=astrologer_prompt, temperature=0.6)
                # Strip any accidental JSON wrapping the LLM might still add
                response_text = response_text.strip().strip('"')
            except Exception as gen_err:
                logger.error(f"Generation failed: {gen_err}")
                response_text = "Mujhe samajhne mein kuch pareshani ho gayi."

            # 7b. Separate call just for suggestions (focused prompt = better quality)
            FALLBACK_SUGGESTIONS = {
                "marriage": ["💍 Shadi kab hogi?", "💑 Love ya arranged marriage?", "👶 Bacche kab honge?"],
                "love":     ["💑 Kya woh wapas aayenge?", "❤️ Hamare future ke baare mein batayein", "💍 Shadi ki chances kya hain?"],
                "career":   ["💼 Promotion kab milegi?", "🌍 Kya main abroad jaunga?", "💰 Financial growth kaisi rahegi?"],
                "finance":  ["💰 Business mein safalta milegi?", "🏠 Property kharidne ka sahi time?", "💼 Career mein progress kab?"],
                "health":   ["💊 Koi upay batayein?", "🪬 Kaunsa gemstone pehnu?", "⚕️ Health kab sudhrega?"],
                "abroad":   ["✈️ Kab jaane ka mauka milega?", "💼 Videsh mein career kaisa?", "🌍 Permanent settlement possible hai?"],
                "default":  ["💍 Marriage ke baare mein batayein", "💼 Career kaisa rahega?", "💰 Finance ke baare mein poochhein"],
            }

            def get_fallback(query: str):
                q = query.lower()
                if any(w in q for w in ["marr", "shadi", "vivah", "kundali milan"]):
                    return FALLBACK_SUGGESTIONS["marriage"]
                if any(w in q for w in ["love", "ex", "pyar", "girlfriend", "boyfriend", "wapas"]):
                    return FALLBACK_SUGGESTIONS["love"]
                if any(w in q for w in ["job", "career", "naukri", "work", "business"]):
                    return FALLBACK_SUGGESTIONS["career"]
                if any(w in q for w in ["money", "finance", "paisa", "wealth", "debt", "loan"]):
                    return FALLBACK_SUGGESTIONS["finance"]
                if any(w in q for w in ["health", "sehat", "bimari", "disease"]):
                    return FALLBACK_SUGGESTIONS["health"]
                if any(w in q for w in ["abroad", "foreign", "videsh", "travel"]):
                    return FALLBACK_SUGGESTIONS["abroad"]
                return FALLBACK_SUGGESTIONS["default"]

            try:
                suggestions_prompt = SUGGESTIONS_PROMPT.format(
                    language=language,
                    query=message_text
                )
                raw_suggestions = llm_service.generate(prompt=suggestions_prompt, temperature=0.7)
                # Aggressively clean up LLM output to find the JSON array
                cleaned = raw_suggestions.strip()
                # Remove markdown code fences
                if "```" in cleaned:
                    parts = cleaned.split("```")
                    for part in parts:
                        part = part.strip().lstrip("json").strip()
                        if part.startswith("["):
                            cleaned = part
                            break
                # Find the JSON array boundaries
                start = cleaned.find("[")
                end = cleaned.rfind("]")
                if start != -1 and end != -1 and end > start:
                    cleaned = cleaned[start:end+1]
                parsed = json.loads(cleaned)
                if isinstance(parsed, list) and len(parsed) > 0:
                    suggestions = [str(s) for s in parsed[:3] if s and len(str(s)) > 3]
                    if len(suggestions) < 2:   # Too few valid suggestions, use fallback
                        suggestions = get_fallback(message_text)
                else:
                    suggestions = get_fallback(message_text)
                logger.info(f"Generated {len(suggestions)} suggestions")
            except Exception as sug_err:
                logger.debug(f"Suggestions LLM failed, using fallback: {sug_err}")
                suggestions = get_fallback(message_text)
            
            db.add_message(session_id, "assistant", response_text)
            return {
                "session_id": session_id, "message": response_text,
                "dob": session.get("dob"), "birth_time": session.get("birth_time"),
                "birth_place": session.get("birth_place"), "language": language,
                "suggestions": suggestions
            }
        
        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            return {
                "session_id": session_id,
                "message": "Kripya dobara koshish karein.",
                "dob": None, "birth_time": None, "birth_place": None, "language": "Hinglish",
                "suggestions": []
            }

# Instantiate global chat service
chat_service = ChatService()
