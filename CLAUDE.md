# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A collection of Home Assistant automation blueprints. There is no build system, test suite, or linter — the artifacts are YAML files consumed directly by Home Assistant.

## How blueprints work

Each `.yaml` file is a standalone HA blueprint. Blueprints are installed in Home Assistant via the `source_url` field (pointing to the raw GitHub URL on `main`) or by manual file upload. Changes only take effect when re-imported or when HA restarts.

Blueprint structure:
- `blueprint:` block — metadata, `domain`, `input` definitions (grouped into sections via nested `input:` keys)
- `trigger_variables:` — variables available during trigger evaluation (limited scope, used for MQTT topic templates)
- `variables:` — resolved from `!input` values, available throughout actions
- `triggers:`, `conditions:`, `actions:` — standard HA automation fields using Jinja2 templating

`!input <name>` references a declared input by name. Variables declared under `variables:` shadow inputs of the same name and are what templates should reference.

## Blueprint-specific patterns

**215Z.yaml** (EnOcean PTM 215Z Friends-of-Hue switch via Zigbee2MQTT):
- Triggers on MQTT payloads `press_1` through `press_4`; button number extracted from `trigger.payload.split('_')[1]`
- Uses a `repeat` loop (up to 5 iterations) to detect multi-clicks: each iteration waits `hold_delay` ms for a release; if no release arrives, it's a hold action; if a release arrives, it waits again for another press to count multi-clicks
- `invert` variable (`2*(button % 2) - 1`) maps odd buttons → `+1` (up/louder/play) and even buttons → `-1` (down/quieter/pause)
- Light dimming is done via `brightness_move_onoff` MQTT payload (Zigbee2MQTT direct control, not HA light entity)
- Single-click behaviour is gated by `default_single_click`; multi-click fires `scene.<prefix>_<button>_<count>` and `script.<prefix>_<button>_<count>`

**temperature.yaml** — time-triggered, applies `climate.set_temperature` to an area, filtered by workday/weekend boolean inputs.

## Editing guidelines

- Keep `source_url` pointing to the raw `main` branch URL when editing `215Z.yaml`.
- MQTT topics are Jinja2 templates evaluated at runtime; use `trigger_variables` (not `variables`) for anything needed in trigger topic expressions.
- HA blueprint input sections require a top-level `input:` key *and* a nested `input:` key inside each section when using grouped inputs (HA 2024.6+ syntax).
- `mode: single` prevents concurrent runs; do not change without considering race conditions in the multi-click detection loop.
