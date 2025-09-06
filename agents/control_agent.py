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
from agents.code_smell_agent import run_code_smell_agent  # Added import
from utils.code_diff import show_code_diff
from cli.apply_fixes import apply_fixes
from memory.session_memory import remember_issue, remember_feedback, show_session_summary
from agents.optimization_agent import run_optimization_agent
from utils.language_detector import detect_language
from utils.context_analyzer import analyze_project_context
from agents.iterative_analysis_agent import run_iterative_analysis

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
    """Enhanced control agent with iterative analysis and better categorization."""

    def __init__(self, config: AnalysisConfig = None, mode: str = "full_scan"):
        self.config = config or AnalysisConfig()
        self.mode = mode
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def analyze_code_comprehensive(self,
                                   code: str,
                                   language: str,
                                   project_dir: str = ".") -> AnalysisResults:
        """
        Comprehensive code analysis with iterative analysis and categorization.

        Args:
            code: Source code to analyze
            language: Programming language
            project_dir: Project directory for context

        Returns:
            Structured analysis results with categorized issues
        """
        print(f"\n🧠 Enhanced Control Agent Activated (Iterative Mode)")
        print(f"➡️ Language: {language}, Mode: {self.mode}")
        print("=" * 60)

        # Validate inputs
        if not code.strip():
            raise ValueError("Empty code provided for analysis")

        # Initialize analysis context
        api_key = self._get_api_key()
        context = analyze_project_context(project_dir)

        print(f"📋 Project Context Analysis:")
        self._print_context_summary(context)

        # Phase 1: Iterative Analysis
        print(f"\n🔍 Phase 1: Iterative {self.mode.replace('_', ' ').title()} Analysis")
        print("-" * 40)

        iterative_results = run_iterative_analysis(
            code=code,
            api_key=api_key,
            mode=self.mode,
            context=context
        )

        # Display categorized results
        self._display_categorized_results(iterative_results)

        # Check if refinement is needed/wanted
        if not self.config.interactive_mode:
            return self._create_analysis_results(
                initial_score=self._calculate_overall_score(iterative_results),
                final_score=self._calculate_overall_score(iterative_results),
                total_issues=iterative_results['total_unique_issues'],
                issues_resolved=0,
                iterations=iterative_results['iterations_run'],
                final_code=code,
                summary=iterative_results,
                issues_by_category=iterative_results.get('issues_by_category', {})
            )

        if not self._should_proceed_with_refinement(iterative_results):
            return self._create_analysis_results(
                initial_score=self._calculate_overall_score(iterative_results),
                final_score=self._calculate_overall_score(iterative_results),
                total_issues=iterative_results['total_unique_issues'],
                issues_resolved=0,
                iterations=iterative_results['iterations_run'],
                final_code=code,
                summary=iterative_results,
                issues_by_category=iterative_results.get('issues_by_category', {})
            )

        # Phase 2: Interactive Refinement
        print(f"\n🔁 Phase 2: Interactive Code Refinement")
        print("-" * 40)

        refinement_results = self._run_interactive_refinement(
            code, iterative_results, context, api_key
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
        print(f"\n📊 Iterative Analysis Results:")
        print(f"  Mode: {results['mode']}")
        print(f"  Iterations: {results['iterations_run']}")
        print(f"  Total Issues: {results['total_unique_issues']}")
        print(f"  Stopping Reason: {results['stopping_reason']}")

        # Show iteration progression
        print(f"\n📈 Analysis Progress:")
        for iteration in results['iteration_history']:
            print(f"  Iteration {iteration['iteration']}: "
                  f"{iteration['total_issues']} total, "
                  f"{iteration['new_issues']} new issues found")

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
                print(f"\n  {emoji} {category.upper()} ({len(issues)} issues):")

                # Group by severity
                severity_groups = {'high': [], 'medium': [], 'low': []}
                for issue in issues[:10]:  # Limit display
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
                            print(f"      {i}. Line {line}: {desc}...")

                        if len(severity_groups[severity]) > 3:
                            print(f"      ... and {len(severity_groups[severity]) - 3} more")

    def _calculate_overall_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall quality score based on issues."""
        total_issues = results.get('total_unique_issues', 0)
        if total_issues == 0:
            return 100.0

        # Weight penalties by category and severity
        category_weights = {
            'security': 3.0,
            'quality': 2.0,
            'code_smell': 1.5,
            'static': 1.0
        }

        severity_weights = {
            'high': 3.0,
            'medium': 2.0,
            'low': 1.0
        }

        total_penalty = 0.0
        issues_by_category = results.get('issues_by_category', {})

        for category, issues in issues_by_category.items():
            cat_weight = category_weights.get(category, 1.0)

            for issue in issues:
                sev_weight = severity_weights.get(issue.get('severity', 'medium'), 2.0)
                confidence = issue.get('confidence', 0.8)
                penalty = cat_weight * sev_weight * confidence * 2  # Base penalty
                total_penalty += penalty

        # Cap penalty and convert to score
        max_penalty = min(total_penalty, 100)
        return max(0, 100 - max_penalty)

    def _should_proceed_with_refinement(self, results: Dict[str, Any]) -> bool:
        """Determine if refinement should proceed."""
        score = self._calculate_overall_score(results)
        total_issues = results['total_unique_issues']

        # Auto-proceed if quality is below threshold
        if score < self.config.min_quality_threshold:
            print(f"\n⚡ Quality score ({score:.1f}) below threshold ({self.config.min_quality_threshold})")
            return True

        if total_issues == 0:
            print(f"\n✅ No issues found! Code quality looks good.")
            return False

        user_input = input(f"\n🤖 Apply fixes and optimize code? (y/N): ").strip().lower()
        return user_input == "y"

    def _run_interactive_refinement(self, code: str, analysis_results: Dict,
                                   context: Dict, api_key: str) -> AnalysisResults:
        """Run interactive code refinement process."""
        final_issues = analysis_results.get('final_issues', [])

        print(f"  🔧 Applying User-Selected Fixes...")
        feedback = apply_fixes(code, code, final_issues, api_key)

        # Apply refactoring
        refactored_code = code
        applied_issues = [f["issue"] for f in feedback if f["applied"]]
        if applied_issues:
            refactored_code = run_refactor_agent(code, applied_issues, api_key) or code

        # Calculate final metrics
        initial_score = self._calculate_overall_score(analysis_results)

        # Re-analyze refactored code for final score
        if refactored_code != code:
            print(f"\n📊 Re-analyzing refactored code...")
            final_analysis = run_iterative_analysis(
                code=refactored_code,
                api_key=api_key,
                mode=self.mode,
                context=context
            )
            final_score = self._calculate_overall_score(final_analysis)
            final_issues_by_category = final_analysis.get('issues_by_category', {})
        else:
            final_score = initial_score
            final_issues_by_category = analysis_results.get('issues_by_category', {})

        return self._create_analysis_results(
            initial_score=initial_score,
            final_score=final_score,
            total_issues=len(final_issues),
            issues_resolved=len(applied_issues),
            iterations=analysis_results['iterations_run'],
            final_code=refactored_code,
            summary={
                'initial_analysis': analysis_results,
                'applied_fixes': len(applied_issues),
                'improvement': final_score - initial_score
            },
            issues_by_category=final_issues_by_category
        )

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


# Backward compatibility function with iterative analysis
def run_control_agent(code: str, language: str, project_dir: str = ".",
                     mode: str = "full_scan") -> Optional[str]:
    """
    Enhanced control agent with iterative analysis.

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

        show_session_summary()
        return results.final_code
    except Exception as e:
        logger.error(f"Control agent failed: {e}")
        print(f"❌ Control agent failed: {e}")
        return None