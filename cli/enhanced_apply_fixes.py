# cli/enhanced_apply_fixes.py
import difflib
from typing import List, Dict, Any, Tuple, Optional
from agents.refactor_agent import run_refactor_agent
from agents.comprehensive_analysis_agent import run_comprehensive_analysis
from memory.session_memory import remember_issue, remember_feedback
from utils.code_diff import show_code_diff
from controls.recursive_controller import build_langgraph_loop
import json


class FixApplicationMode:
    INTERACTIVE = "interactive"
    AUTOMATIC = "automatic"


class EnhancedFixApplicator:
    """Enhanced fix applicator with interactive and automatic modes."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session_history = []

    def apply_fixes_enhanced(self,
                             original_code: str,
                             issues: List[Dict[str, Any]],
                             context: Dict = None,
                             mode: str = "full_scan") -> Tuple[str, List[Dict]]:
        """
        Main entry point for enhanced fix application.

        Args:
            original_code: Original source code
            issues: List of detected issues
            context: Project context
            mode: Analysis mode

        Returns:
            Tuple of (final_code, session_feedback)
        """
        if not issues:
            print("✅ No issues to fix.")
            return original_code, []

        print("\n🔧 Enhanced Fix Application System")
        print("=" * 50)

        # Show mode selection
        application_mode = self._select_application_mode()

        if application_mode == FixApplicationMode.INTERACTIVE:
            return self._run_interactive_mode(original_code, issues, context, mode)
        else:
            return self._run_automatic_mode(original_code, issues, context, mode)

    def _select_application_mode(self) -> str:
        """Let user select between interactive and automatic modes."""
        print("\n🎯 Fix Application Modes:")
        print("1. Interactive Mode - Apply fixes one by one with re-analysis")
        print("2. Automatic Mode - Generate optimized code using iterative process")

        while True:
            choice = input("\nSelect mode (1 for Interactive, 2 for Automatic): ").strip()
            if choice == "1":
                return FixApplicationMode.INTERACTIVE
            elif choice == "2":
                return FixApplicationMode.AUTOMATIC
            else:
                print("❌ Please enter 1 or 2")

    def _run_interactive_mode(self,
                              original_code: str,
                              issues: List[Dict],
                              context: Dict,
                              mode: str) -> Tuple[str, List[Dict]]:
        """Run interactive fix-by-fix mode with continuous re-analysis."""
        print("\n🔄 Interactive Fix-by-Fix Mode Activated")
        print("=" * 40)

        current_code = original_code
        remaining_issues = issues.copy()
        iteration = 0
        total_feedback = []

        while remaining_issues:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")
            print(f"📊 Current Status: {len(remaining_issues)} issues remaining")

            # Display current issues
            self._display_issues(remaining_issues)

            # Get user selection
            selected_issues = self._get_user_issue_selection(remaining_issues)

            if not selected_issues:
                print("🛑 User chose to stop. Exiting interactive mode.")
                break

            # Apply selected fixes
            print(f"\n🔧 Applying {len(selected_issues)} selected fixes...")
            fixed_code = self._apply_selected_fixes(current_code, selected_issues)

            if fixed_code != current_code:
                # Show changes
                show_code_diff(current_code, fixed_code,
                               f"Changes from Iteration {iteration}")

                # Confirm application
                if self._confirm_changes():
                    current_code = fixed_code

                    # Record feedback
                    iteration_feedback = [{
                        "issue": issue,
                        "applied": True,
                        "iteration": iteration,
                        "reason": "Applied in interactive mode"
                    } for issue in selected_issues]
                    total_feedback.extend(iteration_feedback)

                    # Re-analyze the updated code
                    print(f"\n🔍 Re-analyzing updated code...")
                    remaining_issues = self._reanalyze_code(current_code, context, mode)

                    # Show progress
                    self._show_progress_summary(iteration, len(selected_issues),
                                                len(remaining_issues))

                    # Remember feedback
                    for issue in selected_issues:
                        remember_issue(issue)
                        remember_feedback(
                            description=f"Interactive fix applied: {issue.get('description', '')}",
                            accepted=True,
                            line=issue.get('line', 'N/A')
                        )
                else:
                    print("⏭️ Changes discarded. Continuing with current code.")
            else:
                print("⚠️ No changes produced by refactor agent.")
                # Remove the issues that couldn't be fixed
                remaining_issues = [issue for issue in remaining_issues
                                    if issue not in selected_issues]

            # Ask if user wants to continue
            if remaining_issues:
                if not self._ask_continue():
                    print("🛑 User chose to stop iterations.")
                    break

        print(f"\n✅ Interactive mode completed after {iteration} iterations")
        self._show_final_summary(original_code, current_code, total_feedback)

        return current_code, total_feedback

    def _run_automatic_mode(self,
                            original_code: str,
                            issues: List[Dict],
                            context: Dict,
                            mode: str) -> Tuple[str, List[Dict]]:
        """Run automatic optimization mode using iterative process."""
        print("\n🚀 Automatic Optimization Mode Activated")
        print("=" * 40)

        print("📋 Configuration Options:")
        config = self._get_automatic_config()

        # Use existing recursive controller for automatic optimization
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
            "min_score_threshold": config["min_score_threshold"],
            "max_high_severity_issues": config["max_high_severity"],
            "max_iterations": config["max_iterations"],
            "context": context or {},
            "optimization_applied": False,
            "previous_scores": [],
            "stagnation_count": 0,
            "user_stop": False
        }

        print(f"\n🔄 Starting automatic optimization with {len(issues)} initial issues...")
        print(f"🎯 Target Score: {config['min_score_threshold']}")
        print(f"🔄 Max Iterations: {config['max_iterations']}")

        # Run iterative optimization
        final_state = graph.invoke(state)

        # Process results
        best_code = final_state.get("best_code", original_code)
        final_score = final_state.get("best_score", 0)
        history = final_state.get("history", [])
        total_issues_fixed = sum(step.get('issues_fixed', 0) for step in history)

        # Generate feedback
        feedback = [{
            "mode": "automatic",
            "initial_issues": len(issues),
            "final_score": final_score,
            "iterations": len(history),
            "issues_fixed": total_issues_fixed,
            "optimization_applied": final_state.get("optimization_applied", False),
            "history": history
        }]

        print(f"\n✅ Automatic optimization completed!")
        print(f"🏆 Final Score: {final_score:.1f}")
        print(f"🔄 Iterations: {len(history)}")
        print(f"✅ Issues Fixed: {total_issues_fixed}")

        if best_code != original_code:
            show_code_diff(original_code, best_code, "Automatic Optimization Results")
        else:
            print("ℹ️ No changes were made during optimization.")

        return best_code, feedback

    def _display_issues(self, issues: List[Dict]):
        """Display issues in a user-friendly format."""
        print(f"\n📋 Current Issues ({len(issues)} total):")

        # Group by severity
        severity_groups = {'high': [], 'medium': [], 'low': []}
        for issue in issues:
            severity = issue.get('severity', 'medium')
            if severity in severity_groups:
                severity_groups[severity].append(issue)

        issue_counter = 0
        for severity in ['high', 'medium', 'low']:
            if severity_groups[severity]:
                severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[severity]
                print(f"\n{severity_emoji} {severity.upper()} PRIORITY:")

                for issue in severity_groups[severity]:
                    issue_counter += 1
                    line = issue.get('line', 'N/A')
                    description = issue.get('description', 'No description')
                    category = issue.get('category', 'general')
                    source = issue.get('source_agent', 'unknown')

                    print(f"  {issue_counter:2d}. Line {line} ({category}/{source})")
                    print(f"      {description}")
                    if issue.get('suggestion'):
                        print(f"      💡 {issue.get('suggestion')}")

    def _get_user_issue_selection(self, issues: List[Dict]) -> List[Dict]:
        """Get user's selection of issues to fix."""
        print(f"\n🎯 Fix Selection Options:")
        print("1. Select specific issue numbers (e.g., '1,3,5')")
        print("2. Select by severity ('high', 'medium', 'low')")
        print("3. Select all issues ('all')")
        print("4. Stop fixing ('none' or 'stop')")

        while True:
            user_input = input("\nEnter your selection: ").strip().lower()

            if user_input in ['none', 'stop', 'exit']:
                return []
            elif user_input == 'all':
                return issues
            elif user_input in ['high', 'medium', 'low']:
                return [issue for issue in issues
                        if issue.get('severity', 'medium') == user_input]
            else:
                # Try to parse as issue numbers
                try:
                    numbers = [int(n.strip()) for n in user_input.split(',')]
                    if all(1 <= n <= len(issues) for n in numbers):
                        return [issues[n - 1] for n in numbers]
                    else:
                        print(f"❌ Invalid numbers. Must be between 1 and {len(issues)}")
                except ValueError:
                    print("❌ Invalid input. Please try again.")

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
            results = run_comprehensive_analysis(
                code=code,
                api_key=self.api_key,
                mode=mode,
                context=context or {}
            )
            return results.get('final_issues', [])
        except Exception as e:
            print(f"⚠️ Re-analysis failed: {e}")
            return []

    def _show_progress_summary(self, iteration: int, fixes_applied: int, remaining_issues: int):
        """Show progress summary after each iteration."""
        print(f"\n📊 Progress Summary - Iteration {iteration}:")
        print(f"   ✅ Fixes Applied: {fixes_applied}")
        print(f"   📋 Remaining Issues: {remaining_issues}")
        if remaining_issues == 0:
            print("   🎉 All issues resolved!")

    def _ask_continue(self) -> bool:
        """Ask user if they want to continue with more iterations."""
        response = input("\n🔄 Continue with more fixes? (y/N): ").strip().lower()
        return response == 'y'

    def _get_automatic_config(self) -> Dict:
        """Get configuration for automatic mode."""
        print("\n⚙️ Automatic Mode Configuration:")

        # Default values
        defaults = {
            "min_score_threshold": 85,
            "max_iterations": 5,
            "max_high_severity": 0
        }

        use_defaults = input("Use default settings? (Y/n): ").strip().lower()

        if use_defaults != 'n':
            print(f"Using defaults: Score≥{defaults['min_score_threshold']}, "
                  f"Max iterations={defaults['max_iterations']}")
            return defaults

        # Custom configuration
        config = {}

        try:
            config["min_score_threshold"] = float(
                input(f"Minimum score threshold (default {defaults['min_score_threshold']}): ")
                or defaults['min_score_threshold']
            )
            config["max_iterations"] = int(
                input(f"Maximum iterations (default {defaults['max_iterations']}): ")
                or defaults['max_iterations']
            )
            config["max_high_severity"] = int(
                input(f"Max high severity issues allowed (default {defaults['max_high_severity']}): ")
                or defaults['max_high_severity']
            )
        except ValueError:
            print("⚠️ Invalid input, using defaults")
            return defaults

        return config

    def _show_final_summary(self, original_code: str, final_code: str, feedback: List[Dict]):
        """Show final summary of the session."""
        print(f"\n📊 Final Session Summary:")
        print("=" * 40)

        total_applied = len([f for f in feedback if f.get("applied", False)])
        total_iterations = max([f.get("iteration", 0) for f in feedback] + [0])

        print(f"🔄 Total Iterations: {total_iterations}")
        print(f"✅ Total Fixes Applied: {total_applied}")

        if final_code != original_code:
            # Calculate code metrics
            original_lines = len(original_code.splitlines())
            final_lines = len(final_code.splitlines())
            print(f"📏 Lines Changed: {original_lines} → {final_lines}")

            # Show final diff option
            show_final = input("\n📝 Show complete final diff? (y/N): ").strip().lower()
            if show_final == 'y':
                show_code_diff(original_code, final_code, "Complete Session Changes")
        else:
            print("ℹ️ No changes made to the code")


# Updated main apply_fixes function for backward compatibility
def apply_fixes_enhanced(original_code: str,
                         refactored_code: str,
                         issues: List[Dict[str, Any]],
                         api_key: str = None,
                         context: Dict = None,
                         mode: str = "full_scan") -> List[Dict[str, Any]]:
    """
    Enhanced fix application with interactive and automatic modes.

    Args:
        original_code: Original source code
        refactored_code: Initially refactored code (may be same as original)
        issues: List of issues to fix
        api_key: API key for refactor agent
        context: Project context
        mode: Analysis mode

    Returns:
        List of feedback for applied/skipped fixes
    """
    if not api_key:
        raise ValueError("API key is required for enhanced fix application")

    applicator = EnhancedFixApplicator(api_key)
    final_code, feedback = applicator.apply_fixes_enhanced(
        original_code, issues, context, mode
    )

    return feedback


# Legacy compatibility function
def apply_fixes(original_code: str,
                refactored_code: str,
                issues: List[Dict[str, Any]],
                api_key: str = None) -> List[Dict[str, Any]]:
    """
    Legacy apply_fixes function - redirects to enhanced version.
    """
    return apply_fixes_enhanced(
        original_code, refactored_code, issues, api_key
    )