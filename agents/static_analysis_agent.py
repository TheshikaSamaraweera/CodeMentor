# agents/static_analysis_agent.py
import subprocess
import json
import hashlib
import tempfile
import os
from typing import Dict, List, Any, Set, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import logging
from utils.language_detector import detect_language
from utils.cache_manager import load_cached_results, save_cached_results
from dataclasses import dataclass, asdict
from collections import defaultdict
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StaticAnalysisRunner:
    """Enhanced static analysis with better error handling and parallel execution."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.available_tools = self._check_tool_availability()

    def _check_tool_availability(self) -> Dict[str, bool]:
        """Check which static analysis tools are available."""
        tools = {
            'pylint': self._is_tool_available('pylint'),
            'bandit': self._is_tool_available('bandit'),
            'eslint': self._is_tool_available('eslint'),
            'checkstyle': self._is_tool_available('checkstyle')
        }

        logger.info(f"Available static analysis tools: {[k for k, v in tools.items() if v]}")
        return tools

    def _is_tool_available(self, tool_name: str) -> bool:
        """Check if a tool is available in the system."""
        try:
            result = subprocess.run([tool_name, '--version'],
                                    capture_output=True,
                                    text=True,
                                    timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False

    def run_tool_with_timeout(self, cmd: List[str], timeout: int = None) -> subprocess.CompletedProcess:
        """Run a command with timeout and proper error handling."""
        timeout = timeout or self.timeout

        try:
            return subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                check=False  # Don't raise on non-zero exit
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out after {timeout}s: {' '.join(cmd)}")
            raise
        except Exception as e:
            logger.error(f"Command failed: {' '.join(cmd)}, Error: {e}")
            raise


def run_static_analysis(file_path: str) -> List[Dict[str, Any]]:
    """Enhanced static analysis with better error handling and parallel execution."""
    print("🔎 Running Enhanced Static Analysis...")

    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return []

    language = detect_language(file_path)

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return []

    # Check cache first
    cached_results = load_cached_results(code)
    if cached_results:
        print(f"✅ Using cached static analysis results - Found {len(cached_results)} issues")
        return cached_results

    runner = StaticAnalysisRunner()
    all_issues = []

    # Create temporary file with correct extension
    extension = os.path.splitext(file_path)[1] or _get_extension_for_language(language)

    try:
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False, mode="w", encoding='utf-8') as temp_file:
            temp_file.write(code)
            temp_path = temp_file.name

        # Run appropriate analyzers based on language and tool availability
        analyzers = _get_analyzers_for_language(language, runner.available_tools)

        if not analyzers:
            logger.warning(f"No static analysis tools available for {language}")
            return []

        # Run analyzers in parallel for better performance
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []

            for analyzer_name, analyzer_func in analyzers.items():
                future = executor.submit(_run_analyzer_safely, analyzer_func, temp_path, analyzer_name)
                futures.append(future)

            # Collect results
            for future in futures:
                try:
                    issues = future.result(timeout=runner.timeout)
                    all_issues.extend(issues)
                except TimeoutError:
                    logger.warning("Analyzer timed out")
                except Exception as e:
                    logger.error(f"Analyzer failed: {e}")

        # Clean up temp file
        os.unlink(temp_path)

    except Exception as e:
        logger.error(f"Static analysis setup failed: {e}")
        return []

    # Remove duplicates and sort by line number
    all_issues = _deduplicate_issues(all_issues)
    all_issues.sort(key=lambda x: (x.get("line", 0), x.get("tool", "")))

    # Cache results
    save_cached_results(code, all_issues)

    print(f"✅ Enhanced Static Analysis completed - Found {len(all_issues)} issues across {len(analyzers)} tools")
    return all_issues


def _run_analyzer_safely(analyzer_func, temp_path: str, analyzer_name: str) -> List[Dict]:
    """Safely run an analyzer function with error handling."""
    try:
        return analyzer_func(temp_path)
    except Exception as e:
        logger.error(f"{analyzer_name} failed: {e}")
        return []


def _get_extension_for_language(language: str) -> str:
    """Get file extension for a given language."""
    extensions = {
        "Python": ".py",
        "JavaScript": ".js",
        "TypeScript": ".ts",
        "Java": ".java",
        "C++": ".cpp",
        "C": ".c"
    }
    return extensions.get(language, ".py")


def _get_analyzers_for_language(language: str, available_tools: Dict[str, bool]) -> Dict[str, callable]:
    """Get available analyzers for a specific language."""
    analyzers = {}

    if language == "Python":
        if available_tools.get('pylint'):
            analyzers['pylint'] = run_pylint
        if available_tools.get('bandit'):
            analyzers['bandit'] = run_bandit
    elif language in ["JavaScript", "TypeScript"]:
        if available_tools.get('eslint'):
            analyzers['eslint'] = run_eslint
    elif language == "Java":
        if available_tools.get('checkstyle'):
            analyzers['checkstyle'] = run_checkstyle

    return analyzers


def _deduplicate_issues(issues: List[Dict]) -> List[Dict]:
    """Remove duplicate issues based on line number and description."""
    seen = set()
    deduplicated = []

    for issue in issues:
        key = (issue.get("line", 0), issue.get("issue", "").strip().lower())
        if key not in seen:
            seen.add(key)
            deduplicated.append(issue)

    return deduplicated


def run_pylint(file_path: str) -> List[Dict]:
    """Enhanced pylint runner with better error handling."""
    issues = []
    try:
        runner = StaticAnalysisRunner()
        result = runner.run_tool_with_timeout(
            ["pylint", file_path, "-f", "json", "--disable=C0114,C0115,C0116"]
        )

        if result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                for item in data:
                    issues.append({
                        "tool": "pylint",
                        "line": item.get("line", 0),
                        "issue": item.get("message", ""),
                        "suggestion": f"Fix {item.get('symbol', 'issue')}",
                        "severity": _map_pylint_severity(item.get("type", "")),
                        "confidence": 0.8,
                        "rule": item.get("symbol", "")
                    })
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse pylint JSON output: {e}")

    except Exception as e:
        logger.error(f"pylint execution failed: {e}")

    return issues


def run_bandit(file_path: str) -> List[Dict]:
    """Enhanced bandit runner."""
    issues = []
    try:
        runner = StaticAnalysisRunner()
        result = runner.run_tool_with_timeout(
            ["bandit", "-f", "json", "-q", file_path]
        )

        if result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                for item in data.get("results", []):
                    issues.append({
                        "tool": "bandit",
                        "line": item.get("line_number", 0),
                        "issue": item.get("issue_text", ""),
                        "suggestion": f"Security fix needed: {item.get('test_name', '')}",
                        "severity": "high",  # Bandit focuses on security
                        "confidence": _map_bandit_confidence(item.get("issue_confidence", "MEDIUM")),
                        "rule": item.get("test_id", "")
                    })
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse bandit JSON output: {e}")

    except Exception as e:
        logger.error(f"bandit execution failed: {e}")

    return issues


def run_eslint(file_path: str) -> List[Dict]:
    """Enhanced eslint runner."""
    issues = []
    try:
        runner = StaticAnalysisRunner()
        result = runner.run_tool_with_timeout(
            ["eslint", file_path, "--format", "json", "--no-eslintrc", "--env", "browser,node"]
        )

        if result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                for file_result in data:
                    for item in file_result.get("messages", []):
                        issues.append({
                            "tool": "eslint",
                            "line": item.get("line", 0),
                            "issue": item.get("message", ""),
                            "suggestion": f"Fix ESLint rule: {item.get('ruleId', '')}",
                            "severity": _map_eslint_severity(item.get("severity", 1)),
                            "confidence": 0.85,
                            "rule": item.get("ruleId", "")
                        })
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse eslint JSON output: {e}")

    except Exception as e:
        logger.error(f"eslint execution failed: {e}")

    return issues


def run_checkstyle(file_path: str) -> List[Dict]:
    """Enhanced checkstyle runner."""
    issues = []
    try:
        # Try to find checkstyle configuration
        config_options = [
            "/google_checks.xml",
            "/sun_checks.xml",
            "google_checks.xml",
            "sun_checks.xml"
        ]

        config_file = None
        for config in config_options:
            if os.path.exists(config):
                config_file = config
                break

        if not config_file:
            logger.warning("No checkstyle configuration found, skipping")
            return []

        runner = StaticAnalysisRunner()
        result = runner.run_tool_with_timeout(
            ["checkstyle", "-c", config_file, file_path]
        )

        # Parse checkstyle output (usually text format)
        lines = result.stdout.splitlines()
        for line in lines:
            if any(level in line for level in ["ERROR", "WARN", "INFO"]):
                parts = line.split(":")
                if len(parts) >= 3:
                    try:
                        line_num = int(parts[1]) if parts[1].isdigit() else 0
                        message = ":".join(parts[2:]).strip()

                        issues.append({
                            "tool": "checkstyle",
                            "line": line_num,
                            "issue": message,
                            "suggestion": "Follow Java coding standards",
                            "severity": "medium",
                            "confidence": 0.8,
                            "rule": "checkstyle"
                        })
                    except (ValueError, IndexError):
                        continue

    except Exception as e:
        logger.error(f"checkstyle execution failed: {e}")

    return issues


def _map_pylint_severity(pylint_type: str) -> str:
    """Map pylint message types to our severity levels."""
    mapping = {
        "error": "high",
        "warning": "medium",
        "refactor": "medium",
        "convention": "low",
        "info": "low"
    }
    return mapping.get(pylint_type.lower(), "medium")


def _map_bandit_confidence(bandit_confidence: str) -> float:
    """Map bandit confidence levels to numeric values."""
    mapping = {
        "HIGH": 0.9,
        "MEDIUM": 0.7,
        "LOW": 0.5
    }
    return mapping.get(bandit_confidence.upper(), 0.7)


def _map_eslint_severity(eslint_severity: int) -> str:
    """Map eslint severity levels."""
    return "high" if eslint_severity == 2 else "medium"