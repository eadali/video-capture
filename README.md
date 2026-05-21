# video_capture_node

A ROS 2 node that publishes a sequence of images from a folder as a camera stream, paired with synchronized `CameraInfo` on every frame. Designed to replay dataset images as if they were coming from a live camera.

---

## Overview

```
images_dir/
  ├── 0001.png
  ├── 0002.png
  └── ...
        │
        ▼
VideoCaptureNode
  ├── /camera/image_raw     (sensor_msgs/Image)
  └── /camera/camera_info  (sensor_msgs/CameraInfo)
        │
        ▼  (same header.stamp on both)
CameraSubscriberNode
  └── callback(image, camera_info)
```

All images are preloaded into memory at startup. On each timer tick, the node stamps both the image and the camera info with the **same timestamp**, ensuring a downstream `ApproximateTimeSynchronizer` can match them without dropped pairs.

---

## Dependencies

| Package | Purpose |
|---|---|
| `rclpy` | ROS 2 Python client |
| `sensor_msgs` | `Image`, `CameraInfo` message types |
| `cv_bridge` | OpenCV ↔ ROS image conversion |
| `opencv-python` | Image loading and resizing |
| `PyYAML` | Camera calibration file parsing |
| `message_filters` | Timestamp synchronization (subscriber side) |

Install Python dependencies:

```bash
pip install opencv-python pyyaml
```

ROS dependencies are available in any standard ROS 2 desktop installation.

---

## Camera calibration file

The node expects a YAML file in the ROS camera calibration format produced by `camera_calibration` or `kalibr`. Example structure:

```yaml
image_width: 1280
image_height: 720
camera_name: camera
camera_matrix:
  rows: 3
  cols: 3
  data: [fx, 0, cx, 0, fy, cy, 0, 0, 1]
distortion_model: plumb_bob
distortion_coefficients:
  rows: 1
  cols: 5
  data: [k1, k2, p1, p2, k3]
rectification_matrix:
  rows: 3
  cols: 3
  data: [1, 0, 0, 0, 1, 0, 0, 0, 1]
projection_matrix:
  rows: 3
  cols: 4
  data: [fx, 0, cx, 0, 0, fy, cy, 0, 0, 0, 1, 0]
```

---

## Parameters

### Publisher — `video_capture_node`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `camera_topic` | string | `/camera/image_raw` | Topic to publish images on |
| `camera_info_topic` | string | `/camera/camera_info` | Topic to publish camera info on |
| `camera_info_file` | string | `/dataset/camera_info.yml` | Path to the YAML calibration file |
| `images_dir` | string | `/dataset` | Directory containing the image sequence |
| `image_pattern` | string | `*.png` | Glob pattern to match images in `images_dir` |
| `fps` | double | `30.0` | Playback rate in frames per second |
| `resize_factor` | double | `1.0` | Scale factor applied to images and intrinsics. Must be in `(0, 1]` |

### Subscriber — `camera_subscriber_node`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `camera_topic` | string | `/camera/image_raw` | Image topic to subscribe to |
| `camera_info_topic` | string | `/camera/camera_info` | Camera info topic to subscribe to |
| `queue_size` | int | `10` | Buffer depth per topic for the synchronizer |
| `slop` | double | `0.05` | Maximum allowed timestamp difference in seconds |

---

## Usage

### Run the publisher

```bash
ros2 run <your_package> video_capture_node \
  --ros-args \
  -p images_dir:=/path/to/images \
  -p camera_info_file:=/path/to/camera_info.yml \
  -p fps:=30.0 \
  -p resize_factor:=0.5
```

### Run the subscriber

```bash
ros2 run <your_package> camera_subscriber_node \
  --ros-args \
  -p slop:=0.01
```

Since the publisher stamps both messages identically, `slop` can be set very tight (e.g. `0.01`) or you can switch to `ExactTimeSynchronizer` in the subscriber for zero-tolerance matching.

### Verify topics

```bash
ros2 topic list
ros2 topic hz /camera/image_raw
ros2 topic echo /camera/camera_info --once
```

---

## Resize behaviour

When `resize_factor` is set to a value less than `1.0`, the node scales both the images and the camera intrinsics consistently:

| Field | Behaviour |
|---|---|
| `width`, `height` | Multiplied by `resize_factor` |
| `K` — `fx`, `fy`, `cx`, `cy` | Multiplied by `resize_factor` |
| `P` — first two rows | Multiplied by `resize_factor` |
| `D` — distortion coefficients | Unchanged (unit-less) |
| `R` — rectification matrix | Unchanged (pure rotation) |

This ensures the published `CameraInfo` always matches the actual resolution of the published images.

---

## Architecture notes

- Images are loaded and converted to ROS messages **once** at startup, minimising per-frame CPU work.
- `CameraInfo` is loaded once and **re-stamped** on every tick — no file I/O at runtime.
- Both messages receive the **same `header.stamp`** from a single `get_clock().now()` call per tick, guaranteeing the subscriber's `ApproximateTimeSynchronizer` pairs them correctly.
- The publisher stops automatically after all frames have been sent and cancels its timer.

---

## Troubleshooting

**No images found** — check that `images_dir` and `image_pattern` match your files:
```bash
ls /path/to/images/*.png
```

**Subscriber callback never fires** — verify both topics are publishing and check `slop`. With identical timestamps, `slop=0.01` is sufficient:
```bash
ros2 topic hz /camera/image_raw
ros2 topic hz /camera/camera_info
```

**Wrong image size after resize** — `resize_factor` must be in `(0, 1]`. Values outside this range are clamped with a warning.

**Camera info fields look wrong** — confirm your YAML follows the ROS calibration format. The `camera_matrix.data` field must be a flat 9-element list in row-major order.