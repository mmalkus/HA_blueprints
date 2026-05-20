"""Tests for naming convention functions."""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.room_control.const import (
    multiclick_automation_id,
    ptm215z_automation_id,
    scene_entity,
    scene_id,
    script_entity,
)
from custom_components.room_control.models import SwitchConfig


def test_scene_id():
    assert scene_id("living_room", 1, 2) == "living_room_1_2"
    assert scene_id("living_room", 3, 4) == "living_room_3_4"


def test_scene_entity():
    assert scene_entity("living_room", 1, 2) == "scene.living_room_1_2"
    assert scene_entity("living_room", 3, 4) == "scene.living_room_3_4"


def test_script_entity():
    assert script_entity("living_room", 1, 2) == "script.living_room_1_2"


def test_scene_and_script_share_key():
    assert scene_entity("lr", 2, 3).endswith("_2_3")
    assert script_entity("lr", 2, 3).endswith("_2_3")


def test_all_four_buttons_supported():
    for button in range(1, 5):
        assert scene_entity("kitchen", button, 2) == f"scene.kitchen_{button}_2"


def test_ptm215z_automation_id():
    sw = SwitchConfig(type="ptm215z", controller_name="Living Room Switch")
    result = ptm215z_automation_id("living_room", sw)
    assert result == "living_room_ptm215z_living_room_swit"


def test_ptm215z_automation_id_empty_name():
    sw = SwitchConfig(type="ptm215z", controller_name=None)
    result = ptm215z_automation_id("living_room", sw)
    assert result == "living_room_ptm215z_"


def test_multiclick_automation_id():
    sw = SwitchConfig(type="z2m_multiclick", mqtt_topic="zigbee2mqtt/kitchen_switch")
    result = multiclick_automation_id("kitchen", sw)
    assert result == "kitchen_multiclick_zigbee2mqtt_kitchen_switch"
