# ==========================================================================================
# MÓDULO RECEPTOR DE VISÃO E GERENCIADOR (Protobuff Communication)
# ==========================================================================================
"""
Módulo para receber dados de visão e gerenciar comunicação bidirecional.

Classes:
    VisionReceiver: Recebe e desserializa frames protobuff via UDP (herda de Receiver)
    ControlInterface: Gerencia Transmitter e Receiver de forma sincronizada

Uso:
    control = ControlInterface(
        tx_ip='224.0.0.1', tx_port=10002,  # Envio
        rx_ip='127.0.0.1', rx_port=10003   # Recebimento
    )
    control.send_frame(vision_system)
    frame_recebido = control.receive_frame()
    decisions = control.get_decisions()
"""

import socket
import threading
import time
import logging
import struct
import sys
from pathlib import Path
from abc import ABC, abstractmethod
from queue import Queue, Empty

# Adicionar src ao path para imports relativos funcionarem
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.VSSProtoComm.comm.transmitter import Transmitter
from lib.VSSProtoComm.comm.thread_job import Job

logger = logging.getLogger(__name__)

class VisionTransmitter(Transmitter):
    """
    Transmissor de dados de visão em formato protobuff.
    
    Herda de Transmitter para usar a infraestrutura existente do VSSProtoComm,
    que se encarrega de:
    - Gerenciamento de socket UDP
    - Serialização de protobuff (.SerializeToString())
    - Envio dos dados pela rede
    
    Attributes:
        transmitter_ip (str): IP multicast para envio (default: 224.0.0.1)
        transmitter_port (int): Porta para envio (default: 10002)
    """
    
    def __init__(self, transmitter_ip='224.0.0.1', transmitter_port=10002):
        """
        Inicializa o transmissor de visão.
        
        Args:
            transmitter_ip (str): IP para enviar dados (default: 224.0.0.1)
            transmitter_port (int): Porta para enviar dados (default: 10002)
        """
        super().__init__(transmitter_ip=transmitter_ip, transmitter_port=transmitter_port)
        logger.info(f"[VisionTransmitter] Inicializado em {transmitter_ip}:{transmitter_port}")

    def transmit(self, packet):
        """Implementação obrigatória da classe abstrata Transmitter"""
        try:
            data = packet.SerializeToString()
            self.transmitter_socket.sendto(data, (self.transmitter_ip, self.transmitter_port))
            logger.debug(f"[VisionTransmitter] Enviou {len(data)} bytes")
        except Exception as e:
            logger.error(f"[VisionTransmitter] Erro ao enviar: {e}")
            raise
        
    def send_frame(self, vision_system):
        """
        Envia um frame de visão (protobuff serializado) via UDP.
        
        Args:
            vision_system (VisionSystem): Instância do sistema de visão com dados atualizados
            
        Returns:
            bool: True se enviado com sucesso, False caso contrário
            
        Exemplo:
            >>> vision_tx = VisionTransmitter(ip_send='224.0.0.1', port_send=10002)
            >>> success = vision_tx.send_frame(vision_system)
        """
        try:
            # Obtém o frame em formato protobuff
            frame = vision_system.getFrameProtobuff()
            
            # Usa o método transmit() da classe pai (Transmitter)
            # que faz: data = packet.SerializeToString()
            #         socket.sendto(data, (ip, port))
            self.transmit(frame)
            
            logger.debug(f"[VisionTransmitter] Frame enviado com sucesso")
            return True
            
        except AttributeError as e:
            logger.error(f"[VisionTransmitter] VisionSystem não possui getFrameProtobuff(): {e}")
            return False
        except Exception as e:
            logger.error(f"[VisionTransmitter] Erro ao enviar frame: {e}")
            return False
    
    def close(self):
        """
        Fecha a conexão do socket.
        """
        try:
            if hasattr(self, 'transmitter_socket'):
                self.transmitter_socket.close()
                logger.info("[VisionTransmitter] Socket fechado")
        except Exception as e:
            logger.error(f"[VisionTransmitter] Erro ao fechar socket: {e}")

class Receiver(ABC):
    """
    Classe base abstrata para receptores de dados via UDP.
    
    Baseada na implementação de lib/VSSProtoComm/comm/receiver.py
    Define a interface comum para qualquer receptor que use multicast UDP.
    """
    
    def __init__(self, receiver_ip='224.0.0.1', receiver_port=10002, use_multicast=True):
        """
        Inicializa o receptor de dados.
        
        Args:
            receiver_ip (str): IP multicast para escutar (default: 224.0.0.1)
            receiver_port (int): Porta para escutar (default: 10002)
            use_multicast (bool): Se True, usa multicast (para rede real).
                                 Se False, usa UDP simples (para teste local).
        """
        self.receiver_ip = receiver_ip
        self.receiver_port = receiver_port
        self.use_multicast = use_multicast
        
        # Create socket
        self.receiver_socket = self._create_socket()
    
    @abstractmethod
    def receive(self):
        """
        Recebe packet bruto.
        
        Returns:
            bytes: Dados recebidos via UDP
        """
        data, _ = self.receiver_socket.recvfrom(65535)
        return data
    
    def _create_socket(self):
        """
        Cria socket UDP para recebimento com suporte a multicast (opcional).
        
        Se use_multicast=True, configura para multicast (rede real).
        Se use_multicast=False, configura para UDP simples (teste local).
        
        Returns:
            socket: Socket UDP configurado
        """
        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP
        )
        
        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR, 1
        )
        
        sock.bind((self.receiver_ip, self.receiver_port))
        
        # Aumentar buffer de recebimento para melhor performance
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024*1024)  # 1MB
        except:
            pass
        
        # Configurar multicast apenas se solicitado
        if self.use_multicast:
            try:
                mreq = struct.pack(
                    "4sl",
                    socket.inet_aton(self.receiver_ip),
                    socket.INADDR_ANY
                )
                
                sock.setsockopt(
                    socket.IPPROTO_IP,
                    socket.IP_ADD_MEMBERSHIP,
                    mreq
                )
                logger.debug(f"[Receiver] Multicast ativado para {self.receiver_ip}:{self.receiver_port}")
            except OSError as e:
                logger.warning(f"[Receiver] Falha ao ativar multicast: {e}")
                logger.warning(f"[Receiver] Continuando com UDP simples...")
        else:
            logger.debug(f"[Receiver] UDP simples (sem multicast) em {self.receiver_ip}:{self.receiver_port}")
        
        # Timeout mais agressivo para melhor resposta
        sock.settimeout(0.1)  # 100ms em vez de 1s
        
        return sock


class VisionReceiver(Receiver):
    """
    Receptor de dados de visão via UDP.
    
    Herda de Receiver (assim como ProtoVision em lib/VSSProtoComm)
    para usar padrão padronizado de recebimento.
    
    Recebe frames protobuff serializados e os desserializa para uso interno.
    Roda em thread separada (Job) para não bloquear o programa principal.
    
    Attributes:
        receiver_ip (str): IP para escutar (default: 127.0.0.1)
        receiver_port (int): Porta para escutar (default: 10003)
        frame_queue: Fila de frames recebidos (thread-safe)
        job: Thread Job para recebimento contínuo
    """
    
    def __init__(self, receiver_ip='127.0.0.1', receiver_port=10003, use_multicast=False):
        """
        Inicializa o receptor de visão.
        
        Args:
            receiver_ip (str): IP para escutar (default: 127.0.0.1)
            receiver_port (int): Porta para escutar (default: 10003)
            use_multicast (bool): Se True, usa multicast. Default False para teste local.
        """
        super().__init__(receiver_ip=receiver_ip, receiver_port=receiver_port, use_multicast=use_multicast)
        
        self.frame_queue = Queue(maxsize=10)  # Buffer de últimos 10 frames
        self.job = None
        
        logger.info(f"[VisionReceiver] Inicializado em {receiver_ip}:{receiver_port}")
    
    def receive(self):
        """
        Recebe dados brutos via UDP e desserializa em Frame protobuff.
        
        Returns:
            common_pb2.Frame: Frame desserializado
        """
        try:
            # Se socket foi fechado, não tenta receber
            if self.receiver_socket is None:
                return None
                
            data = super().receive()
            
            # Desserializa o frame protobuff
            from lib.VSSProtoComm.comm.protocols import common_pb2
            frame = common_pb2.Frame()
            frame.ParseFromString(data)
            
            logger.debug(f"[VisionReceiver] Frame recebido - {len(data)} bytes")
            return frame
            
        except socket.timeout:
            # Timeout normal, sem erro
            return None
        except (OSError, socket.error, BrokenPipeError) as e:
            # Socket pode ter sido fechado - esperado durante shutdown
            logger.debug(f"[VisionReceiver] Socket indisponível: {type(e).__name__}")
            return None
        except Exception as e:
            logger.error(f"[VisionReceiver] Erro ao receber: {e}")
            return None
    
    def _receive_job(self):
        """
        Job que roda continuamente recebendo frames.
        Cada frame recebido é adicionado à fila.
        
        Chamado pela thread Job de forma contínua.
        """
        try:
            # Verifica se socket ainda é válido antes de tentar receber
            if self.receiver_socket is None:
                return
                
            frame = self.receive()
            
            if frame is not None:
                # Adiciona à fila (descarta o mais antigo se fila estiver cheia)
                try:
                    self.frame_queue.put_nowait(frame)
                except:
                    # Se fila está cheia, remove o mais antigo e adiciona o novo
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(frame)
                    except:
                        pass
                
        except (OSError, socket.error, BrokenPipeError):
            # Socket foi fechado - esperado durante shutdown
            pass
        except Exception as e:
            logger.error(f"[VisionReceiver] Erro em _receive_job: {e}")
    
    def start_listening(self):
        """
        Inicia thread de recebimento (Job).
        
        Utiliza a classe Job do VSSProtoComm que oferece pause/resume/stop.
        """
        if self.job is None:
            self.job = Job(self._receive_job)
            self.job.daemon = True
            self.job.start()
            logger.info("[VisionReceiver] Thread de recebimento iniciada (Job)")
    
    def pause_listening(self):
        """Pausa recebimento sem parar a thread"""
        if self.job:
            self.job.pause()
            logger.info("[VisionReceiver] Recebimento pausado")
    
    def resume_listening(self):
        """Retoma recebimento"""
        if self.job:
            self.job.resume()
            logger.info("[VisionReceiver] Recebimento retomado")
    
    def stop_listening(self):
        """Para thread de recebimento (Job)"""
        if self.job:
            self.job.stop()
            self.job = None
            logger.info("[VisionReceiver] Thread de recebimento parada")
    
    def get_latest_frame(self):
        """
        Retorna o frame mais recente sem bloquear.
        
        Returns:
            common_pb2.Frame ou None se nenhum frame disponível
        """
        try:
            # Tira todos os frames antigos, mantém só o mais recente
            latest_frame = None
            while True:
                latest_frame = self.frame_queue.get_nowait()
        except Empty:
            return latest_frame
    
    def get_frame_blocking(self, timeout=1.0):
        """
        Retorna um frame, bloqueando se necessário.
        
        Args:
            timeout (float): Tempo máximo de espera em segundos
            
        Returns:
            common_pb2.Frame ou None se timeout
        """
        try:
            return self.frame_queue.get(timeout=timeout)
        except Empty:
            return None
    
    def close(self):
        """Fecha receiver e libera recursos"""
        try:
            # Fechar socket PRIMEIRO para que a thread Job receba erro e saia
            if self.receiver_socket:
                self.receiver_socket.close()
                self.receiver_socket = None
            
            # Depois parar a thread
            self.stop_listening()
            logger.info("[VisionReceiver] Socket fechado")
        except Exception as e:
            logger.error(f"[VisionReceiver] Erro ao fechar: {e}")


class ControlInterface:
    """
    Interface de controle bidirecional - gerencia comunicação de visão e decisões.
    
    Coordena Transmitter (envia frames de visão) e Receiver (recebe decisões/frames)
    em um único local, simplificando a arquitetura.
    
    Padrão: Interface de Controle + Producer (VisionSystem) + Consumer (StrategyAI)
    
    Attributes:
        transmitter: VisionTransmitter para envio
        receiver: VisionReceiver para recebimento
        last_frame: Último frame recebido com decisões
        robot_decisions: Últimas decisões para os robôs
    """
    
    def __init__(self, 
                 tx_ip='224.0.0.1', tx_port=10002,
                 rx_ip='127.0.0.1', rx_port=10003,
                 use_multicast=False):
        """
        Inicializa a interface de controle bidirecional.
        
        Args:
            tx_ip (str): IP para envio de frames (default: 224.0.0.1)
            tx_port (int): Porta para envio (default: 10002)
            rx_ip (str): IP para recebimento de decisões (default: 127.0.0.1)
            rx_port (int): Porta para recebimento (default: 10003)
            use_multicast (bool): Se True, usa multicast para rede real.
                                 Se False (padrão), usa UDP simples para teste local.
        """
        # Inicializa transmitter
        self.transmitter = VisionTransmitter(
            transmitter_ip=tx_ip,
            transmitter_port=tx_port
        )
        
        # Inicializa receiver
        self.receiver = VisionReceiver(
            receiver_ip=rx_ip,
            receiver_port=rx_port,
            use_multicast=use_multicast
        )
        
        # Estado interno
        self.last_frame = None
        self.robot_decisions = {}
        self.last_decision_time = 0
        
        # Inicia recebimento
        self.receiver.start_listening()
        
        logger.info(f"[ControlInterface] Inicializado")
        logger.info(f"  ├─ TX: {tx_ip}:{tx_port}")
        logger.info(f"  └─ RX: {rx_ip}:{rx_port}")
    
    def send_frame(self, vision_system):
        """
        Envia frame de visão para o sistema de decisão.
        
        Args:
            vision_system (VisionSystem): Sistema de visão com dados atualizados
            
        Returns:
            bool: True se enviado com sucesso
        """
        try:
            success = self.transmitter.send_frame(vision_system)
            if success:
                logger.debug("[ControlInterface] Frame enviado")
            return success
        except Exception as e:
            logger.error(f"[ControlInterface] Erro ao enviar frame: {e}")
            return False
    
    def receive_frame(self, blocking=False, timeout=1.0):
        """
        Recebe frame do sistema de decisão (pode conter decisões/feedback).
        
        Args:
            blocking (bool): Se True, bloqueia até receber
            timeout (float): Tempo de espera em segundos
            
        Returns:
            common_pb2.Frame ou None
        """
        try:
            if blocking:
                frame = self.receiver.get_frame_blocking(timeout=timeout)
            else:
                frame = self.receiver.get_latest_frame()
            
            if frame:
                self.last_frame = frame
                logger.debug("[ControlInterface] Frame recebido")
            
            return frame
        except Exception as e:
            logger.error(f"[ControlInterface] Erro ao receber frame: {e}")
            return None
    
    def get_decisions(self):
        """
        Extrai informações de decisões do último frame recebido.
        
        Transforma os dados do frame protobuff em um dicionário estruturado
        para que possam ser utilizados pelo usuário.
        
        Este método NÃO implementa lógica de decisão. Ele apenas extrai
        e formata os dados que chegaram no receiver.
        
        Formato de retorno:
        {
            0: {"left": 100, "right": 80},    # Robô 0
            1: {"left": -50, "right": 50},    # Robô 1
            2: {"left": 0, "right": 0}        # Robô 2
        }
        
        Returns:
            dict: Dicionário com dados extraídos para cada robô
        """
        decisions = {}
        
        if self.last_frame is None:
            #logger.warning("[ControlInterface] Nenhum frame recebido ainda")
            # Retorna padrão vazio para todos os robôs
            return {
                0: {"left": 0, "right": 0},
                1: {"left": 0, "right": 0},
                2: {"left": 0, "right": 0}
            }
        
        # Extrai informações do frame recebido e transforma em dicionário
        # O frame contém dados que foram enviados pelo sistema de IA/decisão
        
        # Itera sobre os robôs e extrai suas informações
        for robot_id in range(3):
            # Aqui você pode extrair dados do frame conforme necessário
            # Por exemplo, se o frame tiver campos com velocidades/decisões
            
            # Formato padrão: esquerda e direita
            decisions[robot_id] = {
                "left": 0,
                "right": 0
            }
        
        self.robot_decisions = decisions
        self.last_decision_time = time.time()
        
        logger.debug(f"[ControlInterface] Dados extraídos: {decisions}")
        return decisions
    
    def get_robot_decision(self, robot_id):
        """
        Retorna a decisão para um robô específico.
        
        Args:
            robot_id (int): ID do robô (0, 1, 2)
            
        Returns:
            dict: {"left": int, "right": int}
        """
        if robot_id in self.robot_decisions:
            return self.robot_decisions[robot_id]
        return {"left": 0, "right": 0}
    
    def update(self):
        """
        Atualiza listener (recebe novos frames e gera decisões).
        
        Deve ser chamado no loop principal.
        
        Returns:
            dict: Decisões atualizadas para os robôs
        """
        # Tenta receber novo frame
        frame = self.receive_frame(blocking=False)
        
        # Gera decisões baseado no último frame
        decisions = self.get_decisions()
        
        return decisions
    
    def close(self):
        """Fecha interface de controle e libera recursos"""
        try:
            self.transmitter.close()
            self.receiver.close()
            logger.info("[ControlInterface] Fechado")
        except Exception as e:
            logger.error(f"[ControlInterface] Erro ao fechar: {e}")


# =======================================================================================
# EXEMPLO DE USO
# =======================================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("CONTROL INTERFACE - Sistema Bidirecional")
    print("="*60)
    print("\nModo TESTE LOCAL (sem multicast):")
    print("  ✓ TX: 127.0.0.1:10002 (UDP simples)")
    print("  ✓ RX: 127.0.0.1:10003 (UDP simples)")
    print("  ✓ Sem multicast (funciona em localhost)\n")
    
    try:
        # Criar interface de controle em modo teste (sem multicast)
        # use_multicast=False permite rodar em localhost sem erros
        control = ControlInterface(
            tx_ip='127.0.0.1', tx_port=10002,
            rx_ip='127.0.0.1', rx_port=10003,
            use_multicast=False  # ← Teste local sem multicast
        )
        
        print("✅ Interface de controle iniciada com sucesso!")
        print("   Aguardando frames...")
        print("   Pressione CTRL+C para parar\n")
        
        for i in range(100):
            # Atualiza interface de controle (recebe frames, gera decisões)
            decisions = control.update()
            
            if i % 10 == 0:  # Mostrar a cada 10 iterações
                print(f"[{i}] Aguardando... (nenhum frame recebido ainda)")
            
            time.sleep(0.1)
            
    except OSError as e:
        print(f"\n❌ Erro de socket: {e}")
        print("\nDICAS PARA CORRIGIR:")
        print("  1. Para TESTE LOCAL (localhost):")
        print("     → Use: use_multicast=False (já está no exemplo)")
        print("  2. Para REDE REAL:")
        print("     → Use: use_multicast=True")
        print("     → Use IP multicast válido (224.0.0.0 - 239.255.255.255)")
        print("     → Certifique-se que há um sistema enviando dados")
    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        logger.exception("Erro ao executar ControlInterface")
    finally:
        try:
            control.close()
            print("✅ Interface fechada com sucesso.")
        except:
            pass
        print("Finalizado.")
