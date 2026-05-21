FROM ros:jazzy

# ── System deps ────────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-colcon-common-extensions \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libgomp1 \
    ros-jazzy-cv-bridge \
    ros-jazzy-sensor-msgs \
    ros-jazzy-rclpy \
    ros-jazzy-launch-ros \
    && rm -rf /var/lib/apt/lists/*

# ── Python deps ────────────────────────────────────────────────────────────────
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --break-system-packages --no-cache-dir -r /tmp/requirements.txt

# ── Copy workspace source and build ───────────────────────────────────────────
WORKDIR /ros2_ws
COPY ros2_ws/src ./src

RUN . /opt/ros/jazzy/setup.sh && \
    colcon build --symlink-install --packages-up-to video_capture

# ── Entrypoint ────────────────────────────────────────────────────────────────
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]