import os

from loguru import logger

from .utils import get_import_gpio

model_type = os.getenv("MODEL_TYPE", "onnx")
GPIO = get_import_gpio(model_type)


class Gpio:
    def __init__(self, pins: list, enable: bool = True):
        try:
            self.enable = enable
            self.pins = pins
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(self.pins, GPIO.OUT, initial=GPIO.LOW)
        except Exception as e:
            logger.error(f"gpio init error: {e}")

    def run(self, value=True):
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


class GpioControl:
    def __init__(self, pins: list, enable: bool = True):
        self.enable = enable
        self.gpio = Gpio(pins)

    def __enter__(self):
        return self.gpio

    def __exit__(self, exc_type, exc_value, traceback):
        self.gpio.cleanup()
