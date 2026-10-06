import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # RViz only. It gets the model from /robot_description and the poses from TF, so it can run on
    # any host on the same ROS domain as the robot's robot_state_publisher. That host needs this
    # workspace installed so the package:// mesh paths resolve.
    pkg_lekiwi_bringup = get_package_share_directory('lekiwi_bringup')

    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time')
    rviz_config = LaunchConfiguration('rviz_config')
    fixed_frame = LaunchConfiguration('fixed_frame')

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true'
    )

    declare_rviz_config = DeclareLaunchArgument(
        'rviz_config',
        default_value=os.path.join(pkg_lekiwi_bringup, 'rviz', 'lekiwi.rviz'),
        description='RViz config file'
    )

    declare_fixed_frame = DeclareLaunchArgument(
        'fixed_frame',
        default_value='base_footprint',
        description='RViz fixed frame, e.g. odom, or so101_base_link for the standalone arm'
    )

    # RViz
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config, '-f', fixed_frame],
        parameters=[{
            'use_sim_time': use_sim_time,
        }]
    )

    return LaunchDescription([
        declare_use_sim_time,
        declare_rviz_config,
        declare_fixed_frame,
        rviz_node,
    ])
