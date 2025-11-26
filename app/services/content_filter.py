"""Content Filtering Service for User Input Validation"""

import re
from typing import Any, Dict, List, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContentFilterResult:
    """Result of content filtering operation"""

    def __init__(
        self, is_allowed: bool, cleaned_input: str, violations: List[str], severity: str
    ):
        self.is_allowed = is_allowed
        self.cleaned_input = cleaned_input
        self.violations = violations
        self.severity = severity


class ContentFilter:
    """
    Filters user input for offensive content and toxicity.

    Uses regex patterns to detect profanity, hate speech, and toxic behavior.
    Designed for improv context where some edgy content may be acceptable in character.
    """

    PROFANITY_PATTERNS = [
        r"\bf+u+c+k+",
        r"\bs+h+i+t+",
        r"\bbullshit",
        r"\bc+u+n+t+",
        r"\bd+a+m+n+",
        r"\bh+e+l+l+\b",
        r"\ba+s+s+h+o+l+e+",
        r"\bb+i+t+c+h+",
        r"\bp+i+s+s+",
        r"\bc+r+a+p+",
        r"\bd+i+c+k+\b",
        r"\bc+o+c+k+\b",
        r"\bp+u+s+s+y+",
    ]

    SEVERE_PATTERNS = [
        r"\bn+i+g+g+e+r+",
        r"\bf+a+g+g+o+t+",
        r"\br+a+p+e+",
        r"\bk+i+l+l+\s+yourself",
        r"\bsuicide",
        r"\bsex\s+with\s+children",
        r"\bpedophile",
        r"\bchild\s+porn",
    ]

    TOXIC_PATTERNS = [
        r"\byou\s+(are|r)\s+(stupid|dumb|idiot|moron)",
        r"\bgo\s+die",
        r"\bkill\s+yourself",
        r"\bi\s+hate\s+you",
        r"\byou\s+suck",
    ]

    def __init__(self):
        self._stats = {
            "total_checks": 0,
            "blocked": 0,
            "warnings": 0,
            "by_severity": {"severe": 0, "high": 0, "medium": 0, "low": 0},
        }

    def filter_input(self, user_input: str) -> ContentFilterResult:
        """
        Check user input against content filters.

        Args:
            user_input: Raw user input string

        Returns:
            ContentFilterResult with filtering decision and details
        """
        self._stats["total_checks"] += 1

        violations: List[str] = []
        severity = "none"

        input_lower = user_input.lower()

        severe_matches = self._check_patterns(input_lower, self.SEVERE_PATTERNS)
        if severe_matches:
            violations.extend([f"severe:{match}" for match in severe_matches])
            severity = "severe"
            self._stats["blocked"] += 1
            self._stats["by_severity"]["severe"] += 1

            logger.warning(
                "Severe content filter violation",
                severity=severity,
                violation_count=len(severe_matches),
                input_length=len(user_input),
            )

            return ContentFilterResult(
                is_allowed=False,
                cleaned_input="",
                violations=violations,
                severity=severity,
            )

        profanity_matches = self._check_patterns(input_lower, self.PROFANITY_PATTERNS)
        if profanity_matches:
            violations.extend([f"profanity:{match}" for match in profanity_matches])
            profanity_count = len(
                re.findall(
                    r"\b(?:f+u+c+k+|s+h+i+t+|bullshit|c+u+n+t+|a+s+s+h+o+l+e+|b+i+t+c+h+)",
                    input_lower,
                )
            )
            severity = "high" if profanity_count > 2 else "medium"
            self._stats["by_severity"][severity] += 1

        toxic_matches = self._check_patterns(input_lower, self.TOXIC_PATTERNS)
        if toxic_matches:
            violations.extend([f"toxic:{match}" for match in toxic_matches])
            if severity == "none":
                severity = "medium"
            self._stats["by_severity"]["medium"] += 1

        if violations:
            self._stats["warnings"] += 1

            logger.info(
                "Content filter warnings detected",
                severity=severity,
                violation_count=len(violations),
                input_length=len(user_input),
            )

        is_allowed = severity in ["none", "low", "medium"]
        if not is_allowed:
            self._stats["blocked"] += 1

        return ContentFilterResult(
            is_allowed=is_allowed,
            cleaned_input=user_input if is_allowed else "",
            violations=violations,
            severity=severity,
        )

    def _check_patterns(self, text: str, patterns: List[str]) -> List[str]:
        """Check text against list of regex patterns"""
        matches = []
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(pattern)
        return matches

    def is_toxic(self, user_input: str) -> bool:
        """
        Quick check if input contains toxic content.

        Returns True if content should be blocked.
        """
        result = self.filter_input(user_input)
        return not result.is_allowed

    def get_filter_stats(self) -> Dict[str, Any]:
        """
        Get content filter statistics.

        Returns:
            Dict with filtering metrics
        """
        return {
            "total_checks": self._stats["total_checks"],
            "blocked": self._stats["blocked"],
            "warnings": self._stats["warnings"],
            "block_rate": (
                self._stats["blocked"] / self._stats["total_checks"]
                if self._stats["total_checks"] > 0
                else 0.0
            ),
            "by_severity": self._stats["by_severity"].copy(),
        }


_filter_instance: Optional[ContentFilter] = None


def get_content_filter() -> ContentFilter:
    """Get singleton content filter instance"""
    global _filter_instance
    if _filter_instance is None:
        _filter_instance = ContentFilter()
    return _filter_instance
