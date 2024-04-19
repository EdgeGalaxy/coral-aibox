import os
import time

from loguru import logger

from .utils import get_import_gpio

model_type = os.getenv("MODEL_TYPE", "onnx")
GPIO = get_import_gpio(model_type)


class GpioControl:
    def __init__(self, pins: list, enable: bool = True, interval: float = 1):
        try:
            self.enable = enable
            self.pins = pins
            self.interval = interval
            self.trigger_time = time.time()
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(self.pins, GPIO.OUT, initial=GPIO.LOW)
        except Exception as e:
            logger.error(f"gpio init error: {e}")

    def trigger_on(self):
        if time.time() - self.trigger_time > self.interval:
            self._run(True)
            self.trigger_time = time.time()

    def trigger_off(self):
        self._run(False)

    def _run(self, value=True):
        try:
            if not self.enable:
                logger.warning("gpio not enable, run!")
            else:
                GPIO.output(self.pins, GPIO.HIGH if value else GPIO.LOW)
        except Exception as e:
            logger.error(f"gpio run error: {e}")

    def cleanup(self):
        if not self.enable:
            logger.warning("gpio not enable, cleanup!")
        else:
            GPIO.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.trigger_off()
        self.cleanup()
