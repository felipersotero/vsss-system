import paho.mqtt.client as mqtt
import serial
import logging
from typing import Optional, Union, Tuple
from dataclasses import dataclass

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConnectionStatus:
    is_connected: bool = False
    error_message: str = ""

class MQTTClient:
    """Singleton class for MQTT communication."""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, broker_address: str, port: int):
        if not hasattr(self, 'client'):
            self.client = mqtt.Client()
            self.client.on_connect = self._on_connect
            self.client.on_publish = self._on_publish
            self.status = ConnectionStatus()
            self._connect(broker_address, port)

    def _on_connect(self, client, userdata, flags, rc: int) -> None:
        """Callback when connection is established."""
        if rc == 0:
            self.status.is_connected = True
            logger.info("Successfully connected to MQTT broker")
        else:
            self.status.error_message = f"Connection failed with code {rc}"
            logger.error(self.status.error_message)

    def _on_publish(self, client, userdata, mid: int) -> None:
        """Callback when message is published."""
        logger.debug(f"Message {mid} published successfully")

    def _connect(self, broker_address: str, port: int) -> None:
        """Establish connection to the MQTT broker."""
        try:
            self.client.connect(broker_address, port, 60)
            self.client.loop_start()
        except Exception as e:
            self.status.error_message = str(e)
            logger.error(f"Failed to connect to MQTT broker: {e}")

    def publish_mqtt_data(self, topic: str, message: str) -> Tuple[bool, str]:
        """Publish message to MQTT topic."""
        try:
            result = self.client.publish(topic, message)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return True, "Message published successfully"
            return False, f"Failed to publish message: {result.rc}"
        except Exception as e:
            return False, str(e)

class SerialConnection:
    """Class for serial communication."""
    def __init__(self, serial_port: str, baud_rate: int = 115200):
        self.port = serial_port
        self.baud_rate = baud_rate
        self.com: Optional[serial.Serial] = None
        self.status = ConnectionStatus()
        self._connect()

    def _connect(self) -> None:
        """Establish serial connection."""
        try:
            self.com = serial.Serial(self.port, self.baud_rate)
            self.status.is_connected = True
            logger.info(f"Serial connection established on {self.port}")
        except Exception as e:
            self.status.error_message = str(e)
            logger.error(f"Failed to establish serial connection: {e}")

    def send_serial_data(self, message: str) -> Tuple[bool, str]:
        """Send data through serial connection."""
        if not self.status.is_connected:
            return False, "Serial connection not established"
        
        try:
            data_bytes = message.encode('utf-8')
            self.com.write(data_bytes)
            return True, "Data sent successfully"
        except Exception as e:
            return False, str(e)

    def __del__(self):
        """Cleanup resources on object destruction."""
        if self.com and self.com.is_open:
            self.com.close()



class Communication:
    """
    Communication handler supporting both MQTT and Serial protocols.

    This class abstracts the connection layer, allowing seamless switching 
    between MQTT and Serial without requiring external code changes.
    """

    def __init__(
        self,
        use_mqtt: bool = True,
        broker_address: str = "localhost",
        port: int = 1883,
        serial_port: str = "/dev/ttyUSB0",
    ):
        self.use_mqtt = use_mqtt
        self.broker_address = broker_address
        self.port = port
        self.serial_port = serial_port
        self.client: Optional[Union["MQTTClient", "SerialConnection"]] = None

        # initialize connection
        self._setup_connection()

    # ============================================================
    # Connection setup
    # ============================================================
    def _setup_connection(self) -> None:
        """Initialize the selected communication method."""
        self.close()  # ensure clean state before setting up
        try:
            if self.use_mqtt:
                self.client = MQTTClient(self.broker_address, self.port)
                logger.info(f"[COMM] MQTT connected → {self.broker_address}:{self.port}")
            else:
                self.client = SerialConnection(self.serial_port)
                logger.info(f"[COMM] Serial connected → {self.serial_port}")
        except Exception as e:
            self.client = None
            logger.error(f"[COMM] Failed to setup communication: {e}")

    # ============================================================
    # Communication methods
    # ============================================================
    def send_data(self, topic_or_message: str, message: Optional[str] = None) -> Tuple[bool, str]:
        """Send data using the active communication client."""
        if not self.client:
            return False, "No communication client initialized"

        try:
            if self.use_mqtt:
                if message is None:
                    return False, "MQTT requires both topic and message"
                return self.client.publish_mqtt_data(topic_or_message, message)
            else:
                return self.client.send_serial_data(topic_or_message)
        except Exception as e:
            logger.error(f"[COMM] Failed to send data: {e}")
            return False, str(e)

    def get_connection_status(self) -> "ConnectionStatus":
        """Return connection status safely."""
        if not self.client:
            return ConnectionStatus(False, "No client initialized")
        try:
            return self.client.status
        except Exception as e:
            logger.error(f"[COMM] Failed to get status: {e}")
            return ConnectionStatus(False, f"Error reading status: {e}")

    # ============================================================
    # Reset & State Control
    # ============================================================
    def reset_connection(self) -> None:
        """Reinitialize the communication using current configuration."""
        logger.info("[COMM] Resetting connection...")
        self._setup_connection()

    def reset(self) -> None:
        """
        Full reset: forgets all previous state and parameters,
        returning to an uninitialized state.
        """
        logger.info("[COMM] Full reset — clearing configuration and client.")
        self.close()
        self.client = None
        self.use_mqtt = True
        self.broker_address = "localhost"
        self.port = 1883
        self.serial_port = "/dev/ttyUSB0"

    def close(self) -> None:
        """Safely close current connection, if any."""
        if self.client:
            try:
                if hasattr(self.client, "disconnect"):
                    self.client.disconnect()
                elif hasattr(self.client, "close"):
                    self.client.close()
            except Exception as e:
                logger.warning(f"[COMM] Error while closing client: {e}")
            finally:
                self.client = None
