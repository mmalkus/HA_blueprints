"""Tests for script generator."""
from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

from custom_components.room_control.generators.scripts import (
    build_script_entries,
    sync_scripts,
)
from custom_components.room_control.const import MANAGED_TAG
from custom_components.room_control.models import LightConfig, RoomProfile, SceneConfig


def _room_with_scripts() -> RoomProfile:
    return RoomProfile(
        area_id="living_room",
        scenes=[
            SceneConfig(
                name="Movie",
                button=1,
                clicks=3,
                lights=[LightConfig(entity_id="light.floor", brightness=20)],
                script_sequence=[{"action": "cover.close_cover",
                                   "target": {"entity_id": "cover.blinds"}}],
            ),
            SceneConfig(
                name="Evening",
                button=1,
                clicks=2,
                lights=[LightConfig(entity_id="light.ceil", brightness=80)],
                script_sequence=None,  # no script
            ),
        ],
    )


def test_build_script_entries_only_includes_scenes_with_sequences():
    room = _room_with_scripts()
    entries = build_script_entries(room)
    assert len(entries) == 1
    assert entries[0]["id"] == "living_room_1_3"
    assert entries[0]["alias"] == "living_room — Movie"
    assert entries[0]["description"] == MANAGED_TAG
    assert entries[0]["sequence"][0]["action"] == "cover.close_cover"


def test_build_script_entries_empty_when_no_sequences():
    room = RoomProfile(
        area_id="kitchen",
        scenes=[SceneConfig(name="Bright", button=1, clicks=2)],
    )
    assert build_script_entries(room) == []


async def test_sync_scripts_writes_and_reloads():
    with tempfile.TemporaryDirectory() as tmpdir:
        scripts_path = os.path.join(tmpdir, "scripts.yaml")

        hass = MagicMock()
        hass.config.path = lambda f: os.path.join(tmpdir, f)
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()

        await sync_scripts(hass, _room_with_scripts())

        assert os.path.exists(scripts_path)
        hass.services.async_call.assert_called_once_with("script", "reload")


async def test_sync_scripts_skips_when_no_sequences():
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    room = RoomProfile(area_id="kitchen",
                       scenes=[SceneConfig(name="Bright", button=1, clicks=2)])
    await sync_scripts(hass, room)

    hass.services.async_call.assert_not_called()


async def test_sync_scripts_replaces_existing_managed_entry():
    with tempfile.TemporaryDirectory() as tmpdir:
        scripts_path = os.path.join(tmpdir, "scripts.yaml")

        # Pre-populate with an existing entry for the same ID
        from ruamel.yaml import YAML
        yaml = YAML()
        with open(scripts_path, "w") as fh:
            yaml.dump([{
                "id": "living_room_1_3",
                "alias": "old alias",
                "description": MANAGED_TAG,
                "sequence": [],
            }], fh)

        hass = MagicMock()
        hass.config.path = lambda f: os.path.join(tmpdir, f)
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()

        await sync_scripts(hass, _room_with_scripts())

        with open(scripts_path, encoding="utf-8") as fh:
            data = yaml.load(fh)

        matching = [s for s in data if s["id"] == "living_room_1_3"]
        assert len(matching) == 1
        assert matching[0]["alias"] == "living_room — Movie"
