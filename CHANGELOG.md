# Changelog

## [1.4.0] - 2026-09-12

### Added
- Responsive card sections for Designer, all nine display modes, GIF carousels, and messages, including their stop actions.
- Connection controls, panel resolution selection, layer ordering, and all message styles, icons, fonts, colors, and duration options.
- Frontend regression tests and a local browser harness that uses the real Python preview renderer while simulating device writes.

### Fixed
- Prevented repeated or leaked template subscriptions, including edits, layer removal, late responses, and reconnects.
- Debounced preview rendering, rejected stale responses, and kept the last preview visible during refreshes.
- Removed the duplicate send button; actions now await completion, prevent duplicate submissions, and display errors inline.
- Made Designer preview and panel output use the same resolution. Sending a design selects Designer mode and preserves its explicit refresh trigger.
- Saved designs now retain resolution and refresh metadata, with compatibility for older saved designs.
- Corrected the card editor fields and documentation link, input labels, keyboard tabs, and mobile overflow.
- Bundled Lit locally so the card no longer requires an external CDN.
- Removed duplicate required-field keys from the CO₂ and power service descriptions.

### Upgrade notes
Update the integration, restart Home Assistant, and refresh your dashboard. The card resource version updates automatically. Existing card layers and saved designs remain supported. Dashboard modes and messages support 32×32 or 64×64; the Designer also supports 16×16.

Thank you again to **[Sean Carolan (@scarolan)](https://github.com/scarolan)** for the GIF and dashboard features this card now exposes, and to the original client contributors credited in [CONTRIBUTORS.md](CONTRIBUTORS.md).

## [1.3.0] - 2026-09-12

### Added
- Single GIF uploads and device-managed carousels of up to 12 GIFs, with controls in the Lovelace card.
- Animated weather, Bitcoin price, CO₂, household power, thermostat, sun, and moon dashboards.
- Pixel and analog clock faces, native firmware clock selection, and temporary messages that restore the previous dashboard.
- GIF optimization helper and expanded setup, automation, and Bluetooth proxy documentation.
- Automated runtime regression tests, renderer checks, and release version validation.

### Fixed
- Added explicit Disconnect/Reconnect buttons and release the Bluetooth connection when the integration is unloaded or disabled (#6).
- Added `idotmatrix.show_color` for native fullscreen color notifications (#7).
- Restored the previous multiline setting when Perfect Fit is switched off and moved multiline rendering off the event loop (#4).
- Avoid redundant image-mode commands and identical image uploads to reduce update blanking (#3).
- Normalize Bluetooth MAC addresses and reject duplicate manual/discovered entries, including older address formats; the original mass-duplication report remains unconfirmed (#5).
- Stopped dashboard refreshes can no longer queue an upload over a newly selected mode. Pending refresh tasks are owned and cancelled during unload.
- Legacy text, Designer, time-sync, and clock-date controls now serialize device writes with GIF uploads.
- GIF cancellation propagates correctly. Active shielded transfers are drained before their caller exits, and unload rejects queued transfers.
- Failed carousel setup commands abort the transfer; missing GIF paths and failed uploads report service errors.
- Non-finite sensor readings are treated as unavailable. Display services validate sizes, colors, durations, and sensor inputs.
- The carousel UI now respects the protocol's 1–255 second range.
- Lovelace resources handle the current Home Assistant data API, and the options flow no longer assigns to its read-only config-entry property (#9).
- Release version, integration manifest, and card version now consistently identify 1.3.0.

### Upgrade notes
- Update through HACS, restart Home Assistant, and refresh your dashboard browser.
- For CO₂ and power dashboards, provide your own `co2_entity` or `power_entity`. Thermostat dashboards require at least one of `heat_entity` or `cool_entity`; installation-specific defaults have been removed.
- Dashboard renderers support 32×32 and 64×64 output. Prepare uploaded GIFs at your panel's resolution; raw uploads preserve their original frames.
- Historical `v1.1`, `dev1.2`, and `dev1.3` tags retain their original contents, including the old `1.0.0` manifest. This release establishes consistent semantic versioning without rewriting published tags.
- Runtime tests use Home Assistant 2026.9.2 and simulated Bluetooth. Physical LED panels and ESPHome proxies were not exercised during this maintenance release.

### Thanks
A huge thank you to **[Sean Carolan (@scarolan)](https://github.com/scarolan)** for [PR #8](https://github.com/tukies/iDotMatrix-HomeAssistant/pull/8): GIF support, Bluetooth proxy work, the animated dashboard family, clocks, messages, and extensive documentation. This release builds on his substantial contribution, with maintainer fixes and regression coverage added during integration.

Thanks also to **[@derkalle4](https://github.com/derkalle4)** for the original Python iDotMatrix client, and **[@8none1](https://github.com/8none1)** for the reset-protocol discovery used by the client.

## [1.1] - 2026-01-19
- Added the Designer card, layered templates, saved designs, icons, and trigger-based refresh.
- Added the Text/Designer display-mode selector and development workflow improvements.

## [1.0.0] - 2025-12-31
- Initial public release of the Home Assistant integration.

[1.3.0]: https://github.com/tukies/iDotMatrix-HomeAssistant/compare/v1.1...v1.3.0
[1.1]: https://github.com/tukies/iDotMatrix-HomeAssistant/releases/tag/v1.1
[1.0.0]: https://github.com/tukies/iDotMatrix-HomeAssistant/releases/tag/v1.0.0

[1.4.0]: https://github.com/tukies/iDotMatrix-HomeAssistant/compare/v1.3.0...v1.4.0
