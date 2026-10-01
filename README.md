# Vehicle Pi Bridge

This program implements:

Laptop wheel proxy -> UDP port 8000 -> Raspberry Pi -> UART -> STM32

## Install

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip
mkdir -p ~/vehicle-pi
cd ~/vehicle-pi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure

Edit `config.py` before using the vehicle:

1. Record raw wheel axis values with the supplied `wheelmonitor -r`.
2. Set steering and pedal endpoints.
3. Set real wheel button indices.
4. Confirm `/dev/serial0` exists for GPIO UART.
5. Confirm STM32 firmware uses USART6 on PC6/PC7.

## Run

Bench test with a USB serial device:

```bash
python3 bridge.py --serial /dev/ttyACM0 --no-gpio --verbose
```

Final GPIO-UART configuration:

```bash
python3 bridge.py --serial /dev/serial0 --verbose
```

## Pi GPIO wiring

| Function | BCM GPIO | Physical pin |
|---|---:|---:|
| UART TX | GPIO14 | 8 |
| UART RX | GPIO15 | 10 |
| CMDTX test point | GPIO18 | 12 |
| UDPRX test point | GPIO23 | 16 |
| Ground | - | 6 |

UART connection:

- Pi GPIO14 TX -> STM32 PC7 RX
- Pi GPIO15 RX <- STM32 PC6 TX
- Pi GND -> STM32 GND

Do not connect Pi 5 V or 3.3 V to the STM32.

## Safety behavior

- The bridge sends five STM32 command frames every 50 ms.
- If wheel UDP packets stop for more than 150 ms, the bridge sends neutral throttle and brake.
- The STM32's own 150 ms command watchdog remains the final fail-safe authority.