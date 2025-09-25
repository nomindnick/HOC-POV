#!/usr/bin/env python3
"""
Test script for email ingestion functionality.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
import httpx
import json
from backend.utils.email_parser import parse_email_file, parse_date

# Configuration
BASE_URL = "http://localhost:8000"
SAMPLE_EMAILS_DIR = Path(__file__).parent / "sample_emails"


def test_email_parser():
    """Test the email parser with sample files."""
    print("\n=== Testing Email Parser ===")

    sample_file = SAMPLE_EMAILS_DIR / "email_001_lead_water.txt"
    result = parse_email_file(sample_file)

    print(f"Subject: {result['subject']}")
    print(f"From: {result['from_addr']}")
    print(f"To: {result['to_addr']}")
    print(f"Date: {result['date']}")
    print(f"SHA-256: {result['sha256'][:16]}...")
    print(f"Body preview: {result['body_text'][:100]}...")

    assert result['subject'] == "RE: Fountain water test results - Rm 12"
    assert "19 ppb lead" in result['body_text']
    print("✓ Email parser test passed")


def test_date_parser():
    """Test various date formats."""
    print("\n=== Testing Date Parser ===")

    test_dates = [
        ("Mon, 23 Jun 2024 14:30:00 -0700", "RFC 2822"),
        ("23 Jun 2024 14:30:00", "Without timezone"),
        ("2024-06-23 14:30:00", "ISO-like"),
        ("06/23/2024 14:30:00", "US format"),
        ("Jun 23, 2024 14:30:00", "Month name first"),
    ]

    for date_str, format_name in test_dates:
        result = parse_date(date_str)
        print(f"  {format_name}: {date_str} -> {result}")
        assert result is not None, f"Failed to parse: {date_str}"

    print("✓ Date parser test passed")


def test_single_file_upload():
    """Test uploading a single file via API."""
    print("\n=== Testing Single File Upload ===")

    sample_file = SAMPLE_EMAILS_DIR / "email_001_lead_water.txt"

    with open(sample_file, 'rb') as f:
        files = {'files': (sample_file.name, f, 'text/plain')}
        data = {'project_name': 'Test Project'}

        response = httpx.post(f"{BASE_URL}/api/ingest/", files=files, data=data)

    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")

    assert response.status_code == 200
    assert result['count'] == 1
    assert result['duplicates'] == 0
    print("✓ Single file upload test passed")

    return result['project_id']


def test_duplicate_detection(project_id):
    """Test that duplicate files are detected."""
    print("\n=== Testing Duplicate Detection ===")

    sample_file = SAMPLE_EMAILS_DIR / "email_001_lead_water.txt"

    # Upload the same file again
    with open(sample_file, 'rb') as f:
        files = {'files': (sample_file.name, f, 'text/plain')}
        data = {'project_id': project_id}

        response = httpx.post(f"{BASE_URL}/api/ingest/", files=files, data=data)

    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")

    assert response.status_code == 200
    assert result['count'] == 0
    assert result['duplicates'] == 1
    print("✓ Duplicate detection test passed")


def test_bulk_upload(project_id):
    """Test uploading multiple files at once."""
    print("\n=== Testing Bulk Upload ===")

    # Get all sample emails except the one we already uploaded
    email_files = list(SAMPLE_EMAILS_DIR.glob("*.txt"))
    email_files = [f for f in email_files if f.name != "email_001_lead_water.txt"][:5]

    files = []
    for email_file in email_files:
        with open(email_file, 'rb') as f:
            files.append(('files', (email_file.name, f.read(), 'text/plain')))

    data = {'project_id': project_id}
    response = httpx.post(f"{BASE_URL}/api/ingest/", files=files, data=data)

    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")

    assert response.status_code == 200
    assert result['count'] == len(email_files)
    assert result['duplicates'] == 0
    print(f"✓ Bulk upload test passed - uploaded {result['count']} files")


def test_text_content_upload():
    """Test uploading email content directly as text."""
    print("\n=== Testing Text Content Upload ===")

    content = """Subject: Test email via text upload
From: test@example.com
To: admin@school.edu
Date: Mon, 01 Jan 2024 12:00:00 -0800

This is a test email uploaded directly as text content.
It should be parsed and stored correctly."""

    data = {
        'content': content,
        'filename': 'test_text_upload.txt',
        'project_name': 'Text Upload Test'
    }

    response = httpx.post(f"{BASE_URL}/api/ingest/text", data=data)

    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")

    assert response.status_code == 200
    assert result['count'] == 1
    print("✓ Text content upload test passed")


def test_edge_cases():
    """Test edge cases like files without headers."""
    print("\n=== Testing Edge Cases ===")

    # File without headers
    no_headers_file = SAMPLE_EMAILS_DIR / "email_008_no_headers.txt"

    with open(no_headers_file, 'rb') as f:
        files = {'files': (no_headers_file.name, f, 'text/plain')}
        data = {'project_name': 'Edge Cases Test'}

        response = httpx.post(f"{BASE_URL}/api/ingest/", files=files, data=data)

    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")

    assert response.status_code == 200
    assert result['count'] == 1
    print("✓ Edge cases test passed")


def main():
    """Run all tests."""
    print("Starting Email Ingestion Tests...")

    try:
        # Test components
        test_email_parser()
        test_date_parser()

        # Test API endpoints
        project_id = test_single_file_upload()
        test_duplicate_detection(project_id)
        test_bulk_upload(project_id)
        test_text_content_upload()
        test_edge_cases()

        print("\n" + "="*50)
        print("✅ All tests passed successfully!")
        print("="*50)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()