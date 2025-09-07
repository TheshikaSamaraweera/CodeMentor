import os
import zipfile
from fastapi import FastAPI, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from agents.comprehensive_analysis_agent import run_comprehensive_analysis
from cli.enhanced_apply_fixes import apply_fixes_smart
from utils.language_detector import detect_language
from utils.context_analyzer import analyze_project_context
import chromadb
from chromadb.config import Settings
import ast
import uuid
from sentence_transformers import SentenceTransformer

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Chroma
client = chromadb.Client(Settings(anonymized_telemetry=False, is_persistent=False))
collection = client.get_or_create_collection(name="code_snippets")

# Load local SentenceTransformer model
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


def chunk_code(code: str, file_path: str, language: str) -> list:
    """Split code into semantic chunks with metadata."""
    chunks = []
    if language.lower() == "python":
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    start_line = getattr(node, 'lineno', 1)
                    end_line = getattr(node, 'end_lineno', len(code.splitlines()))
                    snippet = ast.unparse(node) if hasattr(ast, 'unparse') else code
                    chunks.append({
                        'snippet': snippet,
                        'metadata': {
                            'file_path': file_path,
                            'start_line': start_line,
                            'end_line': end_line,
                            'type': node.__class__.__name__,
                            'id': str(uuid.uuid4())
                        }
                    })
        except SyntaxError:
            pass
    lines = code.splitlines()
    for i in range(0, len(lines), 10):
        chunk = '\n'.join(lines[i:i + 10])
        chunks.append({
            'snippet': chunk,
            'metadata': {
                'file_path': file_path,
                'start_line': i + 1,
                'end_line': min(i + 10, len(lines)),
                'type': 'line_chunk',
                'id': str(uuid.uuid4())
            }
        })
    return chunks


def store_project(files_data: list):
    """Store project files in vector DB."""
    all_embeddings = []
    all_documents = []
    all_metadatas = []
    all_ids = []
    for file_data in files_data:
        file_path = file_data['file_path']
        code = file_data['code']
        language = detect_language(file_path)
        chunks = chunk_code(code, file_path, language)
        for chunk in chunks:
            embedding = get_embedding(chunk['snippet'])
            if embedding:
                all_embeddings.append(embedding)
                all_documents.append(chunk['snippet'])
                all_metadatas.append(chunk['metadata'])
                all_ids.append(chunk['metadata']['id'])
            else:
                print(f"Skipping chunk due to empty embedding: {chunk['snippet'][:50]}...")
    if all_embeddings:
        try:
            collection.add(
                ids=all_ids,
                embeddings=all_embeddings,
                documents=all_documents,
                metadatas=all_metadatas
            )
        except Exception as e:
            print(f"Error storing in Chroma: {e}")
    else:
        print("No valid embeddings to store")


def analyze_with_retrieval(query: str, n_results: int = 5):
    """Retrieve relevant snippets for analysis."""
    try:
        query_embedding = get_embedding(query)
        if not query_embedding:
            print("Query failed: Empty query embedding")
            return {'documents': [], 'metadatas': []}
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        return results
    except Exception as e:
        print(f"Retrieval error: {e}")
        return {'documents': [], 'metadatas': []}


@app.post("/upload-project")
async def upload_project(files: list[UploadFile] = File(...)):
    """Handle multiple files or zip uploads."""
    files_data = []
    try:
        for file in files:
            if file.filename.endswith('.zip'):
                with zipfile.ZipFile(file.file, 'r') as zip_ref:
                    for zip_file in zip_ref.infolist():
                        if not zip_file.is_dir():
                            code = zip_ref.read(zip_file.filename).decode('utf-8', errors='ignore')
                            files_data.append({'file_path': zip_file.filename, 'code': code})
            else:
                code = await file.read()
                code = code.decode('utf-8', errors='ignore')
                files_data.append({'file_path': file.filename, 'code': code})
        store_project(files_data)
        return JSONResponse(content={"status": "project stored", "file_count": len(files_data)})
    except Exception as e:
        return JSONResponse(content={"error": f"Upload failed: {str(e)}"}, status_code=500)


@app.post("/analyze")
async def analyze(body: dict = Body(...)):
    """Analyze code with retrieval from vector DB."""
    code = body.get('code', '')
    mode = body.get('mode', 'full_scan')
    api_key = body.get('api_key')
    if not api_key:
        return JSONResponse(content={"error": "Missing api_key"}, status_code=400)

    query = f"analyze {mode} in code"
    retrieval = analyze_with_retrieval(query)

    retrieved_code = '\n\n'.join(retrieval['documents'][0]) if retrieval['documents'] else code
    metadatas = retrieval['metadatas'][0] if retrieval['metadatas'] else []
    full_context = {'retrieved_snippets': retrieved_code, 'language': 'Python', 'metadatas': metadatas}

    project_dir = "."
    context = analyze_project_context(project_dir)
    context.update(full_context)

    try:
        results = run_comprehensive_analysis(retrieved_code, api_key, mode, context)
        for category, issues in results.get('issues_by_category', {}).items():
            for issue in issues:
                issue['file_path'] = next(
                    (m['file_path'] for m in metadatas if m['start_line'] <= issue['line'] <= m['end_line']), 'unknown')
        return JSONResponse(content=results)
    except Exception as e:
        return JSONResponse(content={"error": f"Analysis failed: {str(e)}"}, status_code=500)


@app.post("/fix")
async def fix(body: dict = Body(...)):
    code = body.get('code')
    issues = body.get('issues', [])
    api_key = body.get('api_key')
    mode = body.get('mode', 'full_scan')
    context = body.get('context', {})
    if not code or not issues or not api_key:
        return JSONResponse(content={"error": "Missing parameters"}, status_code=400)

    try:
        final_code, feedback = apply_fixes_smart(
            original_code=code,
            issues=issues,
            api_key=api_key,
            context=context,
            mode=mode,
            fix_mode="automatic"
        )
        return JSONResponse(content={"final_code": final_code, "feedback": feedback})
    except Exception as e:
        return JSONResponse(content={"error": f"Fix failed: {str(e)}"}, status_code=500)