"""ADK Agent Test Endpoints"""
from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.services.adk_agent import ADKAgent, get_adk_agent, test_gemini_connection
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])
logger = get_logger(__name__)


@router.get("/test")
async def test_agent_connection() -> Dict[str, Any]:
    """
    Test VertexAI Gemini connectivity with Workload Identity.

    This endpoint validates:
    - VertexAI initialization
    - Service account permissions
    - Gemini API access
    - Basic generation functionality

    Returns:
        Test result with status and sample response
    """
    logger.info("Agent test endpoint called")

    result = await test_gemini_connection()

    return result


@router.get("/info")
async def get_agent_info(
    agent: ADKAgent = Depends(get_adk_agent)
) -> Dict[str, Any]:
    """
    Get ADK agent configuration information.

    Returns:
        Model configuration and status
    """
    logger.info("Agent info endpoint called")

    return {
        "agent_info": agent.get_model_info(),
        "status": "initialized"
    }


@router.post("/generate")
async def generate_test_response(
    prompt: str,
    agent: ADKAgent = Depends(get_adk_agent)
) -> Dict[str, Any]:
    """
    Test generation endpoint.

    Args:
        prompt: Text prompt for generation

    Returns:
        Generated response
    """
    logger.info("Generate test endpoint called", prompt_length=len(prompt))

    try:
        response = await agent.generate_response(prompt)

        return {
            "status": "success",
            "prompt": prompt,
            "response": response,
            "model": agent.model_name
        }

    except Exception as e:
        logger.error("Generation failed", error=str(e))
        return {
            "status": "failed",
            "error": str(e)
        }
