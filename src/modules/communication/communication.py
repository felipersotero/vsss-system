import paho.mqtt.client as mqtt
import serial

########## Comunicação MQTT ##########
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado ao Broker MQTT")

def on_publish(client, userdata, mid):
    i = 1
    #print("Mensagem publicada com sucesso")
    # client.disconnect()  # Desconecta após publicar a mensagem

def connect_to_broker(broker_address, port):
    # Criando um cliente MQTT
    client = mqtt.Client()

    # Configurando callbacks
    client.on_connect = on_connect
    client.on_publish = on_publish

    # Conectando ao broker
    client.connect(broker_address, port, 60)

    # Inicia o loop em segundo plano
    client.loop_start()

    return client  # Retorna o cliente para futuras interações

def publish_mqtt_data(client, topic, message):
    # Publica uma mensagem no tópico especificado
    result = client.publish(topic, message)
    return result

########## Comunicação Serial ##########

def connect_to_serial(serial_port):
    ser = serial.Serial(serial_port, 115200)
    return ser

def send_serial_data(ser, message):
    data_bytes = message.encode('utf-8')
    print(f"data_bytes: {data_bytes}")
    ser.write(data_bytes)

def close_serial(ser):
    ser.close()