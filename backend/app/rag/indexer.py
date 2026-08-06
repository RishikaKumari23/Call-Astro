import os
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple
from app.config.settings import settings
from app.utils.logger import logger
from app.rag.chunker import RecursiveCharacterTextSplitter
from app.rag.embeddings import EmbeddingsProvider
from app.rag.vector_store import vector_store

class DocumentIndexer:
    def __init__(self):
        self.chunker = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        self.embeddings_provider = EmbeddingsProvider()

    def extract_docx_text(self, file_path: str) -> str:
        try:
            import docx
        except ImportError:
            logger.error("python-docx package is not installed. DOCX extraction will be skipped.")
            raise RuntimeError("python-docx package is required for indexing DOCX documents. Please run 'pip install python-docx'.")

        try:
            doc = docx.Document(file_path)
            content = []
            for element in doc.element.body:
                if element.tag.endswith('p'):
                    p = docx.text.paragraph.Paragraph(element, doc)
                    if p.text.strip():
                        content.append(p.text)
                elif element.tag.endswith('tbl'):
                    table = docx.table.Table(element, doc)
                    for i, row in enumerate(table.rows):
                        row_data = [cell.text.replace("\n", " ").strip() for cell in row.cells]
                        content.append("| " + " | ".join(row_data) + " |")
                        if i == 0:
                            content.append("|" + "|".join(["---"] * len(row.cells)) + "|")
                    content.append("")
            return "\n".join(content)
        except Exception as e:
            logger.error(f"Error parsing DOCX file {file_path}: {e}")
            raise

    def extract_pdf_text(self, file_path: str) -> str:
        try:
            import fitz
        except ImportError:
            logger.error("PyMuPDF package is not installed. PDF extraction will be skipped.")
            raise RuntimeError("PyMuPDF package is required for indexing PDF documents. Please run 'pip install PyMuPDF'.")

        try:
            doc = fitz.open(file_path)
            content = []
            for page in doc:
                page_text = page.get_text()
                if page_text:
                    content.append(page_text)
                
                tables = page.find_tables()
                if tables:
                    for table in tables:
                        table_data = table.extract()
                        if not table_data: continue
                        for i, row in enumerate(table_data):
                            row_clean = [str(cell).replace("\n", " ").strip() if cell is not None else "" for cell in row]
                            content.append("| " + " | ".join(row_clean) + " |")
                            if i == 0:
                                content.append("|" + "|".join(["---"] * len(row)) + "|")
                        content.append("")
            return "\n".join(content)
        except Exception as e:
            logger.error(f"Error parsing PDF file {file_path}: {e}")
            raise

    def load_document(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".txt", ".md"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == ".docx":
            return self.extract_docx_text(file_path)
        elif ext == ".pdf":
            return self.extract_pdf_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _index_single_file(self, file_path: str) -> int:
        """Load, chunk, embed, and store ONE file. Returns chunk count."""
        filename = os.path.basename(file_path)
        logger.info(f"Processing document: {filename}...")

        content = self.load_document(file_path)
        if not content.strip():
            logger.warning(f"File {filename} is empty. Skipping.")
            return 0

        chunks = self.chunker.split_text(content)
        logger.info(f"Generated {len(chunks)} chunks for {filename}")
        if not chunks:
            return 0

        metadatas = [
            {"source": filename, "chunk_index": idx, "total_chunks": len(chunks)}
            for idx in range(len(chunks))
        ]

        embeddings = self.embeddings_provider.get_embeddings(chunks)
        vector_store.add_documents(chunks, metadatas, embeddings)
        logger.info(f"Successfully indexed {filename}.")
        return len(chunks)

    def ingest_knowledge_base(self, force_rebuild: bool = False) -> Tuple[List[str], int]:
        """Scan knowledge_base directory and index documents.

        If force_rebuild=False (default): INCREMENTAL mode — only processes
        files not already present in the vector store (tracked by filename
        in existing chunk metadata). Existing embeddings are preserved,
        no re-embedding of already-indexed books.

        If force_rebuild=True: wipes and re-indexes everything from scratch
        (use this if chunking/embedding settings changed, or to fix a
        corrupted index).
        """
        kb_dir = settings.KNOWLEDGE_BASE_DIR
        if not os.path.exists(kb_dir):
            os.makedirs(kb_dir, exist_ok=True)
            logger.info(f"Created empty knowledge base folder at {kb_dir}")
            return [], 0

        supported_extensions = (".txt", ".md", ".docx", ".pdf")
        files_on_disk = {
            f for f in os.listdir(kb_dir)
            if os.path.splitext(f)[1].lower() in supported_extensions
        }

        if not files_on_disk:
            logger.info("No documents found in knowledge base directory to index.")
            return [], 0

        if force_rebuild:
            logger.info("Force rebuild requested — clearing existing vector store.")
            vector_store.clear()
            already_indexed = set()
        else:
            # Determine which filenames are already represented in the store
            already_indexed = {
                chunk.get("metadata", {}).get("source")
                for chunk in vector_store.chunks
            }
            already_indexed.discard(None)

        files_to_process = sorted(files_on_disk - already_indexed)

        if not files_to_process:
            logger.info(f"All {len(files_on_disk)} documents already indexed. Nothing new to process.")
            return [], len(vector_store.chunks)

        logger.info(f"Found {len(files_to_process)} new document(s) to index "
                    f"(skipping {len(already_indexed)} already-indexed file(s)).")

        processed_files = []
        total_new_chunks = 0

        for filename in files_to_process:
            file_path = os.path.join(kb_dir, filename)
            try:
                chunk_count = self._index_single_file(file_path)
                if chunk_count > 0:
                    processed_files.append(filename)
                    total_new_chunks += chunk_count
            except Exception as e:
                logger.error(f"Failed to index file {filename}: {e}. Skipping this file.")
                continue

        return processed_files, total_new_chunks

document_indexer = DocumentIndexer()