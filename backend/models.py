import os
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DSN = os.environ.get("DATABASE_URL", "postgresql://app:app@localhost:54401/tunnelconv")
engine = create_engine(DSN, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class ConvergenceLog(Base):
    __tablename__ = "convergence_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chainage: Mapped[str] = mapped_column(String, nullable=False)
    delta_mm: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    verdict: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ComparisonReport(Base):
    """邻断面对照报送：一次选定两个桩号与时段，记录最近办结值之差与口径。"""

    __tablename__ = "comparison_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chainage_a: Mapped[str] = mapped_column(String, nullable=False)
    chainage_b: Mapped[str] = mapped_column(String, nullable=False)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value_a: Mapped[float] = mapped_column(Float, nullable=False)
    value_b: Mapped[float] = mapped_column(Float, nullable=False)
    diff_mm: Mapped[float] = mapped_column(Float, nullable=False)
    caliber: Mapped[str] = mapped_column(String, nullable=False)
    submitted_by: Mapped[str] = mapped_column(String, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def row_dict(row: ConvergenceLog) -> dict:
    return {
        "id": row.id,
        "chainage": row.chainage,
        "delta_mm": row.delta_mm,
        "status": row.status,
        "verdict": row.verdict,
        "reason": row.reason,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "processed_at": row.processed_at.isoformat() if row.processed_at else None,
    }


def report_dict(row: ComparisonReport) -> dict:
    return {
        "id": row.id,
        "chainage_a": row.chainage_a,
        "chainage_b": row.chainage_b,
        "start_at": row.start_at.isoformat() if row.start_at else None,
        "cutoff_at": row.cutoff_at.isoformat() if row.cutoff_at else None,
        "value_a": row.value_a,
        "value_b": row.value_b,
        "diff_mm": row.diff_mm,
        "caliber": row.caliber,
        "submitted_by": row.submitted_by,
        "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
    }
