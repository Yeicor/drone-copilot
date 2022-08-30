# WIP: Drone Copilot

An application to control a [DJI Tello](https://www.ryzerobotics.com/tello) drone (and others in the future).

## Features

- [x] Cross-platform: mobile for accessibility (Android, iOS) and desktop for performance (Windows, MacOS, Linux).
- [x] Live video and status of the drone (and high-resolution pictures).
- [x] Manual control of the drone on all platforms (UI joysticks / keyboard / gamepad).
- [ ] Autopilot [...].
- [x] Extensible:
    - [x] A generic [Drone API](src/drone/api/drone.py) makes it easy to add support for most drones.
    - [ ] Custom autopilot algorithms.
- [ ] ...

## Building

See the [BUILD.md](BUILD.md) file.