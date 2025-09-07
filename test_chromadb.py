import chromadb
from chromadb.config import Settings
import ast
import uuid
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

def chunk_code(code: str, file_path: str) -> list:
    """Split code into semantic chunks with metadata."""
    chunks = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                start_line = getattr(node, 'lineno', 1)
                end_line = getattr(node, 'end_lineno', len(code.splitlines()))
                snippet = ast.unparse(node)
                chunks.append({
                    'snippet': snippet,
                    'metadata': {
                        'file_path': file_path,
                        'start_line': start_line,
                        'end_line': end_line,
                        'type': 'FunctionDef',
                        'id': str(uuid.uuid4())
                    }
                })
    except SyntaxError:
        pass
    return chunks

# Initialize Chroma
client = chromadb.Client(Settings(anonymized_telemetry=False))
collection = client.get_or_create_collection(name="test_snippets")

# Test storage
code = "def hello():\n    print('Hello, world!')"
chunks = chunk_code(code, "main.py")
for chunk in chunks:
    embedding = get_embedding(chunk['snippet'])
    if embedding:
        collection.add(
            ids=[chunk['metadata']['id']],
            embeddings=[embedding],
            documents=[chunk['snippet']],
            metadatas=[chunk['metadata']]
        )
    else:
        print(f"Skipping chunk due to empty embedding: {chunk['snippet'][:50]}...")

# Test retrieval
query_embedding = get_embedding("print function")
if query_embedding:
    results = collection.query(query_embeddings=[query_embedding], n_results=1)
    print("Retrieved documents:", results['documents'])
    print("Metadata:", results['metadatas'])
else:
    print("Query failed: Empty query embedding")