import json
from typing import Dict, List, Any

import paho.mqtt.client as mqtt
from loguru import logger

from .featuredb import FeatureDB


class GossipCommunicate:

    def __init__(
        self,
        mqtt_client: mqtt.Client,
        featuredb: FeatureDB,
        mac_addr: str,
        enable: bool = True,
    ) -> None:
        self.enable = enable
        self.featuedb = featuredb
        self.client = mqtt_client
        self.mac_addr = mac_addr
        self._topic = f"aibox/gossip/faces/{mac_addr}"
        # 订阅topic
        self.start_subscribe()

    def start_subscribe(self):
        for topic in self.topics.values():
            self.client.subscribe(topic)
        self.client.on_message = self.on_message

    def on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage):
        topic, recv_data = msg.topic, json.loads(msg.payload.decode())
        if self.mac_addr in topic:
            logger.info(f"ignore topic: {topic}, because it is send from self!")
            return
        if "create" in topic:
            # 创建新的数据
            user_id = recv_data["user_id"]
            self.featuedb.update_user_date_from_remote(user_id, recv_data["faces"])
        elif "move" in topic:
            # 先删除对方的src_user_id数据，再更新dest_user_id数据
            self.featuedb.delete_user(recv_data["src_user_id"])
            self.featuedb.update_user_date_from_remote(
                recv_data["dest_user_id"], recv_data["faces"]
            )
        elif "delete" in topic:
            self.featuedb.delete_user(recv_data["user_id"])
        elif "sync" in topic:
            # 同步数据，先删除对方的数据，再更新数据
            self.featuedb.delete_user(recv_data["user_id"])
            self.featuedb.update_user_date_from_remote(
                recv_data["user_id"], recv_data["faces"]
            )

    @property
    def topics(self):
        return {
            "create": f"{self._topic}/create",
            "move": f"{self._topic}/move",
            "delete": f"{self._topic}/delete",
            "sync": f"{self._topic}/sync",
        }

    def user_faces_create(self, user_id: str, faces: List[Dict]):
        """
        创建用户

        :param user_id:
        :param faces:
        """
        topic = self.topics["create"]
        if not self.enable:
            logger.warning(f"{topic} disabled!")
            return
        payload = {"user_id": user_id, "faces": faces}
        self.client.publish(topic, json.dumps(payload))

    def user_faces_move(self, src_user_id: str, dest_user_id: str, faces: List[Dict]):
        """
        重命名用户名

        :param src_user_id:
        :param dest_user_id:
        :param faces:
        """
        topic = self.topics["move"]
        if not self.enable:
            logger.warning(f"{topic} disabled!")
            return
        payload = {
            "src_user_id": src_user_id,
            "dest_user_id": dest_user_id,
            "faces": faces,
        }
        self.client.publish(topic, json.dumps(payload))

    def user_delete(self, user_id: str):
        """
        删除用户

        :param user_id:
        """
        topic = self.topics["delete"]
        if not self.enable:
            logger.warning(f"{topic} disabled!")
            return
        payload = {"user_id": user_id}
        self.client.publish(topic, json.dumps(payload))

    def user_sync(self, user_id: str, faces: List[Dict]):
        """
        同步用户

        :param user_id:
        :param faces:
        """
        topic = self.topics["sync"]
        if not self.enable:
            logger.warning(f"{topic} disabled!")
            return
        payload = {"user_id": user_id, "faces": faces}
        self.client.publish(topic, json.dumps(payload))
