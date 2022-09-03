# WIP: Drone Copilot

## Features

- [x] Cross-platform: mobile for accessibility (Android, iOS) and desktop for performance (Linux, Windows, MacOS).
- [x] Live video and status of the drone (and high-resolution pictures).
- [x] Manual control of the drone on all platforms (UI joysticks / keyboard / gamepad).
- [x] A fully-featured test environment with a virtual drone for development and testing.
- [ ] Autopilot [...].
- [ ] Simultaneous localization and mapping (SLAM).
- [x] Extensible:
    - [x] A generic [Drone API](src/drone/api/drone.py) makes it easy to add support for most drones.
    - [ ] Custom autopilot algorithms.
- [ ] ...

## Building

See [release.yml](.github/workflows/release.yml), which automatically builds releases for most platforms.
