import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory


def enabled(context, name):
    return LaunchConfiguration(name).perform(context).strip().lower() in ('true', '1')


def optional_parts(context):
    # move_group and the marker follower. Their packages are looked up only when enabled:
    # lekiwi_moveit_config depends on this package for the URDF, so this package cannot declare
    # a dependency back on it, and with moveit:=false the robot does not need MoveIt installed.
    actions = []
    if enabled(context, 'moveit'):
        try:
            pkg_lekiwi_moveit_config = get_package_share_directory('lekiwi_moveit_config')
        except PackageNotFoundError as e:
            raise RuntimeError(
                'moveit:=true needs lekiwi_moveit_config; build it, or pass moveit:=false') from e
        actions.append(IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_lekiwi_moveit_config, 'launch', 'move_group.launch.py')),
        ))

    if enabled(context, 'arm_marker'):
        if not enabled(context, 'moveit'):
            raise RuntimeError('arm_marker:=true needs move_group (moveit:=true)')
        try:
            get_package_share_directory('lekiwi_teleop')
        except PackageNotFoundError as e:
            raise RuntimeError(
                'arm_marker:=true needs lekiwi_teleop; build it, or pass arm_marker:=false') from e
        actions.append(Node(
            package='lekiwi_teleop',
            executable='arm_marker',
            name='arm_marker',
            output='screen',
            parameters=[{
                'mode': LaunchConfiguration('marker_mode').perform(context),
                'max_linear_speed': float(LaunchConfiguration('marker_speed').perform(context)),
            }],
        ))
    return actions


def generate_launch_description():
    # Everything that runs on the robot: the ros2_control stack, move_group (planning, IK,
    # collision checking, execution) and the RViz marker follower. Only RViz runs elsewhere:
    #   ros2 launch lekiwi_moveit_config moveit_rviz.launch.py
    pkg_lekiwi_bringup = get_package_share_directory('lekiwi_bringup')

    declare_port = DeclareLaunchArgument(
        'port',
        default_value='/dev/ttyACM0',
        description='Serial port of the servo bus'
    )

    declare_use_mock_hardware = DeclareLaunchArgument(
        'use_mock_hardware',
        default_value='false',
        description='Use mock_components/GenericSystem instead of the real servos'
    )

    declare_limp = DeclareLaunchArgument(
        'limp',
        default_value='false',
        description='Leave the hardware inactive (torque never switched on) and start only '
                    'joint_state_broadcaster; nothing can move the arm'
    )

    declare_moveit = DeclareLaunchArgument(
        'moveit',
        default_value='true',
        description='Start move_group (lekiwi_moveit_config)'
    )

    declare_arm_marker = DeclareLaunchArgument(
        'arm_marker',
        default_value='true',
        description='Start the RViz marker follower (lekiwi_teleop arm_marker); needs moveit'
    )

    declare_marker_mode = DeclareLaunchArgument(
        'marker_mode',
        default_value='free',
        choices=['free', 'claw', 'planar'],
        description='Initial mode of the marker follower (also in its right-click menu)'
    )

    declare_marker_speed = DeclareLaunchArgument(
        'marker_speed',
        default_value='0.08',
        description='Maximum gripper speed when following the marker [m/s]'
    )

    # Hardware, robot_state_publisher and controllers
    hardware = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_lekiwi_bringup, 'launch', 'hardware_control.launch.py')),
        launch_arguments={
            'port': LaunchConfiguration('port'),
            'use_mock_hardware': LaunchConfiguration('use_mock_hardware'),
            'limp': LaunchConfiguration('limp'),
            'rviz': 'false',
        }.items(),
    )

    return LaunchDescription([
        declare_port,
        declare_use_mock_hardware,
        declare_limp,
        declare_moveit,
        declare_arm_marker,
        declare_marker_mode,
        declare_marker_speed,
        hardware,
        OpaqueFunction(function=optional_parts),
    ])
