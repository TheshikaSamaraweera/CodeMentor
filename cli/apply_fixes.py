import difflib
from typing import List, Dict, Any
from agents.refactor_agent import run_refactor_agent
from memory.session_memory import remember_issue, remember_feedback
from utils.code_diff import show_code_diff

def apply_fixes(original_code: str, refactored_code: str, issues: List[Dict[str, Any]], api_key: str = None) -> List[Dict[str, Any]]:
    """
    Apply selected fixes based on user-specified issue numbers.

    Args:
        original_code: Original source code
        refactored_code: Initially refactored code (may be same as original)
        issues: List of issues to fix
        api_key: API key for refactor agent

    Returns:
        List of feedback for each applied or skipped fix
    """
    print("\n🔧 Fix Application Selection...")
    print("-" * 40)

    feedback = []

    if not issues:
        print("✅ No issues to fix.")
        return feedback

    # Display all issues with numbers
    print("\n📋 Detected Issues:")
    for i, issue in enumerate(issues, 1):
        print(f"\n  {i}. Line: {issue.get('line', 'N/A')}")
        print(f"     Severity: {issue.get('severity', 'medium').upper()}")
        print(f"     Description: {issue.get('description', 'No description')}")
        print(f"     Suggestion: {issue.get('suggestion', 'No suggestion')}")
        if issue.get('explanation'):
            print(f"     Explanation: {issue.get('explanation')}")

    # Prompt user to select issues
    user_input = input("\n🤖 Enter issue numbers to fix (e.g., '1,3,4' or 'none' to skip): ").strip().lower()

    if user_input == 'none' or not user_input:
        print("⏭️ No fixes selected. Skipping fix application.")
        return feedback

    # Parse and validate issue numbers
    try:
        selected_numbers = [int(num.strip()) for num in user_input.split(',')]
        if not all(1 <= num <= len(issues) for num in selected_numbers):
            print(f"❌ Invalid issue numbers. Must be between 1 and {len(issues)}.")
            return feedback
        selected_numbers = sorted(set(selected_numbers))  # Remove duplicates, sort for consistency
    except ValueError:
        print("❌ Invalid input. Please enter numbers separated by commas (e.g., '1,3,4').")
        return feedback

    # Filter selected issues
    selected_issues = [issues[num - 1] for num in selected_numbers]
    print(f"\n🔄 Applying fixes for issues: {', '.join(map(str, selected_numbers))}...")

    # Sort selected issues by severity (high > medium > low) to apply critical fixes first
    severity_order = {'high': 1, 'medium': 2, 'low': 3}
    selected_issues.sort(key=lambda x: severity_order.get(x.get('severity', 'medium').lower(), 2))

    # Apply selected fixes in one go
    new_code = run_refactor_agent(original_code, selected_issues, api_key)

    if not new_code or new_code == original_code:
        print("⚠️ No changes made by refactor agent.")
        feedback = [{
            "issue": issue,
            "applied": False,
            "reason": "No changes produced by refactor agent"
        } for issue in selected_issues]
    else:
        # Show diff for all applied fixes
        show_code_diff(original_code, new_code, title="Changes for Selected Fixes")

        # Confirm application
        confirm = input("\n✅ Confirm applying these changes? (y/N): ").strip().lower()
        if confirm != 'y':
            print("⏭️ Discarding all changes.")
            feedback = [{
                "issue": issue,
                "applied": False,
                "reason": "User discarded the changes"
            } for issue in selected_issues]
        else:
            # Update refactored code and track applied issues
            refactored_code = new_code
            feedback = [{
                "issue": issue,
                "applied": True,
                "reason": "Fix applied successfully"
            } for issue in selected_issues]
            print("\n✅ Selected fixes applied successfully.")
            for issue in selected_issues:
                remember_issue(issue)
                # Updated to pass description, accepted, and line arguments
                remember_feedback(
                    description=f"Fix applied for issue: {issue.get('description', 'No description')}",
                    accepted=True,
                    line=issue.get('line', 'N/A')
                )

    # Generate feedback for skipped issues
    skipped_issues = [issue for i, issue in enumerate(issues, 1) if i not in selected_numbers]
    feedback.extend([{
        "issue": issue,
        "applied": False,
        "reason": "Issue not selected by user"
    } for issue in skipped_issues])

    # Display final refactored code
    if any(f["applied"] for f in feedback):
        print("\n📝 Final Refactored Code:")
        show_code_diff(original_code, refactored_code, title="Final Changes")

    # Display summary
    print("\n📊 Fix Application Summary:")
    applied_count = len([f for f in feedback if f["applied"]])
    print(f"✅ Applied {applied_count}/{len(issues)} fixes.")
    for f in feedback:
        status = "Applied" if f["applied"] else "Skipped"
        print(f"  - {status}: {f['issue'].get('description')} ({f['reason']})")

    return feedback