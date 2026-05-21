from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'video_capture'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description='ROS 2 node for streaming image directories as sensor_msgs/Image topics.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'video_capture_node = video_capture.video_capture_node:main',
        ],
    },
)
