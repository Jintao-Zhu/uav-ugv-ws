#!/usr/bin/env python3
"""
UAV 空中环绕 + UGV 地面环绕 演示节点。
UAV (PX4 offboard): 起飞 -> 在高度 5m 处绕半径 5m 的圆环飞行一圈 -> 降落
UGV (TurtleBot3):   以恒定线速度和角速度绕半径 1m 的圆弧行驶一圈后停止
"""

import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from geometry_msgs.msg import Twist
from px4_msgs.msg import (
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleCommand,
    VehicleLocalPosition,
    VehicleStatus,
)


class CircleDemo(Node):
    def __init__(self):
        super().__init__('circle_demo')

        # ---- PX4 QoS ----
        # 统一使用 BEST_EFFORT + TRANSIENT_LOCAL，匹配 PX4 XRCE-DDS 端
        px4_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        # ---- UAV publishers ----
        self.offboard_mode_pub = self.create_publisher(
            OffboardControlMode, '/fmu/in/offboard_control_mode', px4_qos)
        self.setpoint_pub = self.create_publisher(
            TrajectorySetpoint, '/fmu/in/trajectory_setpoint', px4_qos)
        self.vehicle_cmd_pub = self.create_publisher(
            VehicleCommand, '/fmu/in/vehicle_command', px4_qos)

        # ---- UAV subscribers ----
        # 注意：较新版本 PX4 topic 名带 _v1 后缀
        self.create_subscription(
            VehicleLocalPosition, '/fmu/out/vehicle_local_position_v1',
            self._uav_pos_cb, px4_qos)
        self.create_subscription(
            VehicleStatus, '/fmu/out/vehicle_status_v1',
            self._uav_status_cb, px4_qos)

        # ---- UGV publisher ----
        self.ugv_cmd_pub = self.create_publisher(
            Twist, '/cmd_vel', 10)

        # ---- UAV 状态 ----
        self.uav_pos = VehicleLocalPosition()
        self.uav_status = VehicleStatus()
        self.offboard_counter = 0

        # ---- UAV 圆环参数 ----
        self.uav_radius = 5.0          # 圆环半径 (m)
        self.uav_altitude = -5.0       # NED 坐标系，向上为负
        self.uav_omega = 0.15          # 角速度 (rad/s)，约 42 秒一圈
        self.uav_angle = 0.0           # 当前角度
        self.uav_circle_started = False
        self.uav_circle_done = False

        # ---- UGV 圆环参数 ----
        self.ugv_radius = 1.0          # 圆环半径 (m)
        self.ugv_linear_v = 0.15       # 线速度 (m/s)
        self.ugv_angular_v = self.ugv_linear_v / self.ugv_radius  # ω = v/r
        self.ugv_circle_time = 2.0 * math.pi * self.ugv_radius / self.ugv_linear_v
        self.ugv_elapsed = 0.0
        self.ugv_started = False
        self.ugv_done = False

        # ---- 状态机 ----
        # PREFLIGHT -> TAKEOFF -> CIRCLE -> LAND -> DONE
        self.uav_phase = 'PREFLIGHT'

        # ---- 主定时器 10 Hz ----
        self.dt = 0.1
        self.timer = self.create_timer(self.dt, self._tick)

    # ------------------------------------------------------------------ #
    #  回调
    # ------------------------------------------------------------------ #
    def _uav_pos_cb(self, msg):
        self.uav_pos = msg

    def _uav_status_cb(self, msg):
        self.uav_status = msg

    # ------------------------------------------------------------------ #
    #  UAV 辅助方法
    # ------------------------------------------------------------------ #
    def _publish_offboard_heartbeat(self):
        msg = OffboardControlMode()
        msg.position = True
        msg.velocity = False
        msg.acceleration = False
        msg.attitude = False
        msg.body_rate = False
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.offboard_mode_pub.publish(msg)

    def _publish_position(self, x, y, z, yaw=float('nan')):
        msg = TrajectorySetpoint()
        msg.position = [x, y, z]
        msg.yaw = yaw
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.setpoint_pub.publish(msg)

    def _send_vehicle_command(self, command, **params):
        msg = VehicleCommand()
        msg.command = command
        msg.param1 = params.get('param1', 0.0)
        msg.param2 = params.get('param2', 0.0)
        msg.param3 = params.get('param3', 0.0)
        msg.param4 = params.get('param4', 0.0)
        msg.param5 = params.get('param5', 0.0)
        msg.param6 = params.get('param6', 0.0)
        msg.param7 = params.get('param7', 0.0)
        msg.target_system = 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1
        msg.from_external = True
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.vehicle_cmd_pub.publish(msg)

    def _arm(self):
        self._send_vehicle_command(
            VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=1.0)
        self.get_logger().info('UAV: Arm')

    def _engage_offboard(self):
        self._send_vehicle_command(
            VehicleCommand.VEHICLE_CMD_DO_SET_MODE, param1=1.0, param2=6.0)
        self.get_logger().info('UAV: Offboard mode')

    def _land(self):
        self._send_vehicle_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)
        self.get_logger().info('UAV: Land')

    # ------------------------------------------------------------------ #
    #  主循环
    # ------------------------------------------------------------------ #
    def _tick(self):
        # ---------- UAV 控制 ----------
        self._publish_offboard_heartbeat()

        if self.uav_phase == 'PREFLIGHT':
            # 持续发送 setpoint，和官方示例一致：发够次数后同时切 offboard + arm
            self._publish_position(0.0, 0.0, self.uav_altitude)
            self.offboard_counter += 1
            if self.offboard_counter == 10:
                self._engage_offboard()
                self._arm()
            if self.offboard_counter > 10:
                # 检查是否已 armed 并进入 offboard
                if self.uav_status.arming_state == VehicleStatus.ARMING_STATE_ARMED:
                    self.uav_phase = 'TAKEOFF'
                    self.get_logger().info('UAV: Armed, taking off...')
                elif self.offboard_counter % 20 == 0:
                    # 每 2 秒重试
                    self.get_logger().info(
                        f'UAV: Waiting... nav_state={self.uav_status.nav_state}, '
                        f'arming_state={self.uav_status.arming_state}')
                    self._engage_offboard()
                    self._arm()

        elif self.uav_phase == 'TAKEOFF':
            self._publish_position(0.0, 0.0, self.uav_altitude)
            # 到达目标高度（容差 0.5m）
            if abs(self.uav_pos.z - self.uav_altitude) < 0.5:
                self.uav_phase = 'CIRCLE'
                self.uav_angle = 0.0
                self.get_logger().info('UAV: Reached altitude, starting circle')

        elif self.uav_phase == 'CIRCLE':
            self.uav_angle += self.uav_omega * self.dt
            x = self.uav_radius * math.cos(self.uav_angle)
            y = self.uav_radius * math.sin(self.uav_angle)
            # yaw 朝向切线方向
            yaw = self.uav_angle + math.pi / 2.0
            self._publish_position(x, y, self.uav_altitude, yaw)

            if self.uav_angle >= 2.0 * math.pi:
                self.uav_phase = 'LAND'
                self.get_logger().info('UAV: Circle complete, landing')

        elif self.uav_phase == 'LAND':
            self._land()
            self.uav_phase = 'DONE'

        elif self.uav_phase == 'DONE':
            self.uav_circle_done = True

        # ---------- UGV 控制 ----------
        if not self.ugv_started:
            # 等 UAV 开始环绕后再启动 UGV
            if self.uav_phase in ('CIRCLE', 'LAND', 'DONE'):
                self.ugv_started = True
                self.get_logger().info('UGV: Starting circle')

        if self.ugv_started and not self.ugv_done:
            self.ugv_elapsed += self.dt
            if self.ugv_elapsed < self.ugv_circle_time:
                twist = Twist()
                twist.linear.x = self.ugv_linear_v
                twist.angular.z = self.ugv_angular_v
                self.ugv_cmd_pub.publish(twist)
            else:
                # 停车
                self.ugv_cmd_pub.publish(Twist())
                self.ugv_done = True
                self.get_logger().info('UGV: Circle complete, stopped')

        # ---------- 全部完成 ----------
        if self.uav_circle_done and self.ugv_done:
            self.get_logger().info('Demo finished!')
            self.timer.cancel()


def main(args=None):
    rclpy.init(args=args)
    node = CircleDemo()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
