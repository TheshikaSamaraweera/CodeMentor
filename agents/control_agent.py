# agents/control_agent.py
import os
import tempfile
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, asdict
from agents.comprehensive_analysis_agent import run_comprehensive_analysis
from agents.refactor_agent import run_refactor_agent
from agents.optimization_agent import run_optimization_agent
from utils.code_diff import show_code_diff
from cli.apply_fixes import apply_fixes
from memory.session_memory import remember_issue, remember_feedback, show_session_summary
from utils.language_detector import detect_language
from utils.context_analyzer import analyze_project_context
from controls.recursive_controller import build_langgraph_loop

logger = logging.getLogger(__name__)


@dataclass
class AnalysisConfig:
    """Configuration for analysis parameters."""
    min_quality_threshold: int = 80
    max_iterations: int = 5
    apply_optimizations: bool = True
    interactive_mode: bool = True
    save_intermediate_results: bool = True


@dataclass
class AnalysisResults:
    """Structured results from code analysis."""
    initial_score: float
    final_score: float
    total_issues_found: int
    issues_resolved: int
    iterations_performed: int
    final_code: str
    analysis_summary: Dict[str, Any]
    issues_by_category: Dict[str, List[Dict]]


class EnhancedControlAgent:
    """Enhanced control agent with comprehensive analysis and iterative refinement."""

    def __init__(self, config: AnalysisConfig = None, mode: str = "full_scan"):
        self.config = config or AnalysisConfig()
        self.mode = mode
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def analyze_code_comprehensive(self,
                                   code: str,
                                   language: str,
                                   project_dir: str = ".") -> AnalysisResults:
        """
        Comprehensive code analysis with single-pass analysis and optional iterative refinement.

        Args:
            code: Source code to analyze
            language: Programming language
            project_dir: Project directory for context

        Returns:
            Structured analysis results with categorized issues
        """
        print(f"\n🧠 Enhanced Control Agent Activated")
        print(f"➡️ Language: {language}, Mode: {self.mode}")
        print("=" * 60)

        # Validate inputs
        if not code.strip():
            raise ValueError("Empty code provided for analysis")

        # Initialize analysis context
        api_key = self._get_api_key()
        context = analyze_project_context(project_dir)
        context['language'] = language  # Ensure language is in context

        print(f"📋 Project Context Analysis:")
        self._print_context_summary(context)

        # Phase 1: Comprehensive Single-Pass Analysis
        print(f"\n🔍 Phase 1: Comprehensive {self.mode.replace('_', ' ').title()} Analysis")
        print("-" * 40)

        initial_analysis = run_comprehensive_analysis(
            code=code,
            api_key=api_key,
            mode=self.mode,
            context=context
        )

        # Display categorized results
        self._display_categorized_results(initial_analysis)

        # Check if refinement is needed/wanted
        if not self.config.interactive_mode:
            return self._create_analysis_results(
                initial_score=initial_analysis['overall_score'],
                final_score=initial_analysis['overall_score'],
                total_issues=initial_analysis['total_unique_issues'],
                issues_resolved=0,
                iterations=0,
                final_code=code,
                summary=initial_analysis,
                issues_by_category=initial_analysis.get('issues_by_category', {})
            )

        if not self._should_proceed_with_refinement(initial_analysis):
            return self._create_analysis_results(
                initial_score=initial_analysis['overall_score'],
                final_score=initial_analysis['overall_score'],
                total_issues=initial_analysis['total_unique_issues'],
                issues_resolved=0,
                iterations=0,
                final_code=code,
                summary=initial_analysis,
                issues_by_category=initial_analysis.get('issues_by_category', {})
            )

        # Phase 2: Interactive Refinement
        print(f"\n🔁 Phase 2: Interactive Code Refinement")
        print("-" * 40)

        refinement_results = self._run_interactive_refinement(
            code, initial_analysis, context, api_key
        )

        return refinement_results

    def _get_api_key(self) -> str:
        """Get API key with proper error handling."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ GEMINI_API_KEY environment variable not set.")
        return api_key

    def _print_context_summary(self, context: Dict):
        """Print formatted context summary."""
        print(f"  🗂️  Language: {context.get('language', 'Unknown')}")
        print(f"  📦 Frameworks: {', '.join(context.get('frameworks', ['None']))}")
        print(f"  📋 Dependencies: {len(context.get('dependencies', []))} found")
        if context.get('conventions'):
            print(f"  ⚙️  Conventions: {', '.join(context.get('conventions', {}).keys())}")

    def _display_categorized_results(self, results: Dict[str, Any]):
        """Display results organized by category."""
        print(f"\n📊 Comprehensive Analysis Results:")
        print(f"  Mode: {results['mode']}")
        print(f"  Overall Score: {results['overall_score']:.1f}/100")
        print(f"  Total Issues: {results['total_unique_issues']}")
        print(f"  Analyses Run: {', '.join(results['analyses_run'])}")

        # Show raw analysis counts
        if results.get('raw_analysis_counts'):
            print(f"\n📈 Analysis Breakdown:")
            for analysis, count in results['raw_analysis_counts'].items():
                print(f"    {analysis.title()}: {count} issues found")

        # Display issues by category
        issues_by_category = results.get('issues_by_category', {})
        if issues_by_category:
            print(f"\n📂 Issues by Category:")

            category_emojis = {
                'quality': '🎯',
                'security': '🔒',
                'code_smell': '👃',
                'static': '🔧'
            }

            for category, issues in issues_by_category.items():
                emoji = category_emojis.get(category, '📋')
                category_score = results.get('category_scores', {}).get(category, 0)
                print(f"\n  {emoji} {category.upper()} ({len(issues)} issues, Score: {category_score:.1f}):")

                # Group by severity
                severity_groups = {'high': [], 'medium': [], 'low': []}
                for issue in issues:
                    severity = issue.get('severity', 'medium')
                    if severity in severity_groups:
                        severity_groups[severity].append(issue)

                for severity in ['high', 'medium', 'low']:
                    if severity_groups[severity]:
                        severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[severity]
                        print(f"    {severity_emoji} {severity.upper()}: {len(severity_groups[severity])} issues")

                        # Show first few issues
                        for i, issue in enumerate(severity_groups[severity][:3], 1):
                            line = issue.get('line', 'N/A')
                            desc = issue.get('description', 'No description')[:80]
                            source = issue.get('source_agent', 'unknown')
                            print(f"      {i}. Line {line} ({source}): {desc}...")

                        if len(severity_groups[severity]) > 3:
                            print(f"      ... and {len(severity_groups[severity]) - 3} more")

    def _should_proceed_with_refinement(self, results: Dict[str, Any]) -> bool:
        """Determine if refinement should proceed."""
        score = results['overall_score']
        total_issues = results['total_unique_issues']

        # Auto-proceed if quality is below threshold
        if score < self.config.min_quality_threshold:
            print(f"\n⚡ Quality score ({score:.1f}) below threshold ({self.config.min_quality_threshold})")
            return True

        if total_issues == 0:
            print(f"\n✅ No issues found! Code quality looks excellent.")
            return False

        user_input = input(f"\n🤖 Apply fixes and optimize code iteratively? (y/N): ").strip().lower()
        return user_input == "y"

    def _run_interactive_refinement(self, code: str, initial_analysis: Dict,
                                   context: Dict, api_key: str) -> AnalysisResults:
        """Run interactive code refinement process."""
        final_issues = initial_analysis.get('final_issues', [])

        # Initial fix application with user selection
        print("  🔧 Applying User-Selected Fixes...")
        feedback = apply_fixes(code, code, final_issues, api_key)

        # Use the refactored code from apply_fixes if any fixes were applied
        refactored_code = code
        applied_issues = [f["issue"] for f in feedback if f["applied"]]
        if applied_issues:
            print(f"\n🛠️ Refactoring code with {len(applied_issues)} applied fixes...")
            refactored_code = run_refactor_agent(code, applied_issues, api_key) or code

        # Ask user if they want iterative optimization
        if refactored_code != code:
            print(f"\n🔍 Initial fixes applied. Score improvement analysis...")

            # Quick re-analysis to show improvement
            try:
                temp_analysis = run_comprehensive_analysis(
                    code=refactored_code,
                    api_key=api_key,
                    mode=self.mode,
                    context=context
                )
                initial_score = initial_analysis['overall_score']
                temp_score = temp_analysis['overall_score']
                improvement = temp_score - initial_score

                print(f"   📈 Score: {initial_score:.1f} → {temp_score:.1f} ({improvement:+.1f})")
                print(f"   📋 Issues: {initial_analysis['total_unique_issues']} → {temp_analysis['total_unique_issues']}")

                # Return current results
                return self._create_analysis_results(
                    initial_score=initial_analysis['overall_score'],
                    final_score=temp_score,
                    total_issues=len(final_issues),
                    issues_resolved=len(applied_issues),
                    iterations=1,
                    final_code=refactored_code,
                    summary={
                        'initial_analysis': initial_analysis,
                        'temp_analysis': temp_analysis,
                        'applied_fixes': len(applied_issues),
                        'improvement': improvement
                    },
                    issues_by_category=temp_analysis.get('issues_by_category', {})
                )

            except Exception as e:
                print(f"⚠️ Re-analysis failed: {e}")
                # Fall back to original results
                return self._create_analysis_results(
                    initial_score=initial_analysis['overall_score'],
                    final_score=initial_analysis['overall_score'],
                    total_issues=len(final_issues),
                    issues_resolved=len(applied_issues),
                    iterations=1,
                    final_code=refactored_code,
                    summary={
                        'initial_analysis': initial_analysis,
                        'applied_fixes': len(applied_issues),
                        'improvement': 0
                    },
                    issues_by_category=initial_analysis.get('issues_by_category', {})
                )

        # No fixes applied
        return self._create_analysis_results(
            initial_score=initial_analysis['overall_score'],
            final_score=initial_analysis['overall_score'],
            total_issues=len(final_issues),
            issues_resolved=0,
            iterations=0,
            final_code=code,
            summary={'initial_analysis': initial_analysis, 'applied_fixes': 0},
            issues_by_category=initial_analysis.get('issues_by_category', {})
        )

    def _run_iterative_optimization(self, code: str, current_analysis: Dict,
                                    context: Dict, api_key: str,
                                    initial_analysis: Dict, initial_fixes: int) -> AnalysisResults:
        """Run iterative optimization using the recursive controller."""
        print(f"\n♻️ Starting Iterative Optimization...")

        # Convert comprehensive analysis results to format expected by recursive controller
        refined_issues = current_analysis.get('final_issues', [])

        # Setup iterative refinement using existing recursive controller
        graph = build_langgraph_loop()

        state = {
            "api_key": api_key,
            "code": code,
            "iteration": 0,
            "continue_": True,
            "best_code": code,
            "best_score": current_analysis['overall_score'],
            "best_issues": refined_issues,
            "issue_count": current_analysis['total_unique_issues'],
            "issues_fixed": initial_fixes,
            "feedback": [],
            "min_score_threshold": self.config.min_quality_threshold,
            "max_high_severity_issues": 0,
            "max_iterations": self.config.max_iterations,
            "context": context,
            "optimization_applied": False
        }

        # Run iterative refinement
        final_state = graph.invoke(state)

        # Process results
        best_code = final_state.get("best_code", code)
        final_score = final_state.get("best_score", current_analysis['overall_score'])
        iterations = len(final_state.get("history", [])) + 1  # +1 for initial fix round
        total_issues_resolved = (sum(step.get('issues_fixed', 0) for step in final_state.get("history", [])) +
                                 initial_fixes)

        # Final analysis for categorized results
        final_issues_by_category = current_analysis.get('issues_by_category', {})
        if best_code != code:
            try:
                final_analysis = run_comprehensive_analysis(
                    code=best_code,
                    api_key=api_key,
                    mode=self.mode,
                    context=context
                )
                final_issues_by_category = final_analysis.get('issues_by_category', {})
                # Update final score if new analysis succeeded
                if final_analysis.get('overall_score'):
                    final_score = final_analysis['overall_score']
            except Exception as e:
                print(f"⚠️ Final re-analysis failed: {e}")

        # Display final results
        self._display_iterative_final_results(final_state, initial_analysis, final_score)

        return self._create_analysis_results(
            initial_score=initial_analysis['overall_score'],
            final_score=final_score,
            total_issues=len(refined_issues),
            issues_resolved=total_issues_resolved,
            iterations=iterations,
            final_code=best_code,
            summary={
                'initial_analysis': initial_analysis,
                'current_analysis': current_analysis,
                'final_state': final_state,
                'improvement': final_score - initial_analysis['overall_score']
            },
            issues_by_category=final_issues_by_category
        )

    def _display_iterative_final_results(self, final_state: Dict, initial_analysis: Dict, final_score: float):
        """Display comprehensive final results from iterative optimization."""
        print(f"\n🎯 Iterative Optimization Results:")
        print("=" * 50)

        initial_score = initial_analysis['overall_score']
        improvement = final_score - initial_score

        print(f"📈 Quality Improvement: {initial_score:.1f} → {final_score:.1f} ({improvement:+.1f})")
        print(f"🔄 Iterations Completed: {len(final_state.get('history', [])) + 1}")
        print(f"✅ Total Issues Resolved: {sum(step.get('issues_fixed', 0) for step in final_state.get('history', []))}")

        # Show iteration history
        if final_state.get('history'):
            print(f"\n📚 Iteration History:")
            for step in final_state.get("history", []):
                print(f"  Iteration {step.get('iteration', 0)}: Score {step.get('score', 0):.1f}, "
                      f"Fixed {step.get('issues_fixed', 0)} issues")

        print(f"\n✨ Final Code Quality: {final_score:.1f}/100")

    def _create_analysis_results(self, initial_score: float, final_score: float,
                                total_issues: int, issues_resolved: int,
                                iterations: int, final_code: str,
                                summary: Dict, issues_by_category: Dict) -> AnalysisResults:
        """Create structured analysis results."""
        return AnalysisResults(
            initial_score=initial_score,
            final_score=final_score,
            total_issues_found=total_issues,
            issues_resolved=issues_resolved,
            iterations_performed=iterations,
            final_code=final_code,
            analysis_summary=summary,
            issues_by_category=issues_by_category
        )


# Backward compatibility function
def run_control_agent(code: str, language: str, project_dir: str = ".",
                     mode: str = "full_scan") -> Optional[str]:
    """
    Enhanced control agent with comprehensive analysis and optional iterative refinement.

    Args:
        code: Source code to analyze
        language: Programming language
        project_dir: Project directory path
        mode: Analysis mode ("quality", "security", "code_smell", "full_scan")

    Returns:
        Refactored code or None
    """
    try:
        config = AnalysisConfig(interactive_mode=True)
        agent = EnhancedControlAgent(config, mode=mode)
        results = agent.analyze_code_comprehensive(code, language, project_dir)

        print(f"\n📊 Final Session Summary:")
        print(f"  Initial Score: {results.initial_score:.1f}")
        print(f"  Final Score: {results.final_score:.1f}")
        print(f"  Improvement: {results.final_score - results.initial_score:+.1f}")
        print(f"  Issues Resolved: {results.issues_resolved}/{results.total_issues_found}")
        print(f"  Iterations: {results.iterations_performed}")

        # Show category summary
        if results.issues_by_category:
            print(f"\n📂 Final Issues by Category:")
            for category, issues in results.issues_by_category.items():
                print(f"    {category.title()}: {len(issues)} issues")

        show_session_summary()
        return results.final_code

    except Exception as e:
        logger.error(f"Control agent failed: {e}")
        print(f"❌ Control agent failed: {e}")
        return None