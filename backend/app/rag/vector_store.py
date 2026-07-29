import os
import json
import pickle
import numpy as np
from typing import List, Dict, Tuple, Optional
from app.config.settings import settings
from app.utils.logger import logger

class LocalVectorStore:
    def __init__(self, data_dir: str = settings.VECTOR_DB_DIR):
        self.data_dir = data_dir
        self.chunks_path = os.path.join(data_dir, "chunks.json")
        self.vectors_path = os.path.join(data_dir, "vectors.npy")
        
        self.chunks: List[Dict] = []  # List of dicts: {"text": str, "metadata": dict}
        self.vectors: Optional[np.ndarray] = None  # NumPy array of shape (N, D)
        
        self.load()

    def load(self):
        """Load database records from local storage if they exist."""
        try:
            if os.path.exists(self.chunks_path) and os.path.exists(self.vectors_path):
                with open(self.chunks_path, "r", encoding="utf-8") as f:
                    self.chunks = json.load(f)
                self.vectors = np.load(self.vectors_path)
                logger.info(f"Loaded {len(self.chunks)} chunks and vectors from local cache.")
            else:
                logger.info("No vector store found. Initialising an empty store.")
                self.chunks = []
                self.vectors = None
        except Exception as e:
            logger.error(f"Error loading vector store: {e}. Starting fresh.")
            self.chunks = []
            self.vectors = None

    def save(self):
        """Save vector database indices to local storage."""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.chunks_path, "w", encoding="utf-8") as f:
                json.dump(self.chunks, f, ensure_ascii=False, indent=2)
            
            if self.vectors is not None:
                np.save(self.vectors_path, self.vectors)
            
            logger.info(f"Successfully saved {len(self.chunks)} chunks to {self.data_dir}")
        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")
            raise

    def clear(self):
        """Clear vector store cache files and in-memory lists."""
        self.chunks = []
        self.vectors = None
        if os.path.exists(self.chunks_path):
            os.remove(self.chunks_path)
        if os.path.exists(self.vectors_path):
            os.remove(self.vectors_path)
        logger.info("Cleared vector store cache.")

    def add_documents(self, texts: List[str], metadatas: List[Dict], embeddings: List[List[float]]):
        """Add document chunks along with pre-generated embedding vectors."""
        if not texts or not embeddings:
            return
            
        new_chunks = [{"text": t, "metadata": m} for t, m in zip(texts, metadatas)]
        new_vectors = np.array(embeddings, dtype=np.float32)
        
        if self.vectors is None:
            self.chunks = new_chunks
            self.vectors = new_vectors
        else:
            self.chunks.extend(new_chunks)
            self.vectors = np.vstack([self.vectors, new_vectors])
            
        self.save()

    def _lexical_score(self, text: str, query_tokens: List[str]) -> float:
        """Calculate basic TF-IDF style token occurrence score for a chunk."""
        if not query_tokens:
            return 0.0
        text_lower = text.lower()
        score = 0.0
        for token in query_tokens:
            count = text_lower.count(token)
            if count > 0:
                # Log-scaling frequency of terms to prevent single keyword repetition from dominating
                score += 1.0 + np.log(count)
        # Normalise by log-length of document to penalise extremely long text segments
        return score / (np.log(len(text_lower)) + 1.0)

    def hybrid_search(self, query: str, query_vector: List[float], top_k: int = 5, alpha: float = 0.5) -> List[Dict]:
        """Perform combined semantic vector search and keyword match ranking."""
        if not self.chunks or self.vectors is None:
            return []
            
        # 1. Calculate Vector Cosine Similarity
        q_vec = np.array(query_vector, dtype=np.float32)
        # Normalise query vector
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm
            
        # Normalise all stored vectors
        v_norms = np.linalg.norm(self.vectors, axis=1, keepdims=True)
        v_norms[v_norms == 0] = 1.0 # Avoid division by zero
        normalized_vectors = self.vectors / v_norms
        
        # Matrix dot-product to get all cosine similarities
        cosine_scores = np.dot(normalized_vectors, q_vec)
        
        # Max-min normalisation for cosine scores
        min_cos, max_cos = cosine_scores.min(), cosine_scores.max()
        range_cos = max_cos - min_cos
        if range_cos > 0:
            norm_semantic_scores = (cosine_scores - min_cos) / range_cos
        else:
            norm_semantic_scores = np.ones_like(cosine_scores)

        # 2. Calculate Lexical Token Scores
        # Simple stop-words filtering
        stop_words = {"a", "an", "the", "and", "or", "but", "if", "then", "of", "to", "in", "on", "at", "by", "for", "with", "is", "are", "was", "were", "be", "been", "being"}
        query_tokens = [t.lower() for t in query.split() if t.lower() not in stop_words and len(t) > 1]
        
        lexical_scores = np.array([self._lexical_score(chunk["text"], query_tokens) for chunk in self.chunks])
        
        # Max-min normalisation for lexical scores
        min_lex, max_lex = lexical_scores.min(), lexical_scores.max()
        range_lex = max_lex - min_lex
        if range_lex > 0:
            norm_lexical_scores = (lexical_scores - min_lex) / range_lex
        else:
            norm_lexical_scores = np.zeros_like(lexical_scores)

        # 3. Combine Scores
        combined_scores = alpha * norm_semantic_scores + (1 - alpha) * norm_lexical_scores
        
        # 4. Filter top K
        top_indices = np.argsort(combined_scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            chunk = self.chunks[idx].copy()
            chunk["score"] = float(combined_scores[idx])
            chunk["semantic_score"] = float(cosine_scores[idx])
            chunk["lexical_score"] = float(lexical_scores[idx])
            results.append(chunk)
            
        return results

# Instantiate single global store
vector_store = LocalVectorStore()
