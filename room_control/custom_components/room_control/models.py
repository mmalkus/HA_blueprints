"""Data models for room_control."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class LightConfig:
    entity_id: str
    brightness: Optional[int] = None    # 0–255
    color_temp: Optional[int] = None    # Kelvin; converted to mireds for scene.create


@dataclass
class SceneConfig:
    name: str
    button: int                         # 1–4
    clicks: int                         # ≥1 (≥2 if default_single_click=True)
    lights: list[LightConfig] = field(default_factory=list)
    media_players: list[str] = field(default_factory=list)
    covers: list[str] = field(default_factory=list)
    script_sequence: Optional[list] = None


@dataclass
class PairConfig:
    type: Literal["light", "media_player"]
    entity_id: Optional[str] = None             # HA entity_id for light
    target_z2m_name: Optional[str] = None       # resolved from entity_id; never set by user via UI
    media_player_entity: Optional[str] = None   # HA entity_id for media_player


@dataclass
class SwitchConfig:
    type: str                                   # "ptm215z", "z2m_multiclick", "zha"
    controller_name: Optional[str] = None       # z2m friendly name (ptm215z)
    controller_event: Optional[str] = None      # event entity_id (ptm215z, optional)
    mqtt_topic: Optional[str] = None            # z2m_multiclick
    click_action_payload: str = "single"        # z2m_multiclick
    ieee: Optional[str] = None                  # zha


@dataclass
class RoomProfile:
    area_id: str
    left: Optional[PairConfig] = None
    right: Optional[PairConfig] = None
    scenes: list[SceneConfig] = field(default_factory=list)
    switches: list[SwitchConfig] = field(default_factory=list)
    z2m_base_topic: str = "zigbee2mqtt"
    default_single_click: bool = True
    hold_delay: int = 500
    dim_speed: int = 50
    volume_speed: float = 0.05
