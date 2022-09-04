# WIP: Drone Copilot

## Features

- [x] Cross-platform: mobile for accessibility (Android, iOS) and desktop for performance (Linux, Windows, MacOS).
- [x] Live video and status of the drone (and high-resolution pictures).
- [x] Manual control of the drone on all platforms (UI joysticks / keyboard / gamepad).
- [x] A common drone interface to provide most features for multiple drones:
    - [x] [DJI Tello](https://m.dji.com/es/product/tello): a cheap and fun drone that is stable and has a camera.
    - [x] Test: a fully-featured virtual drone that flies in a 3D environment for development and testing.
    - [x] Add support for your drone simply by implementing [the core API](src/drone/api).
- [ ] Autopilot [...].
- [ ] Simultaneous Localization And Mapping (SLAM) [...].

## Building

See [release.yml](.github/workflows/release.yml), which automatically builds releases for most platforms.
