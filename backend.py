import os
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from agents.comprehensive_analysis_agent import run_comprehensive_analysis
from cli.enhanced_apply_fixes import apply_fixes_smart
from utils.language_detector import detect_language
from utils.context_analyzer import analyze_project_context

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
def analyze(body: dict = Body(...)):
    code = body.get('code')
    mode = body.get('mode', 'full_scan')
    api_key = body.get('api_key')
    if not code or not api_key:
        return {"error": "Missing code or api_key"}

    project_dir = "."
    context = analyze_project_context(project_dir)
    language = "Python"
    context['language'] = language

    results = run_comprehensive_analysis(code, api_key, mode, context)
    return results

@app.post("/fix")
def fix(body: dict = Body(...)):
    code = body.get('code')
    issues = body.get('issues', [])
    api_key = body.get('api_key')
    mode = body.get('mode', 'full_scan')
    context = body.get('context', {})
    if not code or not issues or not api_key:
        return {"error": "Missing parameters"}

    try:
        final_code, feedback = apply_fixes_smart(
            original_code=code,
            issues=issues,
            api_key=api_key,
            context=context,
            mode=mode,
            fix_mode="automatic"
        )
        return {"final_code": final_code, "feedback": feedback}
    except Exception as e:
        return {"error": f"Fix failed: {str(e)}"}