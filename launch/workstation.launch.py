import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory


def rviz(context):
    # Looked up at launch: lekiwi_moveit_config depends on this package (see robot.launch.py).
    if LaunchConfiguration('rviz').perform(context).strip().lower() not in ('true', '1'):
        return []
    try:
        pkg_lekiwi_moveit_config = get_package_share_directory('lekiwi_moveit_config')
    except PackageNotFoundError as e:
        raise RuntimeError('rviz:=true needs lekiwi_moveit_config; build it') from e
    return [IncludeLaunchDescription(PythonLaunchDescriptionSource(
        os.path.join(pkg_lekiwi_moveit_config, 'launch', 'moveit_rviz.launch.py')))]


def generate_launch_description():
    # The workstation side of the robot / workstation split: RViz (with the MotionPlanning panel
    # and the arm marker) and the joystick driver. Everything else runs on the robot
    # (robot.launch.py), on the same ROS_DOMAIN_ID.
    declare_rviz = DeclareLaunchArgument(
        'rviz', default_value='true', description='Start RViz (lekiwi_moveit_config)')

    declare_joy = DeclareLaunchArgument(
        'joy',
        default_value='true',
        description='Start joy_node here, for a joystick plugged into the workstation '
                    '(joy_teleop runs on the robot)'
    )

    declare_joy_device = DeclareLaunchArgument(
        'joy_device', default_value='0', description='joy_node device_id')

    declare_joy_deadzone = DeclareLaunchArgument(
        'joy_deadzone', default_value='0.166', description='joy_node deadzone')

    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node',
        parameters=[{
            'device_id': ParameterValue(LaunchConfiguration('joy_device'), value_type=int),
            'deadzone': ParameterValue(LaunchConfiguration('joy_deadzone'), value_type=float),
        }],
        condition=IfCondition(LaunchConfiguration('joy')),
    )

    return LaunchDescription([
        declare_rviz,
        declare_joy,
        declare_joy_device,
        declare_joy_deadzone,
        joy_node,
        OpaqueFunction(function=rviz),
    ])
