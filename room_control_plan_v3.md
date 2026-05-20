# room_control — Home Assistant Integration
## Implementation Plan v3

---

## Core Design Principle

**The integration is a provisioner, not a runtime dependency.**

It generates native HA objects from a room profile. Once generated, everything runs on HA
core. The integration can be disabled or removed — your lights, switches, and scenes keep
working. The only thing you lose is the ability to re-sync after config changes.

---

## Naming Convention

Everything derives from `area_id`. The PTM 215Z blueprint already establishes the
`{prefix}_{button}_{clicks}` convention — the integration adopts this exactly.

```
area_id: living_room          (= scene_prefix throughout)
│
├── Scenes + Scripts  (the {prefix}_{button}_{clicks} grid)
│     scene.living_room_1_2   ← left-top button, 2 clicks
│     scene.living_room_1_3   ← left-top button, 3 clicks
│     scene.living_room_3_2   ← right-top button, 2 clicks
│     script.living_room_1_2  ← same key, script variant (both called by blueprint)
│     script.living_room_3_2  ← etc.
│
├── Single-click targets (direct entity control, not scenes)
│     left pair  → e.g. light.living_room_ceiling   (on/off + dim on hold)
│     right pair → e.g. media_player.living_room_tv  (play/pause + volume on hold)
│
└── Automations (one per physical switch, generated)
      automation.living_room_ptm215z_{device_slug}
      automation.living_room_multiclick_{topic_slug}  ← for non-215Z wall switches
```

### The `{prefix}_{button}_{clicks}` grid

The PTM 215Z has 4 buttons in 2 pairs:

```
┌──────────┬──────────┐
│ Button 1 │ Button 3 │   ← top row (odd = "on" direction, invert=+1)
│  (left)  │ (right)  │
├──────────┼──────────┤
│ Button 2 │ Button 4 │   ← bottom row (even = "off" direction, invert=-1)
│  (left)  │ (right)  │
└──────────┴──────────┘
  Left pair            Right pair
  (one target)         (one target)
```

Single click (with `default_single_click=true`):
- Button 1 → turn target ON
- Button 2 → turn target OFF
- Button 3 → turn right target ON
- Button 4 → turn right target OFF

Multi-click (N ≥ 2, or N ≥ 1 if `default_single_click=false`):
- Button B, N clicks → `scene.{prefix}_{B}_{N}` + `script.{prefix}_{B}_{N}` (both attempted)

Hold:
- Button 1 or 3 → brightness/volume UP on paired target
- Button 2 or 4 → brightness/volume DOWN on paired target

### What the integration generates per room

```
# For a room with 3 left-button scenes (buttons 1/2, N clicks = 2,3,4)
scene.living_room_1_2    ← button 1 or 2, 2 clicks → "Evening"
scene.living_room_1_3    ← button 1 or 2, 3 clicks → "Movie"
scene.living_room_1_4    ← button 1 or 2, 4 clicks → "Night"

# Mirror for button 2 (same scenes, symmetric)
# Buttons 1 and 2 are symmetric - both address the same left-pair scenes.
# The blueprint uses button number in the scene name, so you can differentiate
# or keep them the same — the integration uses button 1 by default for left scenes,
# button 3 for right scenes.

# Scripts (optional, same key as scenes)
script.living_room_1_2   ← called alongside scene.living_room_1_2

# Direct targets (for single-click + hold, NOT scene-named)
# These are just entity references in the automation, not generated objects.
left_target:  light.living_room_ceiling
right_target: media_player.living_room_tv

# Generated automation (one per switch)
automation.living_room_ptm215z_abc123de
  → uses 215Z blueprint with:
      scene_prefix: living_room
      left_type: light
      left_target_light: living_room_ceiling   ← z2m device name, not entity_id
      right_type: media_player
      right_target_media: media_player.living_room_tv
      default_single_click: true
```

### Convention for the multi-click (non-PTM) blueprint

Wall switches with a single button use the simpler multi-click convention from the
earlier blueprint. These map click count directly to scene index:

```
{prefix}_1_N  where button=1 and N = click count
scene.living_room_1_1   ← 1 click
scene.living_room_1_2   ← 2 clicks
scene.living_room_1_3   ← 3 clicks
```

This is compatible with the 215Z convention — they share the same scene namespace.

---

## What the Blueprint Already Does (don't re-implement)

The existing 215Z blueprint handles all of this at runtime — **do not replicate this logic
in the integration**. The integration only needs to generate the wiring (automation config)
that instantiates the blueprint correctly.

| Behavior | Handled by |
|---|---|
| Hold detection (hold_delay timer) | Blueprint |
| Click counting (repeat loop + wait_for_trigger) | Blueprint |
| `brightness_move_onoff` MQTT publish | Blueprint |
| `brightness_move: stop` on release | Blueprint |
| `scene.turn_on` + `script.turn_on` on multi-click | Blueprint |
| `default_single_click` on/off routing | Blueprint |
| Left/right pair routing by button number | Blueprint |
| Media player volume adjust on hold | Blueprint |

The integration's job for PTM 215Z automations: generate a `use_blueprint` automation
block with the correct input values derived from the room profile.

---

## Room Profile → Blueprint Input Mapping

```python
# Room profile fields → 215Z blueprint inputs

room.area_id              → scene_prefix
room.left.entity_id       → left_target_light OR left_target_media
room.left.type            → left_type  ("light" or "media_player")
room.right.entity_id      → right_target_light OR right_target_media
room.right.type           → right_type
room.z2m_base_topic       → base_topic (default: "zigbee2mqtt")
switch.controller_name    → controller  (z2m friendly name)
switch.controller_event   → controller_event (event entity, optional)
room.default_single_click → default_single_click (default: true)
room.hold_delay           → hold_delay (default: 500ms)
room.dim_speed            → dim_speed (default: 50)
room.volume_speed         → volume_speed (default: 0.05)
```

### Generated automation (use_blueprint style)

```yaml
# automation.living_room_ptm215z_abc123de
alias: "living room — ptm215z abc123de"
description: "room_control_managed"
use_blueprint:
  path: mmalkus/215Z.yaml
  input:
    base_topic: zigbee2mqtt
    controller: "Living Room Switch"
    scene_prefix: living_room
    left_type: light
    left_target_light: "living_room_ceiling"   # z2m name, not entity_id
    right_type: media_player
    right_target_media: media_player.living_room_tv
    default_single_click: true
    hold_delay: 500
    dim_speed: 50
    volume_speed: 0.05
```

This is a `use_blueprint` automation — the blueprint itself runs natively in HA.
The integration just writes this config block. No runtime dependency on the integration.

---

## Data Model (`models.py`)

```python
from dataclasses import dataclass, field
from typing import Optional, Literal

@dataclass
class LightConfig:
    entity_id: str
    brightness: Optional[int] = None    # 0–255
    color_temp: Optional[int] = None    # Kelvin → converted to mireds for scene.create

@dataclass
class SceneConfig:
    """
    Mapped to scene.{area_id}_{button}_{clicks}
    and optionally script.{area_id}_{button}_{clicks}
    """
    name: str                           # human label, e.g. "Evening"
    button: int                         # 1–4 (which button triggers this)
    clicks: int                         # number of clicks (≥2 if default_single_click)
    lights: list[LightConfig] = field(default_factory=list)
    media_players: list[str] = field(default_factory=list)
    covers: list[str] = field(default_factory=list)
    script_sequence: Optional[list] = None  # if set, also generates script.{name}

@dataclass
class PairConfig:
    """Config for a left or right button pair."""
    type: Literal["light", "media_player"]
    # For light: HA entity_id — the only field the user ever sets
    entity_id: Optional[str] = None
    # For light: Z2M friendly name — NEVER set by user.
    # Resolved from entity_id via device registry + Z2M bridge at config-entry
    # creation/edit time, then stored. Syncs read this directly; no re-resolution.
    # In raw YAML config (non-UI path), user may set this explicitly as an override.
    target_z2m_name: Optional[str] = None
    # For media_player: entity_id
    media_player_entity: Optional[str] = None

@dataclass
class SwitchConfig:
    type: str                               # "ptm215z", "z2m_multiclick", "zha"
    # PTM 215Z
    controller_name: Optional[str] = None  # z2m friendly name
    controller_event: Optional[str] = None # event entity_id (optional)
    # Z2M multiclick
    mqtt_topic: Optional[str] = None
    click_action_payload: str = "single"
    # ZHA
    ieee: Optional[str] = None

@dataclass
class RoomProfile:
    area_id: str                            # anchors all naming
    left: Optional[PairConfig] = None      # left button pair (buttons 1/2)
    right: Optional[PairConfig] = None     # right button pair (buttons 3/4)
    scenes: list[SceneConfig] = field(default_factory=list)
    switches: list[SwitchConfig] = field(default_factory=list)
    # Blueprint tuning (passed through to 215Z blueprint)
    z2m_base_topic: str = "zigbee2mqtt"
    default_single_click: bool = True
    hold_delay: int = 500
    dim_speed: int = 50
    volume_speed: float = 0.05
```

---

## Naming Convention Functions (`const.py`)

```python
DOMAIN = "room_control"
MANAGED_TAG = "room_control_managed"

# ── Scenes & Scripts ───────────────────────────────────────────────────────────

def scene_id(area_id: str, button: int, clicks: int) -> str:
    """scene_id("living_room", 1, 2) → 'living_room_1_2'"""
    return f"{area_id}_{button}_{clicks}"

def scene_entity(area_id: str, button: int, clicks: int) -> str:
    """→ 'scene.living_room_1_2'"""
    return f"scene.{scene_id(area_id, button, clicks)}"

def script_entity(area_id: str, button: int, clicks: int) -> str:
    """→ 'script.living_room_1_2'"""
    return f"script.{scene_id(area_id, button, clicks)}"

# ── Automations ────────────────────────────────────────────────────────────────

def ptm215z_automation_id(area_id: str, switch: SwitchConfig) -> str:
    slug = (switch.controller_name or "").replace(" ", "_").lower()[:16]
    return f"{area_id}_ptm215z_{slug}"

def multiclick_automation_id(area_id: str, switch: SwitchConfig) -> str:
    slug = (switch.mqtt_topic or "").replace("/", "_").replace("-", "_")
    return f"{area_id}_multiclick_{slug}"
```

### Full naming example for `living_room`

```
# Left pair scenes (button 1, clicks 2–4)
scene.living_room_1_2   → "Evening"
scene.living_room_1_3   → "Movie"
scene.living_room_1_4   → "Night"

# Optional scripts at same keys
script.living_room_1_2  → sequence for "Evening" (e.g. close blinds)

# Right pair scenes (button 3, clicks 2–4)
scene.living_room_3_2   → "Music On"
scene.living_room_3_3   → "Podcast"

# Automation
automation.living_room_ptm215z_living_room_switch
```

---

## Repository Layout

```
room_control/
├── custom_components/
│   └── room_control/
│       ├── __init__.py          # setup, sync orchestration, service registration
│       ├── manifest.json
│       ├── config_flow.py       # UI config (Phase 5)
│       ├── const.py             # naming functions (scene_entity, script_entity, etc.)
│       ├── models.py            # RoomProfile, SceneConfig, PairConfig, SwitchConfig
│       ├── resolvers.py         # Z2M name resolution via device registry + MQTT
│       ├── generators/
│       │   ├── __init__.py
│       │   ├── scenes.py        # scene.create calls
│       │   ├── scripts.py       # script generation (optional sequences)
│       │   └── automations.py   # use_blueprint automation dicts
│       ├── services.yaml
│       └── strings.json
├── blueprints/
│   └── multiclick_room_control.yaml   # generalized multi-click (non-215Z switches)
│   # Note: 215Z.yaml stays at mmalkus/HA_blueprints — referenced, not forked
├── tests/
│   ├── conftest.py
│   ├── test_naming.py
│   ├── test_models.py
│   ├── test_resolvers.py
│   └── test_generators/
│       ├── test_scenes.py
│       ├── test_scripts.py
│       └── test_automations.py
└── example_config.yaml
```

---

## Phase 1 — Skeleton + Naming

**Goal:** Integration loads, parses config, naming convention fully unit-tested.

### YAML schema (voluptuous)

```python
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
    vol.Optional("script_sequence"): list,    # raw HA action sequence
})

PAIR_SCHEMA = vol.Schema({
    vol.Required("type"): vol.In(["light", "media_player"]),
    # User sets entity_id only. target_z2m_name is resolved and stored automatically.
    vol.Optional("entity_id"): cv.entity_id,
    vol.Optional("media_player_entity"): cv.entity_id,
    # Power-user override (YAML path only). If absent, resolved from entity_id.
    # Never appears in configs created via the UI config flow.
    vol.Optional("target_z2m_name"): str,
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
```

### Naming convention tests

```python
# test_naming.py

def test_scene_entity():
    assert scene_entity("living_room", 1, 2) == "scene.living_room_1_2"
    assert scene_entity("living_room", 3, 4) == "scene.living_room_3_4"

def test_script_entity():
    assert script_entity("living_room", 1, 2) == "script.living_room_1_2"

def test_scene_and_script_share_key():
    # Blueprint calls both; they must share the same {button}_{clicks} key
    assert scene_entity("lr", 2, 3).endswith("_2_3")
    assert script_entity("lr", 2, 3).endswith("_2_3")

def test_ptm215z_automation_id():
    sw = SwitchConfig(type="ptm215z", controller_name="Living Room Switch")
    assert ptm215z_automation_id("living_room", sw) == \
           "living_room_ptm215z_living_room_swit"  # truncated to 16 chars

def test_multiclick_automation_id():
    sw = SwitchConfig(type="z2m_multiclick",
                      mqtt_topic="zigbee2mqtt/kitchen_switch")
    assert multiclick_automation_id("kitchen", sw) == \
           "kitchen_multiclick_zigbee2mqtt_kitchen_switch"
```

---

## Phase 1b — Z2M Name Resolution

**Goal:** Given a light `entity_id`, resolve and return the Z2M friendly name.
Called once at config-entry creation/edit; result stored in the config entry, never re-run during sync.

```python
# resolvers.py

async def resolve_z2m_friendly_name(
    hass: HomeAssistant,
    entity_id: str,
    base_topic: str = "zigbee2mqtt",
) -> str | None:
    """
    Resolve Z2M friendly name from a HA light entity_id.
    Returns None if entity is not a Z2M device or bridge cache is empty.

    Steps:
    1. entity_id -> device_id  (entity registry)
    2. device_id -> IEEE        (device registry identifiers: "mqtt"/"zigbee2mqtt_{ieee}")
    3. IEEE -> friendly_name    (hass.data[DOMAIN]["z2m_devices"] cache)

    Fails gracefully at each step — returns None with a warning log.
    """
    from homeassistant.helpers import entity_registry as er, device_registry as dr

    ent_reg = er.async_get(hass)
    entry = ent_reg.async_get(entity_id)
    if not entry or not entry.device_id:
        _LOGGER.warning("room_control: entity %s not in entity registry", entity_id)
        return None

    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(entry.device_id)
    if not device:
        return None

    ieee = next(
        (ident.removeprefix("zigbee2mqtt_")
         for domain, ident in device.identifiers
         if domain == "mqtt" and ident.startswith("zigbee2mqtt_")),
        None
    )
    if not ieee:
        _LOGGER.warning(
            "room_control: %s is not a Z2M device (no zigbee2mqtt_ identifier)",
            entity_id,
        )
        return None

    z2m_devices: dict = hass.data.get(DOMAIN, {}).get("z2m_devices", {})
    name = z2m_devices.get(ieee)
    if not name:
        _LOGGER.warning(
            "room_control: IEEE %s not found in Z2M device cache "
            "(is Zigbee2MQTT running?)", ieee,
        )
    return name


async def cache_z2m_devices(hass: HomeAssistant, base_topic: str) -> None:
    """
    Subscribe to {base_topic}/bridge/devices once during async_setup.
    Z2M publishes a JSON array on this topic at startup:
    [{"ieee_address": "0x...", "friendly_name": "Living Room Ceiling", ...}, ...]

    Stores: hass.data[DOMAIN]["z2m_devices"] = {ieee_address: friendly_name}

    Uses hass.components.mqtt.async_subscribe. Called before config is parsed
    so the cache is warm when resolve_z2m_friendly_name is first called.
    """
```

### When resolution is called

Resolution runs **only** in these two moments — **never during sync**:

**Config flow (UI):** after user selects `entity_id`, immediately before saving.
If resolution fails, the config flow shows an error and does not save:
> *"Could not resolve Z2M name for light.living_room_ceiling. Is Zigbee2MQTT
> running? Alternatively, set target_z2m_name manually in YAML."*

**YAML config parse (non-UI):** if `target_z2m_name` is absent, resolve at startup.
If it fails, the room's scenes and scripts are still generated but the automation
is skipped, and a warning is logged. The user can add `target_z2m_name` explicitly
as a fallback.

Sync always reads the already-stored `target_z2m_name`. No MQTT lookup at sync time.

### Tests

```python
# test_resolvers.py

async def test_resolve_happy_path(mock_hass, mock_entity_reg, mock_device_reg):
    # Arrange: entity -> device with identifier ("mqtt", "zigbee2mqtt_0xabc")
    # z2m_devices cache: {"0xabc": "Living Room Ceiling"}
    result = await resolve_z2m_friendly_name(mock_hass, "light.living_room_ceiling")
    assert result == "Living Room Ceiling"

async def test_resolve_not_z2m_device(mock_hass, mock_entity_reg, mock_device_reg):
    # Device has no zigbee2mqtt_ identifier (e.g. Hue native integration)
    result = await resolve_z2m_friendly_name(mock_hass, "light.hue_bulb")
    assert result is None

async def test_resolve_bridge_cache_empty(mock_hass, mock_entity_reg, mock_device_reg):
    # IEEE found in device registry but z2m_devices cache not yet populated
    hass.data[DOMAIN]["z2m_devices"] = {}
    result = await resolve_z2m_friendly_name(mock_hass, "light.living_room_ceiling")
    assert result is None  # warn, don't crash

async def test_cache_z2m_devices_parses_payload(mock_hass, mock_mqtt):
    payload = '[{"ieee_address": "0xabc", "friendly_name": "Living Room Ceiling"}]'
    # Simulate MQTT message arriving on bridge/devices topic
    await cache_z2m_devices(mock_hass, "zigbee2mqtt")
    mock_mqtt.fire_message("zigbee2mqtt/bridge/devices", payload)
    assert mock_hass.data[DOMAIN]["z2m_devices"]["0xabc"] == "Living Room Ceiling"
```


---

## Phase 2 — Scene Generator

**Goal:** `generators/scenes.py` creates HA scenes from room profile.

```python
# generators/scenes.py

KELVIN_TO_MIREDS = lambda k: round(1_000_000 / k)

async def sync_scenes(hass: HomeAssistant, room: RoomProfile) -> None:
    """
    For each SceneConfig, call scene.create:

    scene.create payload:
    {
        "scene_id": scene_id(room.area_id, scene.button, scene.clicks),
        "entities": {
            light_entity_id: {
                "state": "on",
                "brightness": ...,
                "color_temp": ...  # mireds = 1_000_000 / kelvin
            },
            ...
        }
    }

    Key notes:
    - scene_id is WITHOUT "scene." prefix (scene.create adds it)
    - color_temp: convert Kelvin → mireds before passing
    - Lights NOT listed in the scene are NOT turned off by scene.create —
      the blueprint calls scene.turn_on which only sets listed entities.
      If you want an "Off" scene, list all room lights with state: "off".
    - media_players and covers: scene.create supports them too —
      state: "playing" / "open" respectively
    - Add MANAGED_TAG to scene description field
    - Idempotent: safe to call multiple times
    """

async def sync_all_scenes(hass: HomeAssistant,
                           profiles: dict[str, RoomProfile]) -> None:
    for room in profiles.values():
        await sync_scenes(hass, room)
```

**Tests:**
```python
def test_kelvin_to_mireds():
    assert KELVIN_TO_MIREDS(4000) == 250
    assert KELVIN_TO_MIREDS(2700) == 370

def test_scene_create_payload(mock_hass, sample_room):
    # sample_room has SceneConfig(button=1, clicks=2, ...)
    # assert scene.create called with scene_id="living_room_1_2"
    # assert color_temp converted to mireds

def test_scene_for_each_scene_config(mock_hass, sample_room):
    # 3 SceneConfigs → 3 scene.create calls
```

---

## Phase 3 — Script Generator (optional)

**Goal:** `generators/scripts.py` creates scripts at `script.{area_id}_{button}_{clicks}`.

Only needed if `scene.script_sequence` is set in the room config. The blueprint calls
`script.turn_on` alongside `scene.turn_on` — if no script exists, HA silently ignores it.
So this phase is genuinely optional; scripts can also be created manually.

```python
async def sync_scripts(hass: HomeAssistant, room: RoomProfile) -> None:
    """
    For each SceneConfig with script_sequence set:
      Write to scripts.yaml (or use hass storage API) a script at:
      script.{scene_id(area_id, button, clicks)}

      Script format:
      {
        "alias": f"{room.area_id} — {scene.name}",
        "description": MANAGED_TAG,
        "sequence": scene.script_sequence   # raw HA action sequence from config
      }

    Then call script.reload.
    """
```

---

## Phase 4 — Automation Generator

**Goal:** `generators/automations.py` generates `use_blueprint` automations and writes them to HA.

### For PTM 215Z switches

```python
def build_ptm215z_automation(room: RoomProfile, switch: SwitchConfig) -> dict:
    """
    Generates a use_blueprint automation referencing mmalkus/215Z.yaml.
    Maps room profile fields to blueprint inputs exactly.

    {
      "id": ptm215z_automation_id(room.area_id, switch),
      "alias": f"{room.area_id} — ptm215z {switch.controller_name}",
      "description": MANAGED_TAG,
      "use_blueprint": {
        "path": "mmalkus/215Z.yaml",
        "input": {
          "base_topic": room.z2m_base_topic,
          "controller": switch.controller_name,
          "controller_event": switch.controller_event or "",
          "scene_prefix": room.area_id,
          "left_type": room.left.type,
          "left_target_light": room.left.target_z2m_name or "",
          "left_target_media": room.left.media_player_entity or {},
          "right_type": room.right.type,
          "right_target_light": room.right.target_z2m_name or "",
          "right_target_media": room.right.media_player_entity or {},
          "default_single_click": room.default_single_click,
          "hold_delay": room.hold_delay,
          "dim_speed": room.dim_speed,
          "volume_speed": room.volume_speed,
        }
      }
    }

    Note: the blueprint must be installed in HA's blueprint directory.
    The integration should check for its presence and warn if missing.
    """
```

### For multi-click wall switches

```python
def build_multiclick_automation(room: RoomProfile, switch: SwitchConfig) -> dict:
    """
    Uses the multiclick_room_control blueprint (or generates native automation).
    Click N → scene.{area_id}_1_{N} + script.{area_id}_1_{N}  (button=1 by default)

    Max clicks = max(scene.clicks for scene in room.scenes if scene.button == 1)

    Blueprint input:
    {
      "mqtt_topic": switch.mqtt_topic,
      "click_action_payload": switch.click_action_payload,
      "scene_prefix": room.area_id,   # blueprint constructs {prefix}_1_{N}
      "max_clicks": <derived from scenes>
    }
    """
```

### Writing to HA

```python
async def sync_automations(hass: HomeAssistant, room: RoomProfile) -> None:
    """
    Strategy: write to /config/automations.yaml via file I/O.

    Steps:
    1. Read existing automations.yaml
    2. Remove entries with description == MANAGED_TAG matching this room's area_id
       (clean up stale entries from previous syncs)
    3. Append newly generated automation dicts
    4. Write back to automations.yaml
    5. Call automation.reload service

    Alternative if automations.yaml is not used: use HA storage API
      homeassistant.components.automation stores entries in
      .storage/core.entity_registry — but file I/O is simpler and more reliable.

    YAML serialization note: use ruamel.yaml (not PyYAML) to preserve
    formatting and avoid mangling existing automations.
    """
```

---

## Phase 5 — Sync Service + Startup

**Goal:** One service call regenerates everything. Runs automatically on startup.

```yaml
# services.yaml
sync:
  name: Sync Room
  description: >
    Regenerate all scenes, scripts, and automations from the room profile.
    Idempotent — safe to call repeatedly after config changes.
  fields:
    area_id:
      name: Room (optional)
      description: Sync one room. Omit to sync all rooms.
      required: false
      selector:
        area:
```

```python
# __init__.py

async def async_setup(hass, config):
    profiles = parse_config(config[DOMAIN])
    hass.data[DOMAIN] = {"profiles": profiles}

    async def handle_sync(call):
        area_id = call.data.get("area_id")
        targets = (
            [profiles[area_id]] if area_id
            else list(profiles.values())
        )
        for room in targets:
            await sync_scenes(hass, room)
            await sync_scripts(hass, room)
            await sync_automations(hass, room)

    hass.services.async_register(DOMAIN, "sync", handle_sync)

    # Sync all on startup
    hass.async_create_task(
        hass.services.async_call(DOMAIN, "sync", {})
    )
    return True
```

**Startup behavior:**
- Re-syncs on every HA restart (idempotent, fast)
- If integration is disabled: scenes/automations/scripts remain and keep working
- If integration is uninstalled: everything generated remains (native HA objects)

---

## Phase 6 — Generalized Multi-Click Blueprint

The existing 215Z blueprint handles PTM 215Z switches natively.
For plain wall switches (Shelly, IKEA, etc.) a separate blueprint is needed.
It must produce the same `{prefix}_{button}_{clicks}` scene/script names.

```yaml
# blueprints/multiclick_room_control.yaml

blueprint:
  name: Multi-Click — Room Control
  description: >
    Activate scenes by clicking a switch multiple times.
    Compatible with room_control naming: scenes must be named
    {scene_prefix}_{button}_{clicks}, e.g. kitchen_1_2 for 2 clicks.
    Supports Zigbee2MQTT (MQTT), ZHA events, and state triggers.
  input:
    scene_prefix:
      name: Scene prefix (= area_id)
      selector: {text: {}}

    button:
      name: Button number
      description: Which button number to use in scene name (1–4)
      default: 1
      selector:
        number: {min: 1, max: 4, mode: box}

    # Trigger type selection
    trigger_type:
      name: Trigger type
      selector:
        select:
          options:
            - label: Zigbee2MQTT (MQTT topic)
              value: z2m
            - label: ZHA event
              value: zha
            - label: State change (binary_sensor, switch)
              value: state

    mqtt_topic:
      name: "[Z2M] MQTT Topic"
      default: ""
      selector: {text: {}}
    click_action_payload:
      name: "[Z2M] Single-click payload"
      default: "single"
      selector: {text: {}}

    zha_device:
      name: "[ZHA] Device"
      default: {}
      selector:
        device:
          integration: zha
    zha_command:
      name: "[ZHA] Click command"
      default: "toggle"
      selector: {text: {}}

    state_entity:
      name: "[State] Entity"
      default: ""
      selector:
        entity:
          domain: [binary_sensor, input_boolean, switch]

    max_clicks:
      name: Maximum clicks
      default: 4
      selector:
        number: {min: 1, max: 6, mode: slider}

    click_timeout:
      name: Click timeout (ms)
      default: 500
      selector:
        number: {min: 200, max: 2000, unit_of_measurement: ms}

# Action (same counter logic as original multi-click blueprint):
# 1. Count clicks within timeout window
# 2. On timeout expiry:
#    - scene.turn_on:  scene.{scene_prefix}_{button}_{click_count}
#    - script.turn_on: script.{scene_prefix}_{button}_{click_count}
#    Both called, matching 215Z blueprint behavior.
```

---


---

## Phase 7 — Config Flow UI (build last)

**Goal:** Add/edit rooms through HA Settings → Integrations without touching YAML.

```
Step 1: Pick area
  → area selector
  → sets area_id

Step 2: Configure left pair
  → type selector: light / media_player
  → entity selector (filtered to chosen domain)
  → on entity selected: call resolve_z2m_friendly_name() in the background
      success: store target_z2m_name silently, show green checkmark
      failure: show inline warning — "Could not resolve Z2M name.
               Is Zigbee2MQTT running? You can add target_z2m_name
               manually in YAML, or skip if this pair isn't Z2M."
               Allow skipping — scenes still work, only automation is skipped.

Step 3: Configure right pair (optional)
  → same as step 2

Step 4: Add scenes (repeating)
  → name, button (1–4), clicks (1–6)
  → light entities + brightness + color_temp (Kelvin)
  → optional: script sequence (raw YAML textarea for power users)
  → "Add another scene" loops back

Step 5: Add switches (repeating)
  → type: ptm215z / z2m_multiclick / zha
  → ptm215z: controller name (z2m friendly name of the switch itself)
             controller_event entity (optional)
  → z2m_multiclick: mqtt topic, click payload
  → zha: device selector (zha integration filter)
  → "Add another switch" loops back

Step 6: Review + confirm
  → summary: area, pairs, N scenes, N switches
  → "Save and sync" button → saves config entry, triggers room_control.sync
```

Implementation notes:
- `target_z2m_name` is **never shown as an input field** — populated by the flow
- Use `config_entries` + `OptionsFlow` for editing existing rooms
- Merge with YAML config: YAML-defined rooms appear as read-only in the UI;
  UI-created rooms are stored in config entries
- Trigger `handle_sync` at end of config flow completion
- Re-resolution: if user edits entity_id in OptionsFlow, re-resolve and update stored name

## Full Example `configuration.yaml`

```yaml
room_control:
  rooms:
    living_room:
      area_id: living_room
      left:
        type: light
        entity_id: light.living_room_ceiling      # Z2M name resolved+stored automatically
      right:
        type: media_player
        media_player_entity: media_player.living_room_tv
      scenes:
        # Left pair scenes (button 1, N clicks)
        - name: Evening
          button: 1
          clicks: 2
          lights:
            - entity: light.living_room_ceiling
              brightness: 80
              color_temp: 2700
            - entity: light.living_room_floor
              brightness: 60
        - name: Movie
          button: 1
          clicks: 3
          lights:
            - entity: light.living_room_floor
              brightness: 20
          script_sequence:
            - service: cover.close_cover
              target:
                entity_id: cover.living_room_blinds
        - name: Night
          button: 1
          clicks: 4
          lights:
            - entity: light.living_room_ceiling
              brightness: 10
              color_temp: 2200
        # Right pair scenes (button 3, N clicks) — controls right target
        - name: Music
          button: 3
          clicks: 2
          media_players:
            - media_player.living_room_tv
      switches:
        - type: ptm215z
          controller_name: "Living Room Switch"
          controller_event: event.living_room_switch_action
      z2m_base_topic: zigbee2mqtt
      default_single_click: true
      hold_delay: 500
      dim_speed: 50

    kitchen:
      area_id: kitchen
      left:
        type: light
        entity_id: light.kitchen_ceiling          # Z2M name resolved+stored automatically
      scenes:
        - name: Bright
          button: 1
          clicks: 2
          lights:
            - entity: light.kitchen_ceiling
              brightness: 255
              color_temp: 4500
        - name: Dim
          button: 1
          clicks: 3
          lights:
            - entity: light.kitchen_ceiling
              brightness: 60
              color_temp: 3000
      switches:
        - type: z2m_multiclick
          mqtt_topic: zigbee2mqtt/kitchen_wall_switch
          click_action_payload: "single"
```

### What gets generated for `living_room`

```
# Scenes (4 total)
scene.living_room_1_2   → Evening  (ceiling 80/2700K, floor 60)
scene.living_room_1_3   → Movie    (floor 20)
scene.living_room_1_4   → Night    (ceiling 10/2200K)
scene.living_room_3_2   → Music    (TV playing)

# Scripts (1 — only where script_sequence is defined)
script.living_room_1_3  → close blinds (called alongside Movie scene)

# Automation (1 — PTM 215Z)
automation.living_room_ptm215z_living_room_swit
  use_blueprint: mmalkus/215Z.yaml
  input:
    scene_prefix: living_room
    left_type: light
    left_target_light: "Living Room Ceiling"   # resolved from entity_id, stored at config time
    right_type: media_player
    right_target_media: media_player.living_room_tv
    default_single_click: true
    ...

# Runtime behavior (handled entirely by 215Z blueprint):
# Button 1 single click → ceiling ON
# Button 2 single click → ceiling OFF
# Button 1 hold         → ceiling brightness UP
# Button 2 hold         → ceiling brightness DOWN
# Button 1, 2 clicks    → scene.living_room_1_2 + script.living_room_1_2 (Evening)
# Button 1, 3 clicks    → scene.living_room_1_3 + script.living_room_1_3 (Movie + close blinds)
# Button 3 single click → TV play
# Button 4 single click → TV pause
# Button 3, 2 clicks    → scene.living_room_3_2 + script.living_room_3_2 (Music)
```

---

## Testing Checklist

### Unit tests (no HA needed)
- [ ] `scene_entity("living_room", 1, 2)` → `"scene.living_room_1_2"`
- [ ] `script_entity("living_room", 1, 2)` → `"script.living_room_1_2"`
- [ ] Scene and script share same `{button}_{clicks}` key for same SceneConfig
- [ ] `resolve_z2m_friendly_name` returns name from cache given valid Z2M entity
- [ ] `resolve_z2m_friendly_name` returns None gracefully for non-Z2M entity
- [ ] `resolve_z2m_friendly_name` returns None gracefully when cache empty
- [ ] `cache_z2m_devices` populates cache from bridge/devices MQTT payload
- [ ] `ptm215z_automation_id` unique per controller_name
- [ ] `multiclick_automation_id` unique per mqtt_topic
- [ ] Kelvin → mireds conversion correct (4000K → 250, 2700K → 370)
- [ ] Scene payload matches HA `scene.create` format
- [ ] PTM215Z automation maps all room profile fields to correct blueprint inputs
- [ ] MANAGED_TAG in all generated object descriptions

### Integration tests (HA test harness)
- [ ] Integration loads from config, no errors
- [ ] `room_control.sync` creates scenes in HA
- [ ] Re-syncing removes stale scenes/automations before recreating
- [ ] `use_blueprint` automation appears in HA with correct inputs
- [ ] Config flow: selecting entity_id triggers Z2M resolution and stores name
- [ ] Config flow: resolution failure shows error, blocks save
- [ ] YAML config without target_z2m_name: resolution runs at startup
- [ ] YAML config with explicit target_z2m_name: resolution is skipped
- [ ] Disabling integration: scenes and automations remain and work
- [ ] Blueprint `scene.turn_on` + `script.turn_on` both fire on multi-click

### Manual tests (real hardware)
- [ ] PTM 215Z button 1 single click → ceiling ON
- [ ] PTM 215Z button 2 single click → ceiling OFF
- [ ] PTM 215Z button 1 hold → ceiling dims UP
- [ ] PTM 215Z button 1, 2 clicks → Evening scene
- [ ] PTM 215Z button 1, 3 clicks → Movie scene + blinds close
- [ ] Multi-click wall switch: 2 clicks → scene.kitchen_1_2

---

## Reference Links

- **215Z blueprint** (yours): https://github.com/mmalkus/HA_blueprints/blob/main/215Z.yaml
- Z2M PTM 215Z device: https://www.zigbee2mqtt.io/devices/PTM_215Z.html
- HA `scene.create` service: https://www.home-assistant.io/integrations/scene/#service-scenecreate
- HA `use_blueprint` automation format: https://www.home-assistant.io/docs/automation/using_blueprints/
- HA custom integration structure: https://developers.home-assistant.io/docs/creating_integration_file_structure
- voluptuous reference: https://github.com/alecthomas/voluptuous
- ruamel.yaml (for safe YAML file editing): https://pypi.org/project/ruamel.yaml/
