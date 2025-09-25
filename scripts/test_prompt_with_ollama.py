#!/usr/bin/env python
"""Integration test script to test prompt generation with actual Ollama LLM"""
import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.llm.client import OllamaClient
from backend.llm.prompt import PromptBuilder
from backend.db.schema import Email


async def test_classification():
    """Test email classification with Ollama"""
    print("=" * 60)
    print("Testing Prompt System with Ollama")
    print("=" * 60)

    # Initialize clients
    ollama = OllamaClient()
    prompt_builder = PromptBuilder()

    # Check Ollama is available
    print("\n1. Checking Ollama availability...")
    if not await ollama.health_check():
        print("❌ Ollama is not running. Please start Ollama first.")
        return False
    print("✅ Ollama is running")

    # Get available models
    print("\n2. Getting available models...")
    models = await ollama.list_models()
    if not models:
        print("❌ No models available. Please pull a model first.")
        print("   Run: ollama pull phi4-mini")
        return False

    # Sort by size and pick the smallest suitable model
    models.sort(key=lambda m: m.size)
    suitable_models = ["phi4-mini", "qwen2.5:7b", "gemma3:4b", "llama3.2:3b"]

    selected_model = None
    for model in models:
        model_name = model.name.split(":")[0]
        if any(sm in model.name for sm in suitable_models):
            selected_model = model.name
            break

    if not selected_model:
        # Just use the first available model
        selected_model = models[0].name

    print(f"✅ Using model: {selected_model}")

    # Test cases
    test_emails = [
        {
            "name": "Lead in Water (Should be Responsive)",
            "email": Email(
                project_id=1,
                path="/test1.txt",
                sha256="test1",
                subject="Water test results concerning",
                from_addr="facilities@school.edu",
                to_addr="principal@school.edu",
                body_text="The latest water quality test shows 18 ppb lead in the drinking fountain near the gym. This exceeds EPA limits and requires immediate action."
            ),
            "expected_responsive": True
        },
        {
            "name": "Lead Teacher Hiring (Should NOT be Responsive)",
            "email": Email(
                project_id=1,
                path="/test2.txt",
                sha256="test2",
                subject="New lead teacher position",
                from_addr="hr@district.edu",
                to_addr="principal@school.edu",
                body_text="We're pleased to announce the hiring of Ms. Johnson as the new lead teacher for 3rd grade. She will lead the team in curriculum development."
            ),
            "expected_responsive": False
        },
        {
            "name": "Mold Discovery (Should be Responsive)",
            "email": Email(
                project_id=1,
                path="/test3.txt",
                sha256="test3",
                subject="Urgent: Mold found in classroom",
                from_addr="custodian@school.edu",
                to_addr="facilities@district.edu",
                body_text="I discovered black mold growing behind the bookshelf in Room 201. The area is about 2 square feet. We need professional remediation immediately."
            ),
            "expected_responsive": True
        },
        {
            "name": "Lead Time for Supplies (Should NOT be Responsive)",
            "email": Email(
                project_id=1,
                path="/test4.txt",
                sha256="test4",
                subject="Supply order timeline",
                from_addr="procurement@district.edu",
                to_addr="principal@school.edu",
                body_text="The lead time for the new desks is 8 weeks. We need to place the order by March to have them before the new school year."
            ),
            "expected_responsive": False
        }
    ]

    # Test each email
    print(f"\n3. Testing {len(test_emails)} email classifications...")
    print("-" * 60)

    results = []
    for test_case in test_emails:
        # Set ID for the email (needed by prompt builder)
        test_case["email"].id = 1

        print(f"\nTest: {test_case['name']}")
        print(f"Expected: {'Responsive' if test_case['expected_responsive'] else 'Non-responsive'}")

        # Build prompt
        prompt = prompt_builder.build(test_case["email"])

        try:
            # Call Ollama
            response = await ollama.generate(
                prompt=prompt,
                model=selected_model,
                temperature=0.3,  # Lower temperature for more consistent results
                format="json"
            )

            # Parse response
            result = prompt_builder.validate_output(response.response)

            print(f"Result: {'Responsive' if result['responsive'] else 'Non-responsive'}")
            print(f"Confidence: {result['confidence']:.2f}")
            print(f"Reason: {result['reason']}")
            print(f"Labels: {', '.join(result['labels']) if result['labels'] else 'None'}")

            # Check if correct
            correct = result["responsive"] == test_case["expected_responsive"]
            print(f"{'✅ CORRECT' if correct else '❌ INCORRECT'}")

            results.append({
                "test": test_case["name"],
                "correct": correct,
                "confidence": result["confidence"]
            })

        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                "test": test_case["name"],
                "correct": False,
                "confidence": 0
            })

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    correct_count = sum(1 for r in results if r["correct"])
    total_count = len(results)
    accuracy = (correct_count / total_count * 100) if total_count > 0 else 0

    print(f"Correct: {correct_count}/{total_count} ({accuracy:.0f}%)")
    print(f"Average Confidence: {sum(r['confidence'] for r in results) / total_count:.2f}")

    # Show metadata
    print(f"\nPrompt Version: {prompt_builder.get_version()}")
    print(f"Number of Examples: {len(prompt_builder.examples)}")
    print(f"Model Used: {selected_model}")

    return correct_count == total_count


async def main():
    """Main function"""
    try:
        success = await test_classification()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())