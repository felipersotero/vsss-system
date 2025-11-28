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
        # Se não há conexão ATIVA → retorna None sem tentar acessar in_waiting
        if not self.com or not self.com.is_open:
            return None

        try:
            if self.com.in_waiting > 0:
                return self.com.read(self.com.in_waiting)
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
        
        self.ROBOT_TIMEOUT = 3.0  # segundos // Tempo máximo para indicar que o robô está fora.
        
        self.robot_status_error_count = 0

        # monitoramento em background
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None

        # Instancia o Gerador de Pacotes (Gerencia Sequence ID e Estrutura)
        self.pfox_controller = PFOXController()


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

        #logger.info(formatted)
        
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
        """Processa bytes recebidos, decodifica pacotes PFOX ou logs (texto)."""

        self._incoming_buffer.extend(new_bytes)

        max_bytes_per_loop = 1024
        bytes_processed = 0

        while len(self._incoming_buffer) > 0 and bytes_processed < max_bytes_per_loop:
            bytes_processed += 1

            first = self._incoming_buffer[0]

            # ============================================================
            # 1️⃣ LOG DO HUB COMEÇANDO POR '['
            # ============================================================
            if first == ord('['):
                try:
                    newline_idx = self._incoming_buffer.index(b'\n')
                    log_line = self._incoming_buffer[:newline_idx+1].decode(
                        'utf-8', errors='ignore'
                    ).strip()

                    self._emit_log(f"🧾 [RX:LOG] HUB → PC | {log_line}")

                    del self._incoming_buffer[:newline_idx+1]
                    continue
                except ValueError:
                    break  # linha incompleta

            # ============================================================
            # 2️⃣ PACOTE PFOX (0xF0)
            # ============================================================
            if first == 0xF0:
                if len(self._incoming_buffer) < 9:
                    break  # pacote incompleto

                try:
                    decoded_pkt, used_len = PFOXPacket.decode(self._incoming_buffer)

                    # Só chegamos aqui se o pacote está INTEIRO e o CRC está CORRETO.
                    if hasattr(self, 'stats'):
                        self.stats.total_received += 1

                    # Log do pacote decodificado
                    self._log_pfox_packet(decoded_pkt, self._incoming_buffer[:used_len])

                    # Enfileira para a aplicação
                    self._rx_queue.put(decoded_pkt)

                    # Remove exatamente o tamanho consumido
                    del self._incoming_buffer[:used_len]
                    continue

                except ValueError as crc_error:
                    self.stats.total_errors += 1
                    self.robot_status_error_count += 1  # opcional

                    self._emit_log(
                        f"❌ [RX:ERR] HUB → PC | PFOX CRC inválido ({crc_error})"
                    )

                    del self._incoming_buffer[0]
                    continue

                except Exception as e:
                    self.robot_status_error_count += 1
                    self._emit_log(
                        f"❌ [RX PFOX ERROR] Erro inesperado: {e}. "
                        f"Bytes: {self._incoming_buffer.hex(' ')}"
                    )
                    del self._incoming_buffer[0]
                    continue

            # 3️⃣ TEXTO comum recebido (HUB → PC)
            if 32 <= first <= 126 or first in (9, 10, 13):
                newline_pos = None
                for i, b in enumerate(self._incoming_buffer):
                    if b in (10, 13):
                        newline_pos = i
                        break

                if newline_pos is None:
                    break  # ainda não chegou a linha inteira

                text = self._incoming_buffer[:newline_pos+1].decode(
                    'utf-8', errors='ignore'
                ).strip()

                self._emit_log(f"📄 [RX:TEXT] HUB → PC | {text}")

                del self._incoming_buffer[:newline_pos+1]
                continue


            # ============================================================
            # 4️⃣ BYTE NÃO PFOX E NÃO ASCII → DESCARTAR
            # ============================================================
            invalid = self._incoming_buffer[0]
            self._emit_log(f"❌ [RX:ERR] HUB → PC | Byte inválido 0x{invalid:02X}")
            del self._incoming_buffer[0]


    def _log_pfox_packet(self, pkt, raw_bytes):
            """Log simplificado para pacotes recebidos (RX)."""
            
            # Se for ACK, mostra apenas o necessário
            if pkt.msg_type == MsgType.ACK:
                self._emit_log(f"[RX:LOG] {pkt.src.name} ack {pkt.seq24}")
                return

            # Para outros pacotes (Texto, Erro, Status)
            payload_info = f" | Pay={pkt.payload.hex().upper()}" if pkt.len > 0 else ""
            self._emit_log(f"[RX:PFOX] {pkt.src.name} -> PC | {pkt.msg_type.name}{payload_info}")

    def _log_tx_packet(self, pkt: PFOXPacket):
            """
            Gera log formatado para envio (TX).
            Mostra velocidades reais em cm/s para CMD_SET_SPEED.
            """
            # Define o destino (HUB, ROBOT, etc)
            dest_name = pkt.dst.name if hasattr(pkt.dst, 'name') else f"0x{pkt.dst:02X}"
            if dest_name.startswith("ROBOT"):
                target_str = f"p/ {dest_name}"
            elif pkt.dst == Address.BROADCAST:
                target_str = "p/ BROADCAST"
            else:
                target_str = f"p/ {dest_name}"

            # Lógica específica por tipo de mensagem
            details = ""

            if pkt.msg_type == MsgType.CMD_SET_SPEED:
                # Payload esperado: [ID_ROBO, L_REAL_H, L_REAL_L, L_DES_H, L_DES_L, R_REAL_H, R_REAL_L, R_DES_H, R_DES_L]
                # Total 9 bytes. O Byte 0 é o ID repetido, dados começam no Byte 1.
                if len(pkt.payload) >= 9:
                    try:
                        # Converter bytes de volta para inteiro com sinal (signed=True)
                        l_real = int.from_bytes(pkt.payload[1:3], 'big', signed=True)
                        l_des  = int.from_bytes(pkt.payload[3:5], 'big', signed=True)
                        r_real = int.from_bytes(pkt.payload[5:7], 'big', signed=True)
                        r_des  = int.from_bytes(pkt.payload[7:9], 'big', signed=True)
                        
                        details = f" | Vel: L(Real={l_real}, Des={l_des}) R(Real={r_real}, Des={r_des})"
                    except Exception:
                        details = " | Erro decodificando velocidades"
                else:
                    details = f" | Payload Speed Inválido ({len(pkt.payload)} bytes)"

            elif pkt.msg_type == MsgType.CMD_FLOW_CTRL:
                status = "RUN" if (len(pkt.payload) > 0 and pkt.payload[0] == 1) else "STOP"
                details = f" | Flow: {status}"

            elif pkt.msg_type == MsgType.HEARTBEAT:
                details = " | (Ping)"
                
            # Log Final Formatado
            # Ex: [TX] PC -> HUB | Seq=12 | CMD_SET_SPEED p/ ROBOT1 | Vel: L(...) R(...)
            self._emit_log(
                f"[TX] PC -> HUB | Seq={pkt.seq24} | {pkt.msg_type.name} {target_str}{details}"
            )

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
            Envia dados (MQTT ou Serial) com logs humanizados e limpos.
            """
            if not self.client:
                self._emit_log("❌ [TX:ERR] Cliente não inicializado")
                return False, "Client not initialized"

            start_time = time.time()
            self.stats.last_send_timestamp = start_time

            try:
                # 1. Preparação Unificada do Payload (Bytes)
                payload_bytes = None
                mqtt_topic = topic_or_message

                if self.use_mqtt:
                    if message is None: return False, "No payload for MQTT"
                    payload_bytes = message.encode("utf-8") if isinstance(message, str) else message
                else:
                    # Serial: se message for None, o dado está em topic_or_message
                    raw_data = message if message is not None else topic_or_message
                    payload_bytes = raw_data.encode("utf-8") if isinstance(raw_data, str) else raw_data

                # 2. LOG INTELIGENTE (Antes de enviar)
                # Verifica se parece um pacote PFOX (Começa com 0xF0 e tem tamanho mínimo)
                is_pfox = (len(payload_bytes) >= 6 and payload_bytes[0] == 0xF0)
                
                if is_pfox:
                    try:
                        # Tenta decodificar apenas para gerar o log bonito com velocidades
                        pkt_preview,_ = PFOXPacket.decode(payload_bytes)
                        self._log_tx_packet(pkt_preview)
                    except:
                        # Se falhar o decode (ex: pacote incompleto), loga o Hex bruto
                        self._emit_log(f"[TX] Raw PFOX: {payload_bytes.hex(' ').upper()}")
                else:
                    # Se não for PFOX (texto puro ou comando simples)
                    try:
                        text_msg = payload_bytes.decode('utf-8')
                        self._emit_log(f"[TX] Msg: {text_msg}")
                    except:
                        self._emit_log(f"[TX] Bytes: {payload_bytes.hex(' ').upper()}")

                # 3. ENVIO REAL
                success = False
                result_msg = ""

                if self.use_mqtt:
                    success, result_msg = self.client.publish_mqtt_data(mqtt_topic, payload_bytes)
                else:
                    success, result_msg = self.client.send_serial_data(payload_bytes)

                # 4. PÓS-ENVIO (Apenas erro ou atualização de stats)
                latency = (time.time() - start_time) * 1000 if success else None
                self._update_stats(success, latency)

                if not success:
                    self._emit_log(f"❌ [TX:ERR] Falha: {result_msg}")

                # Removido propositalmente o log de "Sucesso" para limpar o terminal.
                return success, result_msg

            except Exception as e:
                self._emit_log(f"❌ [TX:CRIT] {e}")
                return False, str(e)
            
    def send(self, data: Union[bytes,str], topic: str = "raw") -> None:
        """
        Envia dados de forma simplificada. 
        Garante envio como BYTES puros para MQTT ou Serial.
        """
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
            Executa bateria de testes PFOX.
            Limpo: Delega toda a geração de logs para o send_data.
            """

            self._emit_log("--- 🟢 Iniciando Bateria de Testes ---")

            pfox = self.pfox_controller
            
            # Lista simples de comandos para gerar (Lambdas)
            # Não precisamos de nomes/descrições, o send_data já vai ler o pacote e dizer o que é!
            scenarios = [
                # 1. Heartbeat
                lambda: pfox.create_packet(Address.ESPMAIN, MsgType.HEARTBEAT, []).to_bytes(),
                
                # 2. Flow Control (Start Robot 1)
                lambda: pfox.send_flow_control(Address.ROBOT1, 0x01).to_bytes(),
                
                # 3. Set Speed (Robot 2 - Testa a visualização do vetor de velocidade)
                lambda: pfox.send_speed_command(Address.ROBOT2, 100, 150, 90, 140).to_bytes(),
                
                # 4. Broadcast
                lambda: pfox.create_packet(Address.BROADCAST, MsgType.HEARTBEAT, []).to_bytes()
            ]

            total_sent = 0
            total_ok = 0

            for create_bytes in scenarios:
                try:
                    packet_bytes = create_bytes()
                    
                    # Chama send_data passando um tópico genérico "TEST" (usado só se for MQTT)
                    # O send_data vai detectar que é PFOX e gerar o log bonito automaticamente.
                    success, _ = self.send_data("TEST", packet_bytes)
                    
                    total_sent += 1
                    if success:
                        total_ok += 1
                    
                    # Pequena pausa visual entre comandos
                    time.sleep(0.15)

                except Exception as e:
                    self._emit_log(f"❌ Erro crítico no loop de teste: {e}")

            self._emit_log(f"--- 🏁 Teste Finalizado: {total_ok}/{total_sent} sucessos ---")
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

    # ==========================================================================================
    # API DE CONTROLE DE ROBÔS (High-Level)
    # ==========================================================================================

    def send_robot_velocity(self, robot: Address, vl_a: int, vl_d: int, vr_a: int, vr_d: int) -> None:
        """
        Envia comando de velocidade para um robô específico.
        """
        try:
            # Gera pacote correto
            pkg = self.pfox_controller.send_speed_command(robot, vl_a, vl_d, vr_a, vr_d).to_bytes()
            
            # Envia
            self.send_data("VELOCITY", pkg)

        except Exception as e:
            self._emit_log(f"❌ Erro ao enviar velocidade: {e}")

    def request_robot_status(self, robot: Address = Address.BROADCAST) -> None:
        """
        Solicita que 1 robô (ou todos) enviem status (bateria, sensores, etc.).
        """
        try:
            pkg = self.pfox_controller.request_status(robot).to_bytes()
            self.send_data("STATUS", pkg)
        except Exception as e:
            self._emit_log(f"❌ Erro ao pedir status: {e}")


    def send_heartbeat(self) -> None:
        """
        Envia heartbeat (ping) para o Hub/Robôs – evita acionamento do watchdog.
        """
        try:
            pkg = self.pfox_controller.send_heartbeat()
            self.send_data("HEARTBEAT", pkg)
        except Exception as e:
            self._emit_log(f"❌ Erro ao enviar heartbeat: {e}")


    def set_match_state(self, running: bool) -> None:
        """
        Controla início/fim da partida (flow control global).

        running = True  → START
        running = False → STOP
        """
        try:
            flag = FlowType.RUN if running else FlowType.STOP
            pkg = self.pfox_controller.send_flow_control(Address.BROADCAST, flag).to_bytes()
            self.send_data("MATCH_STATE", pkg)
        except Exception as e:
            self._emit_log(f"❌ Erro ao enviar estado da partida: {e}")
