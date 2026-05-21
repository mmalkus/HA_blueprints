# HA Blueprints
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://buymeacoffee.com/mauritsmalkus)

This repository contains two Home Assistant blueprints and the **room_control** custom integration that ties them together.

---

## 215Z blueprint

Based on the work of vandalon, khvej8 and others as found in the [HA community thread](https://community.home-assistant.io/t/zigbee2mqtt-enocean-ptm-215z-friends-of-hue-switch/429770/). Adds multi-click detection and media player support.

The blueprint is built so that a single automation covers one physical 215Z switch. Buttons are split into left/right pairs — button 1/2 control one device, button 3/4 control another.

- **Light:** top button turns on / increases brightness on hold; lower button turns off / decreases brightness on hold.
- **Media player:** top button plays / increases volume on hold; lower button pauses / decreases volume on hold.
- **Multi-click:** pressing a button N times calls `scene.{prefix}_{button}_{N}` and `script.{prefix}_{button}_{N}`. E.g. prefix `kitchen`, button 3, 2 clicks → `scene.kitchen_3_2`.

### Install (standalone blueprint)

[![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fmmalkus%2FHA_blueprints%2Frefs%2Fheads%2Fmain%2F215Z.yaml)

Or import manually via **Settings → Automations → Blueprints → Import blueprint** using:
```
https://raw.githubusercontent.com/mmalkus/HA_blueprints/refs/heads/main/215Z.yaml
```

---

## room_control integration

A custom integration that generates scenes, scripts, and automations from a room profile. Once generated, everything runs as native HA objects — the integration can be disabled and your lights keep working.

### What it does

- Creates `scene.{area_id}_{button}_{clicks}` for every scene you define.
- Creates `script.{area_id}_{button}_{clicks}` for scenes with action sequences.
- Generates `use_blueprint` automations for PTM 215Z switches and generic multi-click wall switches.
- Installs the required blueprints automatically on first load.
- Exposes a `room_control.sync` service to regenerate everything after config changes.

### Installation

**1. Copy the integration**

Copy the `room_control/custom_components/room_control/` folder from this repo into your HA config directory:

```
/config/custom_components/room_control/
```

How to get files there:
- **HA OS / Supervisor:** use the File Editor add-on or a Samba share → `\\<ha-ip>\config\custom_components\`
- **Docker:** copy into the volume mapped to `/config`
- **venv / manual install:** copy the folder directly

**2. Add configuration**

Add a `room_control:` block to `/config/configuration.yaml`. Minimal example to verify the integration loads:

```yaml
room_control:
  rooms:
    living_room:
      area_id: living_room
      scenes: []
      switches: []
```

**3. Restart HA**

Settings → System → Restart

**4. Check the logs**

Settings → System → Logs, filter by `room_control`. On a successful first load you should see:

```
room_control: installed blueprint 215Z.yaml
room_control: installed blueprint multiclick_room_control.yaml
room_control: sync complete (1 room(s))
```

### Full configuration example

```yaml
room_control:
  rooms:
    living_room:
      area_id: living_room

      left:
        type: light
        entity_id: light.living_room_ceiling   # Z2M name resolved automatically

      right:
        type: media_player
        media_player_entity: media_player.living_room_tv

      scenes:
        - name: Evening
          button: 1
          clicks: 2
          lights:
            - entity: light.living_room_ceiling
              brightness: 80
              color_temp: 2700   # Kelvin

        - name: Movie
          button: 1
          clicks: 3
          lights:
            - entity: light.living_room_floor
              brightness: 20
          script_sequence:
            - action: cover.close_cover
              target:
                entity_id: cover.living_room_blinds

      switches:
        - type: ptm215z
          controller_name: "Living Room Switch"   # Z2M friendly name of the switch
          controller_event: event.living_room_switch_action   # optional

      # Optional tuning (these are the defaults)
      default_single_click: true
      hold_delay: 500       # ms before a press is treated as a hold
      dim_speed: 50
      volume_speed: 0.05
```

### What gets generated for the example above

```
scene.living_room_1_2   → Evening  (ceiling at 80 brightness, 2700K)
scene.living_room_1_3   → Movie    (floor at 20 brightness)
script.living_room_1_3  → close blinds (called alongside the Movie scene)
automation.living_room_ptm215z_living_room_swit
```

Button behaviour at runtime (handled by the 215Z blueprint):

| Action | Result |
|---|---|
| Button 1 single click | Ceiling light ON |
| Button 2 single click | Ceiling light OFF |
| Button 1 hold | Brightness UP |
| Button 2 hold | Brightness DOWN |
| Button 1, 2 clicks | Evening scene |
| Button 1, 3 clicks | Movie scene + close blinds |
| Button 3 single click | TV play |
| Button 4 single click | TV pause |
| Button 3 hold | Volume UP |
| Button 4 hold | Volume DOWN |

### Services

| Service | Description |
|---|---|
| `room_control.sync` | Regenerate scenes/scripts/automations from config. Accepts optional `area_id` to sync one room. Safe to call repeatedly. |
| `room_control.install_blueprints` | Force-reinstall bundled blueprints (use after updating the integration). |

### UI configuration

Rooms can also be added via **Settings → Devices & Services → Add integration → Room Control**, without editing YAML. YAML-defined rooms are read-only in the UI.

### Updating

After pulling a new version of this repo, copy the updated `custom_components/room_control/` folder to HA again, restart, then call `room_control.install_blueprints` if blueprint files changed.
