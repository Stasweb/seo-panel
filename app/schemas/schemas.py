from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date
from typing import Optional, List

# Site Schemas
class SiteBase(BaseModel):
    domain: str
    cms: Optional[str] = None
    region: Optional[str] = None
    notes: Optional[str] = None

class SiteCreate(SiteBase):
    pass

class SiteUpdate(SiteBase):
    domain: Optional[str] = None

class Site(SiteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime

# Task Schemas
class TaskBase(BaseModel):
    site_id: int
    title: str
    description: Optional[str] = None
    status: str = "todo"
    deadline: Optional[date] = None

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime

# Content Plan Schemas
class ContentPlanBase(BaseModel):
    site_id: int
    title: str
    url: Optional[str] = None
    status: str = "idea"
    publish_date: Optional[date] = None

class ContentPlanCreate(ContentPlanBase):
    pass

class ContentPlan(ContentPlanBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime

# SEO Position Schemas
class SEOPositionBase(BaseModel):
    site_id: int
    keyword: str
    position: int
    check_date: date = Field(default_factory=date.today)
    source: str = "manual"

class SEOPositionCreate(SEOPositionBase):
    pass

class SEOPosition(SEOPositionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

# Auth Schemas
class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Audit Schemas
class AuditResult(BaseModel):
    url: str
    status_code: Optional[int] = None
    title: Optional[str] = None
    title_length: Optional[int] = None
    h1: Optional[str] = None
    is_indexed: Optional[bool] = None
    last_check: datetime = Field(default_factory=datetime.utcnow)
