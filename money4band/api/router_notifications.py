"""Notifications API - status and test."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from money4band.api._deps import ConfigPaths, get_paths, load_user_config
from money4band.api.schemas import NotificationStatus, NotificationTest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/status", response_model=NotificationStatus)
async def notification_status(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return current notification configuration and enabled events."""
    from money4band.notifier import ALL_EVENTS, is_enabled, is_event_enabled

    usr = load_user_config()
    notif = usr.get("notifications", {})
    return {
        "enabled": is_enabled(usr),
        "url_set": bool(notif.get("url")),
        "events": {evt: is_event_enabled(usr, evt) for evt in ALL_EVENTS},
    }


@router.post("/test", response_model=NotificationTest)
async def send_test_notification(
    paths: ConfigPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Send a test notification via the configured service."""
    from money4band.notifier import send_test

    usr = load_user_config()
    success = send_test(usr)
    return {"status": "ok" if success else "failed", "sent": success}
