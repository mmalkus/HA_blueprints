"""Shared pytest fixtures for room_control tests."""
from __future__ import annotations

import sys
import types

import pytest


def _make_ha_stubs() -> None:
    """Inject minimal homeassistant stubs so unit tests run without a full HA install."""
    if "homeassistant" in sys.modules:
        return

    # homeassistant
    ha = types.ModuleType("homeassistant")
    sys.modules["homeassistant"] = ha

    # homeassistant.core
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object  # type: ignore[attr-defined]
    sys.modules["homeassistant.core"] = core
    ha.core = core

    # homeassistant.helpers
    helpers = types.ModuleType("homeassistant.helpers")
    sys.modules["homeassistant.helpers"] = helpers
    ha.helpers = helpers

    # homeassistant.helpers.config_validation — cv.entity_id just validates a string
    cv = types.ModuleType("homeassistant.helpers.config_validation")
    cv.entity_id = str  # type: ignore[attr-defined]
    sys.modules["homeassistant.helpers.config_validation"] = cv
    helpers.config_validation = cv

    # homeassistant.helpers.entity_registry
    er = types.ModuleType("homeassistant.helpers.entity_registry")
    er.async_get = lambda hass: None  # type: ignore[attr-defined]
    sys.modules["homeassistant.helpers.entity_registry"] = er
    helpers.entity_registry = er

    # homeassistant.helpers.device_registry
    dr = types.ModuleType("homeassistant.helpers.device_registry")
    dr.async_get = lambda hass: None  # type: ignore[attr-defined]
    sys.modules["homeassistant.helpers.device_registry"] = dr
    helpers.device_registry = dr


_make_ha_stubs()
