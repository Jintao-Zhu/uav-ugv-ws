import os
from glob import glob
from setuptools import setup

package_name = 'uav_ugv_bringup'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        
        # ---------------------------------------------------------
        # 【关键修改】添加这一段，安装 launch 文件
        # 意思是：把 launch 目录下的所有 .py 文件，拷贝到安装目录的 share/包名/launch 下
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*launch.py'))),
        # ---------------------------------------------------------
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='anders',
    maintainer_email='anders@todo.todo',
    description='UAV and UGV coordination bringup package',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'circle_demo = uav_ugv_bringup.circle_demo:main',
        ],
    },
)