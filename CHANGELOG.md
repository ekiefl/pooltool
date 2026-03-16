# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-03-15

### Added

- Impulse Frictional Inelastic ball-cushion collision model ([#226]).
- Stronge Compliant Lumped-Parameter ball-cushion collision model with configurable `omega_ratio` ([#240], [#256]).
- `simulate_with_snapshots()` for capturing simulation internals at every step ([#232]).
- Algorithm 1010 quartic solver (Orellana & De Michele, 2020) with comprehensive test suite ([#235]).
- Event priority system for resolving simultaneous collisions ([#257]).
- Handling for Newton's-cradle-like continuously touching balls ([#257]).
- `Jump.ANGLE()` for arbitrary-angle ball placement in layouts ([#257]).
- 3D cushion normals via `get_normal_3d()` on cushion segments ([#226]).
- Quaternion and rotation utilities in `ptmath` ([#226]).
- Positive-value validation on `BallParams` friction coefficients ([#265], fixes [#264]).
- Overhauled API reference with custom Sphinx extensions and new CSS ([#276]).
- Codecov integration with per-flag coverage tracking ([#268], [#269], [#270]).

### Changed

- Stronge Compliant is now the default ball-cushion model, replacing Mathavan 2010 ([#256]).
- Replaced Poetry with uv as the package manager and build system ([#275]).
- Simulation loop refactored to expose internals for introspection ([#232]).
- Stick-ball collisions are now first-class events rather than special-cased ([#232]).
- Quartic solver optimized — collision times computed on-the-fly per pair ([#235], [#236]).
- Improved ball-cushion and ball-ball separation (`make_kiss`) logic ([#257], [#271]).
- `get_normal()` renamed to `get_normal_xy()` with simplified signature ([#226], [#248]).
- Overlapping balls now trigger immediate resolution instead of being ignored ([#257]).
- `enforce_rules` setting now applied in interactive mode ([#241]).
- PBR table model loading falls back to non-PBR when `_pbr.glb` is missing ([#244]).
- API reference restructured with simplified templates ([#276]).

### Fixed

- Memory leaks when calling `show()` repeatedly ([#274], fixes [#219]).
- Han 2005 ball-cushion model correctness issues ([#247]).
- Straight shot example geometry error ([#259]).
- Scene node leak causing tables to overlap when starting a new game ([#267], fixes [#229]).
- Single-ball system crash when collision cache is empty ([#271]).
- Read the Docs build failure from astroid 4.x incompatibility ([ec8cc34]).

[#219]: https://github.com/ekiefl/pooltool/issues/219
[#226]: https://github.com/ekiefl/pooltool/pull/226
[#229]: https://github.com/ekiefl/pooltool/issues/229
[#232]: https://github.com/ekiefl/pooltool/pull/232
[#235]: https://github.com/ekiefl/pooltool/pull/235
[#236]: https://github.com/ekiefl/pooltool/pull/236
[#240]: https://github.com/ekiefl/pooltool/pull/240
[#241]: https://github.com/ekiefl/pooltool/pull/241
[#244]: https://github.com/ekiefl/pooltool/pull/244
[#247]: https://github.com/ekiefl/pooltool/pull/247
[#248]: https://github.com/ekiefl/pooltool/pull/248
[#256]: https://github.com/ekiefl/pooltool/pull/256
[#257]: https://github.com/ekiefl/pooltool/pull/257
[#259]: https://github.com/ekiefl/pooltool/pull/259
[#264]: https://github.com/ekiefl/pooltool/issues/264
[#265]: https://github.com/ekiefl/pooltool/pull/265
[#267]: https://github.com/ekiefl/pooltool/pull/267
[#268]: https://github.com/ekiefl/pooltool/pull/268
[#269]: https://github.com/ekiefl/pooltool/pull/269
[#270]: https://github.com/ekiefl/pooltool/pull/270
[#271]: https://github.com/ekiefl/pooltool/pull/271
[#274]: https://github.com/ekiefl/pooltool/pull/274
[#275]: https://github.com/ekiefl/pooltool/pull/275
[#276]: https://github.com/ekiefl/pooltool/pull/276
[ec8cc34]: https://github.com/ekiefl/pooltool/pull/277

## [0.5.0] - 2025-09-18

### Added

- Python 3.13 support (now the dev version).
- `interpolate_ball_states` to calculate exact ball states at arbitrary timestamps.
- Parallel playback mode — press *Enter* to toggle between single and parallel playback.
- On-screen instructions for held-key actions (e.g. "Select a ball to move. Click to confirm while holding 'g'.").
- Menu system built from attrs field metadata, supporting title, heading, button, entry, dropdown, and checkbox elements.
- Settings stored as YAML, isomorphically structured as attrs classes, with a lazy-loading proxy.
- `make docs-live` (live preview) and `make docs-with-notebooks` (executes notebooks rather than merely rendering them).
- Developer guide in documentation.
- Test for overlapping racks ([#203]).

### Changed

- Bumped poetry dev version from 1.8.3 to 1.8.4.
- Typing conventions updated (`List` -> `list`, `Optional[str]` -> `str | None`, etc.).
- Split `pooltool.ani.__init__` into `pooltool.ani.constants` and `pooltool.config.settings`.
- Replaced stdout progress bars and info utilities with `rich`.
- Rehauled documentation; updated API hierarchy (breaking changes).
- Fixed all broken cross-references in notebooks, markdown, and docstrings.
- Dropped jupytext — `.ipynb` files are now directly committed to the repo.
- Introduced `SceneController` for granular asset loading and unloading ([#222]).

### Removed

- Python 3.9 support.
- `terminal.py` module.

### Fixed

- Invalid quadratic roots in `ball_linear_cushion_collision_time` ([#201]).
- Structuring when history is empty ([#204]).
- Parallel playback speed controls ([#207]).
- Alciatore ball-ball friction model ([#205]).
- `FrictionalInelastic` incorrect spin for no-slip condition ([#212]).

[#201]: https://github.com/ekiefl/pooltool/pull/201
[#203]: https://github.com/ekiefl/pooltool/pull/203
[#204]: https://github.com/ekiefl/pooltool/pull/204
[#205]: https://github.com/ekiefl/pooltool/pull/205
[#207]: https://github.com/ekiefl/pooltool/pull/207
[#212]: https://github.com/ekiefl/pooltool/pull/212
[#222]: https://github.com/ekiefl/pooltool/pull/222

## [0.4.4] - 2025-03-16

### Changed

- Consolidated config options ([#189]).
- Made Mathavan ball-ball collision model the default ([#192]).
- Changed default ball-ball collision model ([#198]).
- Billiard cushion height adjustments ([#194]).

### Fixed

- Numerical stability of Mathavan model ([#192]).
- Demo mode ([#193]).
- LICENSE link in CONTRIBUTING.md ([#190]).

[#189]: https://github.com/ekiefl/pooltool/pull/189
[#190]: https://github.com/ekiefl/pooltool/pull/190
[#192]: https://github.com/ekiefl/pooltool/pull/192
[#193]: https://github.com/ekiefl/pooltool/pull/193
[#194]: https://github.com/ekiefl/pooltool/pull/194
[#198]: https://github.com/ekiefl/pooltool/pull/198

## [0.4.3] - 2025-03-12

### Added

- Simple frictional inelastic ball-ball collision model ([#155]).
- `is_point` to three cushion ruleset ([#172]).
- `get_*` convenience methods to API ([#174]).
- Mathavan 2010 ball-cushion model (WIP) ([#183]).

### Changed

- Two players by default ([#168]).
- Refactored resolver serialization and ball-ball friction sub-models ([#171]).
- Account for tip geometry to determine cue contact point ([#182]).
- Updated examples ([#175]).

### Fixed

- Ball-ball frictional inelastic no-slip velocity calculation ([#157], [#177]).
- Cuestick-ball collision issues ([#163]).
- Cue ball ID mismatch safeguard ([#164]).
- Broken example ([#165]).
- `is_point` in `ruleset.three_cushion` ([#173]).
- Cue contact point offset coordinate system mismatch between GUI and physics ([#181]).
- Near-zero case in quadratic solver ([#186]).
- Visualization of carom balls ([#169]).
- Issue #184 ([#185]).

[#155]: https://github.com/ekiefl/pooltool/pull/155
[#157]: https://github.com/ekiefl/pooltool/pull/157
[#163]: https://github.com/ekiefl/pooltool/pull/163
[#164]: https://github.com/ekiefl/pooltool/pull/164
[#165]: https://github.com/ekiefl/pooltool/pull/165
[#168]: https://github.com/ekiefl/pooltool/pull/168
[#169]: https://github.com/ekiefl/pooltool/pull/169
[#171]: https://github.com/ekiefl/pooltool/pull/171
[#172]: https://github.com/ekiefl/pooltool/pull/172
[#173]: https://github.com/ekiefl/pooltool/pull/173
[#174]: https://github.com/ekiefl/pooltool/pull/174
[#175]: https://github.com/ekiefl/pooltool/pull/175
[#177]: https://github.com/ekiefl/pooltool/pull/177
[#181]: https://github.com/ekiefl/pooltool/pull/181
[#182]: https://github.com/ekiefl/pooltool/pull/182
[#183]: https://github.com/ekiefl/pooltool/pull/183
[#185]: https://github.com/ekiefl/pooltool/pull/185
[#186]: https://github.com/ekiefl/pooltool/pull/186

## [0.4.2] - 2024-10-15

### Added

- Mathavan frictional ball-ball collision model, significantly increasing physics realism ([#153]).

[#153]: https://github.com/ekiefl/pooltool/pull/153

## [0.4.1] - 2024-09-22

### Added

- Overhauled README and documentation with an *Examples* section of rendered notebooks.
- Event caching for considerably faster simulation times ([#133]).
- Deflection angle physics (squirt) ([#139]).
- `pooltool.show` abstraction for `ShotViewer`, with automatic window management.

### Changed

- Numba functions are compiled on first entry into the interactive interface, with a translucent progress menu.
- Installation instructions simplified and clarified.

### Removed

- Test files from the package (moved to a mirroring `tests` directory).

[#133]: https://github.com/ekiefl/pooltool/pull/133
[#139]: https://github.com/ekiefl/pooltool/pull/139

## [0.4.0] - 2024-07-28

### Added

- Python 3.12 support.
- Environment management with Poetry ([#124]).
- Streamlined publishing procedure with Poetry and dynamic versioning ([#125]).

### Removed

- Python 3.8 support.

### Changed

- Development version changed to Python 3.12.

[#124]: https://github.com/ekiefl/pooltool/pull/124
[#125]: https://github.com/ekiefl/pooltool/pull/125

## [0.3.3] - 2024-07-22

### Changed

- License changed from GPL to Apache 2.0 ([#123]).

[#123]: https://github.com/ekiefl/pooltool/pull/123

## [0.3.2] - 2024-04-19

### Added

- `paper.md` and associated GitHub Action for JOSS submission ([#122]).

[#122]: https://github.com/ekiefl/pooltool/pull/122

## [0.3.1] - 2024-04-01

### Added

- CONTRIBUTING.md and CODE_OF_CONDUCT.md for pyOpenSci submission ([#121]).

[#121]: https://github.com/ekiefl/pooltool/pull/121

## [0.3.0] - 2024-03-20

### Added

- Docstrings for the core library.
- Documentation and API reference on Read the Docs.
- Continuous integration for code standards.
- API hierarchy redesign — common objects surfaced to top-level (`import pooltool as pt; pt.System`), other objects accessible via subpackage cascading (`pt.ruleset.utils.respot`) ([#120]).

### Changed

- Completed transition from mypy to pyright for type checking.
- Replaced `isort` and `black` with `ruff`.
- Camera improvements ([#108]).
- Table specs improvements ([#109]).

[#108]: https://github.com/ekiefl/pooltool/pull/108
[#109]: https://github.com/ekiefl/pooltool/pull/109
[#120]: https://github.com/ekiefl/pooltool/pull/120

## [0.2.2] - 2024-01-12

### Added

- Game modes for nine ball, eight ball, and three cushion.
- Snooker prototype.

## [0.2.1] - 2023-07-15

### Added

- Physics engine with customizable collision resolution strategies via the event resolver.
- Strategy templates providing standardized interfaces for each collision event type.
- User-configurable physics resolver settings via `resolver.yaml` in `~/.config/pooltool/`.
- Analytic quartic polynomial solving using a hybrid numerical/analytic approach (1.42x speedup).

### Changed

- Expanded `physics.py` into a multi-module `pooltool/physics/` package (ball-ball, ball-cushion, ball-pocket, etc.).
- Simulation times improved ~4x through profiling and optimization ([#81]).
- Improved handling of events occurring within a nanosecond.
- Better ball intersection handling with balls and cushions.

[#81]: https://github.com/ekiefl/pooltool/pull/81

## [0.2.0] - 2023-04-09

### Changed

- Major rewrite: 670 commits, 169 changed files, 14,444 additions, and 5,929 deletions since v0.1.

[0.6.0]: https://github.com/ekiefl/pooltool/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/ekiefl/pooltool/compare/v0.4.4...v0.5.0
[0.4.4]: https://github.com/ekiefl/pooltool/compare/v0.4.3...v0.4.4
[0.4.3]: https://github.com/ekiefl/pooltool/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/ekiefl/pooltool/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/ekiefl/pooltool/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/ekiefl/pooltool/compare/v0.3.3...v0.4.0
[0.3.3]: https://github.com/ekiefl/pooltool/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/ekiefl/pooltool/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/ekiefl/pooltool/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/ekiefl/pooltool/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/ekiefl/pooltool/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/ekiefl/pooltool/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/ekiefl/pooltool/releases/tag/v0.2.0
