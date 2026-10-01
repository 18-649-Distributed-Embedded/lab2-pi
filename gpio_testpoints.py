import time

try:
    from gpiozero import DigitalOutputDevice
except ImportError:
    DigitalOutputDevice = None


class TestPoints:
    def __init__(self, udprx_gpio: int, cmdtx_gpio: int, pulse_s: float):
        self.pulse_s = pulse_s
        self.enabled = DigitalOutputDevice is not None
        self.udprx = None
        self.cmdtx = None

        if self.enabled:
            self.udprx = DigitalOutputDevice(udprx_gpio, active_high=True, initial_value=False)
            self.cmdtx = DigitalOutputDevice(cmdtx_gpio, active_high=True, initial_value=False)
        else:
            print("WARNING: gpiozero unavailable - test-point toggles disabled")

    def pulse_udprx(self) -> None:
        self._pulse(self.udprx)

    def pulse_cmdtx(self) -> None:
        self._pulse(self.cmdtx)

    def _pulse(self, pin) -> None:
        if pin is None:
            return
        pin.on()
        time.sleep(self.pulse_s)
        pin.off()

    def close(self) -> None:
        for pin in (self.udprx, self.cmdtx):
            if pin is not None:
                pin.close()