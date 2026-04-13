from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date
from typing import Optional, List, Any, Dict

# Site Schemas
class SiteBase(BaseModel):
    domain: str
    cms: Optional[str] = None
    region: Optional[str] = None
    notes: Optional[str] = None

class SiteCreate(SiteBase):
    pass

class SiteUpdate(BaseModel):
    domain: Optional[str] = None
    cms: Optional[str] = None
    region: Optional[str] = None
    notes: Optional[str] = None

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

class TaskUpdate(BaseModel):
    site_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[date] = None

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

# API request schemas (JSON-only)
class DensityRequest(BaseModel):
    text: str

class MetaRequest(BaseModel):
    content: str
    max_length: int = 160

class AuditRequest(BaseModel):
    url: str

class TitleRequest(BaseModel):
    title: str

class CSVImportResponse(BaseModel):
    imported_count: int

class DashboardResponse(BaseModel):
    sites_count: int
    tasks_todo: int
    tasks_in_progress: int
    content_idea: int
    last_positions: List[Dict[str, Any]]
