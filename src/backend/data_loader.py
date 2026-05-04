import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pickle

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
MODEL_NAME = 'all-MiniLM-L6-v2'  # Lightweight embedding model

import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pickle
from PyPDF2 import PdfReader

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
MODEL_NAME = 'all-MiniLM-L6-v2'  # Lightweight embedding model

def load_documents():
    documents = []
    for file in os.listdir(DATA_DIR):
        if file.endswith('.pdf'):
            reader = PdfReader(os.path.join(DATA_DIR, file))
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            documents.append(text)
        elif file.endswith('.txt'):
            with open(os.path.join(DATA_DIR, file), 'r') as f:
                content = f.read()
                documents.append(content)
    return documents

def chunk_documents(documents, chunk_size=500, overlap=50):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
    )
    chunks = []
    for doc in documents:
        chunks.extend(text_splitter.split_text(doc))
    return chunks

def create_embeddings(chunks):
    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(chunks, show_progress_bar=True)
    return embeddings, model

def build_faiss_index(embeddings):
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
    faiss.normalize_L2(embeddings)  # Normalize for cosine
    index.add(embeddings)
    return index

def save_index(index, chunks, model, path='faiss_index.pkl'):
    with open(path, 'wb') as f:
        pickle.dump((index, chunks, model), f)

if __name__ == '__main__':
    print("Loading documents...")
    documents = load_documents()
    print(f"Loaded {len(documents)} documents")

    print("Chunking documents...")
    chunks = chunk_documents(documents)
    print(f"Created {len(chunks)} chunks")

    print("Creating embeddings...")
    embeddings, model = create_embeddings(chunks)

    print("Building FAISS index...")
    index = build_faiss_index(embeddings)

    print("Saving index...")
    save_index(index, chunks, model, os.path.join(os.path.dirname(__file__), 'faiss_index.pkl'))

    print("Data pipeline complete!")