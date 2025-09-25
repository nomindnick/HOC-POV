"""Unit tests for prompt template engine"""
import json
import pytest
from datetime import datetime
from pathlib import Path

from backend.llm.prompt import PromptBuilder
from backend.db.schema import Email


@pytest.fixture
def sample_email():
    """Create a sample email for testing"""
    email = Email(
        project_id=1,
        path="/test/email.txt",
        sha256="abc123",
        subject="Test water results",
        from_addr="test@school.edu",
        to_addr="admin@district.edu",
        date=datetime(2024, 1, 15, 10, 30),
        body_text="Found 20 ppb lead in water fountain"
    )
    email.id = 1  # Mock ID since not saved to DB
    return email


@pytest.fixture
def prompt_builder():
    """Create a prompt builder instance"""
    return PromptBuilder()


class TestPromptBuilder:
    """Test PromptBuilder functionality"""

    def test_initialization_with_default_path(self):
        """Test prompt builder initializes with default fewshot.json"""
        builder = PromptBuilder()
        assert builder.version == "1.0"
        assert len(builder.examples) == 12  # We have 12 examples in fewshot.json
        assert "careful legal assistant" in builder.system_prompt

    def test_initialization_with_custom_path(self, tmp_path):
        """Test prompt builder with custom fewshot path"""
        # Create a custom fewshot file
        custom_fewshot = {
            "version": "2.0",
            "system": "Custom system prompt",
            "examples": [
                {
                    "subject": "Test",
                    "body": "Test body",
                    "output": {"responsive": True, "confidence": 0.9}
                }
            ]
        }

        fewshot_path = tmp_path / "custom.json"
        with open(fewshot_path, "w") as f:
            json.dump(custom_fewshot, f)

        builder = PromptBuilder(fewshot_path=str(fewshot_path))
        assert builder.version == "2.0"
        assert builder.system_prompt == "Custom system prompt"
        assert len(builder.examples) == 1

    def test_initialization_with_missing_file(self, tmp_path):
        """Test prompt builder handles missing fewshot file"""
        missing_path = tmp_path / "missing.json"
        builder = PromptBuilder(fewshot_path=str(missing_path))

        # Should use defaults
        assert builder.version == "1.0"
        assert "careful legal assistant" in builder.system_prompt
        assert builder.examples == []

    def test_build_prompt_structure(self, prompt_builder, sample_email):
        """Test that build creates properly structured prompt"""
        prompt = prompt_builder.build(sample_email)

        # Check major sections are present
        assert "careful legal assistant" in prompt  # System prompt
        assert "Your output must be valid JSON" in prompt  # Schema instruction
        assert "Here are some examples" in prompt  # Few-shot examples
        assert "Now classify this email:" in prompt  # Current email section

        # Check email details are included
        assert "Subject: Test water results" in prompt
        assert "From: test@school.edu" in prompt
        assert "Found 20 ppb lead in water fountain" in prompt

    def test_build_prompt_includes_examples(self, prompt_builder, sample_email):
        """Test that few-shot examples are included in prompt"""
        prompt = prompt_builder.build(sample_email)

        # Check specific examples are present
        assert "Fountain water test results" in prompt  # Example 1
        assert "Hiring a lead teacher" in prompt  # Example 2
        assert "Mold discovered" in prompt  # Example 3
        assert "Asbestos abatement" in prompt  # Example 5

    def test_build_prompt_with_missing_fields(self, prompt_builder):
        """Test prompt building with email missing optional fields"""
        email = Email(
            project_id=1,
            path="/test.txt",
            sha256="xyz",
            body_text="Just the body text"
        )
        email.id = 1

        prompt = prompt_builder.build(email)

        assert "Subject: N/A" in prompt  # Missing subject handled
        assert "Body: Just the body text" in prompt
        # Should not have From/To/Date lines if not provided

    def test_build_from_dict(self, prompt_builder):
        """Test building prompt from dictionary"""
        email_dict = {
            "subject": "Dict test",
            "from": "sender@test.com",
            "to": "recipient@test.com",
            "body": "This is from a dictionary"
        }

        prompt = prompt_builder.build_from_dict(email_dict)

        assert "Subject: Dict test" in prompt
        assert "From: sender@test.com" in prompt
        assert "Body: This is from a dictionary" in prompt

    def test_version_tracking(self, prompt_builder):
        """Test version tracking functionality"""
        assert prompt_builder.get_version() == "1.0"

        metadata = prompt_builder.get_metadata()
        assert metadata["version"] == "1.0"
        assert metadata["num_examples"] == 12
        assert "timestamp" in metadata
        assert "fewshot_path" in metadata

    def test_validate_output_valid_json(self, prompt_builder):
        """Test validation of valid JSON output"""
        output = json.dumps({
            "responsive": True,
            "confidence": 0.85,
            "reason": "Contains lead in water",
            "labels": ["lead", "water"]
        })

        result = prompt_builder.validate_output(output)

        assert result["responsive"] is True
        assert result["confidence"] == 0.85
        assert result["reason"] == "Contains lead in water"
        assert result["labels"] == ["lead", "water"]

    def test_validate_output_with_markdown(self, prompt_builder):
        """Test validation handles markdown code blocks"""
        output = """```json
        {
            "responsive": false,
            "confidence": 0.92,
            "reason": "About hiring",
            "labels": []
        }
        ```"""

        result = prompt_builder.validate_output(output)

        assert result["responsive"] is False
        assert result["confidence"] == 0.92

    def test_validate_output_clamping(self, prompt_builder):
        """Test validation clamps values to valid ranges"""
        output = json.dumps({
            "responsive": 1,  # Should convert to boolean
            "confidence": 1.5,  # Should clamp to 1.0
            "reason": "x" * 250,  # Should truncate
            "labels": "single"  # Should convert to list
        })

        result = prompt_builder.validate_output(output)

        assert result["responsive"] is True
        assert result["confidence"] == 1.0
        assert len(result["reason"]) == 200  # Truncated with "..."
        assert result["labels"] == ["single"]

    def test_validate_output_missing_fields(self, prompt_builder):
        """Test validation handles missing fields"""
        output = json.dumps({
            "responsive": True
            # Missing other fields
        })

        result = prompt_builder.validate_output(output)

        assert result["responsive"] is True
        assert result["confidence"] == 0.5  # Default
        assert "No reason provided" in result["reason"]
        assert result["labels"] == []

    def test_validate_output_malformed_json(self, prompt_builder):
        """Test validation handles malformed JSON"""
        # Single quotes instead of double
        output = "{'responsive': true, 'confidence': 0.8}"

        result = prompt_builder.validate_output(output)

        assert result["responsive"] is True
        assert result["confidence"] == 0.8

    def test_validate_output_no_json(self, prompt_builder):
        """Test validation raises error when no JSON found"""
        output = "This is just plain text with no JSON"

        with pytest.raises(ValueError, match="No JSON object found"):
            prompt_builder.validate_output(output)

    def test_validate_output_invalid_json(self, prompt_builder):
        """Test validation raises error for invalid JSON"""
        output = "{this is not: valid json at all}"

        with pytest.raises(ValueError, match="Cannot parse JSON"):
            prompt_builder.validate_output(output)

    def test_edge_case_examples_included(self, prompt_builder, sample_email):
        """Test that edge case examples are included for disambiguation"""
        prompt = prompt_builder.build(sample_email)

        # Check for lead disambiguation examples
        assert "lead teacher" in prompt.lower()  # Non-responsive
        assert "lead paint concern" in prompt.lower()  # Mixed context
        assert "lead time" in prompt.lower()  # Non-responsive
        assert "pencil lead" in prompt.lower()  # Non-responsive

        # These should be marked as responsive or not appropriately
        examples_section = prompt[prompt.find("Example 1"):prompt.find("Now classify")]
        assert '"responsive": false' in examples_section  # For lead teacher
        assert '"responsive": true' in examples_section  # For lead in water