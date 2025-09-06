# cli/enhanced_apply_fixes.py
import difflib
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
from agents.refactor_agent import run_refactor_agent
from agents.comprehensive_analysis_agent import run_comprehensive_analysis
from memory.session_memory import remember_issue, remember_feedback
from utils.code_diff import show_code_diff
from controls.recursive_controller import build_langgraph_loop
import json


class IssueCategory(Enum):
    STRUCTURAL = "structural"  # Long functions, complexity, deep nesting
    DESIGN = "design"  # Parameter coupling, cohesion, SRP violations
    STYLE = "style"  # Naming, comments, formatting
    SECURITY = "security"  # Security vulnerabilities
    PERFORMANCE = "performance"  # Performance issues


class IssuePriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class StoppingCriteria:
    """Configuration for when to stop refactoring."""
    score_threshold: float = 85.0
    max_low_severity_issues: int = 3
    max_iterations: int = 8
    plateau_iterations: int = 3  # Stop after N iterations with minimal improvement
    min_improvement_per_iteration: float = 1.0
    acceptable_issue_categories: Set[str] = None  # Issues that are acceptable to leave

    def __post_init__(self):
        if self.acceptable_issue_categories is None:
            self.acceptable_issue_categories = {"style", "design"}


class RefactoringProgressTracker:
    """Track refactoring progress and detect convergence patterns."""

    def __init__(self, criteria: StoppingCriteria):
        self.criteria = criteria
        self.iteration_history = []
        self.issue_type_history = []
        self.score_history = []

    def add_iteration(self, iteration_data: dict):
        """Add iteration data for analysis."""
        self.iteration_history.append(iteration_data)
        issue_categories = self._categorize_issues(iteration_data.get('issues', []))
        self.issue_type_history.append(issue_categories)
        score = iteration_data.get('score', 0)
        self.score_history.append(score)

    def _categorize_issues(self, issues: List[Dict]) -> Dict[IssueCategory, int]:
        """Categorize issues by type."""
        categories = {cat: 0 for cat in IssueCategory}
        for issue in issues:
            description = issue.get('description', '').lower()
            category = self._classify_issue(description)
            categories[category] += 1
        return categories

    def _classify_issue(self, description: str) -> IssueCategory:
        """Classify an issue into a category based on description."""
        structural_keywords = ['long method', 'long function', 'long class', 'complexity', 'cyclomatic', 'nesting', 'too many', 'large class']
        design_keywords = ['single responsibility', 'parameter', 'cohesion', 'coupling', 'multiple operations', 'violates', 'separate functions', 'passed together', 'data class', 'feature envy']
        style_keywords = ['naming', 'comment', 'formatting', 'convention', 'style', 'redundant', 'magic number', 'variable name']
        security_keywords = ['security', 'vulnerability', 'injection', 'hardcode', 'password', 'token', 'unsafe']
        performance_keywords = ['performance', 'inefficient', 'slow', 'optimization', 'memory', 'loop', 'algorithm']
        if any(keyword in description for keyword in structural_keywords):
            return IssueCategory.STRUCTURAL
        elif any(keyword in description for keyword in design_keywords):
            return IssueCategory.DESIGN
        elif any(keyword in description for keyword in style_keywords):
            return IssueCategory.STYLE
        elif any(keyword in description for keyword in security_keywords):
            return IssueCategory.SECURITY
        elif any(keyword in description for keyword in performance_keywords):
            return IssueCategory.PERFORMANCE
        return IssueCategory.DESIGN

    def should_stop_refactoring(self) -> Tuple[bool, str, Dict]:
        """Determine if refactoring should stop based on convergence patterns."""
        analysis = self._analyze_current_state()
        if analysis['score'] >= self.criteria.score_threshold and analysis['only_acceptable_issues']:
            return True, f"Quality threshold reached ({analysis['score']:.1f}) with only acceptable issue types", analysis
        if analysis['only_low_severity']:
            return True, "Only low-severity issues remaining", analysis
        if analysis['score_plateaued']:
            return True, f"Score plateaued for {self.criteria.plateau_iterations} iterations", analysis
        if len(self.iteration_history) >= self.criteria.max_iterations:
            return True, f"Maximum iterations ({self.criteria.max_iterations}) reached", analysis
        if analysis['diminishing_returns']:
            return True, "Diminishing returns detected", analysis
        if analysis['issue_cycling']:
            return True, "Issue types are cycling - refactoring loop detected", analysis
        return False, "Continue refactoring", analysis

    def _analyze_current_state(self) -> Dict:
        """Analyze current refactoring state."""
        if not self.iteration_history:
            return {"status": "no_data"}
        current_iteration = self.iteration_history[-1]
        current_issues = current_iteration.get('issues', [])
        current_score = current_iteration.get('score', 0)
        issue_severities = [issue.get('severity', 'medium') for issue in current_issues]
        only_low_severity = all(sev == 'low' for sev in issue_severities)
        current_categories = self._categorize_issues(current_issues)
        total_unacceptable = sum(count for cat, count in current_categories.items() if cat.value not in self.criteria.acceptable_issue_categories)
        only_acceptable_issues = total_unacceptable <= self.criteria.max_low_severity_issues
        return {
            'score': current_score,
            'total_issues': len(current_issues),
            'only_low_severity': only_low_severity,
            'only_acceptable_issues': only_acceptable_issues,
            'score_plateaued': self._has_score_plateau(),
            'diminishing_returns': self._has_diminishing_returns(),
            'issue_cycling': self._has_issue_cycling(),
            'category_breakdown': {cat.value: count for cat, count in current_categories.items()},
            'unacceptable_issues': total_unacceptable
        }

    def _has_score_plateau(self) -> bool:
        if len(self.score_history) < self.criteria.plateau_iterations + 1:
            return False
        recent_scores = self.score_history[-(self.criteria.plateau_iterations + 1):]
        improvements = [recent_scores[i] - recent_scores[i - 1] for i in range(1, len(recent_scores))]
        return all(imp < self.criteria.min_improvement_per_iteration for imp in improvements)

    def _has_diminishing_returns(self) -> bool:
        if len(self.score_history) < 3:
            return False
        recent_improvements = [self.score_history[i] - self.score_history[i - 1] for i in range(len(self.score_history) - 2, len(self.score_history)) if i > 0]
        return len(recent_improvements) >= 2 and all(imp < 0.5 for imp in recent_improvements)

    def _has_issue_cycling(self) -> bool:
        if len(self.issue_type_history) < 4:
            return False
        recent_patterns = self.issue_type_history[-4:]
        pattern_signatures = [frozenset(cat.value for cat, count in categories.items() if count > 0) for categories in recent_patterns]
        return len(set(pattern_signatures)) <= 2


class SmartFixApplicator:
    """Enhanced fix applicator with smart convergence detection and issue prioritization."""

    def __init__(self, api_key: str, stopping_criteria: StoppingCriteria = None):
        self.api_key = api_key
        self.stopping_criteria = stopping_criteria or StoppingCriteria()
        self.session_history = []

    def apply_fixes_smart(self, original_code: str, issues: List[Dict[str, Any]], context: Dict = None, mode: str = "full_scan", fix_mode: str = "automatic") -> Tuple[str, List[Dict]]:
        """
        Smart fix application with convergence detection and issue prioritization.

        Args:
            original_code: Original source code
            issues: List of detected issues
            context: Project context
            mode: Analysis mode
            fix_mode: 'automatic' or 'interactive'

        Returns:
            Tuple of (final_code, session_feedback)
        """
        if not issues:
            return original_code, [{"status": "no_issues", "message": "No issues to fix"}]

        # Analyze initial issue composition (without printing for API)
        self._analyze_initial_issues(issues)

        # Select mode
        application_mode = self._select_application_mode(fix_mode)

        if application_mode == "interactive":
            return self._run_smart_interactive_mode(original_code, issues, context, mode)
        else:
            return self._run_automatic_mode(original_code, issues, context, mode)

    def _analyze_initial_issues(self, issues: List[Dict]):
        """Analyze initial issue composition."""
        self.issue_counts = {'structural': 0, 'design': 0, 'style': 0, 'security': 0, 'performance': 0}
        self.severity_counts = {'high': 0, 'medium': 0, 'low': 0}
        for issue in issues:
            description = issue.get('description', '').lower()
            severity = issue.get('severity', 'medium')
            self.severity_counts[severity] += 1
            if any(kw in description for kw in ['long method', 'complexity', 'nesting']):
                self.issue_counts['structural'] += 1
            elif any(kw in description for kw in ['parameter', 'responsibility', 'coupling']):
                self.issue_counts['design'] += 1
            elif any(kw in description for kw in ['comment', 'naming', 'style']):
                self.issue_counts['style'] += 1
            elif any(kw in description for kw in ['security', 'vulnerability']):
                self.issue_counts['security'] += 1
            elif any(kw in description for kw in ['performance', 'inefficient']):
                self.issue_counts['performance'] += 1

    def _select_application_mode(self, fix_mode: str) -> str:
        """Select between interactive and automatic modes."""
        if fix_mode == "automatic":
            return "automatic"
        return "interactive"

    def _run_smart_interactive_mode(self, original_code: str, issues: List[Dict], context: Dict, mode: str) -> Tuple[str, List[Dict]]:
        """Run smart interactive mode with convergence detection."""
        print("\n🔄 Smart Interactive Mode Activated")
        print("=" * 40)
        tracker = RefactoringProgressTracker(self.stopping_criteria)
        current_code = original_code
        remaining_issues = issues.copy()
        iteration = 0
        total_feedback = []

        print(f"\n💡 Smart Recommendations:")
        print(f"   📈 Target Score: {self.stopping_criteria.score_threshold}")
        print(f"   🔄 Max Iterations: {self.stopping_criteria.max_iterations}")
        print(f"   ✅ Will stop when only style/design issues remain")

        while remaining_issues:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")
            print(f"📊 Current Status: {len(remaining_issues)} issues remaining")

            current_score = self._get_current_score(current_code, context, mode)
            tracker.add_iteration({'iteration': iteration, 'score': current_score, 'issues': remaining_issues})
            should_stop, reason, analysis = tracker.should_stop_refactoring()
            if should_stop:
                print(f"\n🎯 Smart Stop Recommendation: {reason}")
                self._display_convergence_analysis(analysis)
                continue_anyway = input(f"\n🤔 Continue refactoring anyway? (y/N): ").strip().lower()
                if continue_anyway != 'y':
                    print("🛑 Stopping based on smart analysis.")
                    break

            self._display_smart_issues(remaining_issues)
            selected_issues = self._get_smart_issue_selection(remaining_issues, analysis)
            if not selected_issues:
                print("🛑 User chose to stop. Exiting interactive mode.")
                break

            print(f"\n🔧 Applying {len(selected_issues)} selected fixes...")
            fixed_code = self._apply_selected_fixes(current_code, selected_issues)
            if fixed_code != current_code:
                show_code_diff(current_code, fixed_code, f"Changes from Iteration {iteration}")
                if self._confirm_changes():
                    current_code = fixed_code
                    iteration_feedback = [{"issue": issue, "applied": True, "iteration": iteration, "reason": "Applied in smart interactive mode"} for issue in selected_issues]
                    total_feedback.extend(iteration_feedback)
                    print(f"\n🔍 Re-analyzing updated code...")
                    remaining_issues = self._reanalyze_code(current_code, context, mode)
                    self._show_smart_progress_summary(iteration, len(selected_issues), len(remaining_issues), current_score)
                    for issue in selected_issues:
                        remember_issue(issue)
                        remember_feedback(description=f"Smart interactive fix applied: {issue.get('description', '')}", accepted=True, line=issue.get('line', 'N/A'))
                else:
                    print("⏭️ Changes discarded. Continuing with current code.")
            else:
                print("⚠️ No changes produced by refactor agent.")
                remaining_issues = [issue for issue in remaining_issues if issue not in selected_issues]

            if remaining_issues and not should_stop:
                if not self._ask_continue():
                    print("🛑 User chose to stop iterations.")
                    break

        print(f"\n✅ Smart interactive mode completed after {iteration} iterations")
        final_score = self._get_current_score(current_code, context, mode)
        self._show_smart_final_summary(original_code, current_code, total_feedback, tracker.score_history[0] if tracker.score_history else 0, final_score)
        return current_code, total_feedback

    def _get_current_score(self, code: str, context: Dict, mode: str) -> float:
        """Get current quality score through re-analysis."""
        try:
            results = run_comprehensive_analysis(code=code, api_key=self.api_key, mode=mode, context=context or {})
            return results.get('overall_score', 0)
        except Exception as e:
            print(f"⚠️ Score calculation failed: {e}")
            return 0

    def _display_convergence_analysis(self, analysis: Dict):
        """Display convergence analysis to user."""
        print(f"\n📊 Convergence Analysis:")
        print(f"   📈 Current Score: {analysis.get('score', 0):.1f}")
        print(f"   📋 Remaining Issues: {analysis.get('total_issues', 0)}")
        print(f"   📂 Category Breakdown:")
        for category, count in analysis.get('category_breakdown', {}).items():
            if count > 0:
                print(f"      {category.title()}: {count}")
        print(f"   🎯 Unacceptable Issues: {analysis.get('unacceptable_issues', 0)}")

    def _display_smart_issues(self, issues: List[Dict]):
        """Display issues with smart categorization and recommendations."""
        print(f"\n📋 Current Issues ({len(issues)} total):")
        structural = design = style = security = performance = []
        for i, issue in enumerate(issues, 1):
            description = issue.get('description', '').lower()
            issue_with_index = {**issue, 'index': i}
            if any(kw in description for kw in ['long method', 'complexity', 'nesting']):
                structural.append(issue_with_index)
            elif any(kw in description for kw in ['parameter', 'responsibility', 'coupling']):
                design.append(issue_with_index)
            elif any(kw in description for kw in ['comment', 'naming', 'style']):
                style.append(issue_with_index)
            elif any(kw in description for kw in ['security', 'vulnerability']):
                security.append(issue_with_index)
            else:
                design.append(issue_with_index)
        if security:
            print(f"\n🔒 SECURITY ISSUES (Fix First!):")
            self._display_issue_group(security)
        if structural:
            print(f"\n🔧 STRUCTURAL ISSUES (High Priority):")
            self._display_issue_group(structural)
        if design:
            print(f"\n🎨 DESIGN ISSUES (Medium Priority):")
            self._display_issue_group(design)
        if style:
            print(f"\n✨ STYLE ISSUES (Low Priority):")
            self._display_issue_group(style)

    def _display_issue_group(self, issue_group: List[Dict]):
        """Display a group of issues."""
        for issue in issue_group:
            severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
            severity = issue.get('severity', 'medium')
            emoji = severity_emoji.get(severity, '🟡')
            print(f"  {emoji} {issue['index']:2d}. Line {issue.get('line', 'N/A')}")
            desc = issue.get('description', 'No description')
            print(f"      {desc[:100]}{'...' if len(desc) > 100 else ''}")

    def _get_smart_issue_selection(self, issues: List[Dict], analysis: Dict) -> List[Dict]:
        """Get user's selection with smart recommendations."""
        print(f"\n🎯 Smart Fix Selection:")
        unacceptable_count = analysis.get('unacceptable_issues', 0)
        if unacceptable_count <= 3:
            print("💡 Smart Recommendation: Focus on structural/security issues only")
        print("1. Select specific issue numbers (e.g., '1,3,5')")
        print("2. Select by priority ('security', 'structural', 'design', 'style')")
        print("3. Select by severity ('high', 'medium', 'low')")
        print("4. Select 'smart' for AI recommendation")
        print("5. Select all issues ('all')")
        print("6. Stop fixing ('none' or 'stop')")
        while True:
            user_input = input("\nEnter your selection: ").strip().lower()
            if user_input in ['none', 'stop', 'exit']:
                return []
            elif user_input == 'all':
                return issues
            elif user_input == 'smart':
                return self._get_smart_recommendations(issues, analysis)
            elif user_input in ['security', 'structural', 'design', 'style']:
                return self._filter_by_category(issues, user_input)
            elif user_input in ['high', 'medium', 'low']:
                return [issue for issue in issues if issue.get('severity', 'medium') == user_input]
            else:
                try:
                    numbers = [int(n.strip()) for n in user_input.split(',')]
                    if all(1 <= n <= len(issues) for n in numbers):
                        return [issues[n - 1] for n in numbers]
                    else:
                        print(f"❌ Invalid numbers. Must be between 1 and {len(issues)}")
                except ValueError:
                    print("❌ Invalid input. Please try again.")

    def _get_smart_recommendations(self, issues: List[Dict], analysis: Dict) -> List[Dict]:
        """Get AI-based smart recommendations for which issues to fix."""
        recommended = []
        for issue in issues:
            description = issue.get('description', '').lower()
            severity = issue.get('severity', 'medium')
            if any(kw in description for kw in ['security', 'vulnerability']):
                recommended.append(issue)
            elif any(kw in description for kw in ['long method', 'complexity', 'nesting']):
                recommended.append(issue)
            elif severity == 'high' and any(kw in description for kw in ['parameter', 'responsibility']):
                recommended.append(issue)
        if recommended:
            print(f"🤖 Smart recommendation: {len(recommended)} high-priority issues selected")
        else:
            print("🤖 Smart recommendation: Consider stopping - only low-priority issues remain")
        return recommended

    def _filter_by_category(self, issues: List[Dict], category: str) -> List[Dict]:
        """Filter issues by category."""
        filtered = []
        category_keywords = {
            'security': ['security', 'vulnerability'],
            'structural': ['long method', 'complexity', 'nesting'],
            'design': ['parameter', 'responsibility', 'coupling'],
            'style': ['comment', 'naming', 'style']
        }
        keywords = category_keywords.get(category, [])
        for issue in issues:
            description = issue.get('description', '').lower()
            if any(kw in description for kw in keywords):
                filtered.append(issue)
        return filtered

    def _apply_selected_fixes(self, code: str, selected_issues: List[Dict]) -> str:
        """Apply the selected fixes to the code."""
        return run_refactor_agent(code, selected_issues, self.api_key) or code

    def _confirm_changes(self) -> bool:
        """Ask user to confirm the changes."""
        response = input("\n✅ Apply these changes? (y/N): ").strip().lower()
        return response == 'y'

    def _reanalyze_code(self, code: str, context: Dict, mode: str) -> List[Dict]:
        """Re-analyze the code and return new issues."""
        try:
            results = run_comprehensive_analysis(code=code, api_key=self.api_key, mode=mode, context=context or {})
            return results.get('final_issues', [])
        except Exception as e:
            print(f"⚠️ Re-analysis failed: {e}")
            return []

    def _show_smart_progress_summary(self, iteration: int, fixes_applied: int, remaining_issues: int, current_score: float):
        """Show smart progress summary after each iteration."""
        print(f"\n📊 Smart Progress Summary - Iteration {iteration}:")
        print(f"   ✅ Fixes Applied: {fixes_applied}")
        print(f"   📋 Remaining Issues: {remaining_issues}")
        print(f"   📈 Current Score: {current_score:.1f}")
        if remaining_issues == 0:
            print("   🎉 All issues resolved!")

    def _ask_continue(self) -> bool:
        """Ask user if they want to continue with more iterations."""
        response = input("\n🔄 Continue with more fixes? (y/N): ").strip().lower()
        return response == 'y'

    def _run_automatic_mode(self, original_code: str, issues: List[Dict], context: Dict, mode: str) -> Tuple[str, List[Dict]]:
        """Run automatic optimization mode using iterative process."""
        tracker = RefactoringProgressTracker(self.stopping_criteria)
        graph = build_langgraph_loop()
        state = {
            "api_key": self.api_key,
            "code": original_code,
            "iteration": 0,
            "continue_": True,
            "best_code": original_code,
            "best_score": 0,
            "best_issues": issues,
            "issue_count": len(issues),
            "issues_fixed": 0,
            "feedback": [],
            "min_score_threshold": self.stopping_criteria.score_threshold,
            "max_high_severity_issues": 0,
            "max_iterations": self.stopping_criteria.max_iterations,
            "context": context or {},
            "optimization_applied": False,
            "previous_scores": [],
            "stagnation_count": 0,
            "user_stop": False
        }
        final_state = graph.invoke(state)
        best_code = final_state.get("best_code", original_code)
        final_score = final_state.get("best_score", 0)
        history = final_state.get("history", [])
        feedback = [{
            "mode": "automatic",
            "initial_issues": len(issues),
            "final_score": final_score,
            "iterations": len(history),
            "optimization_applied": final_state.get("optimization_applied", False),
            "history": history
        }]
        return best_code, feedback

    def _show_smart_final_summary(self, original_code: str, final_code: str, feedback: List[Dict], initial_score: float, final_score: float):
        """Show smart final summary of the session."""
        print(f"\n📊 Smart Session Summary:")
        print("=" * 40)
        total_applied = len([f for f in feedback if f.get("applied", False)])
        total_iterations = max([f.get("iteration", 0) for f in feedback] + [0])
        improvement = final_score - initial_score
        print(f"🔄 Total Iterations: {total_iterations}")
        print(f"✅ Total Fixes Applied: {total_applied}")
        print(f"📈 Score Improvement: {initial_score:.1f} → {final_score:.1f} ({improvement:+.1f})")
        if final_score >= self.stopping_criteria.score_threshold:
            print("🏆 Target quality threshold achieved!")
        elif improvement > 10:
            print("📈 Significant improvement made!")
        elif improvement > 5:
            print("✅ Good improvement made!")
        else:
            print("📊 Minimal improvement - may have reached optimal point")
        if final_code != original_code:
            show_final = input("\n📝 Show complete final diff? (y/N): ").strip().lower()
            if show_final == 'y':
                show_code_diff(original_code, final_code, "Complete Smart Session Changes")


def apply_fixes_smart(original_code: str, issues: List[Dict[str, Any]], api_key: str = None, context: Dict = None, mode: str = "full_scan", stopping_criteria: StoppingCriteria = None, fix_mode: str = "automatic") -> Tuple[str, List[Dict]]:
    """
    Smart fix application with convergence detection and issue prioritization.

    Args:
        original_code: Original source code
        issues: List of issues to fix
        api_key: API key for refactor agent
        context: Project context
        mode: Analysis mode
        stopping_criteria: Custom stopping criteria
        fix_mode: 'automatic' or 'interactive'

    Returns:
        Tuple of (final_code, feedback)
    """
    if not api_key:
        raise ValueError("API key is required for smart fix application")

    if not stopping_criteria:
        high_severity_count = sum(1 for issue in issues if issue.get('severity') == 'high')
        security_count = sum(1 for issue in issues if 'security' in issue.get('description', '').lower())
        if security_count > 0:
            stopping_criteria = StoppingCriteria(score_threshold=90.0, max_iterations=10, plateau_iterations=2)
        elif high_severity_count > 3:
            stopping_criteria = StoppingCriteria(score_threshold=85.0, max_iterations=8, plateau_iterations=3)
        else:
            stopping_criteria = StoppingCriteria()

    applicator = SmartFixApplicator(api_key, stopping_criteria)
    final_code, feedback = applicator.apply_fixes_smart(original_code, issues, context, mode, fix_mode)
    return final_code, feedback


def apply_fixes_enhanced(original_code: str, refactored_code: str, issues: List[Dict[str, Any]], api_key: str = None, context: Dict = None, mode: str = "full_scan") -> List[Dict[str, Any]]:
    """Enhanced fix application - redirects to smart version."""
    return apply_fixes_smart(original_code, issues, api_key, context, mode)[1]


def apply_fixes(original_code: str, refactored_code: str, issues: List[Dict[str, Any]], api_key: str = None) -> List[Dict[str, Any]]:
    """Legacy apply_fixes function - redirects to smart version."""
    return apply_fixes_smart(original_code, issues, api_key)[1]