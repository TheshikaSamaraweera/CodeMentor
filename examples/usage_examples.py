# examples/usage_examples.py
"""
Usage examples for the Smart Fix Application System
"""

from cli.smart_apply_fixes import SmartFixApplicator, StoppingCriteria, apply_fixes_smart
from utils.smart_integration import analyze_issues_for_smart_criteria, should_use_smart_fixes


def example_1_basic_usage():
    """Example 1: Basic smart fix application"""

    # Your existing code
    original_code = """
    def calculate_result(x, y, z, a, b, c, d, e):  # Too many parameters
        if x > 0:
            if y > 0:
                if z > 0:  # Deep nesting
                    result = x + y + z + a + b + c + d + e
                    return result * 2 + 100  # Magic numbers
        return 0
    """

    # Mock issues (normally from your comprehensive analysis)
    issues = [
        {
            "line": 2,
            "description": "Function has too many parameters (8), consider using a parameter object",
            "suggestion": "Create a dataclass or named tuple to group related parameters",
            "severity": "medium",
            "confidence": 0.9
        },
        {
            "line": 3,
            "description": "Deep nesting detected (3 levels), consider using guard clauses",
            "suggestion": "Use early returns to reduce nesting complexity",
            "severity": "medium",
            "confidence": 0.8
        },
        {
            "line": 6,
            "description": "Magic numbers 2 and 100 should be named constants",
            "suggestion": "Extract magic numbers to named constants",
            "severity": "low",
            "confidence": 0.7
        }
    ]

    # Smart fix application
    api_key = "your-gemini-api-key"
    context = {"language": "Python", "project_type": "general"}

    feedback = apply_fixes_smart(
        original_code=original_code,
        issues=issues,
        api_key=api_key,
        context=context,
        mode="code_smell"
    )

    print("Feedback:", feedback)


def example_2_custom_criteria():
    """Example 2: Using custom stopping criteria"""

    # Define strict criteria for production code
    strict_criteria = StoppingCriteria(
        score_threshold=90.0,  # Higher threshold
        max_iterations=12,  # More iterations allowed
        plateau_iterations=2,  # Stop sooner if no improvement
        min_improvement_per_iteration=2.0,  # Require bigger improvements
        max_low_severity_issues=1,  # Very strict on remaining issues
        acceptable_issue_categories={'style'}  # Only style issues acceptable
    )

    applicator = SmartFixApplicator("your-api-key", strict_criteria)

    # Your code and issues here...
    original_code = "..."
    issues = [...]

    final_code, feedback = applicator.apply_fixes_smart(
        original_code, issues, context={}, mode="full_scan"
    )


def example_3_adaptive_criteria():
    """Example 3: Using adaptive criteria based on issue analysis"""

    issues = [
        {"description": "SQL injection vulnerability detected", "severity": "high"},
        {"description": "Hardcoded password found", "severity": "high"},
        {"description": "Long method with 50 lines", "severity": "medium"},
        {"description": "Variable naming convention", "severity": "low"}
    ]

    current_score = 65.0  # Low quality score

    # Automatically determine best criteria
    adaptive_criteria = analyze_issues_for_smart_criteria(issues, current_score)

    print(f"Adaptive criteria selected:")
    print(f"  Score threshold: {adaptive_criteria.score_threshold}")
    print(f"  Max iterations: {adaptive_criteria.max_iterations}")
    print(f"  Acceptable categories: {adaptive_criteria.acceptable_issue_categories}")

    # This will use security-focused criteria due to the security issues


def example_4_integration_with_existing_system():
    """Example 4: Integration with existing analysis pipeline"""

    def your_existing_analysis_workflow(code_path):
        # Your existing comprehensive analysis
        from agents.comprehensive_analysis_agent import run_comprehensive_analysis

        code = load_code(code_path)  # Your existing function

        results = run_comprehensive_analysis(
            code=code,
            api_key="your-api-key",
            mode="full_scan",
            context={"language": "Python"}
        )

        issues = results.get('final_issues', [])

        # Smart decision on whether to use smart fixes
        should_use, reason = should_use_smart_fixes(issues, results)

        if should_use:
            print(f"Smart fixes recommended: {reason}")

            # Apply smart fixes
            feedback = apply_fixes_smart(
                original_code=code,
                issues=issues,
                api_key="your-api-key",
                context={"language": "Python"},
                mode="full_scan"
            )

            return feedback
        else:
            print(f"Manual fixes may be better: {reason}")
            return []


def example_5_cli_usage():
    """Example 5: Command line usage examples"""

    examples = """
    # Basic usage with smart fixes
    python main.py mycode.py --mode=full_scan --fix-mode=smart

    # Security-focused analysis
    python main.py mycode.py --mode=security --fix-mode=smart

    # Custom thresholds
    python main.py mycode.py --score-threshold=90 --max-iterations=10

    # Automatic optimization (no user interaction)
    python main.py mycode.py --fix-mode=automatic

    # Analysis only (no fixes)
    python main.py mycode.py --fix-mode=none
    """

    print("CLI Usage Examples:")
    print(examples)


# Summary of the improvements
IMPROVEMENTS_SUMMARY = """
# Smart Fix Application System - Key Improvements

## Problem Solved: "New Issues Appearing After Fixes"

### Root Cause Analysis:
1. **Normal Behavior**: When you break down large functions, new analysis targets are created
2. **Granular Analysis**: Smaller functions reveal previously hidden design patterns
3. **Different Issue Types**: Original issues (structural) vs new issues (design patterns)

### Smart Solutions Implemented:

#### 1. Convergence Detection
- **Plateau Detection**: Stops when score improvements become minimal
- **Issue Cycling Detection**: Identifies when similar issues keep appearing
- **Diminishing Returns**: Recognizes when effort exceeds benefit

#### 2. Issue Categorization & Prioritization
- **Security Issues**: Highest priority, aggressive fixing
- **Structural Issues**: High priority, significant impact
- **Design Issues**: Medium priority, maintainability focused  
- **Style Issues**: Low priority, acceptable to leave

#### 3. Adaptive Stopping Criteria
- **Security-Focused**: High threshold (90%), strict criteria
- **Structural-Focused**: Moderate threshold (85%), balanced criteria
- **Quality-Focused**: Lower threshold (80%), more iterations allowed
- **Adaptive Selection**: Automatically chooses based on issue composition

#### 4. Smart Recommendations
- **Issue Selection**: AI recommends which issues to fix first
- **Stop Suggestions**: Intelligent stopping point detection
- **Category Filtering**: Focus on high-impact issues only

## Technical Implementation:

### New Classes:
- `SmartFixApplicator`: Main orchestrator with convergence detection
- `RefactoringProgressTracker`: Tracks improvements and detects patterns
- `StoppingCriteria`: Configurable criteria for when to stop
- `IssueCategory` & `IssuePriority`: Proper issue classification

### Key Features:
1. **Interactive Mode**: Step-by-step fixing with progress tracking
2. **Automatic Mode**: Fully automated optimization
3. **Smart Analysis**: Issue composition-based decision making
4. **Progress Tracking**: Detailed metrics and improvement visualization
5. **Backward Compatibility**: Works with existing codebase

### Usage Modes:
```python
# Smart interactive (recommended)
python main.py code.py --fix-mode=smart

# Automatic optimization  
python main.py code.py --fix-mode=automatic

# Legacy compatibility
python main.py code.py --fix-mode=legacy
```

## Benefits:

### For Users:
- **No More Infinite Loops**: Smart stopping prevents endless refactoring
- **Focused Effort**: Prioritizes high-impact fixes
- **Time Savings**: Stops at optimal points
- **Better Results**: Achieves practical improvements vs theoretical perfection

### For Developers:
- **Maintainable**: Clean architecture with proper separation of concerns
- **Configurable**: YAML-based configuration for different projects
- **Extensible**: Easy to add new issue types and stopping criteria
- **Compatible**: Works with existing analysis pipeline

## Expected Workflow:
1. **Analysis**: Detect all issues (as before)
2. **Categorization**: Smart classification by impact/priority  
3. **Interactive Fixing**: User selects fixes with AI guidance
4. **Progress Tracking**: Monitor improvements and detect convergence
5. **Smart Stopping**: Stop at optimal point, not when perfect
6. **Final Review**: Summary of improvements and remaining acceptable issues

This solves the original problem by treating "new issues appearing" as expected behavior and providing intelligent tools to handle it effectively rather than trying to eliminate it entirely.
"""

if __name__ == "__main__":
    print(IMPROVEMENTS_SUMMARY)
    print("\n" + "=" * 80 + "\n")
    print("Running examples...")

    # Run examples (commented out since they need real API keys)
    # example_1_basic_usage()
    # example_2_custom_criteria()
    # example_3_adaptive_criteria()
    # example_4_integration_with_existing_system()
    example_5_cli_usage()