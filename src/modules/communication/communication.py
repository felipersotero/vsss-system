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
            # CORREÇÃO CRÍTICA: Coloca apenas o payload (em bytes) na fila.
            # O parser principal em Communication._process_incoming_data espera bytes.
            self._rx_queue.put(msg.payload) 

        except Exception:
            pass


    def read_mqtt_data(self) -> Optional[bytes]:
        """Lê dados MQTT recebidos, retornando o payload em BYTES."""
        try:
            if not self._rx_queue.empty():
                # O item na fila agora é bytes, conforme corrigido em _on_message
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
        if not self.com or not self.com.is_open:
            return False, "Serial port not connected"

        if isinstance(data, str):
            data = data.encode("utf-8")
        
        self.com.write(data)
        return True, "OK"

    def read_serial_data(self) -> Optional[bytes]:
        # Retorna BYTES, não STRING. Não usa decode().
        if self.com.in_waiting > 0:
            return self.com.read(self.com.in_waiting)
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

        # flags de utilização da comunicação
        self._paused = False           # True se o monitoramento estiver pausado
        self._loop_running = False     # True se o loop de monitoramento estiver ativo
        self._pause_condition = threading.Condition()

        # sistema de logs
        self._log_queue: queue.Queue[str] = queue.Queue()
        self.log_listeners: List[Callable[[str], None]] = []

        # listeners para interceptar mensagens recebidas (emulator, controladores, etc.)
        self.rx_listeners: List[Callable[[str], None]] = []
        self._rx_queue: queue.Queue[str] = queue.Queue()

        # estado dos robôs
        self.robot_status = {1: "FAIL", 2: "FAIL", 3: "FAIL"}
        
        self._robot_status_lock = threading.Lock()

        # buffer de dados que vem
        self._incoming_buffer: bytearray = bytearray()

        # Informação sobre os estados dos robôs
        self.robot_last_seen: Dict[int, float] = {1: 0.0, 2: 0.0, 3: 0.0}

        self.ROBOT_TIMEOUT = 3.0  # segundos

        # monitoramento em background
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None


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
        self._monitoring = False
        with self._pause_condition:
            self._paused = False
            self._pause_condition.notify_all()  # libera qualquer thread em espera
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)


    def _monitor_loop(self):
        """Loop principal que lê bytes e alimenta o parser."""
        self._loop_running = True
        last_robot_check = 0

        while self._monitoring:
            with self._pause_condition:
                while self._paused:
                    self._pause_condition.wait()  # espera até resume() ser chamado

            try:
                data = None

                if self.use_mqtt and self.client:
                    data = self.client.read_mqtt_data()
                elif not self.use_mqtt and self.client:
                    data = self.client.read_serial_data()

                if data:
                    self.stats.total_received += 1
                    self._process_incoming_data(data)

                current_time = time.time()
                if current_time - last_robot_check > 1.0:
                    self._update_robot_status()
                    last_robot_check = current_time

                time.sleep(0.01)

            except Exception as e:
                logger.error(f"Erro no monitoramento: {e}")
                time.sleep(1.0)

        self._loop_running = False


    # ============================================================
    # ⬇️ ADICIONE ESTE MÉTODO NOVO AQUI ⬇️
    # ============================================================
    def _process_incoming_data(self, new_bytes: bytes):
        """
        Parser Inteligente:
        - Detecta Texto (Logs do HUB começados com '[')
        - Detecta Pacotes PFOX (Começados com 0xF0)
        - Atualiza status dos robôs baseado no SRC do pacote
        """
        self._incoming_buffer.extend(new_bytes)
        
        # Limita o número máximo de bytes processados por iteração para evitar CPU alta
        max_bytes_per_loop = 1024
        bytes_processed = 0

        while len(self._incoming_buffer) > 0 and bytes_processed < max_bytes_per_loop:
            bytes_processed += 1

            # ---------------------------------------------------
            # CASO A: LOG DE TEXTO (Inicia com '[')
            # ---------------------------------------------------
            if self._incoming_buffer[0] == ord('['): 
                # Procura final de linha ou final do log
                newline_idx = -1
                if b'\n' in self._incoming_buffer:
                    newline_idx = self._incoming_buffer.find(b'\n')
                
                if newline_idx != -1:
                    # Extrai a linha de log e decodifica apenas ela
                    log_line = self._incoming_buffer[:newline_idx+1].decode('utf-8', errors='ignore').strip()
                    self._emit_log(f"[RX HUB] {log_line}")
                    
                    # Consome do buffer
                    del self._incoming_buffer[:newline_idx+1]
                    continue
                else:
                    # Log incompleto, espera mais dados
                    break

            # ---------------------------------------------------
            # CASO B: PACOTE PFOX (Inicia com 0xF0)
            # ---------------------------------------------------
            elif self._incoming_buffer[0] == 0xF0:
                # Tamanho mínimo do header é 7 bytes
                if len(self._incoming_buffer) < 7:
                    break # Espera mais dados
                
                # Byte 6 é o comprimento do payload (LEN)
                payload_len = self._incoming_buffer[6]
                total_packet_len = 7 + payload_len + 2 # Header + Payload + CRC
                
                if len(self._incoming_buffer) < total_packet_len:
                    break # Espera pacote completo chegar
                
                # Temos um pacote completo! Extrai
                packet_data = self._incoming_buffer[:total_packet_len]
                
                # --- LÓGICA DE STATUS DO ROBÔ ---
                # Byte 2 é SRC (Origem). Se for 1, 2 ou 3, é um robô vivo.
                try:
                    src_addr = packet_data[2]
                    if src_addr in [1, 2, 3]: # IDs dos Robôs
                        with self._robot_status_lock:
                            self.robot_last_seen[src_addr] = time.time()
                except IndexError:
                    pass
                
                # --- LÓGICA DE LOGGING RX PFOX (NOVO!) ---
                try:
                    decoded_pkt = PFOXPacket.decode(packet_data)
                    # Loga o conteúdo decodificado em formato legível
                    self._emit_log(f"[RX PFOX] {decoded_pkt}")
                except ValueError as crc_error:
                    # Loga erro de CRC, que é fundamental para depuração
                    self._emit_log(f"⚠️ [RX PFOX ERROR] CRC inválido ou Decodificação falhou: {crc_error}. Bytes: {packet_data.hex(' ')}")
                except Exception as e:
                    self._emit_log(f"❌ [RX PFOX ERROR] Erro inesperado ao decodificar: {e}. Bytes: {packet_data.hex(' ')}")
                
                # Consome do buffer
                del self._incoming_buffer[:total_packet_len]
                continue

            # ---------------------------------------------------
            # CASO C: LIXO / ERRO DE SINCRONIA
            # ---------------------------------------------------
            else:
                # 💡 CORREÇÃO: Registra o descarte de bytes para debug.
                # Captura o byte para log, remove do buffer e tenta sincronizar.
                invalid_byte = self._incoming_buffer[0]
                self._emit_log(f"⚠️ [RX ERROR] Descartando byte inválido (0x{invalid_byte:02X}). Sincronizando...")
                del self._incoming_buffer[0]


    def send_simulated_ack(self, seq_id: int) -> None:
        """
        Simula o Hub/ESPMAIN enviando um ACK (0x20) de volta para o PC.
        Isso força o fluxo RX a processar um pacote PFOX válido.
        """
        try:
            # 1. Cria o pacote ACK (0x20) do ESPMAIN (0xFE) para o PC (0x00)
            ack_packet = self.pfox_controller.create_packet(
                src=Address.ESPMAIN, 
                dst=Address.PC, 
                msg_type=MsgType.ACK, 
                payload=[],
                seq=seq_id # Usa o ID de sequência do pacote que foi enviado
            )
            ack_bytes = ack_packet.to_bytes()
            
            # 2. Publica o pacote diretamente no tópico 'raw'
            if self.client and hasattr(self.client, "publish"):
                self._emit_log(f"Simulando RX → Publicando ACK PFOX (ID {seq_id})")
                
                # A chave aqui é que publish aceita 'bytes' e garante o formato binário.
                self.client.publish("raw", ack_bytes) 
            else:
                self._emit_log("Falha ao simular ACK: Cliente não está conectado ou é Serial.")
                
        except Exception as e:
            self._emit_log(f"Erro na simulação do ACK: {e}")

    def _update_robot_status(self):
            """Atualiza status 'OK'/'FAIL' baseado no tempo da última mensagem."""
            current_time = time.time()
            
            with self._robot_status_lock:
                for robot_id in [1, 2, 3]:
                    # Pega o tempo da última vez que vimos este robô (padrão 0.0)
                    last_seen = self.robot_last_seen.get(robot_id, 0.0)
                    
                    # Se recebemos algo nos últimos 3 segundos (ROBOT_TIMEOUT), está OK
                    if (current_time - last_seen) < getattr(self, 'ROBOT_TIMEOUT', 3.0):
                        if self.robot_status[robot_id] != "OK":
                            self.robot_status[robot_id] = "OK"
                            self._emit_log(f"✅ Robô {robot_id} Online")
                    else:
                        # Timeout
                        if self.robot_status[robot_id] != "FAIL":
                            self.robot_status[robot_id] = "FAIL"
                            # Só loga falha se já tivemos conexão alguma vez (evita spam na inicialização)
                            if last_seen > 0:
                                self._emit_log(f"⚠️ Robô {robot_id} Offline (Timeout)")

    # ============================================================
    # CONTROLE EXTERNO DO LOOP DE COMUNICAÇÃO
    # ============================================================

    def start(self):
        """Inicia ou reinicia a comunicação e monitoramento."""
        self._paused = False
        self._setup_connection()
        self._start_monitoring()

    def pause(self):
        """Pausa o loop de monitoramento sem fechar a conexão."""
        with self._pause_condition:
            self._paused = True
            self._emit_log("Monitoramento pausado")

    def resume(self):
        """Retoma o loop de monitoramento pausado."""
        with self._pause_condition:
            self._paused = False
            self._pause_condition.notify_all()
            self._emit_log("Monitoramento retomado")

    def stop(self):
        """Para completamente o monitoramento e fecha a comunicação."""
        self._paused = False
        self._stop_monitoring()
        self.close()

    # ============================================================
    # MÉTODOS DE CONSULTA DE ESTADO
    # ============================================================

    def is_monitoring(self) -> bool:
        """Retorna True se o monitoramento está ativo."""
        return self._monitoring

    def is_paused(self) -> bool:
        """Retorna True se o monitoramento está pausado."""
        return self._paused

    def is_loop_running(self) -> bool:
        """Retorna True se o loop de monitoramento está rodando."""
        return self._loop_running


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
        Executa um teste de comunicação enviando vários pacotes PFOX e simulando
        o recebimento de um ACK para confirmar o RX/parser.
        Retorna (total_sent, total_ok).
        """
        # Inicializa o controlador PFOX se necessário
        if not hasattr(self, 'pfox_controller'):
            try:
                self.pfox_controller = PFOXController()
            except NameError:
                self._emit_log("❌ ERRO: PFOXController não definido. Verifique o import de protocolHeader.")
                return 0, 0

        total_sent = 0
        total_ok = 0
        
        # O PFOXController precisa ser inicializado antes de ser usado
        pfox_ctrl = self.pfox_controller
        
        # =================================================================
        # SEQUÊNCIA DE TESTES PFOX (Seus cenários)
        # =================================================================
        test_scenarios = [
            {"name": "HEARTBEAT p/ ESPMAIN", "packet_func": lambda: pfox_ctrl.create_packet(dst=Address.ESPMAIN, msg_type=MsgType.HEARTBEAT, payload=[]).to_bytes()},
            {"name": "CMD_FLOW_CTRL (RUN) p/ ROBOT1", "packet_func": lambda: pfox_ctrl.send_flow_control(dst=Address.ROBOT1, value=0x01).to_bytes()},
            {"name": "CMD_SET_SPEED p/ ROBOT2", "packet_func": lambda: pfox_ctrl.send_speed_command(robot_id=Address.ROBOT2, left_speed_real=100, left_speed_desired=150, right_speed_real=90, right_speed_desired=140).to_bytes()},
            {"name": "HEARTBEAT BROADCAST", "packet_func": lambda: pfox_ctrl.create_packet(dst=Address.BROADCAST, msg_type=MsgType.HEARTBEAT, payload=[]).to_bytes()}
        ]

        # =================================================================
        # EXECUÇÃO DO TESTE
        # =================================================================
        for scenario in test_scenarios:
            try:
                # 1. Prepara o envio e obtem o ID ANTES da criação do pacote
                total_sent += 1
                
                # Gera o pacote PFOX em BYTES (A criação do pacote deve atualizar o ID interno)
                packet_bytes = scenario["packet_func"]()
                
                # Pega o ID de sequência que foi usado no pacote (assumindo que o counter foi atualizado)
                # NOTA: Assumimos que 'seq_id_counter' contém o ID do último pacote criado.
                sent_id = pfox_ctrl.seq_id_counter
                
                # 2. Envia o pacote (TX)
                self.send(packet_bytes)
                self._emit_log(f"✨ [TEST TX] Enviado: {scenario['name']}")
                
                # Pequena pausa para garantir que o TX foi processado pelo Broker
                time.sleep(0.15) 
                
                # 3. 💡 SIMULAÇÃO: Publica o ACK de volta para si mesmo (RX)
                self.send_simulated_ack(sent_id) 
                
                # Espera o ACK simulado voltar pelo tópico 'raw' e ser processado pelo RX parser
                time.sleep(0.15) 

                total_ok += 1 

            except Exception as e:
                self._emit_log(f"❌ Erro durante o envio de teste PFOX ({scenario['name']}): {e}")
                
        return total_sent, total_ok
        
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

    # Ajuste sugerido para Communication.reset_connection()
    def reset_connection(self) -> None:
        """Reinicia a conexão atual e reseta estatísticas."""
        self._emit_log("Reiniciando comunicação e resetando estatísticas...")
        
        # 1. Reset total (fecha conexão, limpa stats, define robôs como FAIL)
        self.reset()
        
        # 2. Configura e inicia a nova conexão
        self._setup_connection()

# Correção sugerida para Communication.reset()
    def reset(self) -> None:
        """Reset completo do módulo."""
        self._emit_log("Reset total do módulo de comunicação")
        self.close()
        
        with self._stats_lock:
            self.stats = CommunicationStats()
            self._connection_start_time = time.time()
        
        with self._robot_status_lock:
            # CORREÇÃO: Status inicial é FAIL (ou UNKNOWN) após um reset completo.
            self.robot_status = {1: "FAIL", 2: "FAIL", 3: "FAIL"}

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