import time

from loguru import logger


class GPIOSignal:

    def __init__(self, enable=True, on_signal_duration=0):
        self.init_ret = -1
        self.enable = enable
        self.on_signal_duration = on_signal_duration
        self.init()
        self._recv_on_signal_at = 0

    def init(self):
        import gpio_control as gpio

        logger.info("gpio start init")
        gpio.gpio_setup()  # 初始化

    def trigger(self):
        if self.enable:
            import gpio_control as gpio

            if time.time() < (self._recv_on_signal_at + self.on_signal_duration):
                logger.info("trigger gpio on")
                gpio.gpio_on()
            else:
                # logger.info("trigger gpio off")
                gpio.gpio_off()

    def gpio_on(self):
        self._recv_on_signal_at = time.time()
