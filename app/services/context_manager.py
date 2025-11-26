"""Context Window Management Service - Simplified with ADK Integration

ADK automatically handles:
- Context window sizing (ADK Runner with session_service)
- Token counting and optimization
- Event-based conversation tracking

This service focuses on:
- Custom context building (location, phase info)
- Session-specific metadata formatting
- Conversation history compaction for display
"""

from typing import List, Dict, Any, Optional

from app.models.session import Session
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContextManager:
    def __init__(self, max_tokens: int = 4000, summarization_threshold: int = 10):
        self.max_tokens = max_tokens
        self.summarization_threshold = summarization_threshold

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def build_optimized_context(
        self, session: Session, user_input: str, turn_number: int
    ) -> str:
        context_parts = [f"Location: {session.location}", f"Turn {turn_number}"]

        if not session.conversation_history:
            return "\n".join(context_parts)

        history_length = len(session.conversation_history)

        if history_length > self.summarization_threshold:
            context_parts.append(self._build_summarized_context(session))
        else:
            context_parts.append(self._build_recent_context(session))

        full_context = "\n".join(context_parts)
        total_tokens = self.estimate_tokens(full_context)

        if total_tokens > self.max_tokens:
            logger.warning(
                "Context exceeds max tokens, applying compaction",
                estimated_tokens=total_tokens,
                max_tokens=self.max_tokens,
                turn_number=turn_number,
            )
            full_context = self._compact_context(context_parts)

        logger.debug(
            "Context built",
            turn_number=turn_number,
            history_length=history_length,
            estimated_tokens=self.estimate_tokens(full_context),
        )

        return full_context

    def _build_recent_context(self, session: Session, window_size: int = 3) -> str:
        if not session.conversation_history:
            return ""

        recent_history = session.conversation_history[-window_size:]
        context_lines = ["Recent conversation:"]

        for turn in recent_history:
            context_lines.append(
                f"Turn {turn['turn_number']}: User: {turn['user_input']}"
            )
            context_lines.append(f"Partner: {turn['partner_response']}")

        return "\n".join(context_lines)

    def _build_summarized_context(self, session: Session) -> str:
        if not session.conversation_history:
            return ""

        total_turns = len(session.conversation_history)
        older_turns = session.conversation_history[:-3]
        recent_turns = session.conversation_history[-3:]

        context_lines = [f"Session summary ({total_turns} turns total):"]

        summary = self._summarize_turns(older_turns)
        context_lines.append(f"Earlier turns: {summary}")

        context_lines.append("\nRecent conversation:")
        for turn in recent_turns:
            context_lines.append(
                f"Turn {turn['turn_number']}: User: {turn['user_input']}"
            )
            context_lines.append(f"Partner: {turn['partner_response']}")

        return "\n".join(context_lines)

    def _summarize_turns(self, turns: List[Dict[str, Any]]) -> str:
        if not turns:
            return "No previous activity"

        turn_count = len(turns)
        phase_changes = []

        for turn in turns:
            if "phase" in turn:
                phase = turn["phase"]
                if not phase_changes or phase_changes[-1] != phase:
                    phase_changes.append(phase)

        key_elements = []

        if turn_count > 0:
            key_elements.append(f"{turn_count} turns completed")

        if len(phase_changes) > 1:
            key_elements.append(f"transitioned through {len(phase_changes)} phases")

        first_turn = turns[0]
        if "user_input" in first_turn:
            first_input_preview = first_turn["user_input"][:50]
            key_elements.append(f"started with '{first_input_preview}...'")

        return ", ".join(key_elements)

    def _compact_context(self, context_parts: List[str]) -> str:
        header = context_parts[0] if context_parts else ""

        if len(context_parts) > 1:
            conversation_text = context_parts[1]
            lines = conversation_text.split("\n")

            compacted_lines = [lines[0]]

            for line in lines[1:]:
                if any(
                    keyword in line.lower() for keyword in ["turn", "user:", "partner:"]
                ):
                    compacted_lines.append(line)

            compact_conversation = "\n".join(compacted_lines[-10:])

            return f"{header}\n{compact_conversation}"

        return header

    def estimate_context_size(self, session: Session) -> Dict[str, Any]:
        if not session.conversation_history:
            return {
                "total_turns": 0,
                "estimated_tokens": 0,
                "requires_summarization": False,
            }

        total_text = ""
        for turn in session.conversation_history:
            total_text += turn.get("user_input", "")
            total_text += turn.get("partner_response", "")

        estimated_tokens = self.estimate_tokens(total_text)
        requires_summarization = (
            len(session.conversation_history) > self.summarization_threshold
        )

        return {
            "total_turns": len(session.conversation_history),
            "estimated_tokens": estimated_tokens,
            "requires_summarization": requires_summarization,
            "within_limit": estimated_tokens < self.max_tokens,
        }


_context_manager_instance: Optional[ContextManager] = None


def get_context_manager(
    max_tokens: int = 4000, summarization_threshold: int = 10
) -> ContextManager:
    global _context_manager_instance

    if _context_manager_instance is None:
        _context_manager_instance = ContextManager(
            max_tokens=max_tokens, summarization_threshold=summarization_threshold
        )

    return _context_manager_instance
