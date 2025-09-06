# main.py
import os
import json
import argparse
from datetime import datetime

from utils.file_loader import load_file
from agents.comprehensive_analysis_agent import run_comprehensive_analysis
from agents.refactor_agent import run_refactor_agent
from utils.context_analyzer import analyze_project_context
from dotenv import load_dotenv
from utils.language_detector import detect_language
from cli.enhanced_apply_fixes import apply_fixes_enhanced, EnhancedFixApplicator


def format_comprehensive_analysis_report(results: dict, code_path: str) -> str:
    """Format comprehensive analysis report with proper categorization."""

    report = f"""
{'=' * 80}
🔍 AI CODE REVIEWER - COMPREHENSIVE ANALYSIS REPORT
{'=' * 80}

📁 File Analyzed: {code_path}
🎯 Analysis Mode: {results['mode'].replace('_', ' ').title()}
📊 Overall Quality Score: {results['overall_score']:.1f}/100
🔍 Analyses Run: {', '.join(results['analyses_run'])}
🕒 Analysis Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'=' * 80}
📈 ANALYSIS BREAKDOWN
{'=' * 80}
"""

    # Show raw analysis counts
    if results.get('raw_analysis_counts'):
        report += "\n📊 Issues Found by Each Analysis:\n"
        for analysis, count in results['raw_analysis_counts'].items():
            report += f"   {analysis.title()}: {count} issues\n"

    report += f"\n📋 Total Unique Issues: {results['total_unique_issues']}\n"
    report += f"💯 Category Scores:\n"

    # Show category scores
    if results.get('category_scores'):
        for category, score in results['category_scores'].items():
            report += f"   {category.title()}: {score:.1f}/100\n"

    report += f"\n{'=' * 80}\n"
    report += "📂 ISSUES BY CATEGORY\n"
    report += "=" * 80 + "\n"

    if results.get('issues_by_category'):
        category_emojis = {
            'quality': '🎯',
            'security': '🔒',
            'code_smell': '👃',
            'static': '🔧'
        }

        for category, issues in results['issues_by_category'].items():
            emoji = category_emojis.get(category, '📋')
            report += f"\n{emoji} {category.upper()} ISSUES ({len(issues)} found):\n"
            report += "-" * 60 + "\n"

            # Group by severity
            severity_groups = {'high': [], 'medium': [], 'low': []}
            for issue in issues:
                severity = issue.get('severity', 'medium')
                if severity in severity_groups:
                    severity_groups[severity].append(issue)

            for severity in ['high', 'medium', 'low']:
                if severity_groups[severity]:
                    severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[severity]
                    report += f"\n{severity_emoji} {severity.upper()} PRIORITY ({len(severity_groups[severity])} issues):\n"

                    # Show detailed issues
                    for i, issue in enumerate(severity_groups[severity], 1):
                        issue_json = {
                            "line": issue.get("line", 0),
                            "description": issue.get("description", "No description"),
                            "suggestion": issue.get("suggestion", "No suggestion"),
                            "severity": issue.get("severity", "medium"),
                            "confidence": issue.get("confidence", 0.8),
                            "source": issue.get("source_agent", "unknown"),
                            "category": category
                        }
                        report += f"{i:2d}. {json.dumps(issue_json, indent=2)}\n"
                        report += "\n"

    else:
        report += "✅ No issues detected! Your code appears to be clean.\n"

    report += f"{'=' * 80}\n"
    report += "📊 QUALITY SCORE INTERPRETATION\n"
    report += "=" * 80 + "\n"

    score = results['overall_score']
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
    total_issues = results['total_unique_issues']

    if total_issues == 0:
        report += "• Your code is in excellent condition!\n"
        report += "• Consider running optimization for performance improvements.\n"
    else:
        # Count high priority issues across all categories
        high_issues = 0
        security_issues = 0
        if results.get('issues_by_category'):
            for category, issues in results['issues_by_category'].items():
                for issue in issues:
                    if issue.get('severity') == 'high':
                        high_issues += 1
                    if category == 'security':
                        security_issues += 1

        if high_issues > 0:
            report += f"• 🔴 PRIORITY: Address {high_issues} high-priority issues first.\n"

        if security_issues > 0:
            report += f"• 🔒 SECURITY: Review {security_issues} security-related issues immediately.\n"

        # Category-specific recommendations
        if 'code_smell' in results.get('issues_by_category', {}):
            smell_count = len(results['issues_by_category']['code_smell'])
            report += f"• 👃 REFACTOR: Address {smell_count} code smell issues to improve maintainability.\n"

        if 'static' in results.get('issues_by_category', {}):
            static_count = len(results['issues_by_category']['static'])
            report += f"• 🔧 STATIC: Fix {static_count} static analysis issues for better code quality.\n"

        report += "• 🔄 Consider applying fixes category by category for systematic improvement.\n"

    report += f"\n{'=' * 80}\n"
    return report


def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY environment variable not set.")
        return

    # Add CLI argument parsing
    parser = argparse.ArgumentParser(description="AI Code Reviewer with Enhanced Fix System")
    parser.add_argument("code_path", help="Path to the code file")
    parser.add_argument(
        "--mode",
        choices=["quality", "security", "code_smell", "full_scan"],
        default="full_scan",
        help="Analysis mode: quality, security, code_smell, or full_scan"
    )
    parser.add_argument(
        "--fix-mode",
        choices=["interactive", "automatic", "legacy"],
        default="interactive",
        help="Fix application mode: interactive (step-by-step), automatic (optimized), or legacy"
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
    context['language'] = language  # Ensure language is in context

    print(f"\n🔍 Starting Comprehensive {args.mode.replace('_', ' ').title()} Analysis...")

    # Run comprehensive analysis (single pass - no AI inconsistency)
    results = run_comprehensive_analysis(
        code=code,
        api_key=api_key,
        mode=args.mode,
        context=context
    )

    # Generate and display comprehensive report
    report = format_comprehensive_analysis_report(results, code_path)
    print(report)

    # Enhanced fix application logic
    if results['total_unique_issues'] > 0:
        final_issues = results.get('final_issues', [])

        if args.fix_mode == "legacy":
            # Use legacy apply_fixes for backward compatibility
            from cli.apply_fixes import apply_fixes
            answer = input("\n🤖 Apply fixes using legacy method? (y/N): ").strip().lower()
            if answer == "y":
                feedback = apply_fixes(code, code, final_issues, api_key)
                applied_issues = [f["issue"] for f in feedback if f["applied"]]

                if applied_issues:
                    refactored_code = run_refactor_agent(code, applied_issues, api_key) or code
                    if refactored_code != code:
                        print(f"\n📝 Final Refactored Code:")
                        print(refactored_code)

        else:
            # Use enhanced fix application system
            print(f"\n🚀 Enhanced Fix Application System Available")
            print(f"   Mode: {args.fix_mode.title()}")
            print(f"   Issues to process: {len(final_issues)}")

            answer = input("\n🤖 Start enhanced fix application? (y/N): ").strip().lower()
            if answer == "y":
                applicator = EnhancedFixApplicator(api_key)

                if args.fix_mode == "interactive":
                    final_code, feedback = applicator._run_interactive_mode(
                        code, final_issues, context, args.mode
                    )
                elif args.fix_mode == "automatic":
                    final_code, feedback = applicator._run_automatic_mode(
                        code, final_issues, context, args.mode
                    )

                # Show final results
                if final_code != code:
                    print(f"\n📊 Final Results Summary:")

                    # Re-analyze final code to show improvement
                    try:
                        final_results = run_comprehensive_analysis(
                            code=final_code,
                            api_key=api_key,
                            mode=args.mode,
                            context=context
                        )

                        improvement = final_results['overall_score'] - results['overall_score']
                        issue_reduction = results['total_unique_issues'] - final_results['total_unique_issues']

                        print(f"   📈 Score Improvement: {results['overall_score']:.1f} → {final_results['overall_score']:.1f} ({improvement:+.1f})")
                        print(f"   📋 Issue Reduction: {results['total_unique_issues']} → {final_results['total_unique_issues']} ({issue_reduction:+d})")

                        # Category improvements
                        print(f"\n📂 Category Improvements:")
                        for category in ['quality', 'security', 'code_smell', 'static']:
                            orig_count = len(results.get('issues_by_category', {}).get(category, []))
                            new_count = len(final_results.get('issues_by_category', {}).get(category, []))
                            if orig_count > 0 or new_count > 0:
                                improvement = orig_count - new_count
                                print(f"   {category.title()}: {orig_count} → {new_count} ({improvement:+d})")

                        # Offer to save improved code
                        save_code = input(f"\n💾 Save improved code to file? (y/N): ").strip().lower()
                        if save_code == "y":
                            output_path = f"{code_path}.improved"
                            with open(output_path, 'w', encoding='utf-8') as f:
                                f.write(final_code)
                            print(f"✅ Improved code saved to: {output_path}")

                    except Exception as e:
                        print(f"⚠️ Final re-analysis failed: {e}")
                        print("💾 Final code available, but improvement metrics unavailable")

                else:
                    print("ℹ️ No changes were made to the code")
            else:
                print("\n🚫 Fix application skipped")

    else:
        print("\n✅ No issues found! Your code is in excellent condition.")

    # Show session summary
    print(f"\n📚 Session Summary:")
    from memory.session_memory import show_session_summary
    show_session_summary()


if __name__ == "__main__":
    main()