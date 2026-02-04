# query_vectors.py
import json
import numpy as np
import faiss

from ..Embedd import embedd_config as embedd

def get_embedding(text):
    """Get embedding for a single text"""
    client = embedd.embedding_model
    
    response = client.embed_query(text)
    return response

def load_vectors():
    """Load FAISS index and metadata"""
    index = faiss.read_index("Backend/Resources/equipment_index.faiss")
    
    with open("Backend/Resources/metadata.json", "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    return index, metadata

def search_query(query, top_k=3):
    """Search for similar text"""
    index, metadata = load_vectors()
    
    # Create query embedding
    query_embedding = get_embedding(query)
    query_vector = np.array([query_embedding]).astype('float32')
    
    # NORMALIZE query vector for cosine similarity
    faiss.normalize_L2(query_vector)
    
    # Search in FAISS (now returns cosine similarity scores)
    scores, indices = index.search(query_vector, top_k)  # scores will be 0-1
    
    # Get results
    results = []
    for i in range(top_k):
        idx = indices[0][i]
        if idx < len(metadata):
            results.append({
                "text": metadata[idx]["text"],
                "similarity": float(scores[0][i]),  # Already 0-1, higher is better
                "id": metadata[idx]["id"]
            })
    
    return results

def ask_question(question):
    
    results = search_query(question, top_k=2)
    
    resp = ""
    
    for res in results:
        
        if res["similarity"] > 0.3 :
            resp += res["text"] 
        
    return resp

def get_retrieved_chunk(question):
    
    out_list = []
    
    results = search_query(question, top_k=3)
    
    for res in results:
        if res["similarity"] > 0.3 :
            out_list.append(res["text"])
            
    return out_list
    