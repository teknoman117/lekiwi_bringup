import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

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

    if enabled(context, 'joy_teleop'):
        try:
            get_package_share_directory('lekiwi_teleop')
        except PackageNotFoundError as e:
            raise RuntimeError(
                'joy_teleop:=true needs lekiwi_teleop; build it, or pass joy_teleop:=false') from e
        actions.append(Node(
            package='lekiwi_teleop',
            executable='joy_teleop',
            name='joy_teleop',
            output='screen',
        ))
    return actions


def generate_launch_description():
    # Everything that runs on the robot: the ros2_control stack, move_group (planning, IK,
    # collision checking, execution), the RViz marker follower and the joystick teleop. RViz and,
    # by default, the joystick driver run on the workstation:
    #   ros2 launch lekiwi_bringup workstation.launch.py
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

    declare_joy_teleop = DeclareLaunchArgument(
        'joy_teleop',
        default_value='true',
        description='Start joy_teleop (lekiwi_teleop): /joy to the base and the arm. The joystick '
                    'driver (joy_node) can run here (joy:=true) or on the workstation '
                    '(workstation.launch.py)'
    )

    declare_joy = DeclareLaunchArgument(
        'joy',
        default_value='false',
        description='Start joy_node here, for a joystick plugged into the robot'
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
        declare_joy_teleop,
        declare_joy,
        declare_joy_device,
        declare_joy_deadzone,
        hardware,
        joy_node,
        OpaqueFunction(function=optional_parts),
    ])
