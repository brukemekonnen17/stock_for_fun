from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, JSON, Index
from datetime import datetime

class Base(DeclarativeBase):
    pass

# Optional tables you may extend later
class Event(Base):
    __tablename__ = "events"
    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    source: Mapped[str] = mapped_column(String(32))
    event_type: Mapped[str] = mapped_column(String(32))
    event_time: Mapped[datetime]
    headline: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(String(512))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

Index("ix_events_time", Event.event_time)

class Signal(Base):
    __tablename__ = "signals"
    signal_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    asof_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    horizon_days: Mapped[int] = mapped_column(Integer, default=5)
    signal_name: Mapped[str] = mapped_column(String(64))
    score: Mapped[float] = mapped_column(Float)
    meta_json: Mapped[dict] = mapped_column(JSON)

class Trade(Base):
    __tablename__ = "trades"
    trade_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    entry_time: Mapped[datetime]
    entry_px: Mapped[float]
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    exit_px: Mapped[float | None] = mapped_column(Float, nullable=True)
    shares: Mapped[int]
    reason_in: Mapped[str] = mapped_column(String(64))
    reason_out: Mapped[str] = mapped_column(String(64), default="")
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)
    max_dd_pct: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(String(512), default="")

class BanditLog(Base):
    __tablename__ = "bandit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    arm_name: Mapped[str] = mapped_column(String(32), index=True)
    x_json: Mapped[list] = mapped_column(JSON)
    reward: Mapped[float] = mapped_column(Float)

class RewardLog(Base):
    """Idempotent reward logging - prevents duplicate rewards for same decision_id"""
    __tablename__ = "reward_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    arm_name: Mapped[str] = mapped_column(String(32))
    reward: Mapped[float] = mapped_column(Float)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

