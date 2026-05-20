"""Room Control integration."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

DOMAIN = "room_control"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up room_control from configuration.yaml."""
    hass.data.setdefault(DOMAIN, {})
    return True
