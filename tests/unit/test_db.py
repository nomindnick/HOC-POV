import pytest
from sqlmodel import Session, create_engine, SQLModel
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tempfile

from backend.db.schema import (
    Project, Email, Classification, Review,
    Sampling, SamplingItem, ClassificationRun
)
from backend.db import crud


@pytest.fixture
def session():
    """Create a test database session"""
    # Use in-memory SQLite for tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


# ============= Project Tests =============
def test_create_project(session):
    """Test creating a project"""
    project = crud.create_project(
        session,
        name="Test Project",
        config={"low_confidence": 0.7}
    )

    assert project.id is not None
    assert project.name == "Test Project"
    assert project.config["low_confidence"] == 0.7
    assert isinstance(project.created_at, datetime)


def test_get_project(session):
    """Test retrieving a project"""
    project = crud.create_project(session, name="Test Project")
    retrieved = crud.get_project(session, project.id)

    assert retrieved is not None
    assert retrieved.id == project.id
    assert retrieved.name == "Test Project"


def test_get_project_by_name(session):
    """Test retrieving a project by name"""
    crud.create_project(session, name="Unique Project")
    retrieved = crud.get_project_by_name(session, "Unique Project")

    assert retrieved is not None
    assert retrieved.name == "Unique Project"


def test_list_projects(session):
    """Test listing all projects"""
    crud.create_project(session, name="Project 1")
    crud.create_project(session, name="Project 2")
    crud.create_project(session, name="Project 3")

    projects = crud.list_projects(session)

    assert len(projects) == 3
    assert all(p.name.startswith("Project") for p in projects)


def test_update_project(session):
    """Test updating a project"""
    project = crud.create_project(session, name="Original Name")
    updated = crud.update_project(
        session,
        project.id,
        name="Updated Name",
        config={"new_setting": True}
    )

    assert updated.name == "Updated Name"
    assert updated.config["new_setting"] is True


# ============= Email Tests =============
def test_create_email(session):
    """Test creating an email"""
    project = crud.create_project(session, name="Test Project")

    email = crud.create_email(
        session,
        project_id=project.id,
        path="/test.txt",
        sha256="abc123",
        body_text="test content",
        subject="Test Subject",
        from_addr="sender@test.com",
        to_addr="recipient@test.com"
    )

    assert email.id is not None
    assert email.sha256 == "abc123"
    assert email.subject == "Test Subject"
    assert email.body_text == "test content"


def test_create_email_auto_sha256(session):
    """Test creating an email with automatic SHA-256 generation"""
    project = crud.create_project(session, name="Test Project")

    body = "unique content for hashing"
    email = crud.create_email(
        session,
        project_id=project.id,
        path="/test.txt",
        body_text=body
    )

    expected_sha256 = hashlib.sha256(body.encode()).hexdigest()
    assert email.sha256 == expected_sha256


def test_duplicate_detection(session):
    """Test duplicate email detection via SHA-256"""
    project = crud.create_project(session, name="Test Project")

    # Create first email
    email1 = crud.create_email(
        session,
        project_id=project.id,
        path="/test1.txt",
        sha256="duplicate_hash",
        body_text="content"
    )

    # Try to create duplicate
    email2 = crud.create_email(
        session,
        project_id=project.id,
        path="/test2.txt",
        sha256="duplicate_hash",
        body_text="content"
    )

    # Should return the same email
    assert email2.id == email1.id
    assert email2.sha256 == email1.sha256


def test_get_email_by_sha256(session):
    """Test retrieving email by SHA-256"""
    project = crud.create_project(session, name="Test Project")
    crud.create_email(
        session,
        project_id=project.id,
        path="/test.txt",
        sha256="unique_hash",
        body_text="content"
    )

    retrieved = crud.get_email_by_sha256(session, project.id, "unique_hash")
    assert retrieved is not None
    assert retrieved.sha256 == "unique_hash"


def test_bulk_create_emails(session):
    """Test bulk email creation with duplicate detection"""
    project = crud.create_project(session, name="Test Project")

    emails_data = [
        {"path": f"/email{i}.txt", "body_text": f"content {i}", "subject": f"Subject {i}"}
        for i in range(5)
    ]

    # Add a duplicate
    emails_data.append({
        "path": "/duplicate.txt",
        "body_text": "content 2",  # Same as email2
        "subject": "Duplicate"
    })

    created, duplicates = crud.bulk_create_emails(
        session,
        project.id,
        emails_data
    )

    assert created == 5
    assert duplicates == 1


def test_list_emails(session):
    """Test listing emails with pagination"""
    project = crud.create_project(session, name="Test Project")

    # Create 10 emails
    for i in range(10):
        crud.create_email(
            session,
            project_id=project.id,
            path=f"/email{i}.txt",
            sha256=f"hash{i}",
            body_text=f"content {i}"
        )

    # Test pagination
    page1 = crud.list_emails(session, project.id, limit=5, offset=0)
    page2 = crud.list_emails(session, project.id, limit=5, offset=5)

    assert len(page1) == 5
    assert len(page2) == 5
    assert page1[0].id != page2[0].id


def test_count_emails(session):
    """Test counting emails in a project"""
    project = crud.create_project(session, name="Test Project")

    for i in range(7):
        crud.create_email(
            session,
            project_id=project.id,
            path=f"/email{i}.txt",
            sha256=f"hash{i}",
            body_text=f"content {i}"
        )

    count = crud.count_emails(session, project.id)
    assert count == 7


# ============= Classification Tests =============
def test_create_classification_run(session):
    """Test creating a classification run"""
    project = crud.create_project(session, name="Test Project")

    run = crud.create_classification_run(
        session,
        project_id=project.id,
        model="phi4:mini",
        prompt_version="1.0",
        params={"temperature": 0.7}
    )

    assert run.run_id is not None
    assert run.model == "phi4:mini"
    assert run.prompt_version == "1.0"
    assert run.params["temperature"] == 0.7


def test_create_classification(session):
    """Test creating a classification"""
    project = crud.create_project(session, name="Test Project")
    email = crud.create_email(
        session,
        project_id=project.id,
        path="/test.txt",
        body_text="content"
    )
    run = crud.create_classification_run(
        session,
        project_id=project.id,
        model="phi4:mini",
        prompt_version="1.0"
    )

    classification = crud.create_classification(
        session,
        email_id=email.id,
        run_id=run.run_id,
        model="phi4:mini",
        prompt_version="1.0",
        responsive_pred=True,
        confidence=0.92,
        labels=["lead", "water"],
        reason="Lead contamination in water"
    )

    assert classification.id is not None
    assert classification.responsive_pred is True
    assert classification.confidence == 0.92
    assert classification.labels == ["lead", "water"]
    assert "Lead contamination" in classification.reason


def test_get_latest_classification(session):
    """Test getting the latest classification for an email"""
    project = crud.create_project(session, name="Test Project")
    email = crud.create_email(
        session,
        project_id=project.id,
        path="/test.txt",
        body_text="content"
    )

    # Create multiple classifications
    for i in range(3):
        crud.create_classification(
            session,
            email_id=email.id,
            run_id=f"run_{i}",
            model="phi4:mini",
            prompt_version="1.0",
            responsive_pred=i % 2 == 0,
            confidence=0.5 + i * 0.1,
            labels=[],
            reason=f"Reason {i}"
        )

    latest = crud.get_latest_classification(session, email.id)
    assert latest.reason == "Reason 2"
    assert latest.confidence == 0.7


def test_count_classifications_by_status(session):
    """Test counting classifications by status"""
    project = crud.create_project(session, name="Test Project")
    run = crud.create_classification_run(
        session,
        project_id=project.id,
        model="phi4:mini",
        prompt_version="1.0"
    )

    # Create emails
    email_ids = []
    for i in range(5):
        email = crud.create_email(
            session,
            project_id=project.id,
            path=f"/email{i}.txt",
            body_text=f"content {i}"
        )
        email_ids.append(email.id)

    # Create classifications with different statuses
    statuses = ["completed", "completed", "completed", "failed", "pending"]
    for email_id, status in zip(email_ids, statuses):
        crud.create_classification(
            session,
            email_id=email_id,
            run_id=run.run_id,
            model="phi4:mini",
            prompt_version="1.0",
            responsive_pred=True,
            confidence=0.8,
            labels=[],
            reason="Test",
            status=status
        )

    counts = crud.count_classifications_by_status(session, run.run_id)
    assert counts["completed"] == 3
    assert counts["failed"] == 1
    assert counts["pending"] == 1


# ============= Review Tests =============
def test_create_review(session):
    """Test creating a review"""
    project = crud.create_project(session, name="Test Project")
    email = crud.create_email(
        session,
        project_id=project.id,
        path="/test.txt",
        body_text="content"
    )

    # Create initial classification
    crud.create_classification(
        session,
        email_id=email.id,
        run_id="run_1",
        model="phi4:mini",
        prompt_version="1.0",
        responsive_pred=False,
        confidence=0.8,
        labels=[],
        reason="Not responsive"
    )

    # Create review (override)
    review = crud.create_review(
        session,
        email_id=email.id,
        reviewer="attorney@firm.com",
        final_responsive=True,
        note="Actually contains environmental hazard info",
        changed_from_pred=True
    )

    assert review.id is not None
    assert review.final_responsive is True
    assert review.changed_from_pred is True
    assert "environmental hazard" in review.note


def test_get_latest_review(session):
    """Test getting the latest review for an email"""
    project = crud.create_project(session, name="Test Project")
    email = crud.create_email(
        session,
        project_id=project.id,
        path="/test.txt",
        body_text="content"
    )

    # Create multiple reviews
    for i in range(3):
        crud.create_review(
            session,
            email_id=email.id,
            reviewer=f"reviewer{i}@test.com",
            final_responsive=i % 2 == 0,
            note=f"Note {i}"
        )

    latest = crud.get_latest_review(session, email.id)
    assert latest.note == "Note 2"
    assert latest.reviewer == "reviewer2@test.com"


# ============= Sampling Tests =============
def test_create_sampling(session):
    """Test creating a sampling"""
    project = crud.create_project(session, name="Test Project")

    sampling = crud.create_sampling(
        session,
        project_id=project.id,
        size=100,
        seed=42,
        method={"stratified": True, "bins": 4}
    )

    assert sampling.id is not None
    assert sampling.size == 100
    assert sampling.seed == 42
    assert sampling.method["stratified"] is True


def test_create_sampling_items(session):
    """Test creating sampling items"""
    project = crud.create_project(session, name="Test Project")
    sampling = crud.create_sampling(session, project.id, size=10, seed=42)

    # Create emails
    email_ids = []
    for i in range(5):
        email = crud.create_email(
            session,
            project_id=project.id,
            path=f"/email{i}.txt",
            body_text=f"content {i}"
        )
        email_ids.append(email.id)

    # Create sampling items
    for email_id in email_ids:
        item = crud.create_sampling_item(
            session,
            sampling_id=sampling.id,
            email_id=email_id,
            stratum="responsive_high_conf"
        )
        assert item.id is not None


def test_bulk_create_sampling_items(session):
    """Test bulk creating sampling items"""
    project = crud.create_project(session, name="Test Project")
    sampling = crud.create_sampling(session, project.id, size=10, seed=42)

    # Create emails
    email_ids = []
    for i in range(5):
        email = crud.create_email(
            session,
            project_id=project.id,
            path=f"/email{i}.txt",
            body_text=f"content {i}"
        )
        email_ids.append(email.id)

    # Bulk create sampling items
    items_data = [
        {"email_id": eid, "stratum": f"stratum_{i}"}
        for i, eid in enumerate(email_ids)
    ]

    count = crud.bulk_create_sampling_items(session, sampling.id, items_data)
    assert count == 5


def test_update_sampling_item_label(session):
    """Test updating sampling item with human label"""
    project = crud.create_project(session, name="Test Project")
    sampling = crud.create_sampling(session, project.id, size=10, seed=42)
    email = crud.create_email(
        session,
        project_id=project.id,
        path="/test.txt",
        body_text="content"
    )

    item = crud.create_sampling_item(
        session,
        sampling_id=sampling.id,
        email_id=email.id,
        stratum="test_stratum"
    )

    # Update with human label
    updated = crud.update_sampling_item_label(
        session,
        item_id=item.id,
        human_label=True,
        reviewer="reviewer@test.com"
    )

    assert updated.human_label is True
    assert updated.reviewer == "reviewer@test.com"
    assert updated.reviewed_at is not None


def test_get_next_unlabeled_item(session):
    """Test getting next unlabeled item for blind review"""
    project = crud.create_project(session, name="Test Project")
    sampling = crud.create_sampling(session, project.id, size=10, seed=42)

    # Create emails and sampling items
    for i in range(3):
        email = crud.create_email(
            session,
            project_id=project.id,
            path=f"/email{i}.txt",
            body_text=f"content {i}"
        )
        crud.create_sampling_item(
            session,
            sampling_id=sampling.id,
            email_id=email.id,
            stratum="test"
        )

    # Get first unlabeled item
    item1 = crud.get_next_unlabeled_item(session, sampling.id)
    assert item1 is not None

    # Label it
    crud.update_sampling_item_label(
        session,
        item_id=item1.id,
        human_label=True,
        reviewer="reviewer@test.com"
    )

    # Get next unlabeled item (should be different)
    item2 = crud.get_next_unlabeled_item(session, sampling.id)
    assert item2 is not None
    assert item2.id != item1.id


# ============= Query Helper Tests =============
def test_get_emails_for_classification(session):
    """Test getting emails that need classification"""
    project = crud.create_project(session, name="Test Project")
    run = crud.create_classification_run(
        session,
        project_id=project.id,
        model="phi4:mini",
        prompt_version="1.0"
    )

    # Create 5 emails
    email_ids = []
    for i in range(5):
        email = crud.create_email(
            session,
            project_id=project.id,
            path=f"/email{i}.txt",
            body_text=f"content {i}"
        )
        email_ids.append(email.id)

    # Classify first 2 emails
    for i in range(2):
        crud.create_classification(
            session,
            email_id=email_ids[i],
            run_id=run.run_id,
            model="phi4:mini",
            prompt_version="1.0",
            responsive_pred=True,
            confidence=0.8,
            labels=[],
            reason="Test"
        )

    # Get unclassified emails
    unclassified = crud.get_emails_for_classification(
        session,
        project.id,
        run.run_id,
        limit=10
    )

    assert len(unclassified) == 3
    assert all(e.id not in email_ids[:2] for e in unclassified)


def test_get_email_with_classification_and_review(session):
    """Test getting email with all related data"""
    project = crud.create_project(session, name="Test Project")
    email = crud.create_email(
        session,
        project_id=project.id,
        path="/test.txt",
        body_text="content",
        subject="Test Subject"
    )

    # Add classification
    crud.create_classification(
        session,
        email_id=email.id,
        run_id="run_1",
        model="phi4:mini",
        prompt_version="1.0",
        responsive_pred=False,
        confidence=0.75,
        labels=["mold"],
        reason="Mentions mold"
    )

    # Add review
    crud.create_review(
        session,
        email_id=email.id,
        reviewer="attorney@test.com",
        final_responsive=True,
        note="Actually responsive",
        changed_from_pred=True
    )

    # Get complete data
    data = crud.get_email_with_classification_and_review(session, email.id)

    assert data is not None
    assert data["email"].subject == "Test Subject"
    assert data["classification"].confidence == 0.75
    assert data["review"].final_responsive is True


# ============= Edge Cases and Error Handling =============
def test_get_nonexistent_project(session):
    """Test retrieving a non-existent project"""
    project = crud.get_project(session, 99999)
    assert project is None


def test_update_nonexistent_project(session):
    """Test updating a non-existent project"""
    updated = crud.update_project(session, 99999, name="New Name")
    assert updated is None


def test_long_reason_truncation(session):
    """Test that long classification reasons are truncated"""
    project = crud.create_project(session, name="Test Project")
    email = crud.create_email(
        session,
        project_id=project.id,
        path="/test.txt",
        body_text="content"
    )

    # Create a very long reason
    long_reason = "x" * 500

    classification = crud.create_classification(
        session,
        email_id=email.id,
        run_id="run_1",
        model="phi4:mini",
        prompt_version="1.0",
        responsive_pred=True,
        confidence=0.8,
        labels=[],
        reason=long_reason
    )

    assert len(classification.reason) == 200  # Should be truncated


def test_email_metadata_json(session):
    """Test email metadata JSON field"""
    project = crud.create_project(session, name="Test Project")

    metadata = {"custom_field": "value", "tags": ["tag1", "tag2"]}
    email = crud.create_email(
        session,
        project_id=project.id,
        path="/test.txt",
        body_text="content",
        metadata_dict=metadata
    )

    retrieved = crud.get_email(session, email.id)
    metadata_retrieved = retrieved.get_metadata()
    assert metadata_retrieved["custom_field"] == "value"
    assert "tag1" in metadata_retrieved["tags"]


def test_classification_labels_json(session):
    """Test classification labels JSON field"""
    project = crud.create_project(session, name="Test Project")
    email = crud.create_email(
        session,
        project_id=project.id,
        path="/test.txt",
        body_text="content"
    )

    labels = ["lead", "water", "testing"]
    classification = crud.create_classification(
        session,
        email_id=email.id,
        run_id="run_1",
        model="phi4:mini",
        prompt_version="1.0",
        responsive_pred=True,
        confidence=0.9,
        labels=labels,
        reason="Multiple hazards"
    )

    retrieved = crud.get_classification(session, classification.id)
    assert retrieved.labels == labels
    assert len(retrieved.labels) == 3


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])