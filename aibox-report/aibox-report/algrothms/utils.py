from loguru import logger


def get_import_gpio(model_type: str):
    if model_type == "rt":
        import Jetson.GPIO as GPIO
    elif model_type == "rknn":
        GPIO = RknnGPIO
    else:
        GPIO = BaseGPIO

    return GPIO


class BaseGPIO:
    BOARD = 10
    OUT = 11
    LOW = 0
    HIGH = 1

    def __init__(self, pins: list) -> None:
        self.pins = pins

    @classmethod
    def setwarnings(cls, value):
        pass

    @classmethod
    def setmode(cls, value):
        pass

    @classmethod
    def setup(cls, pins, value):
        pass

    @classmethod
    def cleanup(cls):
        pass

    @classmethod
    def output(cls, pins: list, value: int):
        switch = "on" if value else "off"
        logger.info(f"gpio set: {switch}")


class RknnGPIO(BaseGPIO):
    def __init__(self, pins: list) -> None:
        super().__init__(pins)

        import gpio_control as gpio

        gpio.gpio_setup()

    @classmethod
    def output(cls, pins: list, value: int):
        super(RknnGPIO, cls).output(pins, value)
        import gpio_control as gpio

        if value:
            gpio.gpio_on()
        else:
            gpio.gpio_off()
