"""Launch file for the video_capture node."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    # ── Launch arguments (mirrors every ROS 2 parameter) ──────────────────────
    args = [
        DeclareLaunchArgument('camera_topic',      default_value='/camera/image_raw'),
        DeclareLaunchArgument('camera_info_topic', default_value='/camera/camera_info'),
        DeclareLaunchArgument('camera_info_file',  default_value='/dataset/camera_info.yml'),
        DeclareLaunchArgument('images_dir',        default_value='/dataset'),
        DeclareLaunchArgument('image_pattern',     default_value='*.png'),
        DeclareLaunchArgument('fps',               default_value='30.0'),
        DeclareLaunchArgument('resize_factor',     default_value='1.0'),
    ]

    def s(name):
        """Wrap a LaunchConfiguration as an explicit string ParameterValue."""
        return ParameterValue(LaunchConfiguration(name), value_type=str)

    node = Node(
        package='video_capture',
        executable='video_capture_node',
        name='video_capture_node',
        output='screen',
        parameters=[{
            'camera_topic':      s('camera_topic'),
            'camera_info_topic': s('camera_info_topic'),
            'camera_info_file':  s('camera_info_file'),
            'images_dir':        s('images_dir'),
            'image_pattern':     s('image_pattern'),
            'fps':               ParameterValue(LaunchConfiguration('fps'),           value_type=float),
            'resize_factor':     ParameterValue(LaunchConfiguration('resize_factor'), value_type=float),
        }],
    )

    return LaunchDescription(args + [node])
