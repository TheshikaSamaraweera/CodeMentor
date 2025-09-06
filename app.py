# app.py - Basic Flask Backend
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tempfile
from datetime import datetime
import traceback

# Import your existing modules (adjust paths as needed)
# from agents.comprehensive_analysis_agent import run_comprehensive_analysis
# from cli.smart_apply_fixes import SmartFixApplicator, StoppingCriteria
# from utils.language_detector import detect_language

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Mock data for testing without your full system initially
MOCK_ANALYSIS_RESULTS = {
    "overall_score": 78.5,
    "total_unique_issues": 5,
    "mode": "full_scan",
    "analyses_run": ["quality", "security", "code_smell", "static"],
    "issues_by_category": {
        "quality": [
            {
                "line": 15,
                "description": "Function has too many parameters",
                "suggestion": "Consider using a parameter object",
                "severity": "medium",
                "confidence": 0.8
            }
        ],
        "security": [
            {
                "line": 23,
                "description": "Potential SQL injection vulnerability",
                "suggestion": "Use parameterized queries",
                "severity": "high",
                "confidence": 0.9
            }
        ],
        "code_smell": [
            {
                "line": 45,
                "description": "Long method detected",
                "suggestion": "Break into smaller functions",
                "severity": "medium",
                "confidence": 0.7
            }
        ]
    },
    "final_issues": [
        {
            "line": 15,
            "description": "Function has too many parameters",
            "suggestion": "Consider using a parameter object",
            "severity": "medium",
            "confidence": 0.8,
            "category": "quality"
        },
        {
            "line": 23,
            "description": "Potential SQL injection vulnerability",
            "suggestion": "Use parameterized queries",
            "severity": "high",
            "confidence": 0.9,
            "category": "security"
        },
        {
            "line": 45,
            "description": "Long method detected",
            "suggestion": "Break into smaller functions",
            "severity": "medium",
            "confidence": 0.7,
            "category": "code_smell"
        }
    ]
}


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "AI Code Review Backend is running"
    })


@app.route('/api/analyze', methods=['POST'])
def analyze_code():
    """Analyze code endpoint"""
    try:
        data = request.get_json()

        if not data or 'code' not in data:
            return jsonify({"error": "No code provided"}), 400

        code = data.get('code')
        mode = data.get('mode', 'full_scan')
        language = data.get('language', 'Python')

        # Validate inputs
        if not code.strip():
            return jsonify({"error": "Empty code provided"}), 400

        if mode not in ['quality', 'security', 'code_smell', 'full_scan']:
            return jsonify({"error": "Invalid analysis mode"}), 400

        # For now, return mock data
        # TODO: Replace with actual analysis
        # api_key = os.getenv("GEMINI_API_KEY")
        # results = run_comprehensive_analysis(code, api_key, mode, {"language": language})

        # Simulate processing time
        import time
        time.sleep(2)  # Remove this in production

        # Return mock results with the requested mode
        mock_results = MOCK_ANALYSIS_RESULTS.copy()
        mock_results['mode'] = mode
        mock_results['language'] = language
        mock_results['code_length'] = len(code)
        mock_results['analysis_timestamp'] = datetime.now().isoformat()

        return jsonify({
            "success": True,
            "results": mock_results
        })

    except Exception as e:
        print(f"Analysis error: {e}")
        print(traceback.format_exc())
        return jsonify({
            "error": "Analysis failed",
            "details": str(e)
        }), 500


@app.route('/api/apply-fixes', methods=['POST'])
def apply_fixes():
    """Apply fixes to code endpoint"""
    try:
        data = request.get_json()

        if not data or 'code' not in data or 'issues' not in data:
            return jsonify({"error": "Missing code or issues"}), 400

        code = data.get('code')
        issues = data.get('issues', [])
        mode = data.get('mode', 'smart')
        selected_issue_indices = data.get('selected_issues', [])

        # Filter issues based on selection
        if selected_issue_indices:
            selected_issues = [issues[i] for i in selected_issue_indices if i < len(issues)]
        else:
            selected_issues = issues

        # Mock fix application
        # TODO: Replace with actual smart fix application
        # applicator = SmartFixApplicator(api_key)
        # final_code, feedback = applicator.apply_fixes_smart(code, selected_issues, context, mode)

        # Simulate processing time
        import time
        time.sleep(3)

        # Mock improved code (just add some comments)
        improved_code = f"""# Code improved by AI Code Reviewer
# Fixed {len(selected_issues)} issues
# Timestamp: {datetime.now().isoformat()}

{code}
"""

        # Mock feedback
        feedback = []
        for i, issue in enumerate(selected_issues):
            feedback.append({
                "issue": issue,
                "applied": True,
                "iteration": 1,
                "reason": f"Mock fix applied for issue at line {issue.get('line', 0)}"
            })

        # Mock improved analysis results
        improved_results = MOCK_ANALYSIS_RESULTS.copy()
        improved_results['overall_score'] = min(95.0, improved_results['overall_score'] + 15.0)
        improved_results['total_unique_issues'] = max(0, improved_results['total_unique_issues'] - len(selected_issues))

        return jsonify({
            "success": True,
            "improved_code": improved_code,
            "feedback": feedback,
            "improved_results": improved_results,
            "fixes_applied": len(selected_issues),
            "improvement": improved_results['overall_score'] - MOCK_ANALYSIS_RESULTS['overall_score']
        })

    except Exception as e:
        print(f"Fix application error: {e}")
        print(traceback.format_exc())
        return jsonify({
            "error": "Fix application failed",
            "details": str(e)
        }), 500


@app.route('/api/detect-language', methods=['POST'])
def detect_language():
    """Detect programming language from code"""
    try:
        data = request.get_json()
        code = data.get('code', '')

        # Simple language detection based on keywords
        # TODO: Replace with your actual language detection
        language = "Python"  # Default

        if any(keyword in code.lower() for keyword in ['function', 'const', 'let', 'var']):
            language = "JavaScript"
        elif any(keyword in code.lower() for keyword in ['public class', 'import java']):
            language = "Java"
        elif any(keyword in code.lower() for keyword in ['#include', 'int main']):
            language = "C++"
        elif any(keyword in code.lower() for keyword in ['def ', 'import ', 'from ']):
            language = "Python"

        return jsonify({
            "success": True,
            "language": language
        })

    except Exception as e:
        return jsonify({
            "error": "Language detection failed",
            "details": str(e)
        }), 500


if __name__ == '__main__':
    # Check for required environment variables
    # if not os.getenv("GEMINI_API_KEY"):
    #     print("Warning: GEMINI_API_KEY not set. Using mock data.")

    print("Starting AI Code Review Backend...")
    print("Mock mode enabled - using test data")
    print("Access health check: http://localhost:5000/api/health")

    app.run(debug=True, host='0.0.0.0', port=5000)