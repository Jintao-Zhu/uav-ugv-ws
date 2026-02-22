from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'coop_bridge'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    scripts=['scripts/coop_bridge_node'],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='anders',
    maintainer_email='2327406014@stu.suda.edu.cn',
    description='UAV-UGV cooperation bridge for ag_coop Gazebo integration',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'coop_bridge_node = coop_bridge.coop_bridge_node:main',
            'map_publisher = coop_bridge.map_publisher:main',
            'static_tf_publisher = coop_bridge.static_tf_publisher:main',
        ],
    },
)
