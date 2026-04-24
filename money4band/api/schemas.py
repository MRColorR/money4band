"""Pydantic response models for the M4B REST API.

Every router should reference these models via ``response_model=…`` so
that FastAPI auto-generates accurate OpenAPI docs, validates outgoing
payloads, and produces typed JSON examples.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Generic status responses
# ---------------------------------------------------------------------------


class StatusOk(BaseModel):
    status: str = Field("ok", examples=["ok"])


class StatusMessage(StatusOk):
    message: str


class StatusPath(StatusOk):
    path: str


# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------


class ReferralOut(BaseModel):
    """A single referral/affiliate URL contributed by a catalog author."""

    url: str
    contributor: str = "MRColorR"
    added: str | None = None
    verified: bool = False
    verified_by: list[str] = Field(default_factory=list)


class AppSummary(BaseModel):
    name: str
    category: str
    active: bool
    image: str = ""
    resource_tier: str = ""
    earnings_range: str = ""
    compose_layer: str = ""
    status: str = ""
    dashboard_url: str = ""
    # Provenance fields
    source: str = Field(
        "builtin",
        description=(
            "Catalog source: 'builtin' (shipped), 'community' (apps.d overlay), "
            "'remote' (fetched community catalog), 'local' (user override)."
        ),
    )
    managed_by_m4b: bool = Field(
        True,
        description=(
            "True when M4B ships + maintains this entry (supported + builtin). "
            "False for newcomers, deprecated, or user-contributed overlays."
        ),
    )
    referrals: list[ReferralOut] = Field(
        default_factory=list,
        description="Full referral pool for this app (attributed + verifiable).",
    )
    picked_referral_url: str = Field(
        "",
        description=(
            "Referral URL currently selected for this user/device. "
            "Sticky via user-config settings.picked_referrals[app_name]."
        ),
    )


class CategorySummary(BaseModel):
    name: str
    active: bool
    app_count: int


class CategoryToggle(BaseModel):
    category: str
    active: bool


# ---------------------------------------------------------------------------
# Backups
# ---------------------------------------------------------------------------


class BackupEntry(BaseModel):
    path: str
    timestamp: datetime
    size: int = Field(0, description="File size in bytes")


class BackupCleanup(StatusOk):
    deleted_count: int


class BackupRestore(StatusOk):
    restored_from: str


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class ProfileDefinition(BaseModel):
    description: str = ""
    cpu_pct: float
    ram_pct: float


class LimitsResponse(BaseModel):
    active_profile: str
    available_profiles: dict[str, ProfileDefinition]
    resource_limits: dict[str, Any]


class LimitSet(StatusOk):
    profile: str


# ---------------------------------------------------------------------------
# Earnings
# ---------------------------------------------------------------------------


class EarningsApp(BaseModel):
    name: str
    model: str = ""
    range_low: float = 0.0
    range_high: float = 0.0
    min_payout: float | str = "unknown"


class EarningsResponse(BaseModel):
    ip_type: str
    apps: list[EarningsApp]
    total_min: float
    total_max: float


# ---------------------------------------------------------------------------
# IP scoring
# ---------------------------------------------------------------------------


class IpScoreEntry(BaseModel):
    model_config = {"extra": "allow"}

    status: str = ""
    query: str = ""
    country: str = ""
    city: str = ""
    isp: str = ""
    org: str = ""
    proxy: bool = False
    hosting: bool = False
    mobile: bool = False


# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------


class ContainerHealth(BaseModel):
    name: str
    running: bool
    health: str
    restart_count: int
    last_started: str
    last_error: str
    image: str


class RestartLoop(BaseModel):
    name: str
    restart_count: int
    last_error: str
    image: str


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


class NotificationStatus(BaseModel):
    enabled: bool
    url_set: bool
    events: dict[str, bool]


class NotificationTest(StatusOk):
    sent: bool


# ---------------------------------------------------------------------------
# Offers
# ---------------------------------------------------------------------------


class OfferEntry(BaseModel):
    model_config = {"extra": "allow"}

    name: str
    url: str = ""
    bonus: str = ""
    category: str = ""
    m4b_app: bool = False
    notes: str | None = None


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


class ProfileCreated(StatusOk):
    profile: str
    path: str


class ProfileSwitched(StatusOk):
    active_profile: str


class ProfileDeleted(StatusOk):
    deleted: str


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


class ApiKeyInfo(BaseModel):
    """Masked view of the dashboard API key."""

    key_preview: str = Field("", description="Last 8 characters of the key, masked")
    has_key: bool = Field(False, description="Whether an API key is configured")


class ApiKeyRegenerated(BaseModel):
    """Response after regenerating an API key."""

    key: str = Field("", description="The new API key (shown once)")


class StaleImage(BaseModel):
    model_config = {"extra": "allow"}

    app: str = ""
    image: str = ""
    last_update: str = ""
    days_old: int = 0


class ImageDigest(BaseModel):
    app: str = ""
    image: str = ""
    digest: str = ""


class ImageScanResult(BaseModel):
    image: str
    report: str | None = None


# ---------------------------------------------------------------------------
# Stack
# ---------------------------------------------------------------------------

# Stack endpoints use StatusMessage.

# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------


class SystemInfo(BaseModel):
    platform: str
    os_type: str
    architecture: str
    docker_arch: str
    total_ram_mb: int
    available_ram_mb: int
    cpu_cores: int | None
    device_name: str
    project_version: str
    enabled_apps: int


class DnsConfig(BaseModel):
    mode: str
    servers: list[str] = Field(default_factory=list)


class DnsSet(StatusOk):
    mode: str


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


class UpdateCheck(BaseModel):
    current_version: str
    latest_version: str | None
    update_available: bool


class UpdateApplied(StatusOk):
    updated_to: str
