# Menu navigation notes

These are the observed input routes used by the MKDS custom/debug layer. They are here so the next automation does not have to rediscover animation timing and menu transitions.

## Input model

- `press(name, frames)` arms a button for `frames` emulated frames; it does not inject a single instantaneous event.
- `wait(frames)` resumes the emulation and pauses again at the requested frame boundary.
- Pause before taking screenshots. `screenshot lower native <path>` captures a 256x192 lower screen.
- Transitions need time. Reading the menu immediately after a press can still show the old state; wait and check again.
- A press can be ignored while a selection animation is playing. Poll `menu` and repeat the press if the expected state did not change.
- Do not force `menu_state 10` (`vs_rules`) directly from the title; in the observed build it jumps through an incomplete scene setup. Navigate naturally.

## Observed menu states

| State | Name |
|---|---|
| 1 | `mode_select` |
| 4 | `gp_class_select` |
| 5 | `gp_character_select` |
| 6 | `gp_kart_select` |
| 8 | `vs_character_select` |
| 9 | `vs_kart_select` |
| 10 | `vs_rules` |
| 20 | `ta_mode_select` |

## Route: VS rules -> 250cc

Starting after boot:

1. `pause`.
2. `scene 1` (skip title), `wait 45`.
3. Expect `mode_select` (state 1).
4. `press DOWN`, `wait 15`; `press DOWN`, `wait 15`; `press A`, `wait 45`.
5. Expect `vs_character_select` (state 8).
6. `press A`, `wait 30`.
7. Expect `vs_kart_select` (state 9). Wait 30 frames for the kart-select screen to settle.
8. `press A`, `wait 30` (select the kart).
9. `press A`, `wait 90` (the second confirmation has the longer animation).
10. Expect `vs_rules` (state 10).
11. The CLASS selector starts at `50cc`. Press `RIGHT` four times with `wait 15` after each: `50 -> 100 -> 150 -> 200 -> 250cc`.
12. Confirm the screen still has `vs_rules` and the CLASS row is focused.
13. `screenshot lower native dbg_vs_rules_250cc.bmp` or the target path.

The selected/confirmed class moves focus to `CPU KART`; press `UP` to return focus to `CLASS` if needed for the screenshot.

## What the automation learned

- From the default mode-select position, one `DOWN` + `A` lands in Time Attack (`ta_mode_select`, state 20); two `DOWN` presses + `A` land in VS (`vs_character_select`, state 8). Do not use `RIGHT`: its result varied with the prior cursor position (one observation was GP, another VS).
- `vs_kart_select` uses two confirmation presses. The second kart-select confirmation (`A2`) has the longer animation: wait about 90 frames after it before expecting `vs_rules`.
- The CLASS row accepts `RIGHT` navigation without needing to open a submenu; a 15-frame wait is enough.
- At `vs_rules`, `CLASS 250cc` is the fourth `RIGHT` from the default `50cc`.
- `menu` returns the current state; `scene` alone is not enough to prove the submenu is ready.
- The lower screen is the useful rules/class display; capture with `screenshot lower native`.

A machine-readable copy is in `routes.json`.
