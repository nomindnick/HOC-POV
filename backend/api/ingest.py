"""
API endpoints for email ingestion and file upload.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from sqlmodel import Session
from typing import List, Optional
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

from backend.db.base import db
from backend.db.crud import (
    create_project,
    get_project,
    get_project_by_name,
    bulk_create_emails
)
from backend.utils.email_parser import (
    parse_email_file,
    validate_email_file
)
from backend.config import settings

router = APIRouter(
    prefix="/api/ingest",
    tags=["ingest"],
    responses={404: {"description": "Not found"}},
)


@router.post("/")
async def ingest_emails(
    files: List[UploadFile] = File(...),
    project_id: Optional[int] = Form(None),
    project_name: Optional[str] = Form(None),
    session: Session = Depends(db.get_session)
):
    """
    Upload and ingest email files.

    Args:
        files: List of .txt files containing emails
        project_id: ID of existing project (optional)
        project_name: Name for new project (used if project_id not provided)

    Returns:
        JSON response with:
        - count: Number of emails successfully created
        - duplicates: Number of duplicate emails skipped
        - project_id: ID of the project
        - errors: List of any files that failed to process
    """
    # Validate project
    if project_id:
        project = get_project(session, project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")
    else:
        # Create or get project by name
        if not project_name:
            project_name = f"Import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        project = get_project_by_name(session, project_name)
        if not project:
            project = create_project(session, project_name, {
                "created_via": "api_ingest",
                "import_timestamp": datetime.utcnow().isoformat()
            })

    # Process files
    emails_data = []
    errors = []
    processed_files = []

    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for upload_file in files:
            # Validate file type
            if not upload_file.filename.endswith('.txt'):
                errors.append({
                    "filename": upload_file.filename,
                    "error": "Invalid file type. Only .txt files are supported"
                })
                continue

            # Save uploaded file temporarily
            temp_file = temp_path / upload_file.filename
            try:
                with temp_file.open("wb") as f:
                    content = await upload_file.read()
                    f.write(content)

                # Validate file
                is_valid, error_msg = validate_email_file(temp_file)
                if not is_valid:
                    errors.append({
                        "filename": upload_file.filename,
                        "error": error_msg
                    })
                    continue

                # Parse email
                parsed = parse_email_file(temp_file)
                parsed['path'] = upload_file.filename  # Use original filename as path
                emails_data.append(parsed)
                processed_files.append(upload_file.filename)

            except Exception as e:
                errors.append({
                    "filename": upload_file.filename,
                    "error": str(e)
                })

    # Bulk create emails in database
    created_count = 0
    duplicate_count = 0

    if emails_data:
        created_count, duplicate_count = bulk_create_emails(
            session,
            project.id,
            emails_data
        )

    return JSONResponse(
        content={
            "project_id": project.id,
            "project_name": project.name,
            "count": created_count,
            "duplicates": duplicate_count,
            "processed_files": processed_files,
            "errors": errors,
            "summary": f"Successfully imported {created_count} emails, skipped {duplicate_count} duplicates"
        }
    )


@router.post("/text")
async def ingest_text_content(
    content: str = Form(...),
    filename: str = Form(...),
    project_id: Optional[int] = Form(None),
    project_name: Optional[str] = Form(None),
    session: Session = Depends(db.get_session)
):
    """
    Ingest email content directly as text (useful for testing).

    Args:
        content: Email content as plain text with RFC-822 headers
        filename: Filename to use for reference
        project_id: ID of existing project (optional)
        project_name: Name for new project (used if project_id not provided)

    Returns:
        JSON response with ingestion results
    """
    from backend.utils.email_parser import parse_email_content

    # Validate project
    if project_id:
        project = get_project(session, project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")
    else:
        # Create or get project by name
        if not project_name:
            project_name = f"Import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        project = get_project_by_name(session, project_name)
        if not project:
            project = create_project(session, project_name, {
                "created_via": "api_ingest_text",
                "import_timestamp": datetime.utcnow().isoformat()
            })

    # Parse email content
    parsed = parse_email_content(content, filename)

    # Create emails in database
    created_count, duplicate_count = bulk_create_emails(
        session,
        project.id,
        [parsed]
    )

    return JSONResponse(
        content={
            "project_id": project.id,
            "project_name": project.name,
            "count": created_count,
            "duplicates": duplicate_count,
            "filename": filename,
            "summary": f"Successfully imported {created_count} emails, skipped {duplicate_count} duplicates"
        }
    )


@router.get("/validate")
async def validate_files(
    filenames: List[str],
):
    """
    Validate a list of filenames before upload.

    Args:
        filenames: List of filenames to validate

    Returns:
        Validation results for each file
    """
    results = []
    for filename in filenames:
        is_valid = filename.lower().endswith('.txt')
        results.append({
            "filename": filename,
            "valid": is_valid,
            "message": "Valid" if is_valid else "Invalid file type. Only .txt files are supported"
        })

    return JSONResponse(content={"results": results})