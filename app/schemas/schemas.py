from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date
from typing import Optional, List, Any, Dict
from app.utils.time import utcnow

# Site Schemas
class SiteBase(BaseModel):
    domain: str
    cms: Optional[str] = None
    region: Optional[str] = None
    notes: Optional[str] = None
    email_alerts_enabled: Optional[bool] = False
    alert_email: Optional[str] = None
    user_agent_choice: Optional[str] = None
    custom_user_agent: Optional[str] = None
    scan_priority: Optional[str] = "normal"
    respect_robots_txt: Optional[bool] = True
    use_sitemap: Optional[bool] = True
    scan_pause_ms: Optional[int] = 300

class SiteCreate(SiteBase):
    pass

class SiteUpdate(BaseModel):
    domain: Optional[str] = None
    cms: Optional[str] = None
    region: Optional[str] = None
    notes: Optional[str] = None
    email_alerts_enabled: Optional[bool] = None
    alert_email: Optional[str] = None
    user_agent_choice: Optional[str] = None
    custom_user_agent: Optional[str] = None
    scan_priority: Optional[str] = None
    respect_robots_txt: Optional[bool] = None
    use_sitemap: Optional[bool] = None
    scan_pause_ms: Optional[int] = None

class Site(SiteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    organization_id: Optional[int] = None

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
    last_check: datetime = Field(default_factory=utcnow)
    ai_used: Optional[bool] = None
    ai_model: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_actions: Optional[List[str]] = None

# API request schemas (JSON-only)
class DensityRequest(BaseModel):
    text: str

class MetaRequest(BaseModel):
    content: str
    max_length: int = 160

class AuditRequest(BaseModel):
    url: str
    ua: Optional[str] = None
    custom_ua: Optional[str] = None


class DeepAuditRequest(BaseModel):
    url: str
    ua: Optional[str] = None
    custom_ua: Optional[str] = None
    suggest_mode: str = "expanded"
    suggest_variants: int = 15
    target_keyword: Optional[str] = None


class DeepAuditResult(BaseModel):
    url: str
    final_url: Optional[str] = None
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    title: Optional[str] = None
    title_length: Optional[int] = None
    meta_description: Optional[str] = None
    meta_description_length: Optional[int] = None
    canonical: Optional[str] = None
    robots_meta: Optional[str] = None
    x_robots_tag: Optional[str] = None
    h1: Optional[str] = None
    headings: Optional[Dict[str, int]] = None
    word_count: Optional[int] = None
    links_internal: Optional[int] = None
    links_external: Optional[int] = None
    images_total: Optional[int] = None
    images_missing_alt: Optional[int] = None
    og_tags: Optional[bool] = None
    viewport: Optional[bool] = None
    structured_data_count: Optional[int] = None
    hreflang_count: Optional[int] = None
    is_indexed: Optional[bool] = None
    indexable: Optional[bool] = None
    indexability_reasons: Optional[List[str]] = None
    keyword_suggestions: Optional[Dict[str, Any]] = None
    spam_score: Optional[int] = None
    spam_flags: Optional[List[str]] = None
    title_spam: Optional[bool] = None
    h1_spam: Optional[bool] = None
    keyword_stuffing: Optional[bool] = None
    target_keyword: Optional[str] = None
    target_keyword_stats: Optional[Dict[str, Any]] = None
    last_check: datetime = Field(default_factory=utcnow)
    ai_used: Optional[bool] = None
    ai_model: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_actions: Optional[List[str]] = None

class TitleRequest(BaseModel):
    title: str

class CSVImportResponse(BaseModel):
    imported_count: int

class DashboardResponse(BaseModel):
    sites_count: int
    tasks_todo: int
    tasks_in_progress: int
    content_idea: int
    positions_count: Optional[int] = None
    scans_24h: Optional[int] = None
    last_positions: List[Dict[str, Any]]
