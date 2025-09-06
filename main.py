# main.py
import os
import tempfile
import json
import argparse
from datetime import datetime

from utils.file_loader import load_file
from agents.iterative_analysis_agent import run_iterative_analysis
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

def format_iterative_analysis_report(results: dict, code_path: str) -> str:
    """Format comprehensive iterative analysis report."""

    # Calculate overall score
    total_issues = results['total_unique_issues']
    score = 100.0 if total_issues == 0 else max(0, 100 - min(total_issues * 5, 100))

    report = f"""
{'=' * 80}
🔄 AI CODE REVIEWER - ITERATIVE ANALYSIS REPORT
{'=' * 80}

📁 File Analyzed: {code_path}
🎯 Analysis Mode: {results['mode'].replace('_', ' ').title()}
📊 Overall Quality Score: {score:.1f}/100
🔄 Iterations Completed: {results['iterations_run']}
⏹️ Stopping Reason: {results['stopping_reason']}
🕒 Analysis Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'=' * 80}
📈 ITERATIVE ANALYSIS PROGRESSION
{'=' * 80}
"""

    # Show iteration progression
    for iteration in results['iteration_history']:
        report += f"\n🔍 Iteration {iteration['iteration']}:\n"
        report += f"   📊 Total Issues: {iteration['total_issues']}\n"
        report += f"   ✨ New Issues: {iteration['new_issues']}\n"

        if iteration.get('issues_by_category'):
            report += f"   📂 By Category: "
            cat_summary = []
            for cat, count in iteration['issues_by_category'].items():
                cat_summary.append(f"{cat}: {count}")
            report += ", ".join(cat_summary) + "\n"

    report += f"\n{'=' * 80}\n"
    report += "📊 FINAL ISSUE SUMMARY\n"
    report += "=" * 80 + "\n"
    report += f"• Total Unique Issues Found: {total_issues}\n"

    if results.get('issues_by_category'):
        report += "\n📂 ISSUES BY CATEGORY:\n"
        report += "-" * 40 + "\n"

        category_emojis = {
            'quality': '🎯',
            'security': '🔒',
            'code_smell': '👃',
            'static': '🔧'
        }

        for category, issues in results['issues_by_category'].items():
            emoji = category_emojis.get(category, '📋')
            report += f"\n{emoji} {category.upper()} ISSUES ({len(issues)} found):\n"

            # Group by severity
            severity_groups = {'high': [], 'medium': [], 'low': []}
            for issue in issues:
                severity = issue.get('severity', 'medium')
                if severity in severity_groups:
                    severity_groups[severity].append(issue)

            for severity in ['high', 'medium', 'low']:
                if severity_groups[severity]:
                    severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[severity]
                    report += f"   {severity_emoji} {severity.upper()}: {len(severity_groups[severity])} issues\n"

                    # Show detailed issues
                    for i, issue in enumerate(severity_groups[severity], 1):
                        issue_json = {
                            "line": issue.get("line", 0),
                            "description": issue.get("description", "No description"),
                            "suggestion": issue.get("suggestion", "No suggestion"),
                            "severity": issue.get("severity", "medium"),
                            "confidence": issue.get("confidence", 0.8),
                            "source": issue.get("source_agent", "unknown"),
                            "iteration_found": issue.get("iteration_found", 1)
                        }
                        report += f"      {i}. {json.dumps(issue_json, indent=6)}\n"
                        report += "\n"

    else:
        report += "✅ No issues detected! Your code appears to be clean.\n"

    report += f"\n{'=' * 80}\n"
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
    else:
        high_issues = sum(len(issues) for category, issues in results.get('issues_by_category', {}).items()
                         for issue in issues if issue.get('severity') == 'high')

        if high_issues > 0:
            report += f"• 🔴 Address {high_issues} high-priority issues first.\n"

        report += f"• Review and fix issues category by category for best results.\n"
        report += f"• Run iterative refinement to improve code quality step by step.\n"

    report += f"\n{'=' * 80}\n"
    return report


def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY environment variable not set.")
        return

    # Add CLI argument parsing
    parser = argparse.ArgumentParser(description="AI Code Reviewer with Iterative Analysis")
    parser.add_argument("code_path", help="Path to the code file")
    parser.add_argument("--max-iterations", type=int, default=3,
                       help="Maximum number of analysis iterations")
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

    print(f"\n🔄 Starting Iterative {args.mode.replace('_', ' ').title()} Analysis...")

    # Run iterative analysis
    results = run_iterative_analysis(
        code=code,
        api_key=api_key,
        mode=args.mode,
        context=context
    )

    # Generate and display comprehensive report
    report = format_iterative_analysis_report(results, code_path)
    print(report)

    # Ask user if they want to apply fixes
    if results['total_unique_issues'] > 0:
        answer = input("\n🤖 Apply fixes and optimize code? (y/N): ").strip().lower()
        if answer == "y":
            final_issues = results.get('final_issues', [])

            print(f"\n🔧 Applying User-Selected Fixes...")
            feedback = apply_fixes(code, code, final_issues, api_key)

            # Apply refactoring for accepted fixes
            refactored_code = code
            applied_issues = [f["issue"] for f in feedback if f["applied"]]

            if applied_issues:
                print(f"\n🛠️ Refactoring code with {len(applied_issues)} applied fixes...")
                refactored_code = run_refactor_agent(code, applied_issues, api_key) or code

                if refactored_code != code:
                    print(f"\n📝 Final Refactored Code:")
                    print(refactored_code)

                    # Optionally re-analyze the refactored code
                    reanalyze = input("\n🔍 Re-analyze the refactored code? (y/N): ").strip().lower()
                    if reanalyze == "y":
                        print(f"\n🔄 Re-analyzing refactored code...")
                        final_results = run_iterative_analysis(
                            code=refactored_code,
                            api_key=api_key,
                            mode=args.mode,
                            context=context
                        )

                        final_report = format_iterative_analysis_report(final_results, f"{code_path} (refactored)")
                        print(final_report)
                else:
                    print("⚠️ No changes were made during refactoring.")
            else:
                print("ℹ️ No fixes were applied.")
        else:
            print("\n🚫 Exiting after analysis. No changes applied.")
    else:
        print("\n✅ No issues found! Your code is in excellent condition.")

    # Show session summary
    print(f"\n📚 Session Summary:")
    from memory.session_memory import show_session_summary
    show_session_summary()


if __name__ == "__main__":
    main()