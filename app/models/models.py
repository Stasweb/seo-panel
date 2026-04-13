from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import String, ForeignKey, DateTime, Date, Integer, Text, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class User(Base):
    """
    Simple User model for authentication.
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Site(Base):
    """
    Main model for managed websites.
    """
    __tablename__ = "sites"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    cms: Mapped[Optional[str]] = mapped_column(String(100))
    region: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    tasks: Mapped[List["Task"]] = relationship(back_populates="site", cascade="all, delete-orphan")
    content_plans: Mapped[List["ContentPlan"]] = relationship(back_populates="site", cascade="all, delete-orphan")
    seo_positions: Mapped[List["SEOPosition"]] = relationship(back_populates="site", cascade="all, delete-orphan")
    audits: Mapped[List["SEOAudit"]] = relationship(back_populates="site", cascade="all, delete-orphan")

class Task(Base):
    """
    Mini CRM Tasks.
    """
    __tablename__ = "tasks"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="todo") # todo, in_progress, done
    deadline: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    site: Mapped["Site"] = relationship(back_populates="tasks")

class ContentPlan(Base):
    """
    Content planning and tracking.
    """
    __tablename__ = "content_plans"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    title: Mapped[str] = mapped_column(String(255))
    url: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="idea") # idea, writing, published
    publish_date: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    site: Mapped["Site"] = relationship(back_populates="content_plans")

class SEOPosition(Base):
    """
    Keyword position history.
    """
    __tablename__ = "seo_positions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    keyword: Mapped[str] = mapped_column(String(255), index=True)
    position: Mapped[int] = mapped_column(Integer)
    check_date: Mapped[date] = mapped_column(Date, default=date.today)
    source: Mapped[str] = mapped_column(String(50), default="manual") # manual, gsc, yandex
    
    site: Mapped["Site"] = relationship(back_populates="seo_positions")

class SEOAudit(Base):
    """
    Basic SEO audit results.
    """
    __tablename__ = "seo_audits"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    url: Mapped[str] = mapped_column(String(500))
    status_code: Mapped[Optional[int]] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String(500))
    title_length: Mapped[Optional[int]] = mapped_column(Integer)
    h1: Mapped[Optional[str]] = mapped_column(String(500))
    is_indexed: Mapped[Optional[bool]] = mapped_column(Boolean)
    last_check: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    site: Mapped["Site"] = relationship(back_populates="audits")
