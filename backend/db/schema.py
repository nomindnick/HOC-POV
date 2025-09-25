from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import json


class Project(SQLModel, table=True):
    __tablename__ = "project"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    config_json: str = Field(default="{}")  # JSON string for flexible config

    # Relationships
    emails: List["Email"] = Relationship(back_populates="project")
    samplings: List["Sampling"] = Relationship(back_populates="project")

    @property
    def config(self) -> dict:
        return json.loads(self.config_json)

    @config.setter
    def config(self, value: dict):
        self.config_json = json.dumps(value)


class Email(SQLModel, table=True):
    __tablename__ = "email"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    path: str
    sha256: str = Field(index=True)  # For duplicate detection
    subject: Optional[str] = None
    from_addr: Optional[str] = None
    to_addr: Optional[str] = None
    date: Optional[datetime] = None
    body_text: str
    meta_json: str = Field(default="{}")  # Additional metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="emails")
    classifications: List["Classification"] = Relationship(back_populates="email")
    reviews: List["Review"] = Relationship(back_populates="email")
    sampling_items: List["SamplingItem"] = Relationship(back_populates="email")

    def get_metadata(self) -> dict:
        return json.loads(self.meta_json)

    def set_metadata(self, value: dict):
        self.meta_json = json.dumps(value)


class Classification(SQLModel, table=True):
    __tablename__ = "classification"

    id: Optional[int] = Field(default=None, primary_key=True)
    email_id: int = Field(foreign_key="email.id", index=True)
    run_id: str = Field(index=True)  # Groups classifications in a run
    model: str
    prompt_version: str
    params_json: str = Field(default="{}")  # Model parameters
    responsive_pred: bool
    confidence: float = Field(ge=0.0, le=1.0)
    labels_json: str = Field(default="[]")  # List of labels as JSON
    reason: str = Field(max_length=200)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="pending")  # pending, completed, failed
    error_message: Optional[str] = None

    # Relationships
    email: Optional["Email"] = Relationship(back_populates="classifications")

    @property
    def params(self) -> dict:
        return json.loads(self.params_json)

    @params.setter
    def params(self, value: dict):
        self.params_json = json.dumps(value)

    @property
    def labels(self) -> List[str]:
        return json.loads(self.labels_json)

    @labels.setter
    def labels(self, value: List[str]):
        self.labels_json = json.dumps(value)


class Review(SQLModel, table=True):
    __tablename__ = "review"

    id: Optional[int] = Field(default=None, primary_key=True)
    email_id: int = Field(foreign_key="email.id", index=True)
    reviewer: str
    final_responsive: bool
    note: Optional[str] = None
    changed_from_pred: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    email: Optional["Email"] = Relationship(back_populates="reviews")


class Sampling(SQLModel, table=True):
    __tablename__ = "sampling"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    seed: int
    size: int
    method_json: str = Field(default="{}")  # Sampling method configuration
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed: bool = Field(default=False)

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="samplings")
    sampling_items: List["SamplingItem"] = Relationship(back_populates="sampling")

    @property
    def method(self) -> dict:
        return json.loads(self.method_json)

    @method.setter
    def method(self, value: dict):
        self.method_json = json.dumps(value)


class SamplingItem(SQLModel, table=True):
    __tablename__ = "sampling_item"

    id: Optional[int] = Field(default=None, primary_key=True)
    sampling_id: int = Field(foreign_key="sampling.id", index=True)
    email_id: int = Field(foreign_key="email.id", index=True)
    stratum: str  # Which stratification bin this item belongs to
    human_label: Optional[bool] = None
    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    # Relationships
    sampling: Optional["Sampling"] = Relationship(back_populates="sampling_items")
    email: Optional["Email"] = Relationship(back_populates="sampling_items")


class ClassificationRun(SQLModel, table=True):
    __tablename__ = "classification_run"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str = Field(unique=True, index=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    model: str
    prompt_version: str
    params_json: str = Field(default="{}")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    status: str = Field(default="pending")  # pending, running, completed, cancelled, failed

    @property
    def params(self) -> dict:
        return json.loads(self.params_json)

    @params.setter
    def params(self, value: dict):
        self.params_json = json.dumps(value)