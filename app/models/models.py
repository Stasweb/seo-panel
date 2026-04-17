from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import String, ForeignKey, DateTime, Date, Integer, Text, Boolean, Float, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.utils.time import utcnow

class User(Base):
    """
    Simple User model for authentication.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column("hashed_password", String(255))
    role: Mapped[str] = mapped_column(String(20), default="viewer")  # admin, manager, viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    oauth_provider: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    oauth_subject: Mapped[Optional[str]] = mapped_column(String(255), index=True)

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), index=True)
    email_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_email: Mapped[Optional[str]] = mapped_column(String(255))
    user_agent_choice: Mapped[Optional[str]] = mapped_column(String(20))
    custom_user_agent: Mapped[Optional[str]] = mapped_column(Text)
    scan_priority: Mapped[str] = mapped_column(String(20), default="normal")
    respect_robots_txt: Mapped[bool] = mapped_column(Boolean, default=True)
    use_sitemap: Mapped[bool] = mapped_column(Boolean, default=True)
    scan_pause_ms: Mapped[int] = mapped_column(Integer, default=300)

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
    priority: Mapped[str] = mapped_column(String(20), default="normal") # low, normal, high
    deadline: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), index=True)
    deep_audit_report_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

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
    last_check: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    site: Mapped["Site"] = relationship(back_populates="audits")


class DeepAuditReport(Base):
    __tablename__ = "deep_audit_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), index=True)
    site_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sites.id"), index=True)

    url: Mapped[str] = mapped_column(String(1000), index=True)
    final_url: Mapped[Optional[str]] = mapped_column(String(1000), index=True)

    status_code: Mapped[Optional[int]] = mapped_column(Integer)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String(500))
    meta_description: Mapped[Optional[str]] = mapped_column(String(1000))
    h1: Mapped[Optional[str]] = mapped_column(String(500))
    canonical: Mapped[Optional[str]] = mapped_column(String(1000))
    robots_meta: Mapped[Optional[str]] = mapped_column(String(500))
    x_robots_tag: Mapped[Optional[str]] = mapped_column(String(500))
    word_count: Mapped[Optional[int]] = mapped_column(Integer)
    links_internal: Mapped[Optional[int]] = mapped_column(Integer)
    links_external: Mapped[Optional[int]] = mapped_column(Integer)
    images_missing_alt: Mapped[Optional[int]] = mapped_column(Integer)
    spam_score: Mapped[Optional[int]] = mapped_column(Integer)
    indexable: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_indexed: Mapped[Optional[bool]] = mapped_column(Boolean)
    target_keyword: Mapped[Optional[str]] = mapped_column(String(255))

    result_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class SiteScanHistory(Base):
    """
    Stores full scan results for a site over time.
    Used for charts and health tracking.
    """
    __tablename__ = "site_scan_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)

    status_code: Mapped[Optional[int]] = mapped_column(Integer)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    title_length: Mapped[Optional[int]] = mapped_column(Integer)
    h1_present: Mapped[Optional[bool]] = mapped_column(Boolean)
    indexed: Mapped[Optional[bool]] = mapped_column(Boolean)

    health_score: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class SeoHealthScoreHistory(Base):
    """
    Tracks SEO health score over time (0..100).
    """
    __tablename__ = "seo_health_score_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class WebmasterData(Base):
    """
    Stores credentials and metadata for webmaster integrations (GSC/Yandex).
    Token-based by default; OAuth can be added later without schema changes.
    """
    __tablename__ = "webmaster_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), unique=True, index=True)

    gsc_site_url: Mapped[Optional[str]] = mapped_column(String(500))
    gsc_access_token: Mapped[Optional[str]] = mapped_column(String(2000))

    yandex_host_id: Mapped[Optional[str]] = mapped_column(String(200))
    yandex_oauth_token: Mapped[Optional[str]] = mapped_column(String(2000))

    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class KeywordMetrics(Base):
    """
    Stores keyword-level metrics imported from webmaster consoles.
    """
    __tablename__ = "keyword_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)

    keyword: Mapped[str] = mapped_column(String(255), index=True)
    clicks: Mapped[Optional[int]] = mapped_column(Integer)
    impressions: Mapped[Optional[int]] = mapped_column(Integer)
    ctr: Mapped[Optional[float]] = mapped_column(Float)
    position: Mapped[Optional[float]] = mapped_column(Float)
    landing_url: Mapped[Optional[str]] = mapped_column(String(1000))
    frequency: Mapped[Optional[int]] = mapped_column(Integer)

    source: Mapped[str] = mapped_column(String(20), default="gsc")
    date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AppLog(Base):
    __tablename__ = "app_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(20), default="INFO", index=True)
    category: Mapped[str] = mapped_column(String(50), default="http", index=True)
    method: Mapped[Optional[str]] = mapped_column(String(10))
    path: Mapped[Optional[str]] = mapped_column(String(500), index=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class IPAddressSnapshot(Base):
    __tablename__ = "ip_address_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    local_ip: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    external_ip: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    local_method: Mapped[Optional[str]] = mapped_column(String(50))
    external_method: Mapped[Optional[str]] = mapped_column(String(50))
    details_json: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class MetricHistory(Base):
    """
    Generic metric storage for audits (robots, sitemap, tech audit, status checks).
    Value is stored as JSON for flexibility.
    """
    __tablename__ = "metric_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    metric_type: Mapped[str] = mapped_column(String(50), index=True)
    value_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class GSCAccount(Base):
    __tablename__ = "gsc_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), unique=True, index=True)

    site_url: Mapped[Optional[str]] = mapped_column(String(500))
    access_token: Mapped[Optional[str]] = mapped_column(String(2000))
    refresh_token: Mapped[Optional[str]] = mapped_column(String(2000))
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    selected_account_email: Mapped[Optional[str]] = mapped_column(String(255))
    connected: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class YandexAccount(Base):
    __tablename__ = "yandex_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), unique=True, index=True)

    host_id: Mapped[Optional[str]] = mapped_column(String(200))
    oauth_token: Mapped[Optional[str]] = mapped_column(String(2000))
    selected_account_login: Mapped[Optional[str]] = mapped_column(String(255))
    connected: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AhrefsAccount(Base):
    __tablename__ = "ahrefs_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), unique=True, index=True)

    api_key: Mapped[Optional[str]] = mapped_column(String(2000))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Backlink(Base):
    __tablename__ = "backlinks"
    __table_args__ = (
        UniqueConstraint("site_id", "source_url", "target_url", "source", name="uq_backlink_site_src_tgt_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)

    source_url: Mapped[str] = mapped_column(String(1000), index=True)
    target_url: Mapped[str] = mapped_column(String(1000), index=True)
    anchor: Mapped[Optional[str]] = mapped_column(Text)

    link_type: Mapped[str] = mapped_column(String(20), default="dofollow")
    status: Mapped[str] = mapped_column(String(20), default="active")
    source: Mapped[str] = mapped_column(String(20), default="manual")

    first_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    lost_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)

    http_status: Mapped[Optional[int]] = mapped_column(Integer)
    redirect_hops: Mapped[Optional[int]] = mapped_column(Integer)
    outgoing_links: Mapped[Optional[int]] = mapped_column(Integer)
    content_length: Mapped[Optional[int]] = mapped_column(Integer)
    domain_score: Mapped[Optional[int]] = mapped_column(Integer)
    toxic_score: Mapped[Optional[int]] = mapped_column(Integer)
    toxic_flag: Mapped[Optional[str]] = mapped_column(String(20))  # safe, suspicious, toxic
    region: Mapped[Optional[str]] = mapped_column(String(20))


class BacklinkStatusHistory(Base):
    __tablename__ = "backlink_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    backlink_id: Mapped[int] = mapped_column(ForeignKey("backlinks.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class BacklinkCheckHistory(Base):
    __tablename__ = "backlink_check_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    backlink_id: Mapped[int] = mapped_column(ForeignKey("backlinks.id"), index=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    http_status: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[Optional[str]] = mapped_column(String(20))
    link_type: Mapped[Optional[str]] = mapped_column(String(20))
    outgoing_links: Mapped[Optional[int]] = mapped_column(Integer)
    content_length: Mapped[Optional[int]] = mapped_column(Integer)
    domain_score: Mapped[Optional[int]] = mapped_column(Integer)
    toxic_score: Mapped[Optional[int]] = mapped_column(Integer)
    toxic_flag: Mapped[Optional[str]] = mapped_column(String(20))


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(20), default="free")  # free, pro
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    site_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sites.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="todo")  # todo, in_progress, done
    color: Mapped[str] = mapped_column(String(20), default="gray")  # gray, yellow, green, red
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), index=True)
    site_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sites.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)

    event_type: Mapped[str] = mapped_column(String(50), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="info")  # info, warning, error
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    seen: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class CompetitorBacklink(Base):
    __tablename__ = "competitor_backlinks"
    __table_args__ = (
        UniqueConstraint("organization_id", "competitor_domain", "source_url", "target_url", name="uq_comp_bl_org_dom_src_tgt"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), index=True)
    competitor_domain: Mapped[str] = mapped_column(String(255), index=True)

    donor_domain: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    source_url: Mapped[str] = mapped_column(String(1000), index=True)
    target_url: Mapped[str] = mapped_column(String(1000), index=True)
    anchor: Mapped[Optional[str]] = mapped_column(Text)
    link_type: Mapped[str] = mapped_column(String(20), default="dofollow")

    domain_score: Mapped[Optional[int]] = mapped_column(Integer)
    toxic_score: Mapped[Optional[int]] = mapped_column(Integer)
    toxic_flag: Mapped[Optional[str]] = mapped_column(String(20))
    region: Mapped[Optional[str]] = mapped_column(String(20))
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Competitor(Base):
    __tablename__ = "competitors"
    __table_args__ = (UniqueConstraint("organization_id", "domain", name="uq_competitors_org_domain"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), index=True)
    site_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sites.id"), index=True)
    domain: Mapped[str] = mapped_column(String(255), index=True)
    label: Mapped[Optional[str]] = mapped_column(String(255))

    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    last_http_status: Mapped[Optional[int]] = mapped_column(Integer)
    last_title: Mapped[Optional[str]] = mapped_column(String(500))

    backlinks_total: Mapped[Optional[int]] = mapped_column(Integer)
    donors_total: Mapped[Optional[int]] = mapped_column(Integer)
    dofollow_pct: Mapped[Optional[float]] = mapped_column(Float)
    avg_dr: Mapped[Optional[int]] = mapped_column(Integer)
    gap_donors: Mapped[Optional[int]] = mapped_column(Integer)
    overlap_donors: Mapped[Optional[int]] = mapped_column(Integer)

    last_snapshot_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class CompetitorSnapshot(Base):
    __tablename__ = "competitor_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    http_status: Mapped[Optional[int]] = mapped_column(Integer)
    backlinks_total: Mapped[Optional[int]] = mapped_column(Integer)
    donors_total: Mapped[Optional[int]] = mapped_column(Integer)
    dofollow_pct: Mapped[Optional[float]] = mapped_column(Float)
    avg_dr: Mapped[Optional[int]] = mapped_column(Integer)
    gap_donors: Mapped[Optional[int]] = mapped_column(Integer)
    overlap_donors: Mapped[Optional[int]] = mapped_column(Integer)

    snapshot_json: Mapped[Optional[str]] = mapped_column(Text)
