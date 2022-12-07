# WIP: Drone Copilot

## Features

- [x] Cross-platform: mobile for accessibility (Android, iOS<sup>1</sup>) and desktop for performance (Linux,
  Windows<sup>1</sup>, MacOS<sup>1</sup>).
- [x] Live video and status of the drone (and high-resolution pictures).
- [x] Manual control of the drone on all platforms (UI joysticks / keyboard / gamepad).
- [x] A common drone interface to provide most features for multiple drones:
    - [x] [DJI Tello](https://m.dji.com/es/product/tello): a cheap and fun drone that is stable and has a camera.
    - [x] Test: a fully-featured virtual drone that flies in a 3D environment for development and testing.
    - [x] Add support for your drone simply by implementing [the core API](src/drone/api).
- [x] EfficientDet-Lite0 for realtime detection of 90 categories of objects in the drone's camera.
- [ ] Object selection and tracking over multiple frames.
- [ ] Follow tracked objects with different constraints.
- [ ] Depth estimation and visualization for the drone's camera.
- [ ] Simultaneous Localization And Mapping (SLAM).

<sup>1</sup> Not tested, minor modifications may be required (help is appreciated).

## Building

See [release.yml](.github/workflows/release.yml), which automatically builds releases for most platforms.

## Demos

### v0.5.3

![android_v0.5.3.png](docs/android_v0.5.3.png)
