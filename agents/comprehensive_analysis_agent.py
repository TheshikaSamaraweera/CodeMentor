# agents/comprehensive_analysis_agent.py
import json
import hashlib
import tempfile
import os
from typing import Dict, List, Any, Set, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
from enum import Enum
import concurrent.futures
from threading import Lock

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
    issue_id: str  # Unique identifier based on content hash

    def to_dict(self) -> Dict:
        result = asdict(self)
        result['category'] = self.category.value
        return result

    @classmethod
    def from_raw_issue(cls, issue: Dict, category: IssueCategory,
                       source_agent: str) -> 'CategorizedIssue':
        """Create from raw issue dict."""
        description = issue.get('description', issue.get('issue', ''))
        suggestion = issue.get('suggestion', '')

        # Create unique ID based on content and line
        content = f"{issue.get('line', 0)}|{description}|{category.value}"
        issue_id = hashlib.md5(content.encode()).hexdigest()[:12]

        return cls(
            line=issue.get('line', 0),
            description=description,
            suggestion=suggestion,
            severity=issue.get('severity', 'medium'),
            confidence=issue.get('confidence', 0.8),
            category=category,
            source_agent=source_agent,
            issue_id=issue_id
        )


class ComprehensiveAnalysisAgent:
    """
    Redesigned analysis agent that runs all analyses once and categorizes properly.
    No more AI inconsistency - each agent runs exactly once per code.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._issue_lock = Lock()

    def analyze_comprehensively(self, code: str, mode: str = "full_scan",
                                context: Dict = None) -> Dict[str, Any]:
        """
        Run comprehensive analysis with proper categorization and mode-based filtering.
        Each analysis type runs exactly once to avoid AI inconsistency.

        Args:
            code: Source code to analyze
            mode: Analysis mode (quality, security, code_smell, full_scan)
            context: Project context

        Returns:
            Comprehensive analysis results with categorized issues
        """
        print(f"\n🔍 Comprehensive Analysis - Mode: {mode}")
        print("=" * 60)

        # Determine which analyses to run based on mode
        analyses_to_run = self._get_analyses_for_mode(mode)

        # Run all analyses and collect issues
        all_issues = []
        analysis_results = {}

        # Run static analysis first (non-AI, can be parallel)
        if 'static' in analyses_to_run:
            print("🔧 Running Static Analysis...")
            static_issues = self._run_static_analysis(code, context)

            # Filter static issues based on mode
            filtered_static_issues = self._filter_issues_by_mode(static_issues, mode)
            all_issues.extend(filtered_static_issues)
            analysis_results['static'] = filtered_static_issues
            print(f"   📋 After mode filtering: {len(filtered_static_issues)} relevant issues")

        # Run AI analyses sequentially to avoid rate limits and ensure consistency
        ai_analyses = [a for a in analyses_to_run if a != 'static']

        for analysis_type in ai_analyses:
            if analysis_type == 'quality':
                print("🎯 Running Quality Analysis...")
                quality_issues = self._run_quality_analysis(code, context)
                all_issues.extend(quality_issues)
                analysis_results['quality'] = quality_issues

            elif analysis_type == 'security':
                print("🔒 Running Security Analysis...")
                security_issues = self._run_security_analysis(code, context)
                all_issues.extend(security_issues)
                analysis_results['security'] = security_issues

            elif analysis_type == 'code_smell':
                print("👃 Running Code Smell Analysis...")
                smell_issues = self._run_code_smell_analysis(code, context)
                all_issues.extend(smell_issues)
                analysis_results['code_smell'] = smell_issues

        print(f"\n📊 Raw Analysis Complete - Found {len(all_issues)} total issues")

        # Remove exact duplicates while preserving categories
        unique_issues = self._deduplicate_issues(all_issues)
        print(f"📋 After deduplication: {len(unique_issues)} unique issues")

        # Run critic agent on final set if we have issues
        final_issues = unique_issues
        if unique_issues and len(unique_issues) > 0:
            print(f"\n🤔 Running Critic Agent on {len(unique_issues)} issues...")
            final_issues = self._run_critic_analysis(code, unique_issues)
            print(f"✅ Critic Agent refined to {len(final_issues)} issues")

        # Organize results by category
        issues_by_category = self._organize_by_category(final_issues)

        # Calculate scores
        overall_score = self._calculate_overall_score(issues_by_category)
        category_scores = self._calculate_category_scores(issues_by_category)

        results = {
            'mode': mode,
            'total_unique_issues': len(final_issues),
            'issues_by_category': issues_by_category,
            'final_issues': [issue.to_dict() for issue in final_issues],
            'overall_score': overall_score,
            'category_scores': category_scores,
            'raw_analysis_counts': {k: len(v) for k, v in analysis_results.items()},
            'analyses_run': analyses_to_run
        }

        self._print_final_summary(results)
        return results

    def _get_analyses_for_mode(self, mode: str) -> List[str]:
        """
        Determine which analyses to run based on mode.
        Static analysis always runs to provide comprehensive coverage.
        """
        mode_mapping = {
            'quality': ['quality', 'static'],  # Quality AI + static (filtered for quality issues)
            'security': ['security', 'static'],  # Security AI + static (filtered for security issues)
            'code_smell': ['code_smell', 'static'],  # Code smell AI + static (filtered for code smell issues)
            'full_scan': ['quality', 'security', 'code_smell', 'static']  # All analyses
        }
        return mode_mapping.get(mode, ['quality', 'static'])

    def _filter_issues_by_mode(self, issues: List[CategorizedIssue], mode: str) -> List[CategorizedIssue]:
        """
        Filter issues based on the analysis mode to only show relevant issues.

        Args:
            issues: List of categorized issues
            mode: Current analysis mode

        Returns:
            Filtered list of issues relevant to the mode
        """
        if mode == "full_scan":
            # In full scan mode, show all issues
            return issues

        # Map modes to relevant categories
        mode_category_map = {
            'quality': [IssueCategory.QUALITY],
            'security': [IssueCategory.SECURITY],
            'code_smell': [IssueCategory.CODE_SMELL]
        }

        relevant_categories = mode_category_map.get(mode, [])

        if not relevant_categories:
            # If mode not recognized, return all issues
            return issues

        # Filter issues to only include those relevant to the current mode
        filtered_issues = [
            issue for issue in issues
            if issue.category in relevant_categories
        ]

        return filtered_issues

    def _run_static_analysis(self, code: str, context: Dict) -> List[CategorizedIssue]:
        """Run static analysis with proper categorization based on issue content."""
        static_issues = []
        try:
            # Detect language and create appropriate temp file
            language = context.get('language', 'Python')
            extension_map = {
                'Python': '.py',
                'JavaScript': '.js',
                'TypeScript': '.ts',
                'Java': '.java',
                'C++': '.cpp',
                'C': '.c'
            }
            extension = extension_map.get(language, '.py')

            # Create temporary file for static analysis
            with tempfile.NamedTemporaryFile(suffix=extension, delete=False,
                                             mode="w", encoding='utf-8') as temp_file:
                temp_file.write(code)
                temp_path = temp_file.name

            try:
                raw_results = run_static_analysis(temp_path)

                # Classify static analysis issues by content
                for issue in raw_results:
                    # Determine the category based on issue content
                    category = self._classify_static_issue(issue)

                    categorized = CategorizedIssue.from_raw_issue(
                        issue, category, 'static_analysis'
                    )
                    static_issues.append(categorized)

                print(f"   📊 Static analysis found {len(static_issues)} issues")

                # Show breakdown by category
                category_counts = {}
                for issue in static_issues:
                    cat = issue.category.value
                    category_counts[cat] = category_counts.get(cat, 0) + 1

                if category_counts:
                    breakdown = ", ".join([f"{cat}: {count}" for cat, count in category_counts.items()])
                    print(f"   📂 Breakdown: {breakdown}")

            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            print(f"   ⚠️ Static analysis failed: {e}")

        return static_issues

    def _classify_static_issue(self, issue: Dict) -> IssueCategory:
        """
        Classify static analysis issues into appropriate categories based on content.

        Args:
            issue: Raw static analysis issue

        Returns:
            Appropriate IssueCategory
        """
        description = issue.get('issue', issue.get('description', '')).lower()
        suggestion = issue.get('suggestion', '').lower()
        rule_id = issue.get('rule', '').lower()

        # Security-related keywords and patterns
        security_patterns = [
            'security', 'vulnerability', 'injection', 'xss', 'csrf', 'hardcode',
            'password', 'secret', 'token', 'key', 'crypto', 'hash', 'ssl', 'tls',
            'sql injection', 'command injection', 'path traversal', 'eval', 'exec',
            'unsafe', 'blacklist', 'whitelist', 'sanitize', 'escape'
        ]

        # Code smell patterns
        code_smell_patterns = [
            'complexity', 'too complex', 'long method', 'long function', 'long class',
            'parameter list', 'too many parameters', 'duplicate', 'duplicated',
            'dead code', 'unused', 'magic number', 'magic string', 'god class',
            'large class', 'feature envy', 'data class', 'lazy class',
            'long parameter list', 'primitive obsession', 'switch statement',
            'cyclomatic', 'nesting', 'nested', 'cognitive', 'maintainability',
            'refactor', 'extract method', 'extract class', 'rename', 'move method',
            'naming', 'convention', 'style', 'format'
        ]

        # Quality/correctness patterns (bugs, errors, best practices)
        quality_patterns = [
            'error', 'exception', 'bug', 'null', 'undefined', 'none', 'missing',
            'incorrect', 'wrong', 'invalid', 'unreachable', 'syntax', 'type',
            'return', 'assignment', 'comparison', 'logic', 'condition',
            'import', 'module', 'scope', 'variable', 'function', 'method',
            'class', 'attribute', 'property', 'deprecated', 'obsolete'
        ]

        # Combine all text for analysis
        full_text = f"{description} {suggestion} {rule_id}"

        # Check security first (highest priority)
        if any(pattern in full_text for pattern in security_patterns):
            return IssueCategory.SECURITY

        # Check code smells
        elif any(pattern in full_text for pattern in code_smell_patterns):
            return IssueCategory.CODE_SMELL

        # Check for specific pylint/bandit rules that indicate categories
        elif rule_id:
            if any(sec_rule in rule_id for sec_rule in ['hardcoded', 'password', 'key', 'token', 'crypto']):
                return IssueCategory.SECURITY
            elif any(smell_rule in rule_id for smell_rule in ['complexity', 'too-many', 'duplicate', 'unused']):
                return IssueCategory.CODE_SMELL

        # Default to QUALITY for other static analysis issues
        return IssueCategory.QUALITY

    def _run_quality_analysis(self, code: str, context: Dict) -> List[CategorizedIssue]:
        """Run quality analysis with proper categorization."""
        quality_issues = []
        try:
            results = run_quality_agent(code, self.api_key, context)
            for issue in results.get('issues', []):
                categorized = CategorizedIssue.from_raw_issue(
                    issue, IssueCategory.QUALITY, 'quality_agent'
                )
                quality_issues.append(categorized)

            print(f"   📊 Quality analysis found {len(quality_issues)} issues")

        except Exception as e:
            print(f"   ⚠️ Quality analysis failed: {e}")

        return quality_issues

    def _run_security_analysis(self, code: str, context: Dict) -> List[CategorizedIssue]:
        """Run security analysis with proper categorization."""
        security_issues = []
        try:
            results = run_security_agent(code, self.api_key, context)
            for issue in results.get('issues', []):
                categorized = CategorizedIssue.from_raw_issue(
                    issue, IssueCategory.SECURITY, 'security_agent'
                )
                security_issues.append(categorized)

            print(f"   📊 Security analysis found {len(security_issues)} issues")

        except Exception as e:
            print(f"   ⚠️ Security analysis failed: {e}")

        return security_issues

    def _run_code_smell_analysis(self, code: str, context: Dict) -> List[CategorizedIssue]:
        """Run code smell analysis with proper categorization."""
        smell_issues = []
        try:
            results = run_code_smell_agent(code, api_key=self.api_key)
            for issue in results.get('issues', []):
                categorized = CategorizedIssue.from_raw_issue(
                    issue, IssueCategory.CODE_SMELL, 'code_smell_agent'
                )
                smell_issues.append(categorized)

            print(f"   📊 Code smell analysis found {len(smell_issues)} issues")

        except Exception as e:
            print(f"   ⚠️ Code smell analysis failed: {e}")

        return smell_issues

    def _deduplicate_issues(self, issues: List[CategorizedIssue]) -> List[CategorizedIssue]:
        """Remove exact duplicates while preserving categories."""
        unique_issues = {}

        for issue in issues:
            # Use issue_id as the key for deduplication
            if issue.issue_id not in unique_issues:
                unique_issues[issue.issue_id] = issue
            else:
                # If duplicate found, keep the one with higher confidence
                existing = unique_issues[issue.issue_id]
                if issue.confidence > existing.confidence:
                    unique_issues[issue.issue_id] = issue

        return list(unique_issues.values())

    def _run_critic_analysis(self, code: str, issues: List[CategorizedIssue]) -> List[CategorizedIssue]:
        """Run critic analysis while preserving categories."""
        if not issues:
            return []

        # Create mapping of original issues by line and description
        original_issues_map = {}
        for issue in issues:
            key = f"{issue.line}|{issue.description[:50]}"  # First 50 chars for fuzzy matching
            original_issues_map[key] = issue

        # Convert to format expected by critic agent
        issues_for_critic = [issue.to_dict() for issue in issues]

        try:
            refined_issues_dicts = run_critic_agent(code, issues_for_critic, self.api_key)

            # Convert back while preserving original categories
            refined_issues = []
            for issue_dict in refined_issues_dicts:
                # Try to find original issue to preserve category
                search_key = f"{issue_dict.get('line', 0)}|{issue_dict.get('description', '')[:50]}"
                original_issue = None

                # Fuzzy search for original issue
                for key, orig_issue in original_issues_map.items():
                    if (str(issue_dict.get('line', 0)) in key and
                            any(word in key.lower() for word in issue_dict.get('description', '').lower().split()[:3])):
                        original_issue = orig_issue
                        break

                # Use original category if found, otherwise default to QUALITY
                category = original_issue.category if original_issue else IssueCategory.QUALITY
                source_agent = original_issue.source_agent if original_issue else 'critic'

                categorized = CategorizedIssue.from_raw_issue(
                    issue_dict, category, source_agent
                )
                refined_issues.append(categorized)

            return refined_issues

        except Exception as e:
            print(f"   ⚠️ Critic analysis failed: {e}")
            return issues  # Return original issues if critic fails

    def _organize_by_category(self, issues: List[CategorizedIssue]) -> Dict[str, List[Dict]]:
        """Organize issues by category."""
        categorized = defaultdict(list)
        for issue in issues:
            categorized[issue.category.value].append(issue.to_dict())
        return dict(categorized)

    def _calculate_overall_score(self, issues_by_category: Dict[str, List[Dict]]) -> float:
        """Calculate overall quality score."""
        if not any(issues_by_category.values()):
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
        total_issues = 0

        for category, issues in issues_by_category.items():
            cat_weight = category_weights.get(category, 1.0)

            for issue in issues:
                sev_weight = severity_weights.get(issue.get('severity', 'medium'), 2.0)
                confidence = issue.get('confidence', 0.8)
                penalty = cat_weight * sev_weight * confidence
                total_penalty += penalty
                total_issues += 1

        # Normalize penalty based on issue count
        if total_issues > 0:
            avg_penalty = total_penalty / total_issues
            max_penalty = min(avg_penalty * 10, 100)  # Cap at 100
        else:
            max_penalty = 0

        return max(0, 100 - max_penalty)

    def _calculate_category_scores(self, issues_by_category: Dict[str, List[Dict]]) -> Dict[str, float]:
        """Calculate scores for each category."""
        category_scores = {}

        for category, issues in issues_by_category.items():
            if not issues:
                category_scores[category] = 100.0
                continue

            # Simple scoring based on issue count and severity
            penalty = 0
            for issue in issues:
                severity_penalty = {'high': 15, 'medium': 10, 'low': 5}
                penalty += severity_penalty.get(issue.get('severity', 'medium'), 10)

            score = max(0, 100 - penalty)
            category_scores[category] = score

        return category_scores

    def _print_final_summary(self, results: Dict[str, Any]):
        """Print comprehensive final summary."""
        print(f"\n🎯 Comprehensive Analysis Complete")
        print("=" * 60)
        print(f"📊 Mode: {results['mode']}")
        print(f"🔍 Analyses Run: {', '.join(results['analyses_run'])}")
        print(f"📋 Total Unique Issues: {results['total_unique_issues']}")
        print(f"🏆 Overall Score: {results['overall_score']:.1f}/100")

        # Show raw analysis counts
        print(f"\n📈 Raw Analysis Results:")
        for analysis, count in results['raw_analysis_counts'].items():
            print(f"   {analysis.title()}: {count} issues found")

        # Show issues by category
        if results['issues_by_category']:
            print(f"\n📂 Final Issues by Category:")
            for category, issues in results['issues_by_category'].items():
                score = results['category_scores'].get(category, 0)
                print(f"   {category.upper()}: {len(issues)} issues (Score: {score:.1f})")


# Integration function for backward compatibility
def run_comprehensive_analysis(code: str, api_key: str, mode: str = "full_scan",
                               context: Dict = None) -> Dict[str, Any]:
    """
    Run comprehensive analysis without AI inconsistency issues.

    Args:
        code: Source code to analyze
        api_key: API key for AI services
        mode: Analysis mode
        context: Project context

    Returns:
        Comprehensive analysis results
    """
    agent = ComprehensiveAnalysisAgent(api_key)
    return agent.analyze_comprehensively(code, mode, context)