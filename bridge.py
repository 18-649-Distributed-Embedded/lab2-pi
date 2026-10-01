#!/usr/bin/env python3
import argparse
import select
import socket
import sys
import threading
import time

import serial

import config
from gpio_testpoints import TestPoints
from protocol import StatusParser, build_command_set
from wheel_packet import (
    WheelState,
    normalize_brake,
    normalize_steering,
    normalize_throttle,
    parse_packet,
)


class VehicleCommand:
    def __init__(self):
        self.lock = threading.Lock()
        self.throttle = 127
        self.steering = 0
        self.brake = 1
        self.blinker = 0
        self.test_active = False
        self.last_udp_time = 0.0
        self.last_wheel: WheelState | None = None
        self.left_latched = False
        self.right_latched = False
        self.left_crossed = False
        self.right_crossed = False

    def update_from_wheel(self, wheel: WheelState) -> None:
        throttle = normalize_throttle(
            wheel.throttle_raw,
            config.THROTTLE_RELEASED,
            config.THROTTLE_PRESSED,
        )
        brake = normalize_brake(
            wheel.brake_raw,
            config.BRAKE_RELEASED,
            config.BRAKE_PRESSED,
        )
        steering = normalize_steering(wheel.steer_raw)

        with self.lock:
            previous = self.last_wheel
            self.last_wheel = wheel
            self.last_udp_time = time.monotonic()
            self.throttle = throttle
            self.steering = steering
            self.brake = brake

            self._handle_buttons(wheel, previous)
            self._self_cancel(wheel.steer_raw)

    def _rising(self, wheel: WheelState, previous: WheelState | None, index: int | None) -> bool:
        if not wheel.button_pressed(index):
            return False
        return previous is None or not previous.button_pressed(index)

    def _handle_buttons(self, wheel: WheelState, previous: WheelState | None) -> None:
        if self._rising(wheel, previous, config.BUTTON_LEFT_BLINKER):
            self.blinker = 0 if self.blinker == 1 else 1
            self.left_latched = self.blinker == 1
            self.right_latched = False
            self.left_crossed = False

        if self._rising(wheel, previous, config.BUTTON_RIGHT_BLINKER):
            self.blinker = 0 if self.blinker == 2 else 2
            self.right_latched = self.blinker == 2
            self.left_latched = False
            self.right_crossed = False

        if self._rising(wheel, previous, config.BUTTON_HAZARD):
            self.blinker = 0 if self.blinker == 3 else 3
            self.left_latched = False
            self.right_latched = False

        if self._rising(wheel, previous, config.BUTTON_TEST):
            self.test_active = not self.test_active
            if not self.test_active:
                self.throttle = 127
                self.steering = 0
                self.brake = 1
                self.blinker = 0

    def _self_cancel(self, steer_raw: int) -> None:
        if self.left_latched:
            if steer_raw <= -config.TURN_CANCEL_THRESHOLD:
                self.left_crossed = True
            elif self.left_crossed and steer_raw >= -config.TURN_CANCEL_RETURN_THRESHOLD:
                self.blinker = 0
                self.left_latched = False
                self.left_crossed = False

        if self.right_latched:
            if steer_raw >= config.TURN_CANCEL_THRESHOLD:
                self.right_crossed = True
            elif self.right_crossed and steer_raw <= config.TURN_CANCEL_RETURN_THRESHOLD:
                self.blinker = 0
                self.right_latched = False
                self.right_crossed = False

    def snapshot(self) -> tuple[int, int, int, int, bool, bool]:
        with self.lock:
            stale = (time.monotonic() - self.last_udp_time) > config.UDP_TIMEOUT_S
            if stale:
                return 127, 0, 1, 0, True, True
            return (
                self.throttle,
                self.steering,
                self.brake,
                self.blinker,
                self.test_active,
                False,
            )


def uart_status_thread(ser: serial.Serial, stop: threading.Event) -> None:
    parser = StatusParser()

    while not stop.is_set():
        try:
            data = ser.read(64)
        except serial.SerialException as exc:
            print(f"\nUART read error: {exc}", file=sys.stderr)
            stop.set()
            return

        if not data:
            continue

        for status in parser.feed(data):
            mode = "NORMAL" if status.safety_flags == 0 else f"FAIL_SAFE flags=0x{status.safety_flags:02X}"
            print(
                f"[STM32] {mode} | "
                f"L={status.left_current_mv}mV "
                f"R={status.right_current_mv}mV "
                f"S={status.servo_current_mv}mV"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Lab 2 Pi UDP-to-UART vehicle bridge")
    parser.add_argument("--serial", default=config.UART_DEVICE)
    parser.add_argument("--baud", type=int, default=config.UART_BAUD)
    parser.add_argument("--no-gpio", action="store_true", help="disable UDPRX/CMDTX test point pulses")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    command = VehicleCommand()
    stop = threading.Event()

    try:
        ser = serial.Serial(
            args.serial,
            args.baud,
            timeout=config.UART_TIMEOUT_S,
            write_timeout=config.UART_TIMEOUT_S,
        )
    except serial.SerialException as exc:
        print(f"Cannot open {args.serial}: {exc}", file=sys.stderr)
        return 1

    testpoints = TestPoints(
        config.UDPRX_GPIO,
        config.CMDTX_GPIO,
        config.TESTPOINT_PULSE_S,
    )
    if args.no_gpio:
        testpoints.close()
        testpoints.enabled = False
        testpoints.udprx = None
        testpoints.cmdtx = None

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((config.UDP_BIND_IP, config.UDP_PORT))
    sock.setblocking(False)

    reader = threading.Thread(
        target=uart_status_thread,
        args=(ser, stop),
        daemon=True,
        name="stm32-status-reader",
    )
    reader.start()

    print(f"Listening for wheel UDP on {config.UDP_BIND_IP}:{config.UDP_PORT}")
    print(f"Sending STM32 frames to {args.serial} at {args.baud} baud")

    seq = 0
    next_send = time.monotonic()

    try:
        while not stop.is_set():
            timeout = max(0.0, next_send - time.monotonic())
            readable, _, _ = select.select([sock], [], [], timeout)

            if readable:
                while True:
                    try:
                        packet, source = sock.recvfrom(1024)
                    except BlockingIOError:
                        break

                    if len(packet) != config.UDP_PACKET_SIZE:
                        print(f"Ignored UDP packet of {len(packet)} bytes from {source}", file=sys.stderr)
                        continue

                    wheel = parse_packet(packet)
                    command.update_from_wheel(wheel)
                    testpoints.pulse_udprx()

                    if args.verbose:
                        print(
                            f"[UDP {wheel.counter}] steer={wheel.steer_raw} "
                            f"thr={wheel.throttle_raw} brk={wheel.brake_raw}"
                        )

            now = time.monotonic()
            if now < next_send:
                continue

            throttle, steering, brake, blinker, test_active, stale = command.snapshot()

            turn_sync = 1 if (now % 1.0) < 0.5 else 0
            hazard_sync = 1 if (now % 0.5) < 0.25 else 0

            frame_set = build_command_set(
                seq=seq,
                throttle=throttle,
                steering=steering,
                brake=brake,
                blinker=blinker,
                test_active=test_active,
                turn_sync=turn_sync,
                hazard_sync=hazard_sync,
            )

            try:
                testpoints.pulse_cmdtx()
                ser.write(frame_set)
                ser.flush()
            except serial.SerialException as exc:
                print(f"UART write error: {exc}", file=sys.stderr)
                break

            if args.verbose and stale:
                print("[SAFETY] UDP stale - sending neutral throttle plus brake")

            seq = (seq + 1) & 0xFF
            next_send += config.COMMAND_PERIOD_S
            if next_send < now:
                next_send = now + config.COMMAND_PERIOD_S

    except KeyboardInterrupt:
        print("\nStopping bridge.")
    finally:
        stop.set()
        sock.close()
        ser.close()
        testpoints.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())