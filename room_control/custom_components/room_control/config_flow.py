"""Config flow for room_control."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# ── Step schemas ───────────────────────────────────────────────────────────────

STEP_USER_SCHEMA = vol.Schema({
    vol.Required("area_id"): selector.TextSelector(),
    vol.Optional("z2m_base_topic", default="zigbee2mqtt"): selector.TextSelector(),
    vol.Optional("default_single_click", default=True): selector.BooleanSelector(),
    vol.Optional("hold_delay", default=500): selector.NumberSelector(
        selector.NumberSelectorConfig(min=100, max=2000, unit_of_measurement="ms", mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("dim_speed", default=50): selector.NumberSelector(
        selector.NumberSelectorConfig(min=1, max=500, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("volume_speed", default=0.05): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0.01, max=0.1, step=0.01, mode=selector.NumberSelectorMode.BOX)
    ),
})

STEP_PAIR_SCHEMA = vol.Schema({
    vol.Required("type", default="none"): selector.SelectSelector(
        selector.SelectSelectorConfig(options=["none", "light", "media_player"])
    ),
    vol.Optional("entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="light")
    ),
    vol.Optional("media_player_entity"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="media_player")
    ),
})

STEP_SCENE_SCHEMA = vol.Schema({
    vol.Required("name"): selector.TextSelector(),
    vol.Required("button", default=1): selector.NumberSelector(
        selector.NumberSelectorConfig(min=1, max=4, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required("clicks", default=2): selector.NumberSelector(
        selector.NumberSelectorConfig(min=1, max=6, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("light_entity"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="light")
    ),
    vol.Optional("brightness"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=255, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional("color_temp"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=1000, max=10000, unit_of_measurement="K", mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("add_another", default=True): selector.BooleanSelector(),
})

STEP_SWITCH_SCHEMA = vol.Schema({
    vol.Required("type"): selector.SelectSelector(
        selector.SelectSelectorConfig(options=["ptm215z", "z2m_multiclick", "zha"])
    ),
    vol.Optional("controller_name"): selector.TextSelector(),
    vol.Optional("controller_event"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="event")
    ),
    vol.Optional("mqtt_topic"): selector.TextSelector(),
    vol.Optional("click_action_payload", default="single"): selector.TextSelector(),
    vol.Optional("add_another", default=False): selector.BooleanSelector(),
})


# ── Config flow ────────────────────────────────────────────────────────────────

class RoomControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Multi-step config flow for a single room."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> RoomControlOptionsFlow:
        return RoomControlOptionsFlow(config_entry)

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._scenes: list[dict] = []
        self._switches: list[dict] = []
        self._z2m_warning: str | None = None

    async def async_step_user(self, user_input: dict | None = None):
        errors: dict = {}
        if user_input is not None:
            area_id = user_input["area_id"].strip().lower().replace(" ", "_")
            # Prevent duplicate entries for the same area
            await self.async_set_unique_id(area_id)
            self._abort_if_unique_id_configured()

            self._data.update(user_input)
            self._data["area_id"] = area_id
            return await self.async_step_left_pair()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_left_pair(self, user_input: dict | None = None):
        errors: dict = {}
        if user_input is not None:
            pair_type = user_input.get("type", "none")
            if pair_type != "none":
                left = {"type": pair_type}
                if pair_type == "light":
                    entity_id = user_input.get("entity_id")
                    if not entity_id:
                        errors["entity_id"] = "required_for_light"
                    else:
                        left["entity_id"] = entity_id
                        left["target_z2m_name"] = await self._resolve_z2m(entity_id)
                elif pair_type == "media_player":
                    mp = user_input.get("media_player_entity")
                    if not mp:
                        errors["media_player_entity"] = "required_for_media_player"
                    else:
                        left["media_player_entity"] = mp
                if not errors:
                    self._data["left"] = left
            if not errors:
                return await self.async_step_right_pair()

        description_placeholders = {}
        if self._z2m_warning:
            description_placeholders["z2m_warning"] = self._z2m_warning
            self._z2m_warning = None

        return self.async_show_form(
            step_id="left_pair",
            data_schema=STEP_PAIR_SCHEMA,
            errors=errors,
            description_placeholders=description_placeholders or None,
        )

    async def async_step_right_pair(self, user_input: dict | None = None):
        errors: dict = {}
        if user_input is not None:
            pair_type = user_input.get("type", "none")
            if pair_type != "none":
                right = {"type": pair_type}
                if pair_type == "light":
                    entity_id = user_input.get("entity_id")
                    if not entity_id:
                        errors["entity_id"] = "required_for_light"
                    else:
                        right["entity_id"] = entity_id
                        right["target_z2m_name"] = await self._resolve_z2m(entity_id)
                elif pair_type == "media_player":
                    mp = user_input.get("media_player_entity")
                    if not mp:
                        errors["media_player_entity"] = "required_for_media_player"
                    else:
                        right["media_player_entity"] = mp
                if not errors:
                    self._data["right"] = right
            if not errors:
                return await self.async_step_add_scene()

        description_placeholders = {}
        if self._z2m_warning:
            description_placeholders["z2m_warning"] = self._z2m_warning
            self._z2m_warning = None

        return self.async_show_form(
            step_id="right_pair",
            data_schema=STEP_PAIR_SCHEMA,
            errors=errors,
            description_placeholders=description_placeholders or None,
        )

    async def async_step_add_scene(self, user_input: dict | None = None):
        if user_input is not None:
            add_another = user_input.pop("add_another", False)
            scene: dict = {
                "name": user_input["name"],
                "button": int(user_input["button"]),
                "clicks": int(user_input["clicks"]),
                "lights": [],
            }
            if user_input.get("light_entity"):
                light: dict = {"entity": user_input["light_entity"]}
                if user_input.get("brightness") is not None:
                    light["brightness"] = int(user_input["brightness"])
                if user_input.get("color_temp") is not None:
                    light["color_temp"] = int(user_input["color_temp"])
                scene["lights"].append(light)
            self._scenes.append(scene)

            if add_another:
                return self.async_show_form(
                    step_id="add_scene",
                    data_schema=STEP_SCENE_SCHEMA,
                    description_placeholders={"count": str(len(self._scenes))},
                )
            return await self.async_step_add_switch()

        return self.async_show_form(
            step_id="add_scene",
            data_schema=STEP_SCENE_SCHEMA,
            description_placeholders={"count": "0"},
        )

    async def async_step_add_switch(self, user_input: dict | None = None):
        if user_input is not None:
            add_another = user_input.pop("add_another", False)
            switch: dict = {"type": user_input["type"]}
            if user_input.get("controller_name"):
                switch["controller_name"] = user_input["controller_name"]
            if user_input.get("controller_event"):
                switch["controller_event"] = user_input["controller_event"]
            if user_input.get("mqtt_topic"):
                switch["mqtt_topic"] = user_input["mqtt_topic"]
            if user_input.get("click_action_payload"):
                switch["click_action_payload"] = user_input["click_action_payload"]
            self._switches.append(switch)

            if add_another:
                return self.async_show_form(
                    step_id="add_switch",
                    data_schema=STEP_SWITCH_SCHEMA,
                    description_placeholders={"count": str(len(self._switches))},
                )
            return await self.async_step_confirm()

        return self.async_show_form(
            step_id="add_switch",
            data_schema=STEP_SWITCH_SCHEMA,
            description_placeholders={"count": "0"},
        )

    async def async_step_confirm(self, user_input: dict | None = None):
        if user_input is not None:
            entry_data = dict(self._data)
            entry_data["scenes"] = self._scenes
            entry_data["switches"] = self._switches
            return self.async_create_entry(
                title=self._data["area_id"],
                data=entry_data,
            )

        summary = (
            f"Area: {self._data['area_id']}\n"
            f"Scenes: {len(self._scenes)}\n"
            f"Switches: {len(self._switches)}"
        )
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"summary": summary},
        )

    async def _resolve_z2m(self, entity_id: str) -> str | None:
        """Resolve Z2M friendly name; sets warning if it fails."""
        from .resolvers import resolve_z2m_friendly_name
        name = await resolve_z2m_friendly_name(
            self.hass, entity_id, self._data.get("z2m_base_topic", "zigbee2mqtt")
        )
        if not name:
            self._z2m_warning = (
                f"Could not resolve Z2M name for {entity_id}. "
                "Is Zigbee2MQTT running? The automation will be skipped until "
                "target_z2m_name is set manually in YAML."
            )
        return name


# ── Options flow (edit existing room) ─────────────────────────────────────────

class RoomControlOptionsFlow(config_entries.OptionsFlow):
    """Edit an existing room entry."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry
        self._data: dict = dict(config_entry.data)

    async def async_step_init(self, user_input: dict | None = None):
        """Show current settings pre-filled for editing."""
        errors: dict = {}
        current = self._entry.data

        if user_input is not None:
            # Re-resolve Z2M name if light entity_id changed
            left = self._data.get("left", {})
            if (
                left.get("type") == "light"
                and user_input.get("left_entity_id")
                and user_input.get("left_entity_id") != left.get("entity_id")
            ):
                from .resolvers import resolve_z2m_friendly_name
                name = await resolve_z2m_friendly_name(
                    self.hass,
                    user_input["left_entity_id"],
                    current.get("z2m_base_topic", "zigbee2mqtt"),
                )
                left["target_z2m_name"] = name
                left["entity_id"] = user_input["left_entity_id"]
                self._data["left"] = left

            self._data["default_single_click"] = user_input.get("default_single_click", True)
            self._data["hold_delay"] = int(user_input.get("hold_delay", 500))
            self._data["dim_speed"] = int(user_input.get("dim_speed", 50))
            self._data["volume_speed"] = float(user_input.get("volume_speed", 0.05))

            return self.async_create_entry(title="", data=self._data)

        schema = vol.Schema({
            vol.Optional(
                "default_single_click",
                default=current.get("default_single_click", True),
            ): selector.BooleanSelector(),
            vol.Optional(
                "hold_delay",
                default=current.get("hold_delay", 500),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=100, max=2000, unit_of_measurement="ms", mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                "dim_speed",
                default=current.get("dim_speed", 50),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=500, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                "volume_speed",
                default=current.get("volume_speed", 0.05),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.01, max=0.1, step=0.01, mode=selector.NumberSelectorMode.BOX)
            ),
        })

        # If left pair is a light, offer to update the entity
        if current.get("left", {}).get("type") == "light":
            schema = schema.extend({
                vol.Optional(
                    "left_entity_id",
                    default=current.get("left", {}).get("entity_id", ""),
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="light")),
            })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={"area_id": current.get("area_id", "")},
        )


