'''
    @GNOMIO: Este módulo gerencia a comunicação via MQTT ou Serial com o HUB e robôs.
    representa uma refatoração completa do sistema de comunicação,
    incluindo análise detalhada dos robôs, estatísticas de comunicação,

    Versão: v1.15.40
    Última modificação: 18/12/2025
    Autor: Saulo (update)

    Patch Notes v1.15.40:
    - Sistema de análise dos robôs
    - Logs aprimorados para pacotes PFOX
    - Correção crítica na leitura MQTT (payload agora é bytes puros)
    - Estatísticas completas de comunicação
    - Suporte a listeners externos para logs e mensagens RX
    - Refatoração geral para melhor organização e clareza
    - Implementação de locks para segurança em threads
    - Monitoramento em background robusto
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
    @GNÔMIO: Communication handler supporting both MQTT and Serial protocols.
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

        self._write_lock = threading.Lock()
        self._send_lock = threading.Lock()

        # flags de utilização da comunicação
        self._paused = False           # True se o monitoramento estiver pausado
        self._loop_running = False     # True se o loop de monitoramento estiver ativo
        self._pause_condition = threading.Condition()

        # sistema de logs
        self._log_queue: queue.Queue[str] = queue.Queue()
        self.log_listeners: List[Callable[[str], None]] = []

        # listeners para interceptar mensagens recebidas (emulator, controladores, etc.)
        self.rx_listeners: List[Callable[[str], None]] = []
        self._rx_queue: queue.Queue[Any] = queue.Queue(maxsize=100)  # Limite para evitar crescimento ilimitado
        self._rx_lock = threading.Lock()  # Lock para proteger o buffer e fila RX

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

        # Flag para controle de envio de informações
        self.sending_enabled = False

        self._pending_acks: Dict[int, float] = {}  # {seq_id: timestamp_envio}


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
            else:
                self._emit_log(f"Falha na conexão {mode_str}")

        except Exception as e:
            self.client = None
            self._emit_log(f"Erro ao inicializar comunicação: {e}")

    def connect(self):
        """Estabelece a conexão sem iniciar o monitoramento."""
        if not self.is_connected():
            self._setup_connection()
            self._emit_log("Conexão estabelecida")
        else:
            self._emit_log("Já conectado")

    def set_sending_enabled(self, enabled: bool):
        """Habilita ou desabilita o envio de informações."""
        self.sending_enabled = enabled
        self._emit_log(f"Envio de informações {'habilitado' if enabled else 'desabilitado'}")

    def is_sending_enabled(self) -> bool:
        """Retorna se o envio está habilitado."""
        return self.sending_enabled

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


    def _process_incoming_data(self, new_bytes: bytes):
        """Processa bytes recebidos, delegando para métodos específicos por tipo."""
        # --- DEBUG VISUAL (Opcional: Mostra bytes brutos chegando) ---
        # Útil para saber se o Arduino está enviando algo, mesmo que o protocolo falhe
        # self._emit_log(f"⚡ RAW: {new_bytes.hex(' ').upper()}")
        
        with self._rx_lock:
            self._incoming_buffer.extend(new_bytes)

            # Limite o buffer para evitar vazamento de memória
            if len(self._incoming_buffer) > 10240:  # 10 KB
                self._emit_log("⚠️ Buffer RX sobrecarregado, descartando dados antigos")
                self._incoming_buffer = self._incoming_buffer[-5120:]  # Mantém os últimos 5 KB

            max_iterations = 1024  # Proteção contra loop infinito
            iterations = 0

            while len(self._incoming_buffer) > 0 and iterations < max_iterations:
                iterations += 1
                first = self._incoming_buffer[0]

                if first == ord('['):
                    self._process_log_line()
                elif first == 0xF0:
                    self._process_pfox_packet()
                elif 32 <= first <= 126 or first in (9, 10, 13):
                    self._process_text_line()
                else:
                    self._process_garbage()

    def _process_log_line(self):
        """Processa uma linha de log começando com '['."""
        try:
            newline_idx = self._incoming_buffer.index(b'\n')
            line_bytes = self._incoming_buffer[:newline_idx+1]
            log_line = line_bytes.decode('utf-8', errors='ignore').strip()
            
            self._emit_log(f"🧾 [RX:LOG] HUB → PC | {log_line}")
            del self._incoming_buffer[:newline_idx+1]
        except ValueError: 
            pass  # Aguarda mais dados

    def _process_pfox_packet(self):
        """Processa um pacote PFOX começando com 0xF0."""
        if len(self._incoming_buffer) < 11:  # Tamanho mínimo
            return  # Aguarda mais dados
        
        try:
            decoded_pkt, used_len = PFOXPacket.decode(self._incoming_buffer)
            self._handle_decoded_packet(decoded_pkt, used_len)
            del self._incoming_buffer[:used_len]
        except Exception as e:
            err_msg = str(e).upper()
            if "INCOMPLETE" in err_msg or "CURTO" in err_msg:
                return  # Aguarda mais dados
            # Erro de CRC/formato: pula o 0xF0
            self.stats.total_errors += 1
            self._emit_log(f"❌ [RX:ERR] PFOX Corrompido ({err_msg})")
            del self._incoming_buffer[0]

    def _process_text_line(self):
        """Processa uma linha de texto comum."""
        try:
            newline_idx = -1
            for i, b in enumerate(self._incoming_buffer):
                if b in (10, 13):
                    newline_idx = i
                    break
            
            if newline_idx == -1:
                if len(self._incoming_buffer) > 256:
                    del self._incoming_buffer[0]  # Evita buffer muito grande
                return
            
            text = self._incoming_buffer[:newline_idx+1].decode('utf-8', errors='ignore').strip()
            if text:
                self._emit_log(f"📄 [RX:TEXT] HUB → PC | {text}")
            
            del self._incoming_buffer[:newline_idx+1]
        except:
            del self._incoming_buffer[0]

    def _process_garbage(self):
        """Remove byte inválido (lixo)."""
        del self._incoming_buffer[0]

    def _handle_decoded_packet(self, decoded_pkt: Any, used_len: int):
        """
        Trata o pacote já decodificado (PFOXPacket), atualiza stats e
        distribui para a lógica correta (Status, Ack, RTT).
        """
        current_time = time.time()

        # RX Real: Incrementa apenas quando um pacote PFOX válido chega
        with self._stats_lock:
            self.stats.total_received += 1
            self.stats.last_activity = current_time

        # --- LOG PARA A INTERFACE ---
        # Formata: [RX] Source -> PC | Tipo
        log_msg = f"[RX] {decoded_pkt.src.name} -> PC | {decoded_pkt.msg_type.name}"
        
        # Adiciona detalhes do payload se houver (Hexadecimal bonito)
        if decoded_pkt.payload and len(decoded_pkt.payload) > 0:
            log_msg += f" | Pay: {decoded_pkt.payload.hex().upper()}"
            
        self._emit_log(log_msg)

        # ---------------------------------------------------------------------
        # 1. ATUALIZAÇÃO DE PRESENÇA (PROVA DE VIDA)
        # ---------------------------------------------------------------------
        # Se a mensagem veio de um Robô (R1, R2, R3), independente do tipo (ACK, STATUS, ERRO),
        # significa que o rádio dele está funcionando. Atualizamos o Watchdog.
        if decoded_pkt.src.value in [Address.ROBOT1.value, Address.ROBOT2.value, Address.ROBOT3.value]:
            rid = decoded_pkt.src.value
            with self._robot_status_lock:
                self.robot_last_seen[rid] = current_time
                if self.robot_status[rid] != "OK":
                    self._emit_log(f"✅ [RX] Robô {rid} voltou Online (Msg Direta)")
                    self.robot_status[rid] = "OK"

        # ---------------------------------------------------------------------
        # 2. TRATAMENTO POR TIPO DE MENSAGEM
        # ---------------------------------------------------------------------
        
        # --- A. STATUS (0x30) ---
        if decoded_pkt.msg_type == MsgType.STATUS:
            # Caso HUB: O Hub envia vetor de presença [StatusR1, StatusR2, StatusR3]
            if decoded_pkt.src == Address.ESPMAIN:
                self._update_network_status(decoded_pkt.payload)
            
            # Caso Robô: Telemetria (Bateria, Sensores, etc - Implementar decoding futuro)
            # A presença já foi atualizada no bloco 1 acima.
            elif decoded_pkt.src != Address.ESPMAIN:
                pass 

        # --- B. ACK (0x20) - CÁLCULO DE RTT ---
        elif decoded_pkt.msg_type == MsgType.ACK:
            # Calcula o tempo de ida e volta baseado no Sequence ID
            seq_id = decoded_pkt.seq24
            if seq_id in self._pending_acks:
                rtt = (current_time - self._pending_acks[seq_id]) * 1000 # ms
                self._update_stats(is_tx=False, success=True, latency=rtt)
                # Opcional: Logar latência se for alta
                # if rtt > 100: self._emit_log(f"⚠️ High Latency: {rtt:.0f}ms")
                del self._pending_acks[seq_id]

        # --- C. ERROR (0x50) ---
        elif decoded_pkt.msg_type == MsgType.ERROR:
             self._emit_log(f"❌ Erro reportado por {decoded_pkt.src.name}")

    def _update_network_status(self, payload: bytes):
        """
        Processa o relatório de presença enviado pelo HUB (ESPMAIN).
        Payload esperado: [R1_Status, R2_Status, R3_Status] onde 1=ON, 0=OFF.
        """
        # Proteção básica
        if not payload or len(payload) < 3:
            return

        current_time = time.time()
        
        with self._robot_status_lock:
            # O payload do Hub é posicional: índice 0 = Robô 1, índice 1 = Robô 2...
            for i in range(1, 4):
                status_byte = payload[i-1]
                
                # Se o Hub diz que o robô está Online (1)
                if status_byte == 1:
                    # O PULO DO GATO: Atualizamos 'last_seen' com o tempo ATUAL do PC.
                    # Isso impede que o método '_check_robot_timeout' (watchdog) 
                    # marque o robô como FAIL.
                    self.robot_last_seen[i] = current_time
                    new_status = "OK"
                else:
                    # Se o Hub diz que está Offline, podemos marcar FAIL imediatamente
                    # ou deixar o watchdog expirar. Vamos confiar no Hub:
                    new_status = "FAIL"

                # Atualiza a string de status apenas se mudou (para não poluir o log)
                if self.robot_status[i] != new_status:
                    self.robot_status[i] = new_status
                    
                    if new_status == "OK":
                        self._emit_log(f"✅ Rede: Robô {i} Online (Confirmado pelo Hub)")
                    else:
                        self._emit_log(f"⚠️ Rede: Robô {i} Offline (Confirmado pelo Hub)")
                        
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
        self._emit_log("🛑 Enviando STOP para todos os robôs...")
        try:
            self.set_match_state(False)  # Envia STOP para BROADCAST
        except Exception as e:
            self._emit_log(f"❌ Erro ao enviar STOP: {e}")
        
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
    def send_data(self, topic_or_message: str, message: Optional[Union[bytes, str]] = None, verbose: bool = True) -> Tuple[bool, str]:
            """
            Envia dados (MQTT ou Serial) de forma thread-safe com log humanizado opcional.
            """
            if not self.client:
                self._emit_log("❌ [TX:ERR] Cliente não inicializado")
                return False, "Client not initialized"

            # 1. PREPARAÇÃO DO PAYLOAD
            try:
                # Helper para garantir conversão para bytes
                to_bytes = lambda d: d.encode("utf-8") if isinstance(d, str) else d

                if self.use_mqtt:
                    if message is None:
                        return False, "MQTT requer um tópico e um payload"
                    mqtt_topic = topic_or_message
                    payload_bytes = to_bytes(message)
                else:
                    # Serial: se message for None, o dado está em topic_or_message
                    raw_data = message if message is not None else topic_or_message
                    payload_bytes = to_bytes(raw_data)
                    mqtt_topic = "serial" # Apenas para referência interna

                if not payload_bytes:
                    return False, "Payload vazio"

            except Exception as e:
                return False, f"Erro na preparação dos dados: {e}"

            # 2. LOG INTELIGENTE (Executa apenas se verbose=True)
            if verbose:
                self._smart_log_tx(payload_bytes)

            # 3. ENVIO REAL (Thread-Safe)
            start_time = time.time()
            self.stats.last_send_timestamp = start_time

            try:
                # O Lock impede que duas threads enviem ao mesmo tempo e "atropelem" os bytes
                with self._send_lock: 
                    if self.use_mqtt:
                        success, result_msg = self.client.publish_mqtt_data(mqtt_topic, payload_bytes)
                    else:
                        success, result_msg = self.client.send_serial_data(payload_bytes)

                # 4. PÓS-ENVIO
                latency = (time.time() - start_time) * 1000 if success else None
                self._update_stats(success, latency)

                if not success:
                    self._emit_log(f"❌ [TX:ERR] Falha no transporte: {result_msg}")

                return success, result_msg

            except Exception as e:
                self._emit_log(f"❌ [TX:CRIT] Erro de hardware/rede: {e}")
                return False, str(e)

    def _smart_log_tx(self, payload: bytes):
        """Método auxiliar para processar a visualização do log sem poluir o send_data."""
        # Verifica se parece um pacote PFOX (Começa com 0xF0)
        if len(payload) >= 6 and payload[0] == 0xF0:
            try:
                pkt_preview, _ = PFOXPacket.decode(payload)
                self._log_tx_packet(pkt_preview)
                return
            except:
                self._emit_log(f"[TX] Raw PFOX: {payload.hex(' ').upper()}")
                return
        # Se não for PFOX, tenta texto ou exibe Hex
        try:
            text_msg = payload.decode('utf-8')
            self._emit_log(f"[TX] Msg: {text_msg}")
        except:
            self._emit_log(f"[TX] Bytes: {payload.hex(' ').upper()}")
            
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
                # --- TESTES EXISTENTES ---
                # 1. Heartbeat
                lambda: pfox.create_packet(Address.ESPMAIN, MsgType.HEARTBEAT, []).to_bytes(),
                
                # 2. Flow Control (Start Robot 1)
                lambda: pfox.send_flow_control(Address.ROBOT1, 0x01).to_bytes(),
                
                # 3. Set Speed (Robot 2)
                lambda: pfox.send_speed_command(Address.ROBOT2, 100, 150, 90, 140).to_bytes(),
                
                # --- NOVOS TESTES (O QUE FALTA) ---
                lambda: pfox.send_speed_command(Address.ROBOT1, 100, 150, 90, 140).to_bytes(),

                lambda: pfox.send_speed_command(Address.ROBOT1, 100, 150, 90, 140).to_bytes(),

                # 4. TESTE DE NETWORK DISCOVERY (CRÍTICO)
                # Este é o mais importante agora. O Hub deve interceptar e responder IMEDIATAMENTE
                # com um pacote STATUS contendo o payload [0, 0, 0] (se nenhum robô conectou).
                # Se isso funcionar, sua lógica de "não usar o rádio para status" está perfeita.
                lambda: pfox.create_packet(Address.BROADCAST, MsgType.STATUS, []).to_bytes(),

                # 5. TESTE DE EMERGÊNCIA (STOP GERAL)
                # Envia um comando de PARAR para BROADCAST.
                # O Hub deve receber e você deve ver (se tivesse o LED) ele disparar o rádio 3 vezes.
                # Como resposta serial, você deve receber apenas o ACK do HUB.
                lambda: pfox.send_flow_control(Address.BROADCAST, 0x20).to_bytes(), # 0x20 = STOP

                # 6. TESTE DE BUFFER (BURST)
                # Envia para o Robô 3 (que ainda não testamos)
                lambda: pfox.send_speed_command(Address.ROBOT3, 50, 50, 0, 0).to_bytes(),
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
                    time.sleep(0.30)

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
        self._emit_log("🛑 Enviando STOP para todos os robôs antes do reset...")
        try:
            self.set_match_state(False)  # Envia STOP para BROADCAST
        except Exception as e:
            self._emit_log(f"❌ Erro ao enviar STOP no reset: {e}")
        
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
            self._emit_log(f"📤 Solicitando status de {robot.name}")
            self.send_data("STATUS", pkg)
        except Exception as e:
            self._emit_log(f"❌ Erro ao pedir status: {e}")


    def send_heartbeat(self, dst: Address = Address.BROADCAST) -> None:
        """
        Envia heartbeat (ping) para o Hub/Robôs – evita acionamento do watchdog.
        """
        try:
            # Enviar para BROADCAST para alcançar todos os robôs
            pkg = self.pfox_controller.send_heartbeat(dst)
            self.send_data("HEARTBEAT", pkg.to_bytes())
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
