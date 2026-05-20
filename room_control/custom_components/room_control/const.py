"""Constants and naming convention functions for room_control."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import SwitchConfig

DOMAIN = "room_control"
MANAGED_TAG = "room_control_managed"


# ── Scenes & Scripts ───────────────────────────────────────────────────────────

def scene_id(area_id: str, button: int, clicks: int) -> str:
    """Return bare scene/script key, e.g. 'living_room_1_2'."""
    return f"{area_id}_{button}_{clicks}"


def scene_entity(area_id: str, button: int, clicks: int) -> str:
    """Return 'scene.living_room_1_2'."""
    return f"scene.{scene_id(area_id, button, clicks)}"


def script_entity(area_id: str, button: int, clicks: int) -> str:
    """Return 'script.living_room_1_2'."""
    return f"script.{scene_id(area_id, button, clicks)}"


# ── Automations ────────────────────────────────────────────────────────────────

def ptm215z_automation_id(area_id: str, switch: SwitchConfig) -> str:
    slug = (switch.controller_name or "").replace(" ", "_").lower()[:16]
    return f"{area_id}_ptm215z_{slug}"


def multiclick_automation_id(area_id: str, switch: SwitchConfig) -> str:
    slug = (switch.mqtt_topic or "").replace("/", "_").replace("-", "_")
    return f"{area_id}_multiclick_{slug}"
