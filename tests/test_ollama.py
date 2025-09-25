"""Tests for Ollama client and model discovery"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from backend.llm.client import OllamaClient, ModelInfo, GenerateResponse
from backend.api.models import list_models, get_recommended_models, refresh_model_cache


@pytest.fixture
def ollama_client():
    """Create an OllamaClient instance for testing"""
    return OllamaClient()


@pytest.fixture
def mock_model_data():
    """Sample model data from Ollama API"""
    return {
        "models": [
            {
                "name": "gemma3:4b",
                "model": "gemma3:4b",
                "size": 3300000000,
                "digest": "abc123",
                "modified_at": "2024-01-15T10:00:00Z",
                "details": {"parameter_size": "4B", "format": "gguf"}
            },
            {
                "name": "phi4-mini:3.8b",
                "model": "phi4-mini:3.8b",
                "size": 2500000000,
                "digest": "def456",
                "modified_at": "2024-01-14T10:00:00Z",
                "details": {"parameter_size": "3.8B", "format": "gguf"}
            }
        ]
    }


@pytest.fixture
def mock_generate_response():
    """Sample generate response from Ollama"""
    return {
        "model": "gemma3:4b",
        "response": '{"responsive": true, "confidence": 0.85, "reason": "Test", "labels": ["test"]}',
        "done": True,
        "total_duration": 1000000000,
        "eval_count": 50
    }


class TestOllamaClient:
    """Test the OllamaClient class"""

    @pytest.mark.asyncio
    async def test_health_check_success(self, ollama_client):
        """Test health check when Ollama is available"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await ollama_client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, ollama_client):
        """Test health check when Ollama is not available"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )

            result = await ollama_client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_list_models_success(self, ollama_client, mock_model_data):
        """Test listing models successfully"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_model_data
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            models = await ollama_client.list_models()

            assert len(models) == 2
            assert models[0].name == "gemma3:4b"
            assert models[0].size_display == "3.1 GB"
            assert models[1].name == "phi4-mini:3.8b"
            assert models[1].size_display == "2.3 GB"

    @pytest.mark.asyncio
    async def test_list_models_caching(self, ollama_client, mock_model_data):
        """Test that models are cached properly"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_model_data
            mock_response.raise_for_status = MagicMock()
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            # First call - should hit API
            models1 = await ollama_client.list_models()
            assert len(models1) == 2
            assert mock_get.call_count == 1

            # Second call - should use cache
            models2 = await ollama_client.list_models()
            assert len(models2) == 2
            assert mock_get.call_count == 1  # Still 1, not 2

            # Clear cache and call again
            ollama_client.clear_cache()
            models3 = await ollama_client.list_models()
            assert len(models3) == 2
            assert mock_get.call_count == 2  # Now incremented

    @pytest.mark.asyncio
    async def test_list_models_connection_error(self, ollama_client):
        """Test handling connection error when listing models"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )

            with pytest.raises(ConnectionError) as exc_info:
                await ollama_client.list_models()
            assert "Cannot connect to Ollama" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_success(self, ollama_client, mock_generate_response):
        """Test successful text generation"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_generate_response
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await ollama_client.generate(
                prompt="Test prompt",
                model="gemma3:4b",
                temperature=0.5,
                format="json"
            )

            assert result.model == "gemma3:4b"
            assert "responsive" in result.response
            assert result.done is True

    @pytest.mark.asyncio
    async def test_generate_timeout(self, ollama_client):
        """Test handling timeout during generation"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Request timed out")
            )

            with pytest.raises(TimeoutError) as exc_info:
                await ollama_client.generate("Test", "gemma3:4b")
            assert "Generation timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_stream_not_implemented(self, ollama_client):
        """Test that streaming is not yet implemented"""
        with pytest.raises(NotImplementedError) as exc_info:
            await ollama_client.generate("Test", "gemma3:4b", stream=True)
        assert "Streaming not yet supported" in str(exc_info.value)


class TestModelsAPI:
    """Test the models API endpoints"""

    @pytest.mark.asyncio
    async def test_list_models_endpoint_success(self, mock_model_data):
        """Test /api/models endpoint when Ollama is available"""
        with patch('backend.api.models.ollama_client') as mock_client:
            mock_client.health_check = AsyncMock(return_value=True)
            mock_client.list_models = AsyncMock(return_value=[
                ModelInfo(**m) for m in mock_model_data["models"]
            ])

            response = await list_models()

            assert response.status == "ok"
            assert response.ollama_available is True
            assert len(response.models) == 2
            assert response.error is None

    @pytest.mark.asyncio
    async def test_list_models_endpoint_ollama_offline(self):
        """Test /api/models endpoint when Ollama is offline"""
        with patch('backend.api.models.ollama_client') as mock_client:
            mock_client.health_check = AsyncMock(return_value=False)

            response = await list_models()

            assert response.status == "error"
            assert response.ollama_available is False
            assert len(response.models) == 0
            assert "Ollama not available" in response.error

    @pytest.mark.asyncio
    async def test_get_recommended_models(self, mock_model_data):
        """Test /api/models/recommended endpoint"""
        with patch('backend.api.models.ollama_client') as mock_client:
            mock_client.list_models = AsyncMock(return_value=[
                ModelInfo(**m) for m in mock_model_data["models"]
            ])

            response = await get_recommended_models()

            assert "recommended" in response
            assert len(response["recommended"]) > 0

            # Check that availability is marked correctly
            for model in response["recommended"]:
                if model["model"] == "gemma3:4b":
                    assert model["available"] is True
                elif model["model"] == "qwen3:8b":
                    assert model["available"] is False

    @pytest.mark.asyncio
    async def test_refresh_model_cache(self, mock_model_data):
        """Test /api/models/refresh endpoint"""
        with patch('backend.api.models.ollama_client') as mock_client:
            mock_client.clear_cache = MagicMock()
            mock_client.list_models = AsyncMock(return_value=[
                ModelInfo(**m) for m in mock_model_data["models"]
            ])

            response = await refresh_model_cache()

            assert response["status"] == "ok"
            assert response["model_count"] == 2
            mock_client.clear_cache.assert_called_once()


class TestModelInfo:
    """Test the ModelInfo class"""

    def test_model_info_size_display(self):
        """Test human-readable size formatting"""
        # Test GB display
        model_gb = ModelInfo(
            name="test",
            model="test",
            size=5000000000,  # 5 GB
            digest="test",
            modified_at="2024-01-01T00:00:00Z"
        )
        assert model_gb.size_display == "4.7 GB"

        # Test MB display
        model_mb = ModelInfo(
            name="test",
            model="test",
            size=500000000,  # 500 MB
            digest="test",
            modified_at="2024-01-01T00:00:00Z"
        )
        assert model_mb.size_display == "477 MB"

        # Test small size
        model_small = ModelInfo(
            name="test",
            model="test",
            size=1000,  # 1 KB
            digest="test",
            modified_at="2024-01-01T00:00:00Z"
        )
        assert model_small.size_display == "1000 B"