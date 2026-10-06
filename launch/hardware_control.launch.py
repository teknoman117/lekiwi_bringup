import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, IncludeLaunchDescription, RegisterEventHandler
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # Get package directories
    pkg_lekiwi_bringup = get_package_share_directory('lekiwi_bringup')
    pkg_lekiwi_description = get_package_share_directory('lekiwi_description')
    pkg_so101_description = get_package_share_directory('so101_description')

    # Paths to files. The base and arm controller configs are merged key by key.
    urdf_file = os.path.join(pkg_lekiwi_bringup, 'urdf', 'lekiwi.urdf.xacro')
    controller_configs = [
        os.path.join(pkg_lekiwi_description, 'config', 'omni_controllers.yaml'),
        os.path.join(pkg_so101_description, 'config', 'so101_controllers.yaml'),
    ]

    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time')
    port = LaunchConfiguration('port')
    use_mock_hardware = LaunchConfiguration('use_mock_hardware')
    limp = LaunchConfiguration('limp')

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true'
    )

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

    declare_rviz = DeclareLaunchArgument(
        'rviz',
        default_value='false',
        description='Also start RViz on this host'
    )

    declare_limp = DeclareLaunchArgument(
        'limp',
        default_value='false',
        description='Leave the hardware inactive so torque is never switched on: the joints are '
                    'read and published, but only joint_state_broadcaster is started'
    )

    # Process the URDF
    robot_description_content = ParameterValue(
        Command([
            FindExecutable(name='xacro'), ' ',
            urdf_file,
            ' port:=', port,
            ' use_mock_hardware:=', use_mock_hardware,
        ]),
        value_type=str
    )

    # Robot State Publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_content,
            'use_sim_time': use_sim_time,
        }]
    )

    # Controller Manager. With limp:=true the hardware component starts inactive: ros2_control
    # still calls read(), so the joint states are live, but on_activate (which switches the servo
    # torque on) never runs. Torque is off after the servo supply is switched on, and it stays on
    # after a previous run, so power-cycle the servos first.
    def controller_manager(context):
        parameters = [
            {'robot_description': robot_description_content},
            *controller_configs,
        ]
        if limp.perform(context).strip().lower() in ('true', '1'):
            parameters.append({'hardware_components_initial_state.inactive': ['lekiwi']})
        return [Node(
            package='controller_manager',
            executable='ros2_control_node',
            parameters=parameters,
            output='screen',
            remappings=[
                ('/controller_manager/robot_description', '/robot_description'),
            ]
        )]

    controller_manager_node = OpaqueFunction(function=controller_manager)

    # Joint State Broadcaster Spawner
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen',
    )

    # Base, Arm and Gripper Controller Spawner
    controllers_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['omni_wheel_drive_controller', 'arm_controller', 'gripper_controller',
                   '--controller-manager', '/controller_manager'],
        output='screen',
        condition=UnlessCondition(limp),
    )

    # Delay spawning the controllers until joint_state_broadcaster is loaded
    delay_controllers_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[controllers_spawner],
        )
    )

    # RViz (also runnable on its own, on another host: rviz.launch.py)
    rviz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_lekiwi_bringup, 'launch', 'rviz.launch.py')),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    return LaunchDescription([
        declare_use_sim_time,
        declare_port,
        declare_use_mock_hardware,
        declare_limp,
        declare_rviz,
        robot_state_publisher_node,
        controller_manager_node,
        joint_state_broadcaster_spawner,
        delay_controllers_spawner,
        rviz,
    ])
