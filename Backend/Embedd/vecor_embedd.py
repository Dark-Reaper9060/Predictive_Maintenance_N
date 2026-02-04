# create_vectors.py
import json
import numpy as np
import faiss
from docx import Document

from ..Embedd import embedd_config as embedd

def load_docx(file_path):
    """Load text from DOCX file"""
    doc = Document(file_path)
    paragraphs = []
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:  # Skip empty paragraphs
            paragraphs.append(text)
    
    return "\n".join(paragraphs)

def split_text(text, chunk_size=500, chunk_overlap=100):
    """Simple text splitter"""
    words = text.split()
    chunks = []
    
    i = 0
    while i < len(words):
        # Take chunk_size words
        chunk_words = words[i:i + chunk_size]
        chunk = " ".join(chunk_words)
        chunks.append(chunk)
        
        # Move back by overlap amount
        i += chunk_size - chunk_overlap
    
    return chunks

def create_embeddings(chunks):
    """Create embeddings for text chunks"""
    embedding_model = embedd.embedding_model
    
    return embedding_model.embed_documents(chunks)

def save_vectors():
    """Main function to create and save vectors"""
    print("Loading DOCX file...")
    text = load_docx(r"Backend\Resources\Equipment Safety Docs.docx")
    
    print("Splitting text into chunks...")
    chunks = split_text(text)
    print(f"Created {len(chunks)} chunks")
    
    print("Creating embeddings...")
    embeddings = create_embeddings(chunks)
    embeddings_array = np.array(embeddings).astype('float32')
    
    print("Creating FAISS index...")
    
    # dimension = embeddings_array.shape[1]
    # index = faiss.IndexFlatL2(dimension)
    # index.add(embeddings_array)
    
    
    dimension = embeddings_array.shape[1]

    # NORMALIZE vectors for cosine similarity
    faiss.normalize_L2(embeddings_array)

    # Use Inner Product (IP) for cosine similarity
    index = faiss.IndexFlatIP(dimension)  # Changed from IndexFlatL2
    index.add(embeddings_array)
    
    print("Saving files...")
    # Save FAISS index
    faiss.write_index(index,"Backend/Resources/equipment_index.faiss")
    
    # Save chunks
    metadata = []
    for i, chunk in enumerate(chunks):
        metadata.append({
            "id": i,
            "text": chunk
        })
    
    with open("Backend/Resources/metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    print("✅ Done! Files created:")
    print("- equipment_index.faiss")
    print("- metadata.json")