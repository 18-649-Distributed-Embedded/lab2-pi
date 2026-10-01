import struct

from protocol import (
    FRAME_END,
    FRAME_SYNC,
    STATUS_END,
    STATUS_SYNC,
    StatusParser,
    build_command_set,
    build_frame,
)


def test_build_frame_layout_and_checksum():
    frame = build_frame(0x100, bytes([7, 200, 0, 1]))

    assert frame[0] == FRAME_SYNC
    assert frame[-1] == FRAME_END
    assert frame[1:3] == struct.pack("<H", 0x100)
    assert frame[3] == 4
    assert frame[4:8] == bytes([7, 200, 0, 1])

    expected_checksum = sum(frame[1:-2]) & 0xFF
    assert frame[-2] == expected_checksum


def test_build_frame_rejects_payload_larger_than_eight_bytes():
    try:
        build_frame(0x100, bytes(9))
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_command_set_contains_five_complete_frames():
    packet = build_command_set(
        seq=42,
        throttle=180,
        steering=-35,
        brake=1,
        blinker=2,
        test_active=False,
        turn_sync=1,
        hazard_sync=0,
    )

    assert packet.count(bytes([FRAME_SYNC])) == 5
    assert packet.count(bytes([FRAME_END])) == 5


def test_status_parser_decodes_one_complete_status_frame():
    raw = bytes([
        STATUS_SYNC,
        0x03,
        0x00, 0x64,
        0xFF, 0x9C,
        0x00, 0x2A,
        STATUS_END,
    ])

    parser = StatusParser()
    frames = parser.feed(raw)

    assert len(frames) == 1
    assert frames[0].safety_flags == 0x03
    assert frames[0].left_current_mv == 100
    assert frames[0].right_current_mv == -100
    assert frames[0].servo_current_mv == 42


def test_status_parser_handles_fragmented_serial_input():
    raw = bytes([
        STATUS_SYNC,
        0x00,
        0x00, 0x01,
        0x00, 0x02,
        0x00, 0x03,
        STATUS_END,
    ])

    parser = StatusParser()

    assert parser.feed(raw[:4]) == []
    frames = parser.feed(raw[4:])

    assert len(frames) == 1
    assert frames[0].left_current_mv == 1
    assert frames[0].right_current_mv == 2
    assert frames[0].servo_current_mv == 3


def test_status_parser_discards_noise_before_frame():
    raw = b"\x00\x01bad" + bytes([
        STATUS_SYNC,
        0x00,
        0x00, 0x01,
        0x00, 0x02,
        0x00, 0x03,
        STATUS_END,
    ])

    parser = StatusParser()
    frames = parser.feed(raw)

    assert len(frames) == 1
    assert frames[0].servo_current_mv == 3