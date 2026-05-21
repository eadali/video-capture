#!/usr/bin/env python3
"""
ROS 2 Node for Publishing Camera Images from Files (preloaded into memory).

Architecture:
  - Publishes sensor_msgs/Image      on /camera/image_raw
  - Publishes sensor_msgs/CameraInfo on /camera/camera_info
  - Both messages share the same header.stamp every timer tick,
    so a message_filters.ApproximateTimeSynchronizer on the
    subscriber side receives them as a matched pair.
"""

import glob
import os
import yaml

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image


class VideoCaptureNode(Node):
    def __init__(self):
        super().__init__("video_capture_node")

        # ── Parameters ────────────────────────────────────────────────────────
        self.declare_parameter("camera_info_topic", "/camera/camera_info")
        self.declare_parameter("camera_topic", "/camera/image_raw")
        self.declare_parameter("camera_info_file", "/dataset/camera_info.yml")
        self.declare_parameter("images_dir", "/dataset")
        self.declare_parameter("image_pattern", "*.png")
        self.declare_parameter("fps", 30.0)
        self.declare_parameter("resize_factor", 1.0)

        camera_info_topic = (
            self.get_parameter("camera_info_topic").get_parameter_value().string_value
        )
        camera_topic = (
            self.get_parameter("camera_topic").get_parameter_value().string_value
        )
        camera_info_file = (
            self.get_parameter("camera_info_file").get_parameter_value().string_value
        )
        images_dir = self.get_parameter("images_dir").get_parameter_value().string_value
        pattern = self.get_parameter("image_pattern").get_parameter_value().string_value
        fps = self.get_parameter("fps").get_parameter_value().double_value
        resize_factor = (
            self.get_parameter("resize_factor").get_parameter_value().double_value
        )

        if not (0.0 < resize_factor <= 1.0):
            self.get_logger().warn(
                f"resize_factor {resize_factor} outside (0, 1]. Clamping."
            )
            resize_factor = max(1e-3, min(1.0, resize_factor))
        self.resize_factor = resize_factor

        if self.resize_factor != 1.0:
            self.get_logger().info(f"Resize factor: {self.resize_factor}")

        # ── Camera info (loaded once, re-stamped every frame) ─────────────────
        self.camera_info_msg = self._load_camera_info(camera_info_file, resize_factor)

        # ── Preload frames ────────────────────────────────────────────────────
        search = os.path.join(images_dir, pattern)
        image_paths = sorted(glob.glob(search))
        if not image_paths:
            raise RuntimeError(f"No images found matching: {search}")

        self.get_logger().info(f"Preloading {len(image_paths)} image(s)...")
        bridge = CvBridge()
        self.frames = []

        for path in image_paths:
            frame = cv2.imread(path)
            if frame is None:
                self.get_logger().warn(f"Skipping unreadable image: {path}")
                continue
            if self.resize_factor != 1.0:
                new_w = int(frame.shape[1] * self.resize_factor)
                new_h = int(frame.shape[0] * self.resize_factor)
                frame = cv2.resize(
                    frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR
                )
            ros_img = bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            ros_img.header.frame_id = "camera"
            self.frames.append(ros_img)

        if not self.frames:
            raise RuntimeError("No valid images could be loaded.")

        self.get_logger().info(f"Preloaded {len(self.frames)} frame(s).")
        if self.resize_factor != 1.0:
            s = self.frames[0]
            self.get_logger().info(f"Frame size after resize: {s.width}x{s.height}")

        self.frame_index = 0

        # ── Publishers & timer ────────────────────────────────────────────────
        self.pub_image = self.create_publisher(Image, camera_topic, 10)
        self.pub_camera_info = self.create_publisher(CameraInfo, camera_info_topic, 10)
        self.timer = self.create_timer(1.0 / fps, self._timer_cb)

        self.get_logger().info(f"Publishing {camera_info_topic} @ {fps} FPS (synced)")
        self.get_logger().info(f"Publishing {camera_topic} @ {fps} FPS (synced)")

    # ── Timer callback ────────────────────────────────────────────────────────

    def _timer_cb(self) -> None:
        if self.frame_index >= len(self.frames):
            self.get_logger().info("All frames published. Stopping.")
            self.timer.cancel()
            return

        # Single timestamp shared by both messages — guarantees sync
        now = self.get_clock().now().to_msg()

        # Image
        ros_img = self.frames[self.frame_index]
        ros_img.header.stamp = now

        # CameraInfo — same stamp, same frame_id
        self.camera_info_msg.header.stamp = now
        self.camera_info_msg.header.frame_id = "camera"

        try:
            self.pub_image.publish(ros_img)
            self.pub_camera_info.publish(self.camera_info_msg)
            self.get_logger().debug(f"Published frame {self.frame_index}")
        except Exception as e:
            self.get_logger().error(f"Publish error: {e}")

        self.frame_index += 1

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_camera_info(self, path: str, resize_factor: float) -> CameraInfo:
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load camera info from {path}: {e}")

        msg = CameraInfo()
        sf = resize_factor

        original_height = data["height"]
        original_width = data["width"]

        if sf != 1.0:
            msg.width = int(original_width * sf)
            msg.height = int(original_height * sf)
            original_k = data["k"]
            msg.k = [
                original_k[0] * sf,
                original_k[1] * sf,
                original_k[2] * sf,
                original_k[3] * sf,
                original_k[4] * sf,
                original_k[5] * sf,
                original_k[6],
                original_k[7],
                original_k[8],
            ]

            original_p = data["p"]
            scaled_p = [p * sf if i < 6 else p for i, p in enumerate(original_p)]
            scaled_p[10] = original_p[10]
            msg.p = scaled_p
        else:
            msg.width = original_width
            msg.height = original_height
            msg.k = data["k"]
            msg.p = data["p"]

        msg.d = data["d"]
        msg.r = data["r"]

        return msg


def main(args=None):
    rclpy.init(args=args)
    node = VideoCaptureNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
