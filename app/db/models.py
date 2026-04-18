# app/db/models.py

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))

    external_case_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False, default="api")
    source_batch_id: Mapped[str | None] = mapped_column(String, nullable=True)

    case_type: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    site: Mapped[str | None] = mapped_column(String, nullable=True)
    responsible_entity: Mapped[str | None] = mapped_column(String, nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity: Mapped[str | None] = mapped_column(String, nullable=True)

    severity_level_source: Mapped[str | None] = mapped_column(String, nullable=True)
    recurrence_frequency_source: Mapped[str | None] = mapped_column(String, nullable=True)
    classification_source: Mapped[str | None] = mapped_column(String, nullable=True)
    cause_category_source: Mapped[str | None] = mapped_column(String, nullable=True)
    cause_source: Mapped[str | None] = mapped_column(String, nullable=True)

    immediate_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    processed_incident: Mapped["ProcessedIncident"] = relationship(
        back_populates="incident",
        uselist=False,
        cascade="all, delete-orphan",
    )

class ProcessedIncident(Base):
    __tablename__ = "processed_incidents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    incident_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("incidents.id"),
        nullable=False,
        unique=True,
    )

    processing_status: Mapped[str] = mapped_column(String, nullable=False)

    original_language: Mapped[str | None] = mapped_column(String, nullable=True)
    cleaned_text: Mapped[str] = mapped_column(Text, nullable=False)

    translated_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    translated_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    hazard_category: Mapped[str] = mapped_column(String, nullable=False)
    hazard_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    hazard_explanation: Mapped[str] = mapped_column(Text, nullable=False)

    cause_category: Mapped[str] = mapped_column(String, nullable=False)
    cause_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    cause_explanation: Mapped[str] = mapped_column(Text, nullable=False)

    severity_level: Mapped[str] = mapped_column(String, nullable=False)
    severity_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity_explanation: Mapped[str] = mapped_column(Text, nullable=False)

    recurrence_frequency: Mapped[str] = mapped_column(String, nullable=False)
    recurrence_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    recurrence_explanation: Mapped[str] = mapped_column(Text, nullable=False)

    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level_label: Mapped[str] = mapped_column(String, nullable=False)

    recommendation_summary: Mapped[str] = mapped_column(Text, nullable=False)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    incident: Mapped["Incident"] = relationship(back_populates="processed_incident")

class UploadBatch(Base):
    __tablename__ = "upload_batches"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))

    file_name: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="excel")

    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
