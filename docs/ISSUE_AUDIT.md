# Historical issue audit — 1.3.0

All seven GitHub issues, including closed reports and their follow-up comments, were reviewed for this release.

| Issue | Outcome | Verification |
| --- | --- | --- |
| [#1 HACS repository link](https://github.com/tukies/iDotMatrix-HomeAssistant/issues/1) | Reporter confirmed HACS was not installed. No integration defect identified. | Installation instructions reviewed; HACS validator is part of the release gate. |
| [#3 Blanking during updates](https://github.com/tukies/iDotMatrix-HomeAssistant/issues/3) | Repeated image updates no longer re-enter DIY mode; identical pixels are not retransmitted. | Simulated uploads verify one mode command across consecutive images and no upload for identical pixels. Firmware-visible flicker still needs physical-panel confirmation. |
| [#4 Text disappears after Perfect Fit](https://github.com/tukies/iDotMatrix-HomeAssistant/issues/4) | Perfect Fit now restores the previous multiline setting when turned off. Multiline rendering runs in the executor. The reporter previously said the symptom cleared without a known cause. | Toggle regression tests and visible-pixel rendering checks at 16, 32, and 64 pixels. Original Bluetooth/interference cause cannot be reconstructed. |
| [#5 Thousands of duplicate devices](https://github.com/tukies/iDotMatrix-HomeAssistant/issues/5) | Address formats are canonicalized, duplicate checks also recognize older stored formats, and duplicate-flow aborts are no longer swallowed. Keep the report open: there are no logs, registry samples, or reproducible steps. | 2,001 repeated claims of an already configured address are rejected; case/dash/compact variants share one identity. This does not prove the original runaway-device cause. No live registry was modified. |
| [#6 Disconnect](https://github.com/tukies/iDotMatrix-HomeAssistant/issues/6) | Disconnect/Reconnect buttons added. Disconnect stops tracking and suspends writes; unload/disable drains pending operations and disconnects BLE. | Simulated connection tests verify disconnect and reject subsequent writes until resumed. Phone handoff requires physical verification. |
| [#7 Fullscreen color](https://github.com/tukies/iDotMatrix-HomeAssistant/issues/7) | Added `idotmatrix.show_color` with validated RGB input. | Native fullscreen-color command receives the requested RGB values and replaces dashboard tracking. Partial-screen notification layouts remain available through Designer layers. |
| [#9 Lovelace registration](https://github.com/tukies/iDotMatrix-HomeAssistant/issues/9) | Supports the current object-based Lovelace data structure and previous dictionary format, plus versioned resource updates. | Tests cover both structures and updating an existing resource without duplication. |

Tests execute the maintained integration against Home Assistant 2026.9.2 with simulated Bluetooth. No production Home Assistant configuration, device registry, LED matrix, or phone was modified during this audit.
