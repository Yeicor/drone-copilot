# WIP: Drone Copilot

## Features

- [x] Cross-platform: mobile (Android, iOS<sup>1</sup>) and desktop (Linux, Windows<sup>1</sup>, MacOS<sup>1</sup>).
- [x] Live video and status of the drone (and high-resolution pictures).
- [x] Manual control of the drone on all platforms (UI joysticks / keyboard / gamepad).
- [x] A common drone interface to provide most features for all drones:
    - [x] [DJI Tello](https://m.dji.com/es/product/tello): a cheap and fun drone that is stable and has a camera.
    - [x] Test: a fully-featured virtual drone that flies in a 3D environment for development and testing.
    - [x] Add support for your drone simply by implementing [the core API](src/drone/api).
- [x] Object tracking and following:
    - [x] Real time detection of lots of objects (people, vehicles, animals, etc.) on each frame.
        - [x] Different trained models balancing speed and accuracy:
          [EfficientDet-Lite\[0-4\]](https://tfhub.dev/tensorflow/lite-model/efficientdet/lite0/detection/metadata/1),
          [YoloV5](https://tfhub.dev/neso613/lite-model/yolo-v5-tflite/tflite_model/1)...
    - [x] Tracking over multiple frames: simple scoring system based on distance and intersection over union.
    - [ ] Select the object to track by clicking on its detection box.
    - [ ] Make the drone automatically follow tracked objects with customizable constraints.
- [ ] Simultaneous Localization And Mapping (SLAM):
    - [ ] Monocular depth estimation and visualization.
    - [ ] [...]

<sup>1</sup> These platforms are not tested, minor modifications may be required (help is appreciated).

## Building

See [release.yml](.github/workflows/release.yml), which automatically builds releases for most platforms.

## Demos

### v0.6.0

![screenshot.png](docs/screenshot.png)
