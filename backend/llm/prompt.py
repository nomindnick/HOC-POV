"""Prompt template engine for LLM classification"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.db.schema import Email


class PromptBuilder:
    """Build prompts for email classification with few-shot examples"""

    def __init__(
        self,
        fewshot_path: Optional[str] = None,
        version: Optional[str] = None
    ):
        """
        Initialize prompt builder

        Args:
            fewshot_path: Path to few-shot examples JSON file
            version: Specific version to load (defaults to latest)
        """
        if fewshot_path is None:
            # Default to fewshot.json in same directory
            fewshot_path = os.path.join(
                os.path.dirname(__file__),
                "fewshot.json"
            )

        self.fewshot_path = Path(fewshot_path)
        self.fewshot_data = self._load_fewshot()

        # Use specified version or default to latest
        if version:
            self.version = version
        else:
            self.version = self.fewshot_data.get("version", "1.0")

        self.system_prompt = self.fewshot_data.get("system", "")
        self.examples = self.fewshot_data.get("examples", [])
        self.output_schema = self.fewshot_data.get("output_schema", {})

    def _load_fewshot(self) -> Dict[str, Any]:
        """Load few-shot examples from JSON file"""
        if not self.fewshot_path.exists():
            # Return minimal default if file doesn't exist
            return {
                "version": "1.0",
                "system": self._get_default_system_prompt(),
                "examples": [],
                "output_schema": self._get_default_schema()
            }

        try:
            with open(self.fewshot_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {self.fewshot_path}: {e}")

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt if not provided"""
        return """You are a careful legal assistant helping classify emails for a California Public Records Act (CPRA) request regarding environmental hazards and building-system conditions at K-12 schools and district facilities.

Your task is to determine whether an email meaningfully discusses or pertains to environmental conditions such as:
- Mold (inspection, testing, remediation, moisture intrusion)
- Lead (water testing, plumbing maintenance, paint/glazing - NOT "lead teacher" or "leadership")
- Asbestos (inspection, abatement, management, monitoring)
- Other environmental hazards (radon, PCBs, pesticides, VOCs, indoor air quality)
- Building and infrastructure systems (HVAC, roofing, windows, drainage)
- Funding and remediation plans for environmental issues

Be very careful to avoid false positives where words like "lead" mean "leadership," "lead teacher," "lead time," or other unrelated senses.

Output your classification as valid JSON matching the provided schema."""

    def _get_default_schema(self) -> Dict[str, Any]:
        """Get default output schema"""
        return {
            "responsive": {
                "type": "boolean",
                "description": "True if email is responsive to CPRA request"
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score between 0.0 and 1.0",
                "minimum": 0.0,
                "maximum": 1.0
            },
            "reason": {
                "type": "string",
                "description": "Brief explanation (max 200 chars)",
                "maxLength": 200
            },
            "labels": {
                "type": "array",
                "description": "List of relevant environmental hazard labels",
                "items": {"type": "string"}
            }
        }

    def build(self, email: Email) -> str:
        """
        Build classification prompt for an email

        Args:
            email: Email object to classify

        Returns:
            Complete prompt string with system prompt, few-shot examples, and email
        """
        prompt_parts = []

        # System prompt
        prompt_parts.append(self.system_prompt)
        prompt_parts.append("")

        # Output schema
        prompt_parts.append("Your output must be valid JSON with this structure:")
        prompt_parts.append("```json")
        prompt_parts.append(json.dumps({
            "responsive": "boolean (true/false)",
            "confidence": "number (0.0-1.0)",
            "reason": "string (max 200 chars)",
            "labels": ["list", "of", "labels"]
        }, indent=2))
        prompt_parts.append("```")
        prompt_parts.append("")

        # Few-shot examples
        if self.examples:
            prompt_parts.append("Here are some examples of correct classifications:")
            prompt_parts.append("")

            for i, example in enumerate(self.examples, 1):
                prompt_parts.append(f"Example {i}:")
                prompt_parts.append(f"Subject: {example.get('subject', 'N/A')}")
                if example.get('from'):
                    prompt_parts.append(f"From: {example['from']}")
                if example.get('body'):
                    prompt_parts.append(f"Body: {example['body'][:500]}")  # Truncate long bodies
                prompt_parts.append("")
                prompt_parts.append("Classification:")
                prompt_parts.append(json.dumps(example.get('output', {}), indent=2))
                prompt_parts.append("")

        # Current email to classify
        prompt_parts.append("Now classify this email:")
        prompt_parts.append("")
        prompt_parts.append(f"Subject: {email.subject or 'N/A'}")
        if email.from_addr:
            prompt_parts.append(f"From: {email.from_addr}")
        if email.to_addr:
            prompt_parts.append(f"To: {email.to_addr}")
        if email.date:
            prompt_parts.append(f"Date: {email.date}")
        prompt_parts.append("")
        prompt_parts.append(f"Body: {email.body_text}")
        prompt_parts.append("")
        prompt_parts.append("Classification (output JSON only):")

        return "\n".join(prompt_parts)

    def build_from_dict(self, email_dict: Dict[str, Any]) -> str:
        """
        Build classification prompt from dictionary representation

        Args:
            email_dict: Dictionary with email fields

        Returns:
            Complete prompt string
        """
        # Create a mock Email object for compatibility
        class MockEmail:
            def __init__(self, data):
                self.subject = data.get("subject")
                self.from_addr = data.get("from_addr") or data.get("from")
                self.to_addr = data.get("to_addr") or data.get("to")
                self.date = data.get("date")
                self.body_text = data.get("body_text") or data.get("body", "")

        mock_email = MockEmail(email_dict)
        return self.build(mock_email)

    def get_version(self) -> str:
        """Get current prompt version"""
        return self.version

    def get_metadata(self) -> Dict[str, Any]:
        """Get prompt metadata for tracking"""
        return {
            "version": self.version,
            "num_examples": len(self.examples),
            "fewshot_path": str(self.fewshot_path),
            "timestamp": datetime.utcnow().isoformat()
        }

    def validate_output(self, output_str: str) -> Dict[str, Any]:
        """
        Validate and parse LLM output

        Args:
            output_str: Raw output from LLM

        Returns:
            Parsed and validated classification result

        Raises:
            ValueError: If output is invalid or cannot be parsed
        """
        # Try to extract JSON from the output
        import re

        # Remove markdown code blocks if present
        output_str = re.sub(r'^```json\s*\n?', '', output_str, flags=re.MULTILINE)
        output_str = re.sub(r'\n?```\s*$', '', output_str, flags=re.MULTILINE)

        # Try to find JSON object
        json_match = re.search(r'\{.*\}', output_str, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON object found in output")

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            # Try to fix common issues
            fixed = json_match.group()
            # Replace single quotes with double quotes
            fixed = re.sub(r"'([^']*)'", r'"\1"', fixed)
            # Remove trailing commas
            fixed = re.sub(r',\s*}', '}', fixed)
            fixed = re.sub(r',\s*]', ']', fixed)

            try:
                data = json.loads(fixed)
            except json.JSONDecodeError:
                raise ValueError(f"Cannot parse JSON: {e}")

        # Validate required fields
        if "responsive" not in data:
            raise ValueError("Missing 'responsive' field")

        # Ensure responsive is boolean
        data["responsive"] = bool(data["responsive"])

        # Validate and clamp confidence
        confidence = data.get("confidence", 0.5)
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.5
        data["confidence"] = confidence

        # Ensure reason is string and truncate if needed
        reason = str(data.get("reason", "No reason provided"))
        if len(reason) > 200:
            reason = reason[:197] + "..."
        data["reason"] = reason

        # Ensure labels is a list
        labels = data.get("labels", [])
        if not isinstance(labels, list):
            labels = [labels] if labels else []
        # Convert all labels to strings
        labels = [str(label) for label in labels]
        data["labels"] = labels

        return data


def get_default_prompt_builder() -> PromptBuilder:
    """Get a default prompt builder instance"""
    return PromptBuilder()