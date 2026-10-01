import struct
from dataclasses import dataclass

FRAME_SYNC = 0xAA
FRAME_END = 0x55

STATUS_SYNC = 0xBB
STATUS_END = 0x66
STATUS_SIZE = 9


@dataclass(frozen=True)
class StatusFrame:
    safety_flags: int
    left_current_mv: int
    right_current_mv: int
    servo_current_mv: int


def build_frame(can_id: int, payload: bytes) -> bytes:
    if not 0 <= can_id <= 0xFFFF:
        raise ValueError("CAN ID outside uint16 range")
    if len(payload) > 8:
        raise ValueError("payload exceeds STM32 MAX_PAYLOAD_LEN")

    body = struct.pack("<HB", can_id, len(payload)) + payload
    checksum = sum(body) & 0xFF
    return bytes([FRAME_SYNC]) + body + bytes([checksum, FRAME_END])


def build_command_set(
    seq: int,
    throttle: int,
    steering: int,
    brake: int,
    blinker: int,
    test_active: bool,
    turn_sync: int,
    hazard_sync: int,
) -> bytes:
    seq &= 0xFF

    if not 0 <= throttle <= 255:
        raise ValueError("throttle must be 0..255")
    if not -128 <= steering <= 127:
        raise ValueError("steering must be -128..127")
    if brake not in (0, 1):
        raise ValueError("brake must be 0 or 1")
    if blinker not in (0, 1, 2, 3):
        raise ValueError("blinker must be 0..3")
    if turn_sync not in (0, 1) or hazard_sync not in (0, 1):
        raise ValueError("sync values must be 0 or 1")

    heartbeat = build_frame(0x020, struct.pack("<BB", seq, 0xFF if test_active else 0))
    brake_frame = build_frame(0x010, struct.pack("<BB", seq, brake))
    motion = build_frame(0x100, struct.pack("<BBbB", seq, throttle, steering, blinker))
    turn = build_frame(0x200, struct.pack("<BB", seq, turn_sync))
    hazard = build_frame(0x011, struct.pack("<BB", seq, hazard_sync))

    return heartbeat + brake_frame + motion + turn + hazard


class StatusParser:
    def __init__(self):
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[StatusFrame]:
        self._buffer.extend(data)
        frames: list[StatusFrame] = []

        while True:
            try:
                start = self._buffer.index(STATUS_SYNC)
            except ValueError:
                self._buffer.clear()
                break

            if start:
                del self._buffer[:start]

            if len(self._buffer) < STATUS_SIZE:
                break

            candidate = self._buffer[:STATUS_SIZE]
            if candidate[-1] != STATUS_END:
                del self._buffer[0]
                continue

            frames.append(
                StatusFrame(
                    safety_flags=candidate[1],
                    left_current_mv=struct.unpack(">h", candidate[2:4])[0],
                    right_current_mv=struct.unpack(">h", candidate[4:6])[0],
                    servo_current_mv=struct.unpack(">h", candidate[6:8])[0],
                )
            )
            del self._buffer[:STATUS_SIZE]

        return frames