from sqlalchemy import Column, Integer, DateTime, Text, Date, ForeignKey, UniqueConstraint, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import Optional
from datetime import datetime, date
import uuid


class Base(DeclarativeBase):
    pass


class PipelineRun(Base):
    """Pipeline run metadata table."""
    
    __tablename__ = "pipeline_runs"
    
    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    rows_in = Column(Integer, default=0)
    rows_loaded = Column(Integer, default=0)
    rows_rejected = Column(Integer, default=0)
    notes = Column(Text, nullable=True)


class Region(Base):
    """Region table for tracking geographic regions."""
    
    __tablename__ = "regions"
    
    region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    population: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


class HospitalCapacityDaily(Base):
    """Daily hospital capacity metrics by region."""
    
    __tablename__ = "hospital_capacity_daily"
    
    __table_args__ = (
        UniqueConstraint('date', 'region_id', name='uq_hospital_capacity_daily_date_region'),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions.region_id"),
        nullable=False
    )
    total_beds: Mapped[int] = mapped_column(Integer, nullable=False)
    occupied_beds: Mapped[int] = mapped_column(Integer, nullable=False)
    icu_beds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    icu_occupied: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.run_id"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


class MetricsDaily(Base):
    """Daily computed metrics by region."""
    
    __tablename__ = "metrics_daily"
    
    __table_args__ = (
        UniqueConstraint('date', 'region_id', name='uq_metrics_daily_date_region'),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions.region_id"),
        nullable=False
    )
    bed_occ_pct: Mapped[float] = mapped_column(Float, nullable=False)
    icu_occ_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    strain_index: Mapped[float] = mapped_column(Float, nullable=False)
    source_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.run_id"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

