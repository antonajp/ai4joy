"""ADK Agent Skeleton with Gemini Integration"""
from typing import Dict, Any, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession
import asyncio

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ADKAgent:
    """
    Skeleton ADK agent implementation with VertexAI Gemini integration.

    This is a foundational implementation that demonstrates:
    - Workload Identity authentication (no API keys)
    - Async execution patterns
    - Basic error handling and retry logic
    - Structured logging for observability

    Future enhancements will add:
    - Multi-agent orchestration
    - Custom tools (GameDatabase, SentimentGauge, etc.)
    - Session management integration
    - Advanced retry strategies with exponential backoff
    """

    def __init__(self, model_name: str = None):
        """
        Initialize ADK agent with VertexAI model.

        Args:
            model_name: Gemini model to use (defaults to flash)
        """
        self.model_name = model_name or settings.vertexai_flash_model
        self.model = None
        self.chat_session = None

        self._initialize_vertexai()

    def _initialize_vertexai(self):
        """
        Initialize VertexAI with Workload Identity.
        No API keys required - uses GCP service account permissions.
        """
        try:
            vertexai.init(
                project=settings.gcp_project_id,
                location=settings.gcp_location
            )

            self.model = GenerativeModel(self.model_name)

            logger.info(
                "VertexAI initialized successfully",
                model=self.model_name,
                project=settings.gcp_project_id,
                location=settings.gcp_location
            )

        except Exception as e:
            logger.error(
                "Failed to initialize VertexAI",
                model=self.model_name,
                error=str(e)
            )
            raise

    async def generate_response(
        self,
        prompt: str,
        max_retries: int = 3
    ) -> str:
        """
        Generate response from Gemini model with retry logic.

        Args:
            prompt: Input prompt
            max_retries: Number of retry attempts for transient failures

        Returns:
            Generated text response

        Raises:
            Exception: If generation fails after retries
        """
        for attempt in range(max_retries):
            try:
                logger.debug(
                    "Generating response",
                    model=self.model_name,
                    prompt_length=len(prompt),
                    attempt=attempt + 1
                )

                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    self._sync_generate,
                    prompt
                )

                logger.info(
                    "Response generated successfully",
                    model=self.model_name,
                    response_length=len(response),
                    attempt=attempt + 1
                )

                return response

            except Exception as e:
                logger.warning(
                    "Generation attempt failed",
                    model=self.model_name,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e)
                )

                if attempt == max_retries - 1:
                    logger.error(
                        "All generation attempts failed",
                        model=self.model_name,
                        error=str(e)
                    )
                    raise

                await asyncio.sleep(2 ** attempt)

    def _sync_generate(self, prompt: str) -> str:
        """Synchronous generation wrapper for executor"""
        response = self.model.generate_content(prompt)
        return response.text

    async def start_chat_session(
        self,
        history: Optional[list] = None
    ) -> ChatSession:
        """
        Start new chat session with optional history.

        Args:
            history: Optional conversation history

        Returns:
            ChatSession object
        """
        try:
            self.chat_session = self.model.start_chat(history=history or [])

            logger.info(
                "Chat session started",
                model=self.model_name,
                history_length=len(history) if history else 0
            )

            return self.chat_session

        except Exception as e:
            logger.error("Failed to start chat session", error=str(e))
            raise

    async def send_message(
        self,
        message: str,
        max_retries: int = 3
    ) -> str:
        """
        Send message in active chat session.

        Args:
            message: User message
            max_retries: Number of retry attempts

        Returns:
            Model response
        """
        if not self.chat_session:
            logger.error("No active chat session")
            raise RuntimeError("No active chat session. Call start_chat_session() first.")

        for attempt in range(max_retries):
            try:
                logger.debug(
                    "Sending message in chat session",
                    message_length=len(message),
                    attempt=attempt + 1
                )

                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    self._sync_send_message,
                    message
                )

                logger.info(
                    "Chat message response received",
                    response_length=len(response),
                    attempt=attempt + 1
                )

                return response

            except Exception as e:
                logger.warning(
                    "Chat message attempt failed",
                    attempt=attempt + 1,
                    error=str(e)
                )

                if attempt == max_retries - 1:
                    logger.error("All chat attempts failed", error=str(e))
                    raise

                await asyncio.sleep(2 ** attempt)

    def _sync_send_message(self, message: str) -> str:
        """Synchronous message send wrapper"""
        response = self.chat_session.send_message(message)
        return response.text

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "project": settings.gcp_project_id,
            "location": settings.gcp_location,
            "has_active_session": self.chat_session is not None
        }


async def test_gemini_connection() -> Dict[str, Any]:
    """
    Test endpoint for validating Gemini API connectivity.

    Returns:
        Test result with status and response sample
    """
    try:
        agent = ADKAgent(model_name=settings.vertexai_flash_model)

        test_prompt = "Say 'Hello from Improv Olympics!' in a friendly way."

        response = await agent.generate_response(test_prompt)

        logger.info("Gemini test successful", response=response)

        return {
            "status": "success",
            "model": agent.model_name,
            "test_prompt": test_prompt,
            "response": response,
            "model_info": agent.get_model_info()
        }

    except Exception as e:
        logger.error("Gemini test failed", error=str(e))
        return {
            "status": "failed",
            "error": str(e)
        }


def get_adk_agent(model_name: Optional[str] = None) -> ADKAgent:
    """Factory function for ADK agent"""
    return ADKAgent(model_name=model_name)
