"""Voluptuous config schema and parser for room_control."""
from __future__ import annotations

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from .models import (
    LightConfig,
    PairConfig,
    RoomProfile,
    SceneConfig,
    SwitchConfig,
)

LIGHT_CONFIG_SCHEMA = vol.Schema({
    vol.Required("entity"): cv.entity_id,
    vol.Optional("brightness"): vol.All(int, vol.Range(0, 255)),
    vol.Optional("color_temp"): vol.All(int, vol.Range(1000, 10000)),
})

SCENE_SCHEMA = vol.Schema({
    vol.Required("name"): str,
    vol.Required("button"): vol.All(int, vol.Range(1, 4)),
    vol.Required("clicks"): vol.All(int, vol.Range(1, 6)),
    vol.Optional("lights", default=[]): [LIGHT_CONFIG_SCHEMA],
    vol.Optional("media_players", default=[]): [cv.entity_id],
    vol.Optional("covers", default=[]): [cv.entity_id],
    vol.Optional("script_sequence"): list,
})

PAIR_SCHEMA = vol.Schema({
    vol.Required("type"): vol.In(["light", "media_player"]),
    vol.Optional("entity_id"): cv.entity_id,
    vol.Optional("media_player_entity"): cv.entity_id,
    vol.Optional("target_z2m_name"): str,   # power-user YAML override only
})

SWITCH_SCHEMA = vol.Schema({
    vol.Required("type"): vol.In(["ptm215z", "z2m_multiclick", "zha"]),
    vol.Optional("controller_name"): str,
    vol.Optional("controller_event"): cv.entity_id,
    vol.Optional("mqtt_topic"): str,
    vol.Optional("click_action_payload", default="single"): str,
    vol.Optional("ieee"): str,
})

ROOM_SCHEMA = vol.Schema({
    vol.Required("area_id"): str,
    vol.Optional("left"): PAIR_SCHEMA,
    vol.Optional("right"): PAIR_SCHEMA,
    vol.Optional("scenes", default=[]): [SCENE_SCHEMA],
    vol.Optional("switches", default=[]): [SWITCH_SCHEMA],
    vol.Optional("z2m_base_topic", default="zigbee2mqtt"): str,
    vol.Optional("default_single_click", default=True): bool,
    vol.Optional("hold_delay", default=500): vol.All(int, vol.Range(100, 2000)),
    vol.Optional("dim_speed", default=50): vol.All(int, vol.Range(1, 500)),
    vol.Optional("volume_speed", default=0.05): vol.All(float, vol.Range(0.01, 0.1)),
})

CONFIG_SCHEMA = vol.Schema({
    vol.Required("rooms"): {str: ROOM_SCHEMA},
})


def _parse_pair(data: dict | None) -> PairConfig | None:
    if data is None:
        return None
    return PairConfig(
        type=data["type"],
        entity_id=data.get("entity_id"),
        target_z2m_name=data.get("target_z2m_name"),
        media_player_entity=data.get("media_player_entity"),
    )


def _parse_scene(data: dict) -> SceneConfig:
    return SceneConfig(
        name=data["name"],
        button=data["button"],
        clicks=data["clicks"],
        lights=[
            LightConfig(
                entity_id=light["entity"],
                brightness=light.get("brightness"),
                color_temp=light.get("color_temp"),
            )
            for light in data.get("lights", [])
        ],
        media_players=data.get("media_players", []),
        covers=data.get("covers", []),
        script_sequence=data.get("script_sequence"),
    )


def _parse_switch(data: dict) -> SwitchConfig:
    return SwitchConfig(
        type=data["type"],
        controller_name=data.get("controller_name"),
        controller_event=data.get("controller_event"),
        mqtt_topic=data.get("mqtt_topic"),
        click_action_payload=data.get("click_action_payload", "single"),
        ieee=data.get("ieee"),
    )


def parse_config(config: dict) -> dict[str, RoomProfile]:
    """Validate and parse the room_control config block into RoomProfile objects."""
    validated = CONFIG_SCHEMA(config)
    profiles: dict[str, RoomProfile] = {}
    for _key, room_data in validated["rooms"].items():
        profile = RoomProfile(
            area_id=room_data["area_id"],
            left=_parse_pair(room_data.get("left")),
            right=_parse_pair(room_data.get("right")),
            scenes=[_parse_scene(s) for s in room_data.get("scenes", [])],
            switches=[_parse_switch(sw) for sw in room_data.get("switches", [])],
            z2m_base_topic=room_data.get("z2m_base_topic", "zigbee2mqtt"),
            default_single_click=room_data.get("default_single_click", True),
            hold_delay=room_data.get("hold_delay", 500),
            dim_speed=room_data.get("dim_speed", 50),
            volume_speed=room_data.get("volume_speed", 0.05),
        )
        profiles[profile.area_id] = profile
    return profiles
