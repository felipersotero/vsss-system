import paho.mqtt.client as mqtt

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

def publish_data(client, topic, message):
    # Publica uma mensagem no tópico especificado
    result = client.publish(topic, message)
    return result

# Configurações do broker MQTT
# broker_address = "mqtt.eclipse.org"
# port = 1883

# # Conecta ao broker
# mqtt_client = connect_to_broker(broker_address, port)

# # Publica uma mensagem no tópico "topic/test"
# publish_data(mqtt_client, "topic/test", "Hello MQTT")

# # Aguarda a conclusão da publicação e da desconexão
# mqtt_client.loop_forever()