import ast
import uuid

def chunk_code(code: str, file_path: str, language: str) -> list:
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
        chunk = '\n'.join(lines[i:i+10])
        chunks.append({
            'snippet': chunk,
            'metadata': {
                'file_path': file_path,
                'start_line': i+1,
                'end_line': min(i+10, len(lines)),
                'type': 'line_chunk',
                'id': str(uuid.uuid4())
            }
        })
    return chunks

# Test AST parsing
code = """
def hello():
    print('Hello, world!')
class MyClass:
    def method(self):
        return 42
"""
chunks = chunk_code(code, "main.py", "python")
for chunk in chunks:
    print(f"Snippet: {chunk['snippet']}\nMetadata: {chunk['metadata']}\n")