import os
import json
import atexit

from loguru import logger


class EventRecord:
    def __init__(self, event_dir: str):
        self.event_dir = event_dir
        self.event_fp = os.path.join(self.event_dir, "gpio_trigger.json")

        self._event_data = self.init_event_buffer()
        atexit.register(self.save_to_file)

    @property
    def events(self):
        return self._event_data[::-1]

    def init_event_buffer(self) -> list:
        if not os.path.exists(self.event_fp):
            with open(self.event_fp, "w") as f:
                json.dump([], f)
                data = []
        else:
            with open(self.event_fp, "r") as f:
                # 只取前1000条
                data = json.load(f)[:1000]
        logger.info(f"init event buffer: {self.event_fp}!")
        return data

    def add_event(self, event_data: dict):
        if len(self._event_data) > 10000:
            self._event_data = self._event_data[:2000]
        self._event_data.append(event_data)

    def save_to_file(self):
        with open(self.event_fp, "w") as f:
            json.dump(self._event_data, f)
        logger.info(f"event save to file: {self.event_fp}")
