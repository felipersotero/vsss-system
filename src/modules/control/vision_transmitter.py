# ==========================================================================================
# MÓDULO TRANSMISSOR DE VISÃO (Protobuff Communication)
# ==========================================================================================
"""
Módulo para transmitir dados de visão usando protobuff via UDP.
Herda da classe Transmitter do VSSProtoComm para manter compatibilidade com a infraestrutura existente.

Uso:
    vision_tx = VisionTransmitter(ip_send='224.0.0.1', port_send=10002)
    vision_tx.send_frame(vision_system)
"""

from lib.VSSProtoComm.comm.transmitter import Transmitter
import logging

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
