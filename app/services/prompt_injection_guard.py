"""Prompt Injection Detection and Prevention Service"""
import re
from typing import Dict, List, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InjectionDetectionResult:
    """Result of prompt injection detection"""

    def __init__(
        self,
        is_safe: bool,
        threat_level: str,
        detections: List[str],
        sanitized_input: str
    ):
        self.is_safe = is_safe
        self.threat_level = threat_level
        self.detections = detections
        self.sanitized_input = sanitized_input


class PromptInjectionGuard:
    """
    Detects and blocks prompt injection attempts.

    Protects against:
    - System prompt leaks
    - Role hijacking
    - Instruction overrides
    - Context manipulation
    - Jailbreak attempts
    """

    SYSTEM_PROMPT_LEAK_PATTERNS = [
        r'(?i)ignore\s+(previous|all|above)\s+(instructions|prompts?|commands?)',
        r'(?i)show\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions?)',
        r'(?i)what\s+(are|is)\s+your\s+(instructions?|system\s+prompt)',
        r'(?i)repeat\s+(your|the)\s+(instructions?|system\s+prompt)',
        r'(?i)disregard\s+(previous|all|prior)',
    ]

    ROLE_HIJACKING_PATTERNS = [
        r'(?i)you\s+are\s+now\s+(a|an)',
        r'(?i)act\s+as\s+(if\s+)?you',
        r'(?i)pretend\s+(to\s+be|you\s+are)',
        r'(?i)from\s+now\s+on,?\s+you',
        r'(?i)system:\s',
        r'(?i)assistant:\s',
        r'(?i)user:\s',
        r'(?i)\[system\]',
        r'(?i)\[assistant\]',
        r'(?i)<\s*system\s*>',
    ]

    INSTRUCTION_OVERRIDE_PATTERNS = [
        r'(?i)new\s+instructions?:',
        r'(?i)override\s+(previous|all|existing)',
        r'(?i)instead,?\s+(do|say|respond|tell)',
        r'(?i)forget\s+(everything|all|previous)',
        r'(?i)start\s+over',
        r'(?i)reset\s+(your|the)\s+(instructions?|context)',
    ]

    CONTEXT_MANIPULATION_PATTERNS = [
        r'(?i)end\s+of\s+(conversation|session)',
        r'(?i)session\s+(ended|complete|over)',
        r'(?i)terminate\s+(this|the)\s+(session|conversation)',
        r'(?i)exit\s+(simulation|mode)',
    ]

    JAILBREAK_PATTERNS = [
        r'(?i)for\s+(research|educational|testing)\s+purposes',
        r'(?i)in\s+a\s+hypothetical\s+(scenario|world)',
        r'(?i)without\s+any\s+(ethical|moral)\s+constraints',
        r'(?i)ignore\s+(safety|ethical|content)\s+(guidelines|filters?)',
        r'(?i)bypass\s+(restrictions?|filters?|safety)',
        r'(?i)sudo\s+',
        r'(?i)admin\s+mode',
        r'(?i)developer\s+mode',
    ]

    SUSPICIOUS_ENCODING_PATTERNS = [
        r'\\x[0-9a-fA-F]{2}',
        r'&#\d{2,4};',
        r'\\u[0-9a-fA-F]{4}',
        r'%[0-9a-fA-F]{2}',
    ]

    def __init__(self):
        self._stats = {
            "total_checks": 0,
            "blocked": 0,
            "by_threat_level": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "by_type": {
                "system_leak": 0,
                "role_hijack": 0,
                "instruction_override": 0,
                "context_manipulation": 0,
                "jailbreak": 0,
                "encoding": 0
            }
        }

    def check_injection(self, user_input: str) -> InjectionDetectionResult:
        """
        Check user input for prompt injection attempts.

        Args:
            user_input: Raw user input string

        Returns:
            InjectionDetectionResult with detection details
        """
        self._stats["total_checks"] += 1

        detections: List[str] = []
        threat_level = "none"

        system_leak = self._check_patterns(
            user_input,
            self.SYSTEM_PROMPT_LEAK_PATTERNS
        )
        if system_leak:
            detections.append("system_leak")
            threat_level = "critical"
            self._stats["by_type"]["system_leak"] += 1

        role_hijack = self._check_patterns(
            user_input,
            self.ROLE_HIJACKING_PATTERNS
        )
        if role_hijack:
            detections.append("role_hijack")
            if threat_level == "none":
                threat_level = "high"
            self._stats["by_type"]["role_hijack"] += 1

        instruction_override = self._check_patterns(
            user_input,
            self.INSTRUCTION_OVERRIDE_PATTERNS
        )
        if instruction_override:
            detections.append("instruction_override")
            if threat_level == "none":
                threat_level = "high"
            self._stats["by_type"]["instruction_override"] += 1

        context_manip = self._check_patterns(
            user_input,
            self.CONTEXT_MANIPULATION_PATTERNS
        )
        if context_manip:
            detections.append("context_manipulation")
            if threat_level == "none":
                threat_level = "high"
            self._stats["by_type"]["context_manipulation"] += 1

        jailbreak = self._check_patterns(
            user_input,
            self.JAILBREAK_PATTERNS
        )
        if jailbreak:
            detections.append("jailbreak")
            if threat_level == "none":
                threat_level = "high"
            self._stats["by_type"]["jailbreak"] += 1

        encoding = self._check_patterns(
            user_input,
            self.SUSPICIOUS_ENCODING_PATTERNS
        )
        if encoding:
            detections.append("suspicious_encoding")
            if threat_level == "none":
                threat_level = "medium"
            self._stats["by_type"]["encoding"] += 1

        is_safe = threat_level in ["none", "low"]

        if not is_safe:
            self._stats["blocked"] += 1
            self._stats["by_threat_level"][threat_level] += 1

            logger.warning(
                "Prompt injection attempt detected",
                threat_level=threat_level,
                detections=detections,
                input_length=len(user_input)
            )

        sanitized = self.sanitize_input(user_input) if is_safe else ""

        return InjectionDetectionResult(
            is_safe=is_safe,
            threat_level=threat_level,
            detections=detections,
            sanitized_input=sanitized
        )

    def sanitize_input(self, user_input: str) -> str:
        """
        Sanitize user input by removing potentially dangerous patterns.

        Args:
            user_input: Raw input string

        Returns:
            Sanitized input with dangerous patterns removed
        """
        sanitized = user_input

        sanitized = re.sub(r'(?i)system:\s*', '', sanitized)
        sanitized = re.sub(r'(?i)assistant:\s*', '', sanitized)
        sanitized = re.sub(r'(?i)user:\s*', '', sanitized)
        sanitized = re.sub(r'\[system\]', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'\[assistant\]', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'<\s*system\s*>', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'<\s*/\s*system\s*>', '', sanitized, flags=re.IGNORECASE)

        sanitized = sanitized.strip()

        return sanitized

    def get_threat_level(self, user_input: str) -> str:
        """
        Get threat level for input without full check.

        Returns: 'none', 'low', 'medium', 'high', or 'critical'
        """
        result = self.check_injection(user_input)
        return result.threat_level

    def _check_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if any pattern matches the text"""
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        return False

    def get_stats(self) -> Dict[str, any]:
        """Get prompt injection detection statistics"""
        return {
            "total_checks": self._stats["total_checks"],
            "blocked": self._stats["blocked"],
            "block_rate": (
                self._stats["blocked"] / self._stats["total_checks"]
                if self._stats["total_checks"] > 0
                else 0.0
            ),
            "by_threat_level": self._stats["by_threat_level"].copy(),
            "by_type": self._stats["by_type"].copy()
        }


_guard_instance: Optional[PromptInjectionGuard] = None


def get_prompt_injection_guard() -> PromptInjectionGuard:
    """Get singleton prompt injection guard instance"""
    global _guard_instance
    if _guard_instance is None:
        _guard_instance = PromptInjectionGuard()
    return _guard_instance
