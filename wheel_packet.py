import struct
from dataclasses import dataclass

from config import (
    BRAKE_OFFSET,
    BUTTON_COUNT,
    BUTTONS_OFFSET,
    COUNTER_OFFSET,
    PEDAL_DEADBAND,
    STEER_CENTER,
    STEER_MAX,
    STEER_MIN,
    STEER_OFFSET,
    STEERING_DEADBAND,
    THROTTLE_OFFSET,
)


@dataclass(frozen=True)
class WheelState:
    counter: int
    steer_raw: int
    throttle_raw: int
    brake_raw: int
    buttons: tuple[int, ...]

    def button_pressed(self, index: int | None) -> bool:
        return index is not None and 0 <= index < len(self.buttons) and self.buttons[index] != 0


def parse_packet(packet: bytes) -> WheelState:
    counter = struct.unpack_from("<I", packet, COUNTER_OFFSET)[0]
    steer = struct.unpack_from("<i", packet, STEER_OFFSET)[0]
    throttle = struct.unpack_from("<i", packet, THROTTLE_OFFSET)[0]
    brake = struct.unpack_from("<i", packet, BRAKE_OFFSET)[0]
    buttons = tuple(packet[BUTTONS_OFFSET:BUTTONS_OFFSET + BUTTON_COUNT])

    return WheelState(counter, steer, throttle, brake, buttons)


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def map_linear(value: int, in_low: int, in_high: int, out_low: int, out_high: int) -> int:
    if in_high == in_low:
        raise ValueError("input range cannot be zero")
    value = clamp(value, min(in_low, in_high), max(in_low, in_high))
    return round(out_low + (value - in_low) * (out_high - out_low) / (in_high - in_low))


def normalize_steering(raw: int) -> int:
    if abs(raw - STEER_CENTER) <= STEERING_DEADBAND:
        return 0

    if raw >= STEER_CENTER:
        return clamp(
            map_linear(raw, STEER_CENTER, STEER_MAX, 0, 127),
            0,
            127,
        )

    return clamp(
        map_linear(raw, STEER_MIN, STEER_CENTER, -128, 0),
        -128,
        0,
    )


def pedal_fraction(raw: int, released: int, pressed: int) -> float:
    if released == pressed:
        raise ValueError("pedal calibration endpoints cannot match")

    low = min(released, pressed)
    high = max(released, pressed)
    raw = clamp(raw, low, high)
    fraction = (raw - released) / (pressed - released)
    return max(0.0, min(1.0, fraction))


def normalize_throttle(raw: int, released: int, pressed: int) -> int:
    fraction = pedal_fraction(raw, released, pressed)
    if fraction * abs(pressed - released) <= PEDAL_DEADBAND:
        fraction = 0.0
    return clamp(round(127 + fraction * 128), 127, 255)


def normalize_brake(raw: int, released: int, pressed: int) -> int:
    fraction = pedal_fraction(raw, released, pressed)
    if fraction * abs(pressed - released) <= PEDAL_DEADBAND:
        return 0
    return 1 if fraction >= 0.10 else 0