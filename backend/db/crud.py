from sqlmodel import Session, select
from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib
import json
import logging
from uuid import uuid4

from backend.db.schema import (
    Project, Email, Classification, Review,
    Sampling, SamplingItem, ClassificationRun
)

logger = logging.getLogger(__name__)


# ============= Project CRUD =============
def create_project(session: Session, name: str, config: dict = None) -> Project:
    """Create a new project"""
    project = Project(
        name=name,
        config_json=json.dumps(config or {})
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    logger.info(f"Created project: {project.name} (ID: {project.id})")
    return project


def get_project(session: Session, project_id: int) -> Optional[Project]:
    """Get project by ID"""
    return session.get(Project, project_id)


def get_project_by_name(session: Session, name: str) -> Optional[Project]:
    """Get project by name"""
    statement = select(Project).where(Project.name == name)
    return session.exec(statement).first()


def list_projects(session: Session) -> List[Project]:
    """List all projects"""
    statement = select(Project).order_by(Project.created_at.desc())
    return list(session.exec(statement).all())


def update_project(session: Session, project_id: int, **kwargs) -> Optional[Project]:
    """Update project"""
    project = get_project(session, project_id)
    if not project:
        return None

    for key, value in kwargs.items():
        if key == 'config':
            project.config = value
        else:
            setattr(project, key, value)

    session.add(project)
    session.commit()
    session.refresh(project)
    return project


# ============= Email CRUD =============
def create_email(
    session: Session,
    project_id: int,
    path: str,
    body_text: str,
    sha256: str = None,
    subject: str = None,
    from_addr: str = None,
    to_addr: str = None,
    date: datetime = None,
    metadata_dict: dict = None
) -> Email:
    """Create a new email"""
    # Generate SHA-256 if not provided
    if not sha256:
        sha256 = hashlib.sha256(body_text.encode()).hexdigest()

    # Check for duplicates
    existing = get_email_by_sha256(session, project_id, sha256)
    if existing:
        logger.warning(f"Duplicate email detected: {sha256}")
        return existing

    email = Email(
        project_id=project_id,
        path=path,
        sha256=sha256,
        subject=subject,
        from_addr=from_addr,
        to_addr=to_addr,
        date=date,
        body_text=body_text,
        meta_json=json.dumps(metadata_dict or {})
    )

    session.add(email)
    session.commit()
    session.refresh(email)
    logger.info(f"Created email: {email.id} (SHA: {email.sha256})")
    return email


def get_email(session: Session, email_id: int) -> Optional[Email]:
    """Get email by ID"""
    return session.get(Email, email_id)


def get_email_by_sha256(session: Session, project_id: int, sha256: str) -> Optional[Email]:
    """Get email by SHA-256 hash"""
    statement = select(Email).where(
        Email.project_id == project_id,
        Email.sha256 == sha256
    )
    return session.exec(statement).first()


def list_emails(
    session: Session,
    project_id: int,
    limit: int = 100,
    offset: int = 0
) -> List[Email]:
    """List emails for a project"""
    statement = (
        select(Email)
        .where(Email.project_id == project_id)
        .offset(offset)
        .limit(limit)
        .order_by(Email.created_at.desc())
    )
    return list(session.exec(statement).all())


def count_emails(session: Session, project_id: int) -> int:
    """Count emails in a project"""
    statement = select(Email).where(Email.project_id == project_id)
    return len(session.exec(statement).all())


def bulk_create_emails(
    session: Session,
    project_id: int,
    emails_data: List[Dict[str, Any]]
) -> tuple[int, int]:
    """Bulk create emails, returning (created_count, duplicate_count)"""
    created = 0
    duplicates = 0

    for data in emails_data:
        sha256 = data.get('sha256') or hashlib.sha256(
            data['body_text'].encode()
        ).hexdigest()

        existing = get_email_by_sha256(session, project_id, sha256)
        if existing:
            duplicates += 1
            continue

        email = Email(
            project_id=project_id,
            path=data['path'],
            sha256=sha256,
            subject=data.get('subject'),
            from_addr=data.get('from_addr'),
            to_addr=data.get('to_addr'),
            date=data.get('date'),
            body_text=data['body_text'],
            meta_json=json.dumps(data.get('metadata_dict', {}))
        )
        session.add(email)
        created += 1

    session.commit()
    logger.info(f"Bulk created {created} emails, {duplicates} duplicates")
    return created, duplicates


# ============= Classification CRUD =============
def create_classification_run(
    session: Session,
    project_id: int,
    model: str,
    prompt_version: str,
    params: dict = None
) -> ClassificationRun:
    """Create a new classification run"""
    run = ClassificationRun(
        run_id=str(uuid4()),
        project_id=project_id,
        model=model,
        prompt_version=prompt_version,
        params_json=json.dumps(params or {})
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    logger.info(f"Created classification run: {run.run_id}")
    return run


def get_classification_run(session: Session, run_id: str) -> Optional[ClassificationRun]:
    """Get classification run by ID"""
    statement = select(ClassificationRun).where(ClassificationRun.run_id == run_id)
    return session.exec(statement).first()


def update_classification_run(
    session: Session,
    run_id: str,
    **kwargs
) -> Optional[ClassificationRun]:
    """Update classification run"""
    run = get_classification_run(session, run_id)
    if not run:
        return None

    for key, value in kwargs.items():
        setattr(run, key, value)

    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def create_classification(
    session: Session,
    email_id: int,
    run_id: str,
    model: str,
    prompt_version: str,
    responsive_pred: bool,
    confidence: float,
    labels: List[str],
    reason: str,
    params: dict = None,
    status: str = "completed"
) -> Classification:
    """Create a classification result"""
    classification = Classification(
        email_id=email_id,
        run_id=run_id,
        model=model,
        prompt_version=prompt_version,
        responsive_pred=responsive_pred,
        confidence=confidence,
        labels_json=json.dumps(labels),
        reason=reason[:200],  # Truncate to max length
        params_json=json.dumps(params or {}),
        status=status
    )
    session.add(classification)
    session.commit()
    session.refresh(classification)
    return classification


def get_classification(session: Session, classification_id: int) -> Optional[Classification]:
    """Get classification by ID"""
    return session.get(Classification, classification_id)


def get_latest_classification(session: Session, email_id: int) -> Optional[Classification]:
    """Get the latest classification for an email"""
    statement = (
        select(Classification)
        .where(Classification.email_id == email_id)
        .order_by(Classification.created_at.desc())
    )
    return session.exec(statement).first()


def list_classifications_by_run(
    session: Session,
    run_id: str,
    status: str = None
) -> List[Classification]:
    """List classifications for a run"""
    statement = select(Classification).where(Classification.run_id == run_id)
    if status:
        statement = statement.where(Classification.status == status)
    return list(session.exec(statement).all())


def count_classifications_by_status(
    session: Session,
    run_id: str
) -> Dict[str, int]:
    """Count classifications by status for a run"""
    classifications = list_classifications_by_run(session, run_id)
    counts = {
        "pending": 0,
        "completed": 0,
        "failed": 0
    }
    for c in classifications:
        counts[c.status] = counts.get(c.status, 0) + 1
    return counts


# ============= Review CRUD =============
def create_review(
    session: Session,
    email_id: int,
    reviewer: str,
    final_responsive: bool,
    note: str = None,
    changed_from_pred: bool = False
) -> Review:
    """Create a review (human override)"""
    review = Review(
        email_id=email_id,
        reviewer=reviewer,
        final_responsive=final_responsive,
        note=note,
        changed_from_pred=changed_from_pred
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    logger.info(f"Created review for email {email_id} by {reviewer}")
    return review


def get_latest_review(session: Session, email_id: int) -> Optional[Review]:
    """Get the latest review for an email"""
    statement = (
        select(Review)
        .where(Review.email_id == email_id)
        .order_by(Review.created_at.desc())
    )
    return session.exec(statement).first()


def list_reviews(
    session: Session,
    email_ids: List[int] = None,
    reviewer: str = None
) -> List[Review]:
    """List reviews with optional filters"""
    statement = select(Review)
    if email_ids:
        statement = statement.where(Review.email_id.in_(email_ids))
    if reviewer:
        statement = statement.where(Review.reviewer == reviewer)
    return list(session.exec(statement).all())


# ============= Sampling CRUD =============
def create_sampling(
    session: Session,
    project_id: int,
    size: int,
    seed: int,
    method: dict = None
) -> Sampling:
    """Create a new sampling"""
    sampling = Sampling(
        project_id=project_id,
        size=size,
        seed=seed,
        method_json=json.dumps(method or {})
    )
    session.add(sampling)
    session.commit()
    session.refresh(sampling)
    logger.info(f"Created sampling {sampling.id} for project {project_id}")
    return sampling


def get_sampling(session: Session, sampling_id: int) -> Optional[Sampling]:
    """Get sampling by ID"""
    return session.get(Sampling, sampling_id)


def create_sampling_item(
    session: Session,
    sampling_id: int,
    email_id: int,
    stratum: str
) -> SamplingItem:
    """Create a sampling item"""
    item = SamplingItem(
        sampling_id=sampling_id,
        email_id=email_id,
        stratum=stratum
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def bulk_create_sampling_items(
    session: Session,
    sampling_id: int,
    items_data: List[Dict[str, Any]]
) -> int:
    """Bulk create sampling items"""
    count = 0
    for data in items_data:
        item = SamplingItem(
            sampling_id=sampling_id,
            email_id=data['email_id'],
            stratum=data['stratum']
        )
        session.add(item)
        count += 1

    session.commit()
    logger.info(f"Created {count} sampling items for sampling {sampling_id}")
    return count


def update_sampling_item_label(
    session: Session,
    item_id: int,
    human_label: bool,
    reviewer: str
) -> Optional[SamplingItem]:
    """Update sampling item with human label"""
    item = session.get(SamplingItem, item_id)
    if not item:
        return None

    item.human_label = human_label
    item.reviewer = reviewer
    item.reviewed_at = datetime.utcnow()

    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def get_next_unlabeled_item(
    session: Session,
    sampling_id: int
) -> Optional[SamplingItem]:
    """Get next unlabeled item for blind review"""
    statement = (
        select(SamplingItem)
        .where(
            SamplingItem.sampling_id == sampling_id,
            SamplingItem.human_label == None
        )
        .order_by(SamplingItem.id)
    )
    return session.exec(statement).first()


def list_sampling_items(
    session: Session,
    sampling_id: int,
    labeled_only: bool = False
) -> List[SamplingItem]:
    """List sampling items"""
    statement = select(SamplingItem).where(SamplingItem.sampling_id == sampling_id)
    if labeled_only:
        statement = statement.where(SamplingItem.human_label != None)
    return list(session.exec(statement).all())


# ============= Query Helpers =============
def get_emails_for_classification(
    session: Session,
    project_id: int,
    run_id: str,
    limit: int = 100
) -> List[Email]:
    """Get emails that haven't been classified in this run"""
    # Get all email IDs that have been classified in this run
    classified_statement = (
        select(Classification.email_id)
        .where(Classification.run_id == run_id)
    )
    classified_ids = [row for row in session.exec(classified_statement)]

    # Get emails not in classified list
    statement = (
        select(Email)
        .where(
            Email.project_id == project_id,
            ~Email.id.in_(classified_ids) if classified_ids else True
        )
        .limit(limit)
    )
    return list(session.exec(statement).all())


def get_email_with_classification_and_review(
    session: Session,
    email_id: int
) -> Dict[str, Any]:
    """Get email with its latest classification and review"""
    email = get_email(session, email_id)
    if not email:
        return None

    classification = get_latest_classification(session, email_id)
    review = get_latest_review(session, email_id)

    return {
        "email": email,
        "classification": classification,
        "review": review
    }