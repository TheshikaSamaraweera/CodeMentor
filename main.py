# main.py
import os
import tempfile
import json
import argparse

from agents.refactor_agent import run_refactor_agent
from utils.file_loader import load_file
from agents.quality_agent import run_quality_agent
from agents.static_analysis_agent import run_static_analysis
from agents.error_comparator_agent import compare_issues
from agents.security_agent import run_security_agent
from controls.recursive_controller import build_langgraph_loop
from utils.context_analyzer import analyze_project_context
from dotenv import load_dotenv
from agents.code_smell_agent import run_code_smell_agent  # Added import
from utils.language_detector import detect_language
from cli.apply_fixes import apply_fixes  # Added import

def format_initial_analysis_report(quality_results, security_results, static_results, smell_results, merged_issues, code_path):
    # Use smell_results score for code_smell mode, otherwise quality_results
    score = (smell_results.get("score", 0) if smell_results else quality_results.get("score", 0)) if (smell_results or quality_results) else 0
    quality_issues = quality_results.get("issues", []) if quality_results else []
    security_issues = security_results.get("issues", []) if security_results else []
    static_issues = static_results if static_results else []
    smell_issues = smell_results.get("issues", []) if smell_results else []

    total_issues = len(merged_issues)
    ai_only_issues = len([i for i in merged_issues if i.get("source", "").lower() == "ai"])
    static_only_issues = len([i for i in merged_issues if i.get("source", "").lower() == "static"])
    both_issues = len([i for i in merged_issues if i.get("source", "").lower() == "both"])

    high_severity = [i for i in merged_issues if i.get("severity") == "high"]
    medium_severity = [i for i in merged_issues if i.get("severity") == "medium"]
    low_severity = [i for i in merged_issues if i.get("severity") == "low"]

    report = f"""
{'=' * 80}
🔍 AI CODE REVIEWER - INITIAL ANALYSIS REPORT
{'=' * 80}

📁 File Analyzed: {code_path}
📊 Overall Quality Score: {score}/100
🕒 Analysis Timestamp: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'=' * 80}
📈 SUMMARY STATISTICS
{'=' * 80}
• Total Issues Found: {total_issues}
• AI Analysis Issues: {ai_only_issues}
• Static Analysis Issues: {static_only_issues}
• Confirmed Issues (Both): {both_issues}

📊 SEVERITY BREAKDOWN:
• 🔴 High Priority: {len(high_severity)} issues
• 🟡 Medium Priority: {len(medium_severity)} issues
• 🟢 Low Priority: {len(low_severity)} issues

{'=' * 80}
🔍 DETAILED ISSUE ANALYSIS
{'=' * 80}
"""

    if not merged_issues:
        report += "✅ No issues detected! Your code appears to be clean.\n"
    else:
        sources = {"AI": [], "Static": [], "Both": []}
        # Normalize source explicitly to match dictionary keys
        source_map = {
            "ai": "AI",
            "Ai": "AI",
            "AI": "AI",
            "static": "Static",
            "Static": "Static",
            "both": "Both",
            "Both": "Both"
        }
        for issue in merged_issues:
            issue.setdefault("explanation", "No specific explanation provided.")
            issue.setdefault("severity", "medium")
            issue.setdefault("confidence", 0.8)
            issue.setdefault("priority", 0.8 if issue["severity"] == "high" else 0.6)
            raw_source = issue.get("source", "AI")
            source = source_map.get(raw_source.lower(), "AI")
            sources[source].append(issue)

        for source, issues in sources.items():
            if issues:
                source_icon = "🤖" if source == "AI" else "🔧" if source == "Static" else "🤝"
                report += f"\n{source_icon} {source.upper()} ANALYSIS ISSUES ({len(issues)} found):\n"
                report += "-" * 60 + "\n"

                for i, issue in enumerate(issues, 1):
                    issue_json = {
                        "line": issue.get("line", 0),
                        "description": issue.get("description", issue.get("issue", "No description")),
                        "suggestion": issue.get("suggestion", "No suggestion provided"),
                        "explanation": issue.get("explanation", "No specific explanation provided"),
                        "severity": issue.get("severity", "medium"),
                        "confidence": issue.get("confidence", 0.8),
                        "priority": issue.get("priority", 0.6)
                    }
                    report += f"{i:2d}. {json.dumps(issue_json, indent=2)}\n"
                    report += "\n"

    report += f"{'=' * 80}\n"
    report += "📊 QUALITY SCORE INTERPRETATION\n"
    report += "=" * 80 + "\n"

    if score >= 90:
        report += "🏆 EXCELLENT (90-100): Code follows best practices excellently!\n"
    elif score >= 80:
        report += "✅ GOOD (80-89): Code is well-structured with minor improvements possible.\n"
    elif score >= 70:
        report += "⚠️  FAIR (70-79): Code needs some improvements but is generally acceptable.\n"
    elif score >= 60:
        report += "🔧 NEEDS WORK (60-69): Several issues need to be addressed.\n"
    else:
        report += "🚨 POOR (0-59): Significant refactoring required.\n"

    report += f"\n🎯 RECOMMENDATIONS:\n"
    if total_issues == 0:
        report += "• Your code is in excellent condition!\n"
        report += "• Consider running optimization for performance improvements.\n"
    elif len(high_severity) > 0:
        report += f"• 🔴 Address {len(high_severity)} high-priority issues first.\n"
    if len(medium_severity) > 0:
        report += f"• 🟡 Review {len(medium_severity)} medium-priority issues.\n"
    if score < 80:
        report += "• Consider running iterative optimization to improve code quality.\n"

    report += f"\n{'=' * 80}\n"
    return report

def format_iteration_summary(final):
    report = f"""
{'=' * 80}
🎯 ITERATIVE OPTIMIZATION COMPLETE
{'=' * 80}

📊 FINAL RESULTS:
• Total Iterations: {len(final.get('history', []))}
• Best Quality Score: {final.get('best_score', 'N/A')}
• Final Code Length: {len(final.get('best_code', ''))} characters
• Total Issues Fixed: {sum(h.get('issues_fixed', 0) for h in final.get('history', []))}

{'=' * 80}
📚 ITERATION HISTORY
{'=' * 80}
"""

    for i, step in enumerate(final.get("history", []), 1):
        report += f"\n🧾 Iteration {step.get('iteration')}:\n"
        report += f"   📊 Quality Score: {step.get('score', 'N/A')}\n"
        report += f"   🔍 Issues Remaining: {step.get('issue_count', 0)}\n"
        report += f"   ✅ Issues Fixed: {step.get('issues_fixed', 0)}\n"
        report += f"   🔴 High-Severity Issues: {step.get('high_severity_count', 0)}\n"
        report += f"   🚀 Optimization Applied: {'Yes' if step.get('optimization_applied') else 'No'}\n"
        report += f"   📝 Code Preview: {step.get('refactored_code', '')}\n"
        report += "-" * 40 + "\n"

    report += f"\n{'=' * 80}\n"
    report += "✅ FINAL REFACTORED CODE\n"
    report += "=" * 80 + "\n"
    report += final.get("best_code", "[No final code]")
    report += f"\n{'=' * 80}\n"

    return report

def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY environment variable not set.")
        return

    # Add CLI argument parsing
    parser = argparse.ArgumentParser(description="AI Code Reviewer")
    parser.add_argument("code_path", help="Path to the code file")
    parser.add_argument("--max-iterations", type=int, default=5, help="Maximum number of iterations")
    parser.add_argument("--force-stop", action="store_true", help="Force stop after one iteration")
    parser.add_argument(
        "--mode",
        choices=["quality", "security", "code_smell", "full_scan"],
        default="full_scan",
        help="Analysis mode: quality, security, code_smell, or full_scan"
    )
    args = parser.parse_args()

    code_path = args.code_path.strip()
    if not os.path.exists(code_path):
        print("❌ File not found.")
        return

    code = load_file(code_path)
    project_dir = os.path.dirname(code_path) or "."
    context = analyze_project_context(project_dir)
    language = detect_language(code_path)

    print(f"\n🔍 Phase 1: Running {args.mode.replace('_', ' ').title()} Analysis...")
    quality_results = security_results = static_results = smell_results = None

    if args.mode in ["quality", "full_scan"]:
        quality_results = run_quality_agent(code, api_key, context)
    if args.mode in ["security", "full_scan"]:
        security_results = run_security_agent(code, api_key, context)
    if args.mode in ["code_smell", "full_scan"]:
        smell_results = run_code_smell_agent(code, api_key, language=language)
    if args.mode == "full_scan":
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as temp_file:
            temp_file.write(code)
            temp_path = temp_file.name
        static_results = run_static_analysis(temp_path)
        os.remove(temp_path)

    merged_issues = []
    if args.mode == "quality":
        merged_issues = quality_results.get("issues", []) if quality_results else []
    elif args.mode == "security":
        merged_issues = security_results.get("issues", []) if security_results else []
    elif args.mode == "code_smell":
        merged_issues = smell_results.get("issues", []) if smell_results else []
    elif args.mode == "full_scan":
        merged_issues = compare_issues(quality_results, security_results, static_results)
        if smell_results:
            merged_issues += smell_results.get("issues", [])

    report = format_initial_analysis_report(quality_results, security_results, static_results, smell_results, merged_issues, code_path)
    print(report)

    answer = input("\n🤖 Apply fixes and optimize code iteratively? (y/N): ").strip().lower()
    if answer != "y":
        print("\n🚫 Exiting after initial review. No changes applied.")
        return

    # Apply user-selected fixes
    feedback = apply_fixes(code, code, merged_issues, api_key)
    refactored_code = code
    for f in feedback:
        if f["applied"]:
            refactored_code = run_refactor_agent(code, [f["issue"]], api_key) or code
            break  # Use the last applied code (already handled in apply_fixes)

    # Prompt user for another analysis
    if any(f["applied"] for f in feedback):
        answer = input("\n🤖 Would you like to run another analysis and apply more fixes? (y/N): ").strip().lower()
        if answer == "y":
            print("\n♻️ Starting Iterative Optimization...")
            from agents.control_agent import run_control_agent
            final_code = run_control_agent(refactored_code, language, project_dir, mode=args.mode)
        else:
            print("\n🚫 Exiting after applying fixes. No further analysis performed.")
            final_code = refactored_code
    else:
        final_code = refactored_code

    if final_code:
        print("\n📝 Final Refactored Code:")
        print(final_code)
    print("\n📚 Session Summary:")
    from memory.session_memory import show_session_summary
    show_session_summary()


if __name__ == "__main__":
    main()