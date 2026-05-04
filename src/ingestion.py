"""
Document ingestion module for BIS Standards.
Handles PDF/text loading, cleaning, and chunking.
"""

import os
import logging
from typing import List, Tuple
from pathlib import Path

try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / 'data'
CHUNK_SIZE = 400
CHUNK_OVERLAP = 50


def load_documents() -> List[Tuple[str, str]]:
    """
    Load all documents from data directory.
    Returns list of (filename, content) tuples.
    """
    documents = []
    
    if not DATA_DIR.exists():
        logger.warning(f"Data directory not found: {DATA_DIR}")
        return documents
    
    for file_path in DATA_DIR.iterdir():
        try:
            if file_path.suffix == '.pdf' and HAS_PYPDF2:
                logger.info(f"Loading PDF: {file_path.name}")
                reader = PdfReader(file_path)
                text = ""
                for page_num, page in enumerate(reader.pages):
                    try:
                        text += page.extract_text() or ""
                    except Exception as e:
                        logger.warning(f"Failed to extract page {page_num}: {e}")
                if text:
                    documents.append((file_path.name, text))
                    
            elif file_path.suffix == '.txt':
                logger.info(f"Loading text file: {file_path.name}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    documents.append((file_path.name, content))
        except Exception as e:
            logger.error(f"Error loading {file_path.name}: {e}")
    
    logger.info(f"Loaded {len(documents)} documents")
    return documents


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Remove control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    return text.strip()


def chunk_documents(documents: List[Tuple[str, str]]) -> List[Tuple[str, str, int]]:
    """
    Chunk documents into segments.
    Returns list of (doc_name, chunk_text, chunk_index) tuples.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunks = []
    for doc_name, content in documents:
        cleaned = clean_text(content)
        doc_chunks = text_splitter.split_text(cleaned)
        
        for idx, chunk in enumerate(doc_chunks):
            if chunk.strip():  # Skip empty chunks
                chunks.append((doc_name, chunk, idx))
    
    logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
    return chunks


def get_chunk_text(chunk: Tuple[str, str, int]) -> str:
    """Extract text from chunk tuple."""
    return chunk[1]


def get_chunk_metadata(chunk: Tuple[str, str, int]) -> dict:
    """Extract metadata from chunk tuple."""
    return {
        "doc_name": chunk[0],
        "chunk_index": chunk[2]
    }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("Testing document ingestion...")
    docs = load_documents()
    print(f"Loaded {len(docs)} documents")
    
    chunks = chunk_documents(docs)
    print(f"Created {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n--- Chunk {i} ---")
        print(f"Document: {chunk[0]}, Index: {chunk[2]}")
        print(f"Text (first 100 chars): {chunk[1][:100]}...")
