'''
    @GNOMIO: Aqui está o módulo de comunicação FoxCOM, código responsável pelo controle 
    da comunicação

    Versão: v1.0.0
    Última modificação: 22/11/2025
    Autor: Saulo (update)

    Patch Notes v1.0.0:
    - Início da programação do código
'''
#=============================================================

import paho.mqtt.client as mqtt
import serial
import logging
from typing import Optional, Union, Tuple, List, Dict, Any, Callable
from dataclasses import dataclass, field
import time
import queue
import threading
from datetime import datetime
import statistics

from modules.communication.protocol.protocolHeader import * #Protocolo PFOX


# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConnectionStatus:
    is_connected: bool = False
    error_message: str = ""

@dataclass
class CommunicationStats:
    """Estatísticas completas de comunicação"""
    # Contadores básicos
    total_sent: int = 0
    total_received: int = 0
    total_errors: int = 0
    
    # Latências
    last_rtt_ms: float = 0.0
    last_send_timestamp: float = 0.0
    latencies: List[float] = field(default_factory=list)
    
    # Métricas calculadas
    success_rate: float = 0.0
    avg_latency: float = 0.0
    max_latency: float = 0.0
    min_latency: float = 0.0
    
    # Status do sistema
    connection_uptime: float = 0.0
    last_activity: float = 0.0

class MQTTClient:
    def __init__(self, broker_address: str, port: int):
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_publish = self._on_publish
        self.client.on_message  = self._on_message
        self._rx_queue = queue.Queue()
        self.status = ConnectionStatus()
        self._connect(broker_address, port)


    @property
    def broker_address(self) -> str:
        """Retorna o endereço do broker para a interface."""
        return getattr(self, '_broker_address', 'localhost')
    
    @property
    def port(self) -> int:
        """Retorna a porta para a interface."""
        return getattr(self, '_port', 1883)
    
    def _on_message(self, cliente, userdata, msg):
        try:
            payload = msg.payload

            if isinstance(payload, bytes):
                payload_str = payload.hex(" ").upper()
            else:
                payload_str = str(payload)

            self._rx_queue.put(f"{msg.topic}: {payload_str}")

        except Exception:
            pass


    def read_mqtt_data(self) -> Optional[str]:
        """Lê dados MQTT recebidos."""
        try:
            if not self._rx_queue.empty():
                return self._rx_queue.get_nowait()
            return None
        except Exception:
            return None

    def _on_connect(self, client, userdata, flags, rc: int) -> None:
        """Callback when connection is established."""
        if rc == 0:
            self.status.is_connected = True
        else:
            self.status.error_message = f"Connection failed with code {rc}"

    def _on_publish(self, client, userdata, mid: int) -> None:
        """Callback when message is published."""
        pass  # sem logging direto

    def _connect(self, broker_address: str, port: int) -> None:
        """Establish connection to the MQTT broker."""
        try:
            # Armazena os parâmetros para acesso pela interface
            self._broker_address = broker_address
            self._port = port
            self.client.connect(broker_address, port, 60)
            self.client.loop_start()
            self.client.subscribe("#")  # Assina todos os tópicos por padrão

        except Exception as e:
            self.status.error_message = str(e)

    def publish_mqtt_data(self, topic: str, payload: Union[str, bytes]):
        try:
            if isinstance(payload, str):
                payload = payload.encode("utf-8")

            result = self.client.publish(topic, payload)
            result.wait_for_publish()
            return True, "Published"

        except Exception as e:
            return False, str(e)

    
    def disconnect(self):
        try:
            self.client.loop_stop(force=True)
            self.client.disconnect()
        except Exception:
            pass

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
            self.com = serial.Serial(self.port, self.baud_rate, timeout=1)
            self.status.is_connected = True
        except Exception as e:
            self.status.error_message = str(e)

    def send_serial_data(self, data: Union[str, bytes]):
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.com.write(data)
        return True, "OK"

    def read_serial_data(self) -> Optional[str]:
        """Read data from serial connection."""
        if not self.status.is_connected:
            return None
        try:
            if self.com.in_waiting > 0:
                return self.com.readline().decode("utf-8").strip()
            return None
        except Exception:
            return None

    def __del__(self):
        """Cleanup resources on object destruction."""
        try:
            if self.com and self.com.is_open:
                self.com.close()
        except Exception:
            pass

    def close(self):
        """Close serial connection."""
        try:
            if self.com and self.com.is_open:
                self.com.close()
        except Exception:
            pass


class Communication:
    """
    Communication handler supporting both MQTT and Serial protocols.
    Includes comprehensive logging, statistics, RTT calculation, and external log listeners.
    """

    def __init__(
        self,
        use_mqtt: bool = True,
        broker_address: str = "localhost",
        port: int = 1883,
        serial_port: str = "/dev/ttyUSB0",
    ):
        # parâmetros gerais
        self.use_mqtt = use_mqtt
        self.broker_address = broker_address
        self.port = port
        self.serial_port = serial_port

        # cliente de comunicação
        self.client: Optional[Union[MQTTClient, SerialConnection]] = None

        # sistema de estatísticas
        self.stats = CommunicationStats()
        self._stats_lock = threading.Lock()
        self._connection_start_time = time.time()

        # sistema de logs
        self._log_queue: queue.Queue[str] = queue.Queue()
        self.log_listeners: List[Callable[[str], None]] = []

        # listeners para interceptar mensagens recebidas (emulator, controladores, etc.)
        self.rx_listeners: List[Callable[[str], None]] = []
        self._rx_queue: queue.Queue[str] = queue.Queue()

        # estado dos robôs
        self.robot_status = {1: "FAIL", 2: "FAIL", 3: "FAIL"}

        self._robot_status_lock = threading.Lock()

        # monitoramento em background
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None

        self._setup_connection()

    # ============================================================
    # SISTEMA DE LOG
    # ============================================================

    def add_log_listener(self, callback: Callable[[str], None]):
        """Register a callback for external log handling (e.g., GUI)."""
        self.log_listeners.append(callback)

    def _emit_log(self, msg: str):
        """Send log message to listeners and standard logging."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted = f"[{timestamp}] {msg}"

        logger.info(formatted)
        
        # Adiciona à fila interna
        self._log_queue.put(formatted)

        # Envia para listeners externos
        for cb in self.log_listeners:
            try:
                cb(formatted)
            except Exception as e:
                logger.error(f"Error in log listener: {e}")

    def read_logs(self) -> List[str]:
        """Lê e limpa os logs pendentes (para interface)."""
        logs = []
        while not self._log_queue.empty():
            try:
                logs.append(self._log_queue.get_nowait())
            except queue.Empty:
                break
        return logs

    # ============================================================
    # CONEXÃO E CONFIGURAÇÃO
    # ============================================================
    def get_responses(self) -> List[str]:
        """
        Retorna todas as mensagens recebidas desde a última chamada.
        Usado pela thread de comunicação bidirecional.
        """
        responses = []
        while not self._rx_queue.empty():
            try:
                responses.append(self._rx_queue.get_nowait())
            except queue.Empty:
                break
        return responses


    def _setup_connection(self) -> None:
        """Initialize the selected communication method."""
        self.close()

        try:
            if self.use_mqtt:
                self.client = MQTTClient(self.broker_address, self.port)
                mode_str = f"MQTT → {self.broker_address}:{self.port}"
            else:
                self.client = SerialConnection(self.serial_port)
                mode_str = f"Serial → {self.serial_port}"

            if self.client and self.client.status.is_connected:
                self._emit_log(f"Conectado via {mode_str}")
                self._start_monitoring()
            else:
                self._emit_log(f"Falha na conexão {mode_str}")

        except Exception as e:
            self.client = None
            self._emit_log(f"Erro ao inicializar comunicação: {e}")

    def _update_stats(self, success: bool = True, latency: Optional[float] = None):
        """Atualiza estatísticas de forma thread-safe."""
        with self._stats_lock:
            self.stats.total_sent += 1
            if not success:
                self.stats.total_errors += 1
            
            if latency is not None:
                self.stats.last_rtt_ms = latency
                self.stats.latencies.append(latency)
                
                # Atualiza métricas calculadas
                if self.stats.latencies:
                    self.stats.avg_latency = statistics.mean(self.stats.latencies[-100:])  # Últimos 100 valores
                    self.stats.max_latency = max(self.stats.latencies)
                    self.stats.min_latency = min(self.stats.latencies) if len(self.stats.latencies) > 1 else latency
            
            # Calcula taxa de sucesso
            total_attempts = self.stats.total_sent
            if total_attempts > 0:
                self.stats.success_rate = ((total_attempts - self.stats.total_errors) / total_attempts) * 100
            
            # Atualiza tempos
            self.stats.connection_uptime = time.time() - self._connection_start_time
            self.stats.last_activity = time.time()

    # ============================================================
    # MONITORAMENTO EM BACKGROUND
    # ============================================================
    def add_rx_listener(self, callback: Callable[[str], None]):
        """
        Registra callbacks que recebem mensagens RX da comunicação.
        Usado pelo emulator ou sistemas de controle.
        """
        if callback not in self.rx_listeners:
            self.rx_listeners.append(callback)

    def _start_monitoring(self):
        """Inicia thread de monitoramento."""
        if self._monitoring:
            return
            
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self._emit_log("Monitoramento iniciado")

    def _stop_monitoring(self):
        """Para thread de monitoramento."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)

    def _monitor_loop(self):
        """Loop principal de monitoramento."""
        last_robot_update = 0
        while self._monitoring:
            try:
                current_time = time.time()
                
                # === SERIAL RX ===
                if not self.use_mqtt and self.client:
                    data = self.client.read_serial_data()
                    if data:
                        self.stats.total_received += 1
                        self._emit_log(f"[RX] {data}")
                        self._rx_queue.put(data)


                        for cb in self.rx_listeners:
                            try:
                                cb(data)
                            except Exception:
                                pass

                # === MQTT RX ===
                elif self.use_mqtt and self.client:
                    data = self.client.read_mqtt_data()
                    if data:
                        self.stats.total_received += 1
                        self._emit_log(f"[RX] {data}")
                        self._rx_queue.put(data)


                        for cb in self.rx_listeners:
                            try:
                                cb(data)
                            except Exception:
                                pass

                
                # Atualiza status dos robôs periodicamente (simulado)
                if current_time - last_robot_update > 2.0:  # A cada 2 segundos
                    self._update_robot_status()
                    last_robot_update = current_time
                
                time.sleep(0.1)  # 100ms
                
            except Exception as e:
                logger.error(f"Erro no loop de monitoramento: {e}")
                time.sleep(1.0)

    def _update_robot_status(self):
        """Atualiza status dos robôs (simulado - substituir por lógica real)."""
        with self._robot_status_lock:
            for robot_id in self.robot_status:
                # Simula mudanças ocasionais de status
                if self.stats.total_sent > 0 and self.stats.success_rate < 95:
                    # Chance maior de falha se taxa de sucesso baixa
                    if hash(f"{robot_id}{time.time():.0f}") % 100 < 15:
                        self.robot_status[robot_id] = "FAIL"
                    else:
                        self.robot_status[robot_id] = "OK"
                else:
                    # Normalmente OK
                    if hash(f"{robot_id}{time.time():.0f}") % 100 < 5:
                        self.robot_status[robot_id] = "FAIL"
                    else:
                        self.robot_status[robot_id] = "OK"

    # ============================================================
    # COMUNICAÇÃO PRINCIPAL
    # ============================================================
    def send_data(self, topic_or_message: str, message: Optional[Union[bytes,str]] = None) -> Tuple[bool, str]:
        """
        Envia dados usando o cliente ativo (MQTT ou Serial).
        Gera logs completos:
        - conteúdo enviado
        - protocolo utilizado
        - resultado (OK / falha)
        - latência medida
        """

        if not self.client:
            self._emit_log("❌ Falha ao enviar: cliente não inicializado")
            return False, "No communication client initialized"

        # Marca tempo inicial do envio
        start_time = time.time()
        self.stats.last_send_timestamp = start_time

        try:
            # ================================================================
            # ENVIO MQTT
            # ================================================================
            if self.use_mqtt:
                if message is None:
                    return False, "MQTT requires payload"

                is_bytes = isinstance(message, bytes)

                # Log bonito
                payload_log = message.hex(" ").upper() if is_bytes else message
                self._emit_log(f"[TX MQTT] topic='{topic_or_message}' payload='{payload_log}'")

                success, result_msg = self.client.publish_mqtt_data(topic_or_message, message)

                latency = (time.time() - start_time) * 1000 if success else None

            # ================================================================
            # ENVIO SERIAL
            # ================================================================
            else:
                # Em Serial o "topic_or_message" é sempre o PAYLOAD se message=None
                if isinstance(topic_or_message, bytes):
                    full_msg = topic_or_message
                elif isinstance(message, bytes):
                    full_msg = message
                elif message is None:
                    # Só string -> vira bytes
                    full_msg = topic_or_message.encode("utf-8")
                else:
                    # Caso queira string + string concatenada (sem bytes)
                    full_msg = (str(topic_or_message) + str(message)).encode("utf-8")

                payload_log = full_msg.hex(" ").upper()
                self._emit_log(f"[TX SERIAL] bytes={payload_log}")

                success, result_msg = self.client.send_serial_data(full_msg)
                latency = (time.time() - start_time) * 1000 if success else None


            # ================================================================
            # ATUALIZA ESTATÍSTICAS DO SISTEMA
            # ================================================================
            self._update_stats(success, latency)

            # ================================================================
            # LOG FINAL DO ENVIO
            # ================================================================
            if success:
                if isinstance(message, bytes):
                    payload_info = f"payload(bytes)={message.hex(' ').upper()}"
                else:
                    payload_info = f"payload={message}" if message else ""

                self._emit_log(
                    f"✔ Enviado com sucesso | Conteúdo='{topic_or_message}' {payload_info} "
                    f"| Latência={latency:.1f}ms"
                )

            else:
                if isinstance(message, bytes):
                    payload_info = f"payload(bytes)={message.hex(' ').upper()}"
                else:
                    payload_info = f"payload={message}" if message else ""

                self._emit_log(
                    f"❌ Falha ao enviar '{topic_or_message}' {payload_info} | Motivo: {result_msg}"
                )


            return success, result_msg

        except Exception as e:
            # Falha crítica no envio
            self._update_stats(False)
            self._emit_log(f"❌ Erro crítico no envio: {e}")
            return False, str(e)

    def send(self, data: Union[str, bytes], topic: str = "raw") -> None:
        try:
            if self.use_mqtt:
                self.send_data(topic, data)
            else:
                self.send_data(data, None)

        except Exception as e:
            self._emit_log(f"Erro no envio: {e}")





    # ============================================================
    # ESTATÍSTICAS E STATUS (PARA INTERFACE)
    # ============================================================

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas para a interface."""
        with self._stats_lock:
            return {
                "mode": "MQTT" if self.use_mqtt else "Serial",
                "tx": self.stats.total_sent,
                "rx_ok": self.stats.total_sent - self.stats.total_errors,  # Pacotes bem-sucedidos
                "avg_latency": round(self.stats.avg_latency, 1) if self.stats.latencies else None,
                "last_latency": round(self.stats.last_rtt_ms, 1) if self.stats.last_rtt_ms > 0 else None,
                "success_rate": round(self.stats.success_rate, 1),
                "total_errors": self.stats.total_errors,
                "uptime": round(self.stats.connection_uptime, 1),
            }

    def get_robot_status(self) -> Dict[int, str]:
        """Retorna status dos robôs para a interface."""
        with self._robot_status_lock:
            return self.robot_status.copy()

    # ============================================================
    # TESTES E DIAGNÓSTICOS
    # ============================================================

    def run_test(self) -> Tuple[int, int]:
        """
        Executa um teste completo de comunicação (compatível com a interface).
        O teste:
        - Envia uma sequência de mensagens
        - Mede latência real
        - Conta envios bem-sucedidos
        - Funciona em MQTT ou Serial
        """
        self._emit_log("=== Iniciando teste de comunicação ===")

        if not self.client or not self.client.status.is_connected:
            self._emit_log("❌ Nenhuma conexão ativa — teste abortado.")
            return (0, 0)

        # Pacotes que serão enviados
        test_messages = [
            ("TEST_PING",        "Ping de latência"),
            ("TEST_DATA",        "Teste de payload"),
            ("TEST_ACK",         "Teste de confirmação"),
            ("TEST_SPEED",       "Teste de velocidade"),
            ("TEST_RELIABILITY", "Teste de estabilidade"),
        ]

        sent = 0
        success = 0

        # Marca início do teste
        test_start = time.time()

        for idx, (msg, description) in enumerate(test_messages):
            topic = f"test/topic/{idx}"
            sent += 1

            try:
                self._emit_log(f"📡 Enviando {description}: {msg}")

                # Envio
                if self.use_mqtt:
                    ok, result = self.send_data(topic, msg)
                else:
                    ok, result = self.send_data(msg)

                # Resultado
                if ok:
                    success += 1
                    self._emit_log(f"  ✔ Sucesso: {result}")
                else:
                    self._emit_log(f"  ❌ Falha: {result}")

                # Pequena pausa controlada
                time.sleep(0.08)

            except Exception as e:
                self._emit_log(f"❌ Erro fatal ao enviar pacote {idx}: {e}")

        total_time = (time.time() - test_start) * 1000  # ms

        # Finalização
        self._emit_log("=== Teste Finalizado ===")
        self._emit_log(f"Resumo: {success}/{sent} pacotes OK")
        self._emit_log(f"Duração total: {total_time:.1f} ms")

        return sent, success


    def start_monitoring(self) -> None:
        """Inicia monitoramento (para interface)."""
        self._start_monitoring()

    def stop_monitoring(self) -> None:
        """Para monitoramento (para interface)."""
        self._stop_monitoring()

    def is_connected(self)-> bool:
        """Retorna o status da conexão atual."""
        if not self.client:
            return False
        return self.client.status.is_connected
    # ============================================================
    # CONTROLE DE ESTADO E LIMPEZA
    # ============================================================

    def reset_connection(self) -> None:
        """Reinicia a conexão atual."""
        self._emit_log("Reiniciando comunicação...")
        self._stop_monitoring()
        self._setup_connection()

    def reset(self) -> None:
        """Reset completo do módulo."""
        self._emit_log("Reset total do módulo de comunicação")
        self.close()
        
        with self._stats_lock:
            self.stats = CommunicationStats()
            self._connection_start_time = time.time()
        
        with self._robot_status_lock:
            self.robot_status = {1: "OK", 2: "OK", 3: "OK"}

    def close(self) -> None:
        """Fecha conexões de forma segura."""
        self._stop_monitoring()
        
        if self.client:
            try:
                if hasattr(self.client, "disconnect"):
                    self.client.disconnect()
                elif hasattr(self.client, "close"):
                    self.client.close()
            except Exception as e:
                self._emit_log(f"Erro ao fechar cliente: {e}")
            finally:
                self.client = None
                self._emit_log("Comunicação encerrada")