# utils/smart_integration.py
"""
Integration utilities for the smart fix application system.
This module helps bridge the old system with the new smart system.
"""

import yaml
import os
from typing import Dict, List, Any, Optional
from cli.smart_apply_fixes import SmartFixApplicator, StoppingCriteria

from cli.enhanced_apply_fixes import apply_fixes_smart


def load_smart_config(config_path: str = "config/smart_fix_config.yaml") -> Dict:
    """Load smart configuration from YAML file."""
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        else:
            print(f"⚠️ Config file {config_path} not found. Using built-in defaults.")
    except Exception as e:
        print(f"⚠️ Error loading config: {e}. Using built-in defaults.")

    # Return built-in default configuration
    return {
        "stopping_criteria": {
            "default": {
                "score_threshold": 85.0,
                "max_iterations": 8,
                "plateau_iterations": 3,
                "min_improvement_per_iteration": 1.0,
                "max_low_severity_issues": 3,
                "acceptable_issue_categories": ["style", "design"]
            }
        },
        "issue_classification": {
            "structural": {
                "keywords": ["long method", "complexity", "nesting"],
                "priority": "high"
            },
            "design": {
                "keywords": ["parameter", "responsibility", "coupling"],
                "priority": "medium"
            },
            "style": {
                "keywords": ["naming", "comment", "formatting"],
                "priority": "low"
            },
            "security": {
                "keywords": ["security", "vulnerability", "injection"],
                "priority": "critical"
            }
        }
    }


def analyze_issues_for_smart_criteria(issues: List[Dict], current_score: float) -> StoppingCriteria:
    """
    Analyze issues and create adaptive stopping criteria.

    Args:
        issues: List of detected issues
        current_score: Current quality score

    Returns:
        Adaptive StoppingCriteria based on issue composition
    """
    config = load_smart_config()
    criteria_config = config.get("stopping_criteria", {})

    # Analyze issue composition
    security_count = 0
    structural_count = 0
    high_severity_count = 0

    for issue in issues:
        description = issue.get('description', '').lower()
        severity = issue.get('severity', 'medium')

        if severity == 'high':
            high_severity_count += 1

        # Check for security issues
        if any(kw in description for kw in ['security', 'vulnerability', 'injection', 'hardcode']):
            security_count += 1

        # Check for structural issues
        elif any(kw in description for kw in ['long method', 'complexity', 'nesting', 'too many']):
            structural_count += 1

    # Select appropriate criteria based on analysis
    if security_count > 0:
        criteria = criteria_config.get("security_focused", criteria_config["default"])
    elif structural_count > 2 or high_severity_count > 3:
        criteria = criteria_config.get("structural_focused", criteria_config["default"])
    elif current_score < 70:
        criteria = criteria_config.get("quality_focused", criteria_config["default"])
    else:
        criteria = criteria_config.get("default")

    # Create StoppingCriteria object
    return StoppingCriteria(
        score_threshold=criteria.get("score_threshold", 85.0),
        max_iterations=criteria.get("max_iterations", 8),
        plateau_iterations=criteria.get("plateau_iterations", 3),
        min_improvement_per_iteration=criteria.get("min_improvement_per_iteration", 1.0),
        max_low_severity_issues=criteria.get("max_low_severity_issues", 3),
        acceptable_issue_categories=set(criteria.get("acceptable_issue_categories", ["style", "design"]))
    )


def get_smart_issue_recommendations(issues: List[Dict], config: Dict = None) -> Dict[str, List[Dict]]:
    """
    Categorize and prioritize issues based on smart analysis.

    Args:
        issues: List of detected issues
        config: Configuration dict (optional)

    Returns:
        Dictionary with categorized issues and recommendations
    """
    if not config:
        config = load_smart_config()

    classification = config.get("issue_classification", {})

    categorized_issues = {
        "critical": [],  # Security issues
        "high": [],  # Structural issues
        "medium": [],  # Design issues
        "low": []  # Style issues
    }

    recommendations = []

    for issue in issues:
        description = issue.get('description', '').lower()
        severity = issue.get('severity', 'medium')

        # Categorize by content analysis
        issue_category = "design"  # Default
        priority_level = "medium"  # Default

        for category, category_config in classification.items():
            keywords = category_config.get("keywords", [])
            if any(keyword in description for keyword in keywords):
                issue_category = category
                priority_level = category_config.get("priority", "medium")
                break

        # Map priority to our categorization
        if priority_level == "critical":
            categorized_issues["critical"].append({**issue, "category": issue_category})
        elif priority_level == "high":
            categorized_issues["high"].append({**issue, "category": issue_category})
        elif priority_level == "medium":
            categorized_issues["medium"].append({**issue, "category": issue_category})
        else:
            categorized_issues["low"].append({**issue, "category": issue_category})

    # Generate smart recommendations
    if categorized_issues["critical"]:
        recommendations.append({
            "priority": "immediate",
            "message": f"Fix {len(categorized_issues['critical'])} critical security issues first",
            "suggested_selection": "critical"
        })

    if categorized_issues["high"]:
        recommendations.append({
            "priority": "high",
            "message": f"Address {len(categorized_issues['high'])} structural issues for maximum impact",
            "suggested_selection": "high"
        })

    if len(categorized_issues["medium"]) > 5:
        recommendations.append({
            "priority": "medium",
            "message": f"Consider addressing design issues in batches",
            "suggested_selection": "medium"
        })

    total_low_priority = len(categorized_issues["low"])
    if total_low_priority > 0 and sum(len(issues) for issues in categorized_issues.values()) == total_low_priority:
        recommendations.append({
            "priority": "low",
            "message": "Only style issues remain - consider stopping or batch processing",
            "suggested_selection": "stop"
        })

    return {
        "categorized_issues": categorized_issues,
        "recommendations": recommendations,
        "summary": {
            "critical": len(categorized_issues["critical"]),
            "high": len(categorized_issues["high"]),
            "medium": len(categorized_issues["medium"]),
            "low": len(categorized_issues["low"]),
            "total": len(issues)
        }
    }


def should_use_smart_fixes(issues: List[Dict], results: Dict) -> tuple[bool, str]:
    """
    Determine if smart fixes would be beneficial based on analysis.

    Args:
        issues: List of detected issues
        results: Analysis results

    Returns:
        (should_use_smart: bool, reason: str)
    """
    current_score = results.get('overall_score', 0)
    total_issues = len(issues)

    # Count issue types
    security_issues = sum(1 for issue in issues
                          if any(kw in issue.get('description', '').lower()
                                 for kw in ['security', 'vulnerability']))
    structural_issues = sum(1 for issue in issues
                            if any(kw in issue.get('description', '').lower()
                                   for kw in ['long method', 'complexity', 'nesting']))
    high_severity = sum(1 for issue in issues if issue.get('severity') == 'high')

    # Decision logic
    if security_issues > 0:
        return True, f"Security issues detected ({security_issues}) - smart fixes recommended"

    if current_score < 70:
        return True, f"Low quality score ({current_score:.1f}) - smart fixes can provide significant improvement"

    if structural_issues > 2:
        return True, f"Multiple structural issues ({structural_issues}) - smart fixes most effective"

    if high_severity > 3:
        return True, f"Many high-severity issues ({high_severity}) - systematic approach recommended"

    if total_issues > 10:
        return True, f"Many issues detected ({total_issues}) - smart prioritization helpful"

    if total_issues <= 2 and current_score > 85:
        return False, f"Few issues with good score - manual fixes may be simpler"

    if current_score > 90:
        return False, f"Excellent code quality ({current_score:.1f}) - minimal improvement needed"

    # Default to smart fixes for most cases
    return True, f"Smart fixes can help systematically improve code quality"


def create_migration_guide() -> str:
    """Create a migration guide for transitioning from old to new system."""
    return """
# Migration Guide: Enhanced Fix Application System

## Key Improvements

### 1. Smart Convergence Detection
- **Problem Solved**: Prevents infinite refactoring loops where new issues appear after fixing others
- **How**: Detects when improvements plateau, issue types cycle, or only low-priority issues remain
- **Benefit**: Saves time and focuses effort on impactful changes

### 2. Issue Categorization & Prioritization
- **Problem Solved**: Not all issues are equally important
- **How**: Automatically categorizes issues (Security > Structural > Design > Style)
- **Benefit**: Fix high-impact issues first, leave acceptable issues for later

### 3. Adaptive Stopping Criteria
- **Problem Solved**: One-size-fits-all approach doesn't work
- **How**: Adjusts stopping criteria based on issue composition and current code quality
- **Benefit**: More aggressive for security issues, more lenient for style issues

## Migration Steps

### For Existing Users:

1. **Replace import**:
   ```python
   # Old
   from cli.apply_fixes import apply_fixes

   # New  
   from cli.smart_apply_fixes import SmartFixApplicator, apply_fixes_smart
   ```

2. **Update function calls**:
   ```python
   # Old
   feedback = apply_fixes(original_code, refactored_code, issues, api_key)

   # New
   feedback = apply_fixes_smart(original_code, issues, api_key, context, mode)
   ```

3. **Use new main entry point**:
   ```bash
   # Old
   python main.py code.py --mode=full_scan

   # New
   python main.py code.py --mode=full_scan --fix-mode=smart
   ```

### Backward Compatibility

The system maintains full backward compatibility:
- Old `apply_fixes()` function still works (redirects to smart version)
- All existing CLI arguments continue to work
- Legacy mode available via `--fix-mode=legacy`

### New Features

1. **Smart Interactive Mode**: Fix issues one-by-one with convergence detection
2. **Automatic Mode**: Fully automated optimization with smart stopping
3. **Adaptive Configuration**: Criteria adjust based on issue types
4. **Progress Tracking**: Detailed tracking of improvements over iterations
5. **Category-based Filtering**: Focus on specific issue types

### Configuration

Create `config/smart_fix_config.yaml` to customize:
```yaml
stopping_criteria:
  default:
    score_threshold: 85.0
    max_iterations: 8
    acceptable_issue_categories: ["style", "design"]
```

This approach solves the core issue of "new issues appearing after fixes" by:
1. **Expecting it**: This is normal behavior, not a bug
2. **Categorizing wisely**: Not all new issues need immediate fixing
3. **Setting smart limits**: Stop when diminishing returns occur
4. **Focusing on impact**: Prioritize high-impact fixes over completeness
"""


# Utility functions for backward compatibility
def convert_legacy_issues_format(legacy_issues: List[Dict]) -> List[Dict]:
    """Convert legacy issue format to new standardized format."""
    converted = []
    for issue in legacy_issues:
        # Normalize the issue format
        converted_issue = {
            "line": issue.get("line", 0),
            "description": issue.get("issue", issue.get("description", "")),
            "suggestion": issue.get("suggestion", ""),
            "severity": issue.get("severity", "medium"),
            "confidence": issue.get("confidence", 0.8),
            "source_agent": issue.get("source", "unknown"),
            "category": "general"
        }
        converted.append(converted_issue)

    return converted


def integrate_with_existing_workflow(original_apply_fixes):
    """Decorator to integrate smart fixes with existing workflow."""

    def wrapper(original_code: str, refactored_code: str, issues: List[Dict], api_key: str = None):
        # Check if smart fixes would be beneficial
        mock_results = {"overall_score": 75.0}  # Estimate
        should_use_smart, reason = should_use_smart_fixes(issues, mock_results)

        if should_use_smart and len(issues) > 3:
            print(f"\n💡 Smart Fix Recommendation: {reason}")
            use_smart = input("Use smart fix application? (y/N): ").strip().lower() == 'y'

            if use_smart:
                return apply_fixes_smart(original_code, issues, api_key)

        # Fall back to original function
        return original_apply_fixes(original_code, refactored_code, issues, api_key)

    return wrapper