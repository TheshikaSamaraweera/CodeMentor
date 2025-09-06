# agents/error_comparator_agent.py
from typing import List, Dict, Any, Tuple, Set
from dataclasses import dataclass
import difflib


@dataclass
class Issue:
    """Structured representation of a code issue."""
    line: int
    description: str
    suggestion: str
    source: str
    severity: str = "medium"
    confidence: float = 0.8
    category: str = "general"


class IssueComparator:
    """Advanced issue comparison and merging logic."""

    SEVERITY_WEIGHTS = {"critical": 1.0, "high": 0.8, "medium": 0.6, "low": 0.4}

    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text descriptions."""
        text1_clean = text1.strip().lower()
        text2_clean = text2.strip().lower()

        if text1_clean == text2_clean:
            return 1.0

        # Use SequenceMatcher for fuzzy matching
        matcher = difflib.SequenceMatcher(None, text1_clean, text2_clean)
        return matcher.ratio()

    def are_issues_similar(self, issue1: Dict, issue2: Dict) -> bool:
        """Determine if two issues are similar enough to merge."""
        # Same line number
        if issue1.get("line") != issue2.get("line"):
            return False

        # Similar descriptions
        similarity = self.calculate_text_similarity(
            issue1.get("description", ""),
            issue2.get("description", "")
        )

        return similarity >= self.similarity_threshold

    def merge_similar_issues(self, issue1: Dict, issue2: Dict) -> Dict:
        """Merge two similar issues, taking the best attributes."""
        # Combine descriptions if different
        desc1 = issue1.get("description", "").strip()
        desc2 = issue2.get("description", "").strip()

        if desc1.lower() != desc2.lower():
            merged_description = f"{desc1}. Additional: {desc2}"
        else:
            merged_description = desc1

        # Take higher confidence and more severe rating
        conf1 = issue1.get("confidence", 0.8)
        conf2 = issue2.get("confidence", 0.8)

        sev1 = issue1.get("severity", "medium")
        sev2 = issue2.get("severity", "medium")

        # Choose more severe issue
        if self.SEVERITY_WEIGHTS.get(sev1, 0.6) >= self.SEVERITY_WEIGHTS.get(sev2, 0.6):
            severity = sev1
        else:
            severity = sev2

        return {
            "line": issue1.get("line"),
            "description": merged_description,
            "suggestion": issue1.get("suggestion", "") or issue2.get("suggestion", ""),
            "source": "Both",
            "severity": severity,
            "confidence": max(conf1, conf2),
            "category": issue1.get("category", "general")
        }


def compare_issues(quality_issues: Dict[str, Any], security_issues: Dict[str, Any],
                  static_issues: List[Dict]) -> List[Dict]:
    """Enhanced issue comparison with better merging logic."""
    print("🧮 Running Enhanced Error Comparator...")

    comparator = IssueComparator()
    merged = []
    quality_issue_list = quality_issues.get("issues", []) if quality_issues else []
    security_issue_list = security_issues.get("issues", []) if security_issues else []

    # Convert Quality issues to standard format
    processed_quality_issues = []
    for issue in quality_issue_list:
        processed_issue = {
            "line": issue.get("line", 0),
            "description": issue.get("issue", issue.get("description", "")),
            "suggestion": issue.get("suggestion", ""),
            "source": "AI",
            "severity": issue.get("severity", "medium"),
            "confidence": issue.get("confidence", 0.8),
            "category": _categorize_issue(issue.get("issue", issue.get("description", "")))
        }
        processed_quality_issues.append(processed_issue)

    # Convert Security issues to standard format
    processed_security_issues = []
    for issue in security_issue_list:
        processed_issue = {
            "line": issue.get("line", 0),
            "description": issue.get("issue", issue.get("description", "")),
            "suggestion": issue.get("suggestion", ""),
            "source": "AI",
            "severity": issue.get("severity", "medium"),
            "confidence": issue.get("confidence", 0.8),
            "category": _categorize_issue(issue.get("issue", issue.get("description", "")))
        }
        processed_security_issues.append(processed_issue)

    # Combine AI issues from both quality and security analyses
    processed_ai_issues = processed_quality_issues + processed_security_issues

    # Convert static issues to standard format
    processed_static_issues = []
    for issue in static_issues:
        processed_issue = {
            "line": issue.get("line", 0),
            "description": issue.get("issue", issue.get("description", "")),
            "suggestion": issue.get("suggestion", ""),
            "source": "Static",
            "severity": issue.get("severity", "medium"),
            "confidence": issue.get("confidence", 0.8),
            "category": _categorize_issue(issue.get("issue", issue.get("description", "")))
        }
        processed_static_issues.append(processed_issue)

    # Find matches between AI and static issues
    matched_static_indices = set()

    for ai_issue in processed_ai_issues:
        best_match = None
        best_match_idx = -1

        for idx, static_issue in enumerate(processed_static_issues):
            if idx in matched_static_indices:
                continue

            if comparator.are_issues_similar(ai_issue, static_issue):
                best_match = static_issue
                best_match_idx = idx
                break

        if best_match:
            # Merge the issues
            merged_issue = comparator.merge_similar_issues(ai_issue, best_match)
            merged.append(merged_issue)
            matched_static_indices.add(best_match_idx)
        else:
            # Add AI issue as standalone
            merged.append(ai_issue)

    # Add remaining unmatched static issues
    for idx, static_issue in enumerate(processed_static_issues):
        if idx not in matched_static_indices:
            merged.append(static_issue)

    # Calculate statistics
    count = {"AI": 0, "Static": 0, "Both": 0}
    severity_count = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for issue in merged:
        source = issue["source"]
        if source == "Both":
            count["Both"] += 1
        elif source == "AI":
            count["AI"] += 1
        else:
            count["Static"] += 1
        severity_count[issue.get("severity", "medium")] += 1

    # Sort by severity and line number
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    merged.sort(key=lambda x: (severity_order.get(x.get("severity", "medium"), 2), x.get("line", 0)))

    print(f"✅ Enhanced Error Comparator completed:")
    print(f"   📊 Total issues: {len(merged)}")
    print(f"   🤖 AI only: {count['AI']}, 🔧 Static only: {count['Static']}, 🤝 Both: {count['Both']}")
    print(f"   🔴 Critical: {severity_count['critical']}, High: {severity_count['high']}")
    print(f"   🟡 Medium: {severity_count['medium']}, 🟢 Low: {severity_count['low']}")

    return merged


def _categorize_issue(description: str) -> str:
    """Categorize issue based on description keywords."""
    desc_lower = description.lower()

    security_keywords = ["security", "vulnerability", "injection", "xss", "csrf", "hardcode"]
    performance_keywords = ["performance", "slow", "inefficient", "loop", "complexity"]
    style_keywords = ["style", "formatting", "convention", "naming"]
    bug_keywords = ["bug", "error", "exception", "null", "undefined"]

    if any(keyword in desc_lower for keyword in security_keywords):
        return "security"
    elif any(keyword in desc_lower for keyword in performance_keywords):
        return "performance"
    elif any(keyword in desc_lower for keyword in style_keywords):
        return "style"
    elif any(keyword in desc_lower for keyword in bug_keywords):
        return "bug"
    else:
        return "general"

def _categorize_issue(description: str) -> str:
    """Categorize issue based on description keywords."""
    desc_lower = description.lower()

    security_keywords = ["security", "vulnerability", "injection", "xss", "csrf", "hardcode"]
    performance_keywords = ["performance", "slow", "inefficient", "loop", "complexity"]
    style_keywords = ["style", "formatting", "convention", "naming"]
    bug_keywords = ["bug", "error", "exception", "null", "undefined"]

    if any(keyword in desc_lower for keyword in security_keywords):
        return "security"
    elif any(keyword in desc_lower for keyword in performance_keywords):
        return "performance"
    elif any(keyword in desc_lower for keyword in style_keywords):
        return "style"
    elif any(keyword in desc_lower for keyword in bug_keywords):
        return "bug"
    else:
        return "general"