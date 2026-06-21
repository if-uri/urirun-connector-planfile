# Changelog

## [Unreleased]

### Changed
- Reuse the urirun host backend (`urirun.host.planfile_adapter`) instead of a bundled copy of
  the logic; the connector now owns only the URI routes and JSON envelope.
  urirun is the single source of truth. Routes/manifest/CLI unchanged.

### Added
- Add follow-up tasks for IFURI-016 matrix coverage and richer Planfile route
  documentation.
- Expose `urirun_bindings()` through the `urirun.bindings` entry-point group
  and document `urirun discover` / `urirun list --entry-points`.

### Changed
- Link README related projects to the `if-uri/urirun` runtime repository.
- Mark the connector hub detail page as published.
- Update tests to call the explicit `urirun.v2` runtime API.

## [0.1.1] - 2026-06-20

### Changed
- Point the `urirun` dependency at the `if-uri/urirun` repository.
- Pin README and manifest install examples to the published `v0.1.1` tag.

## [0.1.0] - 2026-06-20

### Added
- Add initial Planfile connector with decorated URI bindings, CLI, tests and
  Docker smoke coverage.
