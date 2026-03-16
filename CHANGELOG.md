# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-03-15

### Added

#### Ball-Cushion Collision Models

- **Impulse Frictional Inelastic model** for ball-cushion collisions ([#226]).
- **Stronge Compliant Lumped-Parameter model** for ball-cushion collisions ([#240]). Based on Stronge's tangential compliance theory (*Impact Mechanics*, Cambridge University Press, 2018)
- Configurable `omega_ratio` parameter on `StrongeCompliantLinear`/`StrongeCompliantCircular` for controlling the tangential-to-normal frequency ratio, with conversion functions `poisson_ratio_from_omega_ratio()` and `omega_ratio_from_poisson_ratio()` ([#256]).
- `get_normal_3d()` method on `LinearCushionSegment` and `CircularCushionSegment` for computing full 3D cushion normals ([#226]).
- `decompose_normal_tangent()` utility in `ptmath` for decomposing a velocity vector into signed normal/tangent components and tangent direction ([#248]).

#### Simulation Introspection

- `SimulationSnapshot` and `SimulationSnapshotSequence` classes for capturing the complete internal state at every simulation step, including system state, prospective events, caches, and the physics engine ([#232]).
- `simulate_with_snapshots()` function that runs the simulation while recording a snapshot at every step, with optional incremental JSON saving ([#232]).
- Methods on `SimulationSnapshot`: `get_prospective_events()`, `pre_evolve_system()`, `post_evolve_system()`, `post_resolve_system()` for reconstructing the system state at different points within a single step ([#232]).
- `copy()` methods on `TransitionCache` and `CollisionCache` ([#232]).
- JSON serialization support for `CollisionCache` and resolver model objects ([#232]).

#### Quartic Solver

- Algorithm 1010 quartic solver (Orellana & De Michele, ACM TOMS, 2020), a numba-compiled translation of the peer-reviewed C reference implementation ([#235]). Decomposes the quartic into two quadratics with careful coefficient estimation and Newton-Raphson refinement.
- `get_real_positive_smallest_root()` function for extracting the smallest positive real root from a single quartic's roots ([#235]).
- Per-pair on-the-fly collision time functions: `ball_ball_collision_time()`, `ball_circular_cushion_collision_time()`, `ball_pocket_collision_time()` that combine coefficient computation, quartic solving, and root extraction into single numba-jitted calls ([#235]).
- `solve_complex()` quadratic solver in `ptmath.roots` for complex-domain root finding ([#257]).
- Comprehensive quartic solver test suite with 3000 ground-truth test cases (standard, pathological, and C-reference-validated) using mpmath at 100-digit precision ([#235]).

#### Ball-Ball Collision Handling

- Event priority system via `get_event_priority()` for resolving simultaneous events: stick-ball (tier 1) > transitions/pocket (tier 2) > ball-ball/cushion (tier 3), with energy-based tiebreaking within tiers ([#257]).
- `resolve_continually_touching()` for handling Newton's-cradle-like scenarios where balls with nearly identical velocities repeatedly trigger events — transfers 10% of radial momentum from chaser to chased ball ([#257]).
- Quadratic-solver-based `make_kiss()` for ball-ball collisions that traces balls back along their velocity vectors to find the correct separation distance, replacing the old midpoint correction ([#257]).
- `Jump.ANGLE(degrees)` for arbitrary-angle ball placement in layouts, with `Translation` type alias supporting both discrete `Dir` and continuous float angles ([#257]).

#### Math Utilities

- `quaternion_from_vector_to_vector()` and `rotation_from_vector_to_vector()` for computing rotations between arbitrary 3D vectors ([#226]).
- `squared_norm3d()` and `squared_norm2d()` numba-jitted squared norm functions ([#226]).
- 3D `angle_between_vectors()` returning radians in [0, pi], replacing the old 2D version that returned degrees ([#226]).

#### Validation

- Positive-value validation on `BallParams` friction coefficients (`u_s`, `u_r`, `u_sp_proportionality`, `u_b`, `f_c`), preventing infinite event prediction loops from zero/negative friction ([#265], fixes [#264]).

#### Documentation

- Complete overhaul of API reference appearance with custom Sphinx extensions ([#276]):
  - `restructure_class_layout.py`: inlines attribute types, restructures class sections with rubric headings, restyles parameter fields.
  - `clean_enum_signature.py`: strips constructor arguments from enum signatures.
  - `fix_dataclass_defaults.py`: replaces `<factory>` placeholders with actual factory names.
  - `resolve_missing_references.py`: handles CPython internal paths, intersphinx mismatches, and re-exported objects.
- New CSS for headings, rubric sections, parameter styling, TOC, and notebook galleries ([#276]).

#### CI/CD

- Codecov push-event uploads on main branch for base coverage tracking ([#268]).
- `service-no-ani` Codecov flag that excludes `pooltool/ani/` from coverage metrics, with separate per-flag uploads ([#269], [#270]).

### Changed

- **Stronge Compliant is now the default ball-cushion model**, replacing Mathavan 2010. Default `omega_ratio` is 1.8. Resolver `VERSION` bumped from 8 to 9 ([#256]).
- **Replaced Poetry with uv** as the package manager, build system, and task runner ([#275]). Migrated to PEP 621 standard `[project]` metadata in `pyproject.toml`, replaced `poetry-dynamic-versioning` with static versioning via `importlib.metadata`, split the monolithic lint-and-check CI workflow into separate lint and typecheck workflows, updated all CI workflows and documentation.
- Simulation loop refactored into `_SimulationState` class with explicit `init()`, `step()`, and `update_caches()` methods, enabling external observation of simulation internals ([#232]).
- Stick-ball collisions promoted from special-cased pre-loop handling to first-class events detected inside `get_next_event()` at t=0 ([#232]).
- `evolve_ball_motion()` now always returns a freshly-copied array, preventing shared-reference corruption when resolvers modify arrays in-place ([#232]).
- `get_normal()` on cushion segments renamed to `get_normal_xy()` to clarify it returns a 2D normal with zeroed z-component ([#226]).
- `get_normal_xy()` parameter changed from `rvw` (full kinematic state matrix) to `xyz` (position vector) ([#248]).
- Normal-flipping logic moved from inside `han2005()` to its caller `_solve()` ([#248]).
- Overlapping balls now return the current simulation time as their collision time instead of `np.inf`, triggering immediate resolution rather than silent ignoring ([#257]).
- Ball-cushion `make_kiss()` rewritten to trace balls along their velocity vectors (solving linear/quadratic equations for correct separation) instead of displacing along the geometric normal, with fallback for non-translating balls and grazing angles exceeding 5x spacer displacement ([#271]).
- `MIN_DIST` constant (1e-6) replaces `EPS_SPACE` (1e-9) as the default spacer ([#257], [#271]).
- Quartic solver `d2` factorization threshold loosened by a safety factor of 100x `macheps` to handle edge cases like Newton's cradle ([#257]).
- Numba quartic solver optimized by replacing all numpy array allocations with scalar variables — throughput improved from ~200ms/100k quartics to 2.8 million quartics/second ([#236]).
- Removed the `quartic_solver` parameter from `simulate()`, `simulate_with_snapshots()`, and `get_next_event()` — Algorithm 1010 is now the only implementation ([#235]).
- Eliminated batch-solve-then-extract pattern: collision times are computed on-the-fly per object pair instead of collecting coefficients into arrays ([#235]).
- `System.get_system_energy()` replaced with `_system_has_energy()` that returns a boolean and short-circuits on the first energetic ball ([#232]).
- Four internal evolve functions privatized: `evolve_slide_state`, `evolve_roll_state`, `evolve_perpendicular_spin_component`, `evolve_perpendicular_spin_state` ([#232]).
- `CushionSegment` union type alias removed in favor of `Cushion` TypeVar centralized in `components.py` ([#226]).
- `enforce_rules` setting from user config now applied when creating game rulesets in interactive mode ([#241]).
- PBR table model loading falls back to non-PBR `.glb` when the `_pbr.glb` file does not exist, instead of raising `ConfigError` ([#244]).
- `fail_fast: true` added to pre-commit configuration ([#255]).
- CodeRabbit auto-review disabled ([#227]).
- `CachedPropertyDirective` removed from documentation; `cached_property_note` directives stripped from all docstrings ([#230]).
- API reference restructured: removed summary table overview sections, module template simplified, class pages no longer show constructor args in autoapi template ([#276]).
- Read the Docs config updated to Ubuntu 24.04, Python 3.13, uv-based install ([#275]).

### Fixed

- **Memory leaks** when calling `show()` repeatedly ([#274], fixes [#219]):
  - simplepbr `FilterManager` buffers and update tasks now cleaned up in `ShotViewer._stop()`.
  - Ambient light `NodePath` now stored and properly removed via `removeNode()` during environment unload.
  - All HUD element `destroy()` methods changed from `hide()` + `del` (which left orphaned nodes in `aspect2d`/`render2d`) to `removeNode()` (~130 KB/iteration, 20 nodes/cycle leaked previously).
- **Han 2005 ball-cushion model** had multiple bugs ([#247]):
  - Missing friction coefficient `mu` in slip/stick impulse threshold comparison (`PzS <= PzE` changed to `PzS <= mu * PzE`).
  - Incorrect sign convention for `c` and `PzE` (signs now match the paper's equations).
  - Impulse computation separated into contact normal coordinates first (Eqs 18-19), then transformed to rail coordinates (Eqs 21-22), replacing the previous coupled expressions.
  - `HAN_2005` re-enabled in the energy conservation test.
- **Straight shot example** geometry error: `pocket.radius * np.sqrt(2)` corrected to `pocket.radius / np.sqrt(2)` for computing pocket points along the 45-degree diagonal ([#259]).
- **Scene node leak** causing old and new tables to overlap when starting a new game — `close_scene()` now removes the scene node itself from the render tree, not just its children ([#267], fixes [#229]).
- **Single-ball system crash** in `get_next_ball_ball_collision()` when the collision cache is empty ([#271]).
- **Read the Docs build failure** from astroid 4.x incompatibility with sphinx-autoapi — pinned `astroid==3.3.11` ([ec8cc34]).

### Dependencies

- Added `numpy-quaternion>=2024.0.12` ([#226]).
- Added `llvmlite<0.46` upper bound ([#275]).
- Added `rich>=14.0.0,<15.0.0` explicit range ([#275]).
- Bumped `starlette` from 0.47.3 to 0.49.1 ([#233]).
- Bumped `filelock` to 3.20.1, `fonttools` to 4.61.1 ([#246]).
- Pinned `astroid==3.3.11` in docs dependencies ([ec8cc34]).
- Removed `poetry-dynamic-versioning` build plugin ([#275]).
- Replaced `poetry-core` build backend with `uv_build` ([#275]).

[#219]: https://github.com/ekiefl/pooltool/issues/219
[#226]: https://github.com/ekiefl/pooltool/pull/226
[#227]: https://github.com/ekiefl/pooltool/pull/227
[#229]: https://github.com/ekiefl/pooltool/issues/229
[#230]: https://github.com/ekiefl/pooltool/pull/230
[#232]: https://github.com/ekiefl/pooltool/pull/232
[#233]: https://github.com/ekiefl/pooltool/pull/233
[#235]: https://github.com/ekiefl/pooltool/pull/235
[#236]: https://github.com/ekiefl/pooltool/pull/236
[#240]: https://github.com/ekiefl/pooltool/pull/240
[#241]: https://github.com/ekiefl/pooltool/pull/241
[#244]: https://github.com/ekiefl/pooltool/pull/244
[#246]: https://github.com/ekiefl/pooltool/pull/246
[#247]: https://github.com/ekiefl/pooltool/pull/247
[#248]: https://github.com/ekiefl/pooltool/pull/248
[#255]: https://github.com/ekiefl/pooltool/pull/255
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
