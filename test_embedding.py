from sentence_transformers import SentenceTransformer

# Load local model
try:
    model = SentenceTransformer('paraphrase-MiniLM-L3-v2')
except Exception as e:
    print(f"Failed to load SentenceTransformer model: {e}")
    raise

def get_embedding(text: str) -> list:
    """Generate embedding using local SentenceTransformer model."""
    try:
        embedding = model.encode([text], convert_to_numpy=True)[0].tolist()
        if isinstance(embedding, list) and len(embedding) == 384:
            return embedding
        raise ValueError(f"Invalid embedding: {embedding}")
    except Exception as e:
        print(f"Embedding error: {str(e)} for text: {text[:50]}...")
        return []

# Test embedding
code_snippet = "def hello():\n    print('Hello, world!')"
embedding = get_embedding(code_snippet)
print(f"Embedding length: {len(embedding)}\nFirst 5 values: {embedding[:5]}")