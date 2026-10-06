# lekiwi_bringup

Combined description and launch files for the LeKiwi mobile manipulator: the LeKiwi base
(`lekiwi_description`) with an SO-101 arm (`so101_description`) on its `arm_mount`.

## Launch files

| Launch | Starts | Runs on |
|---|---|---|
| `hardware_control.launch.py` | `robot_state_publisher`, `ros2_control_node`, all controllers | the robot |
| `rviz.launch.py` | RViz only | any host |
| `display.launch.py` | `robot_state_publisher`, `joint_state_publisher_gui`, RViz (no controllers) | any host, no robot needed |

`hardware_control.launch.py` arguments: `port` (default `/dev/ttyACM0`), `use_mock_hardware`
(default `false`), and `rviz` (default `false`; starts `rviz.launch.py` on the same host).

`rviz.launch.py` arguments: `fixed_frame` (default `base_footprint`), `rviz_config`.

## Limp mode

`hardware_control.launch.py limp:=true` (also in `so101_description`) starts the hardware component
`inactive` and only `joint_state_broadcaster`. ros2_control still reads the servos, so
`/joint_states` and TF show the real pose while you move the joints by hand, but the driver never
switches the torque on (only its activation does).

- Torque is off after the servo supply is switched on, and stays on after a previous run. Switch
  the servo supply off and on before a limp session, or the joints hold their pose.
- Support the arm: it falls under its own weight.
- To take control without a restart, support the arm, then:

  ```bash
  ros2 control set_hardware_component_state lekiwi active   # torque on
  ros2 run controller_manager spawner omni_wheel_drive_controller arm_controller gripper_controller
  ```

  Keep clear at activation: after a power-up the servo's goal register is 0, and the driver
  switches the torque on about one control period before it sends the first goal
  (waveshare_servos `docs/operation.md`, "Torque before the first goal").

## Running RViz or control commands on another host

The robot publishes everything a remote host needs: the model on `/robot_description`
(transient local, so a late subscriber still gets it), the poses on `/tf` and `/tf_static`, and
the controller manager's services and the controllers' topics and actions.

On the robot:

```bash
ros2 launch lekiwi_bringup hardware_control.launch.py
```

On the other host:

```bash
ros2 launch lekiwi_bringup rviz.launch.py
ros2 control list_controllers
ros2 action send_goal /arm_controller/follow_joint_trajectory control_msgs/action/FollowJointTrajectory \
  "{trajectory: {joint_names: [shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll],
    points: [{positions: [0.5, -0.5, 0.8, 0.3, 1.0], time_from_start: {sec: 2}}]}}"
```

Requirements for the other host:

- The same `ROS_DOMAIN_ID` as the robot. Use a domain that nothing else on the network uses, or
  another robot's nodes will join the graph.
- DDS discovery between the hosts: the same subnet, multicast allowed, and
  `ROS_AUTOMATIC_DISCOVERY_RANGE` not set to `LOCALHOST`. In Docker, use `--network=host`.
- This workspace built and sourced, so RViz can resolve the `package://lekiwi_description/...`
  and `package://so101_description/...` mesh paths. `ros2 control` needs `ros2controlcli` (in
  `ros-jazzy-ros2-control`).
