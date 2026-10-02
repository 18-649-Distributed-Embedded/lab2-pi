from dataclasses import dataclass

# UDP input from the laptop wheel proxy
UDP_BIND_IP = "172.26.5.201"
UDP_PORT = 8000
UDP_PACKET_SIZE = 276
UDP_TIMEOUT_S = 0.150

# STM32 serial link
# Pi GPIO 14/15 UART TX/RX to STM32 USART6 on PC6/PC7
UART_DEVICE = "/dev/serial0"
UART_BAUD = 115200
UART_TIMEOUT_S = 0.02
COMMAND_PERIOD_S = 0.050

# Test-point GPIOs
UDPRX_GPIO = 23
CMDTX_GPIO = 18
TESTPOINT_PULSE_S = 0.001

# UDP layout
# Packet: uint32 little-endian packet counter + 272-byte DIJOYSTATE2
# DirectInput DIJOYSTATE2 begins with lX at byte 4, lY at byte 8, lRz at byte 24
COUNTER_OFFSET = 0
STEER_OFFSET = 4
THROTTLE_OFFSET = 8
BRAKE_OFFSET = 24
BUTTONS_OFFSET = 48
BUTTON_COUNT = 128

# Wheel thresholds
STEER_MIN = -32768
STEER_CENTER = 0
STEER_MAX = 32767
THROTTLE_RELEASED = 0
THROTTLE_PRESSED = 32767
BRAKE_RELEASED = 0
BRAKE_PRESSED = 32767

# Button mappings
BUTTON_LEFT_BLINKER = 9
BUTTON_RIGHT_BLINKER = 8
BUTTON_HAZARD = 7
BUTTON_TEST = 6

# Steering-based turn-signal self-cancel settings in raw wheel units
TURN_CANCEL_THRESHOLD = 12000
TURN_CANCEL_RETURN_THRESHOLD = 4000

# Deadbands to remove slight wheel/pedal noise
STEERING_DEADBAND = 1200
PEDAL_DEADBAND = 1000


@dataclass(frozen=True)
class CanId:
    HEARTBEAT: int = 0x020
    BRAKE: int = 0x010
    MOTION: int = 0x100
    TURN_SYNC: int = 0x200
    HAZARD_SYNC: int = 0x011