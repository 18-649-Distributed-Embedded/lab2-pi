from dataclasses import dataclass

# UDP input from the laptop wheel proxy.
UDP_BIND_IP = "172.26.5.201"
UDP_PORT = 8000
UDP_PACKET_SIZE = 276
UDP_TIMEOUT_S = 0.150

# STM32 serial link.
# Final wiring: Pi GPIO UART TX/RX to STM32 USART6 on PC6/PC7.
UART_DEVICE = "/dev/serial0"
UART_BAUD = 115200
UART_TIMEOUT_S = 0.02
COMMAND_PERIOD_S = 0.050

# Test-point GPIOs, BCM numbering.
# GPIO18 is physical pin 12 and is already labeled CMD_INT in your schematic.
# GPIO23 is physical pin 16 - reserve it for UDPRX.
UDPRX_GPIO = 23
CMDTX_GPIO = 18
TESTPOINT_PULSE_S = 0.001

# UDP layout.
# Packet: uint32 little-endian packet counter + 272-byte DIJOYSTATE2.
# DirectInput DIJOYSTATE2 begins with:
# lX at byte 4, lY at byte 8, lRz at byte 20.
# Confirm against the supplied state.h before vehicle testing.
COUNTER_OFFSET = 0
STEER_OFFSET = 4
THROTTLE_OFFSET = 8
BRAKE_OFFSET = 24
BUTTONS_OFFSET = 48
BUTTON_COUNT = 128

# Replace these with the measured raw values from your Pi wheel monitor.
# Typical DirectInput-style range is approximately -32768 to 32767.
STEER_MIN = -32768
STEER_CENTER = 0
STEER_MAX = 32767

# Update after recording pedal values. Set RELEASED and PRESSED according to
# what your specific wheel proxy reports, regardless of sign/order.
THROTTLE_RELEASED = 0
THROTTLE_PRESSED = 32767
BRAKE_RELEASED = 0
BRAKE_PRESSED = 32767

# Wheel button indices - intentionally unset until measured with wheelmonitor -r.
BUTTON_LEFT_BLINKER = 9
BUTTON_RIGHT_BLINKER = 8
BUTTON_HAZARD = 7
BUTTON_TEST = 6

# Steering-based turn-signal self-cancel settings in raw wheel units.
TURN_CANCEL_THRESHOLD = 12000
TURN_CANCEL_RETURN_THRESHOLD = 4000

# Deadbands remove slight wheel/pedal noise.
STEERING_DEADBAND = 1200
PEDAL_DEADBAND = 1000


@dataclass(frozen=True)
class CanId:
    HEARTBEAT: int = 0x020
    BRAKE: int = 0x010
    MOTION: int = 0x100
    TURN_SYNC: int = 0x200
    HAZARD_SYNC: int = 0x011
