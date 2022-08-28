import math
from dataclasses import dataclass
from typing import Dict

from tellopy._internal.protocol import FlightData, LogData

from drone.api.linearangular import LinearAngular
from drone.api.status import Status


@dataclass
class TelloStatus(Status):
    flight_data: FlightData
    """The last decoded flight data packet received from the drone."""
    log_data: LogData
    """The last decoded log data packet received from the drone."""

    @property
    def battery(self) -> float:
        if self.flight_data is None:
            return super().battery
        return self.flight_data.battery_percentage / 100  # % -> [0, 1]

    @property
    def signal_strength(self) -> float:
        if self.flight_data is None:
            return super().signal_strength
        return self.flight_data.wifi_strength / 100  # % -> [0, 1]

    @property
    def temperatures(self) -> Dict[str, float]:
        if self.flight_data is None:
            return super().temperatures
        return {'temp': self.flight_data.temperature_height}  # TODO: Check values!

    @property
    def flying(self) -> bool:
        if self.flight_data is None:
            return super().flying
        return self.flight_data.fly_time > 0

    @property
    def height(self) -> float:
        if self.flight_data is None:
            return super().height
        return self.flight_data.height * .1  # dm -> m

    @property
    def position_attitude(self) -> LinearAngular:
        if self.log_data is None:
            return super().position_attitude
        res = LinearAngular()
        res.linear_x = self.log_data.mvo.pos_x  # TODO: Check axes!
        res.linear_y = self.log_data.mvo.pos_y  # TODO: Check axes!
        res.linear_z = self.log_data.mvo.pos_z  # TODO: Check axes!
        res.roll, res.pitch, res.yaw = quaternion_to_euler(  # TODO: Check axes!
            self.log_data.imu.q0, self.log_data.imu.q1, self.log_data.imu.q2, self.log_data.imu.q3)
        return res

    @property
    def velocity(self) -> LinearAngular:
        if self.log_data is None:
            return super().velocity
        res = LinearAngular()
        res.linear_x = self.log_data.mvo.vel_x  # TODO: Check axes!
        res.linear_y = self.log_data.mvo.vel_y  # TODO: Check axes!
        res.linear_z = self.log_data.mvo.vel_z  # TODO: Check axes!
        res.roll = self.log_data.imu.gyro_x  # TODO: Check axes!
        res.pitch = self.log_data.imu.gyro_y  # TODO: Check axes!
        res.yaw = self.log_data.imu.gyro_z  # TODO: Check axes!
        return res

    @property
    def acceleration(self) -> LinearAngular:
        if self.log_data is None:
            return super().acceleration
        res = LinearAngular()
        res.linear_x = self.log_data.imu.acc_x  # TODO: Check axes!
        res.linear_y = self.log_data.imu.acc_y  # TODO: Check axes!
        res.linear_z = self.log_data.imu.acc_z  # TODO: Check axes!
        # No angular acceleration available
        return res


def quaternion_to_euler(x: float, y: float, z: float, w: float) -> (float, float, float):
    """
    Returns the Euler angles as a tuple(roll, pitch, yaw)

    Code from: https://pypi.org/project/squaternion/ (MIT license)
    """
    y2 = y * y

    t0 = +2.0 * (w * x + y * z)
    t1 = +1.0 - 2.0 * (x * x + y2)
    out_x = math.atan2(t0, t1)

    t2 = +2.0 * (w * y - z * x)
    t2 = +1.0 if t2 > +1.0 else t2
    t2 = -1.0 if t2 < -1.0 else t2
    out_y = math.asin(t2)

    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (y2 + z * z)
    out_z = math.atan2(t3, t4)

    return out_x, out_y, out_z
