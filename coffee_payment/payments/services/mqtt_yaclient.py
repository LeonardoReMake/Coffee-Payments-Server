import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import sys
import threading
from enum import IntEnum


MQTT_SERVER = 'mqtt.cloud.yandex.net'
MQTT_PORT = 8883
ROOTCA_PATH = '/Users/mac14/Desktop/FWSoft/Кофемашины/scripts/verle_missing_drinks/mqtt/rootCA.crt'

REGISTRY_ID = "are9c0fja239plmjmrnn"
REGISTRY_PASSWORD = "ComponentTestRegistryPassword1"

# REGISTRY_COMMANDS = "$registries/" + REGISTRY_ID + "/commands"
# REGISTRY_EVENTS = "$registries/" + REGISTRY_ID + "/events"

# DEVICE_COMMANDS = "$devices/" + DEVICE_ID + "/commands"
# DEVICE_EVENTS = "$devices/" + DEVICE_ID + "/events"

# False means use certificates
USE_DEVICE_LOGIN_PASSWORD = True
USE_REGISTRY_LOGIN_PASSWORD = True

class Qos(IntEnum):
    AT_MOST_ONCE = 0
    AT_LEAST_ONCE = 1

class YaClient:

    def __init__(self, client_id):
        self.received = threading.Event()
        self.qos = Qos.AT_LEAST_ONCE
        self.client = mqtt.Client(client_id=client_id, clean_session=False, transport="tcp")
        self.client.user_data_set(self.received)
        self.client.on_message = self.on_message
        # self.client._connect_timeout = (10);

    def start_with_cert(self, cert_file, key_file):
        self.client.tls_set(ROOTCA_PATH, cert_file, key_file)
        self.client.connect(MQTT_SERVER, MQTT_PORT, 60)
        self.client.loop_start()

    def start_with_login(self, login, password):
        self.client.tls_set(ROOTCA_PATH)
        self.client.username_pw_set(login, password)
        self.client.connect(MQTT_SERVER, MQTT_PORT, 60)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()

    @staticmethod
    def on_message(client, userdata, message):
        print("Received message '" + str(len(message.payload)) + "' on topic '"
              + message.topic + "' with QoS " + str(message.qos))
        userdata.set()

    def publish(self, topic, payload):
        rc = self.client.publish(topic, payload, self.qos)
        rc.wait_for_publish()
        return rc.rc

    def subscribe(self, topic):
        return self.client.subscribe(topic, self.qos)

    def wait_subscribed_data(self):
        self.received.wait()
        self.received.clear()