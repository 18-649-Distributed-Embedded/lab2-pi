import struct

import config
from wheel_packet import (
    normalize_brake,
    normalize_steering,
    normalize_throttle,
    parse_packet,
)


def make_wheel_packet(
    counter=1,
    steer=0,
    throttle=-32768,
    brake=-32768,
    buttons=None,
):
    packet = bytearray(config.UDP_PACKET_SIZE)
    struct.pack_into("<I", packet, config.COUNTER_OFFSET, counter)
    struct.pack_into("<i", packet, config.STEER_OFFSET, steer)
    struct.pack_into("<i", packet, config.THROTTLE_OFFSET, throttle)
    struct.pack_into("<i", packet, config.BRAKE_OFFSET, brake)

    if buttons:
        for index in buttons:
            packet[config.BUTTONS_OFFSET + index] = 1

    return bytes(packet)


def test_packet_parser_reads_counter_axes_and_buttons():
    packet = make_wheel_packet(
        counter=99,
        steer=-12345,
        throttle=22222,
        brake=-11111,
        buttons=[3, 21],
    )

    wheel = parse_packet(packet)

    assert wheel.counter == 99
    assert wheel.steer_raw == -12345
    assert wheel.throttle_raw == 22222
    assert wheel.brake_raw == -11111
    assert wheel.button_pressed(3)
    assert wheel.button_pressed(21)
    assert not wheel.button_pressed(4)


def test_steering_center_is_zero():
    assert normalize_steering(config.STEER_CENTER) == 0


def test_steering_maps_to_signed_command_range():
    assert normalize_steering(config.STEER_MIN) == -128
    assert normalize_steering(config.STEER_MAX) == 127


def test_throttle_maps_released_to_neutral_and_pressed_to_full():
    assert normalize_throttle(
        config.THROTTLE_RELEASED,
        config.THROTTLE_RELEASED,
        config.THROTTLE_PRESSED,
    ) == 127

    assert normalize_throttle(
        config.THROTTLE_PRESSED,
        config.THROTTLE_RELEASED,
        config.THROTTLE_PRESSED,
    ) == 255


def test_brake_maps_released_and_pressed():
    assert normalize_brake(
        config.BRAKE_RELEASED,
        config.BRAKE_RELEASED,
        config.BRAKE_PRESSED,
    ) == 0

    assert normalize_brake(
        config.BRAKE_PRESSED,
        config.BRAKE_RELEASED,
        config.BRAKE_PRESSED,
    ) == 1