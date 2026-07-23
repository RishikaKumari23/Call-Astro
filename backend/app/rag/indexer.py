import os
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple
from backend.app.config.settings import settings
from backend.app.utils.logger import logger
from backend.app.rag.chunker import RecursiveCharacterTextSplitter
from backend.app.rag.embeddings import EmbeddingsProvider
from backend.app.rag.vector_store import vector_store

class DocumentIndexer:
    def __init__(self):
        self.chunker = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE, 
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        self.embeddings_provider = EmbeddingsProvider()

    def extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX files using built-in XML parsing to avoid python-docx binary issues."""
        try:
            with zipfile.ZipFile(file_path) as docx:
                xml_content = docx.read('word/document.xml')
                root = ET.fromstring(xml_content)
                namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                
                paragraphs = []
                for p in root.findall('.//w:p', namespaces):
                    texts = [t.text for t in p.findall('.//w:t', namespaces) if t.text]
                    if texts:
                        paragraphs.append("".join(texts))
                return "\n".join(paragraphs)
        except Exception as e:
            logger.error(f"Error parsing DOCX file {file_path}: {e}")
            raise

    def extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF files using pure-python pypdf library."""
        try:
            import pypdf
        except ImportError:
            logger.error("pypdf package is not installed. PDF extraction will be skipped.")
            raise RuntimeError(
                "pypdf package is required for indexing PDF documents. Please run 'pip install pypdf'."
            )

        try:
            reader = pypdf.PdfReader(file_path)
            text = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
            return "\n".join(text)
        except Exception as e:
            logger.error(f"Error parsing PDF file {file_path}: {e}")
            raise

    def load_document(self, file_path: str) -> str:
        """Identify file format and load raw document string content."""
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

    def ingest_knowledge_base(self) -> Tuple[List[str], int]:
        """Scan knowledge_base directory, parse files, create chunks, embed, and store in vector database."""
        kb_dir = settings.KNOWLEDGE_BASE_DIR
        if not os.path.exists(kb_dir):
            os.makedirs(kb_dir, exist_ok=True)
            logger.info(f"Created empty knowledge base folder at {kb_dir}")
            return [], 0
            
        supported_extensions = (".txt", ".md", ".docx", ".pdf")
        files_to_process = [
            os.path.join(kb_dir, f) for f in os.listdir(kb_dir)
            if os.path.splitext(f)[1].lower() in supported_extensions
        ]
        
        if not files_to_process:
            logger.info("No documents found in knowledge base directory to index.")
            return [], 0
            
        logger.info(f"Found {len(files_to_process)} documents to index.")
        
        # Clear vector store first to avoid duplicate chunks
        vector_store.clear()
        
        processed_files = []
        total_chunks_indexed = 0
        
        for file_path in files_to_process:
            filename = os.path.basename(file_path)
            logger.info(f"Processing document: {filename}...")
            
            try:
                # 1. Load file contents
                content = self.load_document(file_path)
                if not content.strip():
                    logger.warning(f"File {filename} is empty. Skipping.")
                    continue
                
                # 2. Split content into logical overlapping chunks
                chunks = self.chunker.split_text(content)
                logger.info(f"Generated {len(chunks)} chunks for {filename}")
                
                if not chunks:
                    continue
                
                # 3. Create metadata and generate embeddings
                metadatas = []
                for idx, chunk in enumerate(chunks):
                    metadatas.append({
                        "source": filename,
                        "chunk_index": idx,
                        "total_chunks": len(chunks)
                    })
                
                # Retrieve dense semantic embeddings in batch
                embeddings = self.embeddings_provider.get_embeddings(chunks)
                
                # 4. Insert chunks and embeddings into local vector store
                vector_store.add_documents(chunks, metadatas, embeddings)
                
                processed_files.append(filename)
                total_chunks_indexed += len(chunks)
                logger.info(f"Successfully indexed {filename}.")
                
            except Exception as e:
                logger.error(f"Failed to index file {filename}: {e}. Skipping this file.")
                continue
                
        return processed_files, total_chunks_indexed

# Instantiate global indexer service
document_indexer = DocumentIndexer()
