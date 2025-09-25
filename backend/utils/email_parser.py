"""
Email parser for RFC-822 formatted plain text emails.
Extracts headers (Subject, From, To, Date) and body text.
"""

from typing import Dict, Optional, Any
from datetime import datetime
from pathlib import Path
import hashlib
import re


def parse_email_file(filepath: Path) -> Dict[str, Any]:
    """
    Parse a plain text email file with RFC-822 headers.

    Args:
        filepath: Path to the email file

    Returns:
        Dictionary with parsed email data including:
        - subject: Email subject line
        - from_addr: Sender address
        - to_addr: Recipient address(es)
        - date: Parsed datetime or None
        - body_text: Email body (everything after first blank line)
        - sha256: SHA-256 hash of the entire file content
    """
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    return parse_email_content(content, str(filepath))


def parse_email_content(content: str, path: str = "") -> Dict[str, Any]:
    """
    Parse email content string with RFC-822 headers.

    Args:
        content: Email content as string
        path: Optional path for reference

    Returns:
        Dictionary with parsed email data
    """
    lines = content.split('\n')

    # Extract headers until first blank line
    headers = {}
    body_start_idx = 0

    for i, line in enumerate(lines):
        # Blank line signals end of headers
        if line.strip() == '':
            body_start_idx = i + 1
            break

        # Handle header continuation (lines starting with whitespace)
        if line.startswith((' ', '\t')) and headers:
            # Append to previous header
            last_key = list(headers.keys())[-1]
            headers[last_key] += ' ' + line.strip()
        else:
            # Parse new header
            match = re.match(r'^([^:]+):\s*(.*)$', line)
            if match:
                key = match.group(1).strip().lower()
                value = match.group(2).strip()
                headers[key] = value

    # Extract body (everything after first blank line)
    body_text = '\n'.join(lines[body_start_idx:]).strip()

    # If no blank line found, treat entire content as body
    if body_start_idx == 0 and not headers:
        body_text = content.strip()

    # Calculate SHA-256 hash of entire content
    sha256 = hashlib.sha256(content.encode()).hexdigest()

    # Parse date if present
    date_str = headers.get('date', '')
    parsed_date = parse_date(date_str) if date_str else None

    return {
        'path': path,
        'subject': headers.get('subject', ''),
        'from_addr': headers.get('from', ''),
        'to_addr': headers.get('to', ''),
        'date': parsed_date,
        'body_text': body_text,
        'sha256': sha256,
        'metadata_dict': {
            'cc': headers.get('cc', ''),
            'bcc': headers.get('bcc', ''),
            'message_id': headers.get('message-id', ''),
            'reply_to': headers.get('reply-to', ''),
            'raw_headers': headers
        }
    }


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse various date formats commonly found in emails.

    Args:
        date_str: Date string to parse

    Returns:
        Parsed datetime or None if parsing fails
    """
    # Common email date formats
    date_formats = [
        '%a, %d %b %Y %H:%M:%S %z',  # RFC 2822: Mon, 23 Jun 2024 14:30:00 +0000
        '%a, %d %b %Y %H:%M:%S',      # Without timezone
        '%d %b %Y %H:%M:%S %z',        # Without day name
        '%d %b %Y %H:%M:%S',           # Without day name and timezone
        '%Y-%m-%d %H:%M:%S',           # ISO-like format
        '%Y/%m/%d %H:%M:%S',           # Alternative format
        '%m/%d/%Y %H:%M:%S',           # US format
        '%d/%m/%Y %H:%M:%S',           # European format
        '%b %d, %Y %H:%M:%S',          # Jan 15, 2024 14:30:00
        '%B %d, %Y %H:%M:%S',          # January 15, 2024 14:30:00
        '%Y-%m-%d',                    # Date only
        '%m/%d/%Y',                    # US date only
        '%d/%m/%Y',                    # European date only
    ]

    # Clean the date string
    date_str = date_str.strip()

    # Remove day name parentheses if present (e.g., "(Mon)")
    date_str = re.sub(r'\([^)]+\)', '', date_str).strip()

    # Try parsing with each format
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    # Try parsing with timezone abbreviations (EST, PST, etc.)
    # Convert common timezone abbreviations to offsets
    tz_replacements = {
        'PST': '-0800', 'PDT': '-0700',
        'EST': '-0500', 'EDT': '-0400',
        'CST': '-0600', 'CDT': '-0500',
        'MST': '-0700', 'MDT': '-0600',
        'UTC': '+0000', 'GMT': '+0000',
    }

    for tz_abbr, tz_offset in tz_replacements.items():
        if tz_abbr in date_str:
            modified_date = date_str.replace(tz_abbr, tz_offset)
            for fmt in date_formats[:4]:  # Try with timezone-aware formats
                try:
                    return datetime.strptime(modified_date, fmt)
                except ValueError:
                    continue

    # If all parsing attempts fail, return None
    return None


def validate_email_file(filepath: Path) -> tuple[bool, str]:
    """
    Validate that a file is a valid email file.

    Args:
        filepath: Path to the file to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file exists
    if not filepath.exists():
        return False, f"File not found: {filepath}"

    # Check file extension
    if filepath.suffix.lower() != '.txt':
        return False, f"Invalid file type: {filepath.suffix}. Only .txt files are supported"

    # Check file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    if filepath.stat().st_size > max_size:
        return False, f"File too large: {filepath.stat().st_size / 1024 / 1024:.1f}MB. Max size is 10MB"

    # Check if file is readable
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            f.read(1)
        return True, ""
    except Exception as e:
        return False, f"Cannot read file: {e}"