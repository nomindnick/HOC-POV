"""API endpoints for LLM model management"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
from backend.llm.client import ollama_client, ModelInfo
from backend.config import settings


class ModelsResponse(BaseModel):
    """Response for models endpoint"""
    status: str
    ollama_available: bool
    models: List[ModelInfo]
    error: str = None


router = APIRouter(
    prefix=f"{settings.api_v1_str}/models",
    tags=["models"]
)


@router.get("/", response_model=ModelsResponse)
async def list_models():
    """
    Get list of available LLM models from Ollama

    Returns:
        ModelsResponse with model list and Ollama status
    """
    # Check if Ollama is available
    ollama_available = await ollama_client.health_check()

    if not ollama_available:
        return ModelsResponse(
            status="error",
            ollama_available=False,
            models=[],
            error="Ollama not available. Please ensure Ollama is running on localhost:11434"
        )

    try:
        models = await ollama_client.list_models()

        # Sort models by size (smallest first) for better UX
        models.sort(key=lambda m: m.size)

        return ModelsResponse(
            status="ok",
            ollama_available=True,
            models=models
        )

    except Exception as e:
        return ModelsResponse(
            status="error",
            ollama_available=False,
            models=[],
            error=str(e)
        )


@router.get("/recommended")
async def get_recommended_models():
    """
    Get recommended models for CPRA classification

    Returns models that are known to work well for the task
    """
    recommended = [
        {
            "model": "gemma3:4b",
            "reason": "Good balance of speed and accuracy",
            "min_ram": "8GB",
            "speed": "fast"
        },
        {
            "model": "phi4-mini:3.8b",
            "reason": "Fast inference, decent accuracy",
            "min_ram": "6GB",
            "speed": "very fast"
        },
        {
            "model": "qwen3:8b",
            "reason": "Higher accuracy, slower inference",
            "min_ram": "12GB",
            "speed": "moderate"
        },
        {
            "model": "llama3:8b-instruct-q5_K_M",
            "reason": "Best accuracy, instruction-tuned",
            "min_ram": "12GB",
            "speed": "moderate"
        }
    ]

    # Check which recommended models are actually available
    try:
        available_models = await ollama_client.list_models()
        available_names = {m.name for m in available_models}

        for model in recommended:
            model["available"] = model["model"] in available_names

    except Exception:
        # If can't check availability, mark all as unknown
        for model in recommended:
            model["available"] = None

    return {
        "recommended": recommended,
        "note": "Models marked as available are currently installed in Ollama"
    }


@router.post("/refresh")
async def refresh_model_cache():
    """
    Force refresh of the model cache

    Useful after installing new models in Ollama
    """
    ollama_client.clear_cache()

    try:
        models = await ollama_client.list_models()
        return {
            "status": "ok",
            "message": "Model cache refreshed",
            "model_count": len(models)
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to refresh models: {str(e)}"
        )