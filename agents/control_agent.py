import os
import tempfile
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, asdict
from agents.quality_agent import run_quality_agent
from agents.static_analysis_agent import run_static_analysis
from agents.error_comparator_agent import compare_issues
from agents.critic_agent import run_critic_agent
from agents.refactor_agent import run_refactor_agent
from agents.security_agent import run_security_agent
from utils.code_diff import show_code_diff
from cli.apply_fixes import apply_fixes
from memory.session_memory import remember_issue, remember_feedback, show_session_summary
from agents.optimization_agent import run_optimization_agent
from utils.language_detector import detect_language
from utils.context_analyzer import analyze_project_context

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

class EnhancedControlAgent:
    """Enhanced control agent with better flow management and configuration."""
    def __init__(self, config: AnalysisConfig = None):
        self.config = config or AnalysisConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def analyze_code_comprehensive(self,
                                   code: str,
                                   language: str,
                                   project_dir: str = ".") -> AnalysisResults:
        """
        Comprehensive code analysis with structured results.

        Args:
            code: Source code to analyze
            language: Programming language
            project_dir: Project directory for context

        Returns:
            Structured analysis results
        """
        print(f"\n🧠 Enhanced Control Agent Activated")
        print(f"➡️ Language: {language}")
        print("=" * 60)

        # Validate inputs
        if not code.strip():
            raise ValueError("Empty code provided for analysis")

        # Initialize analysis context
        api_key = self._get_api_key()
        context = analyze_project_context(project_dir)

        print(f"📋 Project Context Analysis:")
        self._print_context_summary(context)

        # Phase 1: Initial Analysis
        print("\n🔍 Phase 1: Comprehensive Initial Analysis")
        print("-" * 40)

        initial_analysis = self._run_initial_analysis(code, language, context, api_key)

        if not self.config.interactive_mode:
            return self._create_analysis_results(
                initial_score=initial_analysis['quality_score'],
                final_score=initial_analysis['quality_score'],
                total_issues=len(initial_analysis['merged_issues']),
                issues_resolved=0,
                iterations=0,
                final_code=code,
                summary=initial_analysis
            )

        # Display initial results
        self._display_initial_results(initial_analysis)

        # Check if refinement is needed/wanted
        if not self._should_proceed_with_refinement(initial_analysis):
            return self._create_analysis_results(
                initial_score=initial_analysis['quality_score'],
                final_score=initial_analysis['quality_score'],
                total_issues=len(initial_analysis['merged_issues']),
                issues_resolved=0,
                iterations=0,
                final_code=code,
                summary=initial_analysis
            )

        # Phase 2: Interactive Refinement
        print("\n🔁 Phase 2: Interactive Code Refinement")
        print("-" * 40)

        refinement_results = self._run_iterative_refinement(
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

    def _run_initial_analysis(self, code: str, language: str, context: Dict, api_key: str) -> Dict:
        """Run comprehensive initial analysis."""
        # Quality analysis
        print("  🤖 Running AI Quality Analysis...")
        quality_results = run_quality_agent(code, api_key, context)
        quality_score = quality_results.get("score", 0)
        print(f"✅ Quality Agent completed - Score: {quality_score}/100")
        print("  🔒 Running Security Analysis...")
        security_results = run_security_agent(code, api_key, context)

        # Static analysis
        print("  🔧 Running Static Analysis...")
        with tempfile.NamedTemporaryFile(suffix=f".{language.lower()}", delete=False, mode="w") as temp_file:
            temp_file.write(code)
            temp_path = temp_file.name

        try:
            static_results = run_static_analysis(temp_path)
        finally:
            os.unlink(temp_path)

        # Merge and refine issues
        print("  🧮 Comparing and Merging Issues...")
        merged_issues = compare_issues(quality_results, security_results, static_results)

        print("  🤔 Running Critical Analysis...")
        refined_issues = run_critic_agent(code, merged_issues, api_key)
        print("  🤔 Running Critical Analysis...")
        refined_issues = run_critic_agent(code, merged_issues, api_key)

        return {
            'quality_results': quality_results,
            'quality_score': quality_score,
            'security_results': security_results,
            'static_results': static_results,
            'merged_issues': merged_issues,
            'refined_issues': refined_issues,
            'context': context
        }

    def _display_initial_results(self, analysis: Dict):
        """Display formatted initial analysis results."""
        quality_score = analysis['quality_score']
        refined_issues = analysis['refined_issues']

        print(f"\n📊 Initial Analysis Results:")
        print(f"  Quality Score: {quality_score}/100")
        print(f"  Issues Found: {len(refined_issues)}")

        # Group issues by severity
        severity_counts = {}
        for issue in refined_issues:
            severity = issue.get('severity', 'medium')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        if severity_counts:
            print("  Issue Breakdown:")
            for severity, count in severity_counts.items():
                emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
                print(f"    {emoji} {severity.title()}: {count}")

        # Display top issues
        if refined_issues:
            print(f"\n📋 Top Issues Found:")
            for i, issue in enumerate(refined_issues[:5], 1):  # Show top 5
                print(f"\n  {i}. Line {issue.get('line', 'N/A')} | {issue.get('severity', 'medium').upper()}")
                print(f"     🔍 {issue.get('description', 'No description')}")
                print(f"     💡 {issue.get('suggestion', 'No suggestion')}")
                if issue.get('explanation'):
                    print(f"     📝 {issue.get('explanation')}")

    def _should_proceed_with_refinement(self, analysis: Dict) -> bool:
        """Determine if refinement should proceed."""
        quality_score = analysis['quality_score']
        issues_count = len(analysis['refined_issues'])

        # Auto-proceed if quality is below threshold
        if quality_score < self.config.min_quality_threshold:
            print(f"\n⚡ Quality score ({quality_score}) below threshold ({self.config.min_quality_threshold})")
            return True

        # Ask user in interactive mode
        if issues_count == 0:
            print("\n✅ No issues found! Code quality looks good.")
            return False

        user_input = input(f"\n🤖 Apply fixes and optimize code iteratively? (y/N): ").strip().lower()
        return user_input == "y"

    def _run_iterative_refinement(self, code: str, initial_analysis: Dict, context: Dict,
                                  api_key: str) -> AnalysisResults:
        """Run iterative code refinement process."""
        refined_issues = initial_analysis['refined_issues']

        # Initial refactoring
        print("  🔧 Applying Initial Fixes...")
        refactored_code = run_refactor_agent(code, refined_issues, api_key)

        if not refactored_code:
            print("⚠️ Initial refactoring failed, using original code")
            refactored_code = code

        # Apply fixes interactively
        feedback = apply_fixes(code, refactored_code, refined_issues)

        # Setup iterative refinement using existing recursive controller
        print("\n♻️ Starting Iterative Optimization...")

        from controls.recursive_controller import build_langgraph_loop
        graph = build_langgraph_loop()
        from controls.recursive_controller import build_langgraph_loop
        graph = build_langgraph_loop()

        state = {
            "api_key": api_key,
            "code": refactored_code,
            "iteration": 0,
            "continue_": True,
            "best_code": code,
            "best_score": initial_analysis['quality_score'],
            "best_issues": refined_issues,
            "issue_count": len(refined_issues),
            "issues_fixed": 0,
            "feedback": feedback,
            "min_score_threshold": self.config.min_quality_threshold,
            "max_high_severity_issues": 0,
            "max_iterations": self.config.max_iterations,
            "context": context,
            "optimization_applied": False
        }

        # Run iterative refinement
        final_state = graph.invoke(state)
        state = {
            "api_key": api_key,
            "code": refactored_code,
            "iteration": 0,
            "continue_": True,
            "best_code": code,
            "best_score": initial_analysis['quality_score'],
            "best_issues": refined_issues,
            "issue_count": len(refined_issues),
            "issues_fixed": 0,
            "feedback": feedback,
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
        final_score = final_state.get("best_score", initial_analysis['quality_score'])
        iterations = len(final_state.get("history", []))
        issues_resolved = sum(step.get('issues_fixed', 0) for step in final_state.get("history", []))

        # Display final results
        self._display_final_results(final_state, initial_analysis)

        return self._create_analysis_results(
            initial_score=initial_analysis['quality_score'],
            final_score=final_score,
            total_issues=len(refined_issues),
            issues_resolved=issues_resolved,
            iterations=iterations,
            final_code=best_code,
            summary={
                'initial_analysis': initial_analysis,
                'final_state': final_state,
                'improvement': final_score - initial_analysis['quality_score']
            }
        )

    def _display_final_results(self, final_state: Dict, initial_analysis: Dict):
        """Display comprehensive final results."""
        print(f"\n🎯 Final Optimization Results:")
        print("=" * 50)

        initial_score = initial_analysis['quality_score']
        final_score = final_state.get("best_score", initial_score)
        improvement = final_score - initial_score

        print(f"📈 Quality Improvement: {initial_score:.1f} → {final_score:.1f} ({improvement:+.1f})")
        print(f"🔄 Iterations Completed: {len(final_state.get('history', []))}")
        print(f"✅ Total Issues Resolved: {sum(step.get('issues_fixed', 0) for step in final_state.get('history', []))}")

        # Show iteration history
        print(f"\n📚 Iteration History:")
        for step in final_state.get("history", []):
            print(f"  Iteration {step.get('iteration', 0)}: Score {step.get('score', 0):.1f}, "
                  f"Fixed {step.get('issues_fixed', 0)} issues")

        print(f"\n✨ Final Code Quality: {final_score:.1f}/100")

    def _create_analysis_results(self, initial_score: float, final_score: float,
                                 total_issues: int, issues_resolved: int,
                                 iterations: int, final_code: str,
                                 summary: Dict) -> AnalysisResults:
        """Create structured analysis results."""
        return AnalysisResults(
            initial_score=initial_score,
            final_score=final_score,
            total_issues_found=total_issues,
            issues_resolved=issues_resolved,
            iterations_performed=iterations,
            final_code=final_code,
            analysis_summary=summary
        )


# Backward compatibility function
def run_control_agent(code: str, language: str, project_dir: str = ".") -> Optional[str]:
    """
    Backward compatible function for running control agent.

    Args:
        code: Source code to analyze
        language: Programming language
        project_dir: Project directory path

    Returns:
        Refactored code or None
    """
    try:
        config = AnalysisConfig(interactive_mode=True)
        agent = EnhancedControlAgent(config)

        results = agent.analyze_code_comprehensive(code, language, project_dir)

        print(f"\n📊 Session Summary:")
        show_session_summary()

        return results.final_code

    except Exception as e:
        logger.error(f"Control agent failed: {e}")
        print(f"❌ Control agent failed: {e}")
        return None
        # Process results
        best_code = final_state.get("best_code", code)
        final_score = final_state.get("best_score", initial_analysis['quality_score'])
        iterations = len(final_state.get("history", []))
        issues_resolved = sum(step.get('issues_fixed', 0) for step in final_state.get("history", []))

        # Display final results
        self._display_final_results(final_state, initial_analysis)

        return self._create_analysis_results(
            initial_score=initial_analysis['quality_score'],
            final_score=final_score,
            total_issues=len(refined_issues),
            issues_resolved=issues_resolved,
            iterations=iterations,
            final_code=best_code,
            summary={
                'initial_analysis': initial_analysis,
                'final_state': final_state,
                'improvement': final_score - initial_analysis['quality_score']
            }
        )

    def _display_final_results(self, final_state: Dict, initial_analysis: Dict):
        """Display comprehensive final results."""
        print(f"\n🎯 Final Optimization Results:")
        print("=" * 50)

        initial_score = initial_analysis['quality_score']
        final_score = final_state.get("best_score", initial_score)
        improvement = final_score - initial_score

        print(f"📈 Quality Improvement: {initial_score:.1f} → {final_score:.1f} ({improvement:+.1f})")
        print(f"🔄 Iterations Completed: {len(final_state.get('history', []))}")
        print(f"✅ Total Issues Resolved: {sum(step.get('issues_fixed', 0) for step in final_state.get('history', []))}")

        # Show iteration history
        print(f"\n📚 Iteration History:")
        for step in final_state.get("history", []):
            print(f"  Iteration {step.get('iteration', 0)}: Score {step.get('score', 0):.1f}, "
                  f"Fixed {step.get('issues_fixed', 0)} issues")

        print(f"\n✨ Final Code Quality: {final_score:.1f}/100")

    def _create_analysis_results(self, initial_score: float, final_score: float,
                                 total_issues: int, issues_resolved: int,
                                 iterations: int, final_code: str,
                                 summary: Dict) -> AnalysisResults:
        """Create structured analysis results."""
        return AnalysisResults(
            initial_score=initial_score,
            final_score=final_score,
            total_issues_found=total_issues,
            issues_resolved=issues_resolved,
            iterations_performed=iterations,
            final_code=final_code,
            analysis_summary=summary
        )


# Backward compatibility function
def run_control_agent(code: str, language: str, project_dir: str = ".") -> Optional[str]:
    """
    Backward compatible function for running control agent.

    Args:
        code: Source code to analyze
        language: Programming language
        project_dir: Project directory path

    Returns:
        Refactored code or None
    """
    try:
        config = AnalysisConfig(interactive_mode=True)
        agent = EnhancedControlAgent(config)
        results = agent.analyze_code_comprehensive(code, language, project_dir)
        print(f"\n📊 Session Summary:")
        show_session_summary()
        return results.final_code
    except Exception as e:
        logger.error(f"Control agent failed: {e}")
        print(f"❌ Control agent failed: {e}")
        return None