# agents/iterative_analysis_agent.py
import json
import hashlib
from typing import Dict, List, Any, Set, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
from enum import Enum

from agents.quality_agent import run_quality_agent
from agents.security_agent import run_security_agent
from agents.code_smell_agent import run_code_smell_agent
from agents.static_analysis_agent import run_static_analysis
from agents.critic_agent import run_critic_agent
from memory.session_memory import remember_issue


class IssueCategory(Enum):
    QUALITY = "quality"
    SECURITY = "security"
    CODE_SMELL = "code_smell"
    STATIC = "static"


@dataclass
class CategorizedIssue:
    """Structured issue with category and metadata."""
    line: int
    description: str
    suggestion: str
    severity: str
    confidence: float
    category: IssueCategory
    source_agent: str
    iteration_found: int
    issue_id: str  # Unique identifier based on content hash

    def to_dict(self) -> Dict:
        result = asdict(self)
        result['category'] = self.category.value
        return result

    @classmethod
    def from_raw_issue(cls, issue: Dict, category: IssueCategory,
                       source_agent: str, iteration: int) -> 'CategorizedIssue':
        """Create from raw issue dict."""
        description = issue.get('description', issue.get('issue', ''))
        suggestion = issue.get('suggestion', '')

        # Create unique ID based on content
        content = f"{issue.get('line', 0)}|{description}|{suggestion}"
        issue_id = hashlib.md5(content.encode()).hexdigest()[:12]

        return cls(
            line=issue.get('line', 0),
            description=description,
            suggestion=suggestion,
            severity=issue.get('severity', 'medium'),
            confidence=issue.get('confidence', 0.8),
            category=category,
            source_agent=source_agent,
            iteration_found=iteration,
            issue_id=issue_id
        )


class IterativeAnalysisAgent:
    """Enhanced iterative analysis with proper issue tracking."""

    def __init__(self, api_key: str, max_iterations: int = 3):
        self.api_key = api_key
        self.max_iterations = max_iterations
        self.issue_history: Dict[int, List[CategorizedIssue]] = {}
        self.cumulative_issues: Dict[str, CategorizedIssue] = {}

    def analyze_iteratively(self, code: str, mode: str = "full_scan",
                            context: Dict = None) -> Dict[str, Any]:
        """
        Run iterative analysis with proper issue tracking.

        Args:
            code: Source code to analyze
            mode: Analysis mode (quality, security, code_smell, full_scan)
            context: Project context

        Returns:
            Comprehensive analysis results with categorized issues
        """
        print(f"\n🔄 Starting Iterative Analysis - Mode: {mode}")
        print("=" * 60)

        analysis_results = {
            'mode': mode,
            'iterations_run': 0,
            'total_unique_issues': 0,
            'issues_by_category': defaultdict(list),
            'iteration_history': [],
            'final_issues': [],
            'stopping_reason': ''
        }

        previous_issue_signatures = set()
        stable_iterations = 0

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n🔍 Iteration {iteration}/{self.max_iterations}")
            print("-" * 40)

            # Run analysis based on mode
            iteration_issues = self._run_single_iteration(
                code, mode, context, iteration
            )

            # Track new issues
            current_signatures = {issue.issue_id for issue in iteration_issues}
            new_issues = [
                issue for issue in iteration_issues
                if issue.issue_id not in previous_issue_signatures
            ]

            # Update cumulative tracking
            for issue in iteration_issues:
                if issue.issue_id not in self.cumulative_issues:
                    self.cumulative_issues[issue.issue_id] = issue

            self.issue_history[iteration] = iteration_issues

            # Log iteration results
            iteration_summary = {
                'iteration': iteration,
                'total_issues': len(iteration_issues),
                'new_issues': len(new_issues),
                'issues_by_category': self._categorize_issues(iteration_issues)
            }
            analysis_results['iteration_history'].append(iteration_summary)

            print(f"   📊 Total issues: {len(iteration_issues)}")
            print(f"   ✨ New issues: {len(new_issues)}")

            # Check stopping criteria
            if len(new_issues) == 0:
                stable_iterations += 1
                print(f"   ⚖️ Stable iteration {stable_iterations}")
            else:
                stable_iterations = 0

            # Stop if issues have stabilized
            if stable_iterations >= 2:
                analysis_results['stopping_reason'] = 'Issues stabilized (no new issues for 2 iterations)'
                break

            previous_issue_signatures = current_signatures

            # Stop if no issues found at all
            if len(iteration_issues) == 0:
                analysis_results['stopping_reason'] = 'No issues detected'
                break

        # Finalize results
        analysis_results['iterations_run'] = iteration
        final_issues_list = list(self.cumulative_issues.values())

        # Run critic agent on final issue set
        if final_issues_list:
            print(f"\n🤔 Running Critic Agent on {len(final_issues_list)} total issues...")
            final_issues_dicts = [issue.to_dict() for issue in final_issues_list]
            refined_issues = run_critic_agent(code, final_issues_dicts, self.api_key)

            # Convert back to CategorizedIssue objects
            final_issues_list = []
            for issue_dict in refined_issues:
                # Preserve original category if available
                category_str = issue_dict.get('category', 'quality')
                try:
                    category = IssueCategory(category_str)
                except ValueError:
                    category = IssueCategory.QUALITY

                categorized_issue = CategorizedIssue.from_raw_issue(
                    issue_dict, category, 'critic', iteration
                )
                final_issues_list.append(categorized_issue)

        # Organize final results
        analysis_results['final_issues'] = [issue.to_dict() for issue in final_issues_list]
        analysis_results['total_unique_issues'] = len(final_issues_list)
        analysis_results['issues_by_category'] = self._categorize_final_issues(final_issues_list)

        if not analysis_results['stopping_reason']:
            analysis_results['stopping_reason'] = f'Reached maximum iterations ({self.max_iterations})'

        self._print_final_summary(analysis_results)
        return analysis_results

    def _run_single_iteration(self, code: str, mode: str, context: Dict,
                              iteration: int) -> List[CategorizedIssue]:
        """Run a single analysis iteration."""
        all_issues = []

        if mode in ['quality', 'full_scan']:
            print("   🎯 Running Quality Analysis...")
            quality_results = run_quality_agent(code, self.api_key, context)
            for issue in quality_results.get('issues', []):
                categorized = CategorizedIssue.from_raw_issue(
                    issue, IssueCategory.QUALITY, 'quality_agent', iteration
                )
                all_issues.append(categorized)

        if mode in ['security', 'full_scan']:
            print("   🔒 Running Security Analysis...")
            security_results = run_security_agent(code, self.api_key, context)
            for issue in security_results.get('issues', []):
                categorized = CategorizedIssue.from_raw_issue(
                    issue, IssueCategory.SECURITY, 'security_agent', iteration
                )
                all_issues.append(categorized)

        if mode in ['code_smell', 'full_scan']:
            print("   👃 Running Code Smell Analysis...")
            smell_results = run_code_smell_agent(code, api_key=self.api_key)
            for issue in smell_results.get('issues', []):
                categorized = CategorizedIssue.from_raw_issue(
                    issue, IssueCategory.CODE_SMELL, 'code_smell_agent', iteration
                )
                all_issues.append(categorized)

        # Remove duplicates within this iteration
        unique_issues = {}
        for issue in all_issues:
            if issue.issue_id not in unique_issues:
                unique_issues[issue.issue_id] = issue

        return list(unique_issues.values())

    def _categorize_issues(self, issues: List[CategorizedIssue]) -> Dict[str, int]:
        """Count issues by category."""
        counts = defaultdict(int)
        for issue in issues:
            counts[issue.category.value] += 1
        return dict(counts)

    def _categorize_final_issues(self, issues: List[CategorizedIssue]) -> Dict[str, List[Dict]]:
        """Organize final issues by category."""
        categorized = defaultdict(list)
        for issue in issues:
            categorized[issue.category.value].append(issue.to_dict())
        return dict(categorized)

    def _print_final_summary(self, results: Dict[str, Any]):
        """Print comprehensive final summary."""
        print(f"\n🎯 Iterative Analysis Complete")
        print("=" * 60)
        print(f"📊 Mode: {results['mode']}")
        print(f"🔄 Iterations: {results['iterations_run']}")
        print(f"📋 Total Unique Issues: {results['total_unique_issues']}")
        print(f"⏹️ Stopping Reason: {results['stopping_reason']}")

        # Show issues by category
        if results['issues_by_category']:
            print(f"\n📊 Issues by Category:")
            for category, issues in results['issues_by_category'].items():
                print(f"   {category.upper()}: {len(issues)} issues")

        # Show iteration progression
        print(f"\n📈 Iteration History:")
        for hist in results['iteration_history']:
            print(f"   Iteration {hist['iteration']}: {hist['total_issues']} total, {hist['new_issues']} new")


# Integration function for backward compatibility
def run_iterative_analysis(code: str, api_key: str, mode: str = "full_scan",
                           context: Dict = None) -> Dict[str, Any]:
    """
    Convenience function for running iterative analysis.

    Args:
        code: Source code to analyze
        api_key: API key for AI services
        mode: Analysis mode
        context: Project context

    Returns:
        Comprehensive analysis results
    """
    agent = IterativeAnalysisAgent(api_key, max_iterations=3)
    return agent.analyze_iteratively(code, mode, context)