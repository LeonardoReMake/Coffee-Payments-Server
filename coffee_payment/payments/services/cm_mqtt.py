import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import struct
import json
from payments.utils.logging import log_error, log_info

MQTT_HOST = 'mqtt-proxy'
MQTT_PORT = 1883

# Обратный вызов для обработки подтверждений публикации сообщений
def on_publish(client, userdata, mid):
    log_info(f'Message {mid} published successfully', 'yookassa_payment_result_webhook')
    print(f'Message {mid} published successfully')

# Обратный вызов для обработки успешного подключения
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log_info('Connected to MQTT broker successfully', 'yookassa_payment_result_webhook')
        print('Connected to MQTT broker successfully')
    else:
        log_error(f'Failed to connect to MQTT broker, return code {rc}', 'yookassa_payment_result_webhook')
        print(f'Failed to connect to MQTT broker, return code {rc}')

crc8_tab = [
    0, 94, 188, 226, 97, 63, 221, 131, 194, 156, 126, 32, 163, 253, 31, 65, 157, 195, 33,
    127, 252, 162, 64, 30, 95, 1, 227, 189, 62, 96, 130, 220, 35, 125, 159, 193, 66, 28, 254,
    160, 225, 191, 93, 3, 128, 222, 60, 98, 190, 224, 2, 92, 223, 129, 99, 61, 124, 34, 192,
    158, 29, 67, 161, 255, 70, 24,
    250, 164, 39, 121, 155, 197, 132, 218, 56, 102, 229, 187, 89, 7, 219, 133, 103, 57, 186,
    228, 6, 88, 25, 71, 165, 251, 120, 38, 196, 154, 101, 59, 217, 135, 4, 90, 184, 230, 167,
    249, 27, 69, 198, 152, 122, 36, 248, 166, 68, 26, 153, 199, 37, 123, 58, 100, 134, 216,
    91, 5, 231, 185, 140, 210, 48, 110, 237,
    179, 81, 15, 78, 16, 242, 172, 47, 113, 147, 205, 17, 79, 173, 243, 112, 46, 204, 146,
    211, 141, 111, 49, 178, 236, 14, 80, 175, 241, 19, 77, 206, 144, 114, 44, 109, 51, 209,
    143, 12, 82, 176, 238, 50, 108, 142, 208, 83, 13, 239, 177, 240, 174, 76, 18, 145, 207,
    45, 115, 202, 148, 118, 40, 171, 245, 23, 73, 8,
    86, 180, 234, 105, 55, 213, 139, 87, 9, 235, 181, 54, 104, 138, 212, 149, 203, 41, 119,
    244, 170, 72, 22, 233, 183, 85, 11, 136, 214, 52, 106, 43, 117, 151, 201, 74, 20, 246,
    168, 116, 42, 200, 150, 21, 75, 169, 247, 182, 232, 10, 84, 215, 137, 107, 53
]

def calc_crc8(send_data, offset, length):
    ret = 0x8C  # Initial value as per the C++ code
    for i in range(offset, offset + length):
        ret = crc8_tab[0xFF & (ret ^ send_data[i])]
    return ret

def create_message(header, version, msg_body, tail, protocol_command=None):
    if protocol_command is not None:
        msg_body = struct.pack('B', protocol_command) + msg_body

    body_length = len(msg_body)
    offset = 0
    message_crc = calc_crc8(msg_body, offset, body_length)   # 1 byte for CRC

    # Use struct to pack data in a binary format according to the given fields
    message = struct.pack(
        '>H B H B {}s H'.format(body_length),
        header,          # 2 bytes
        version,         # 1 byte
        body_length,     # 2 bytes
        message_crc,     # 1 byte
        msg_body,        # variable length
        tail             # 2 bytes
    )

    return message

def generate_json_payload(order_uuid, drink_uuid, size, price):
    return json.dumps({
        "orderUuid": order_uuid,
        "drinkNo": drink_uuid,
        "textFlag": size,
        "price": int(price)
    }, separators=(',', ':')).encode('utf-8')

def generate_mqtt_payload(order_json):
    header = 0xAA55
    version = 0x01
    msg_body = order_json
    tail = 0x8866
    protocol_command = 0x22
    return create_message(header, version, msg_body, tail, protocol_command)

def send_cmd_make_drink(order_uuid, drink_uuid, size, price):
    # MQTT client setup
    mqtt_client = mqtt.Client()
    mqtt_client.on_publish = on_publish 
    mqtt_client.on_connect = on_connect
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
    
    log_info('Generating payload', 'yookassa_payment_result_webhook')
    json_payload = generate_json_payload(order_uuid, drink_uuid, size, price)
    log_info(f'Payload: {str(json_payload)}', 'yookassa_payment_result_webhook')
    payload = generate_mqtt_payload(json_payload)
    print('Sending payload: ' + str(payload))
    log_info(f'Payload: {str(payload)}', 'yookassa_payment_result_webhook')
    # res = mqtt_client.publish("technical", payload)
    # if res != mqtt.MQTT_ERR_SUCCESS:
    #     log_info(f'Error while sending message', 'yookassa_payment_result_webhook')
    
    publish.single(hostname=MQTT_HOST, port=MQTT_PORT, topic="technical", payload=payload, keepalive=1)

    return "Payment Successful, order has been sent to MQTT broker.", 200