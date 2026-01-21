import socket
import struct
from abc import ABC, abstractmethod

class Receiver(ABC):
    def __init__(self, receiver_ip='224.0.0.1', receiver_port=10002):
        self.receiver_ip = receiver_ip
        self.receiver_port = receiver_port
        self.receiver_socket = self._create_socket()

    def receive(self):
        try:
            data, _ = self.receiver_socket.recvfrom(1024)
            return data
        except socket.timeout:
            return None

    def _is_multicast(self, ip):
        """Verifica se o IP está na faixa de Multicast (224.0.0.0 a 239.255.255.255)"""
        try:
            first_octet = int(ip.split('.')[0])
            return 224 <= first_octet <= 239
        except:
            return False

    def _create_socket(self):
        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP
        )

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # LÓGICA HÍBRIDA MULTICAST / UNICAST
        if self._is_multicast(self.receiver_ip):
            # --- CONFIGURAÇÃO MULTICAST ---
            
            # No Windows, para Multicast, geralmente fazemos o bind no endereço '0.0.0.0' (INADDR_ANY)
            # ou no IP local da interface, mas NÃO no IP do grupo multicast diretamente.
            sock.bind(('', self.receiver_port))

            # Configura a estrutura para entrar no grupo
            mreq = struct.pack(
                "4sl",
                socket.inet_aton(self.receiver_ip),
                socket.INADDR_ANY
            )

            # Só executa isso se for realmente Multicast
            sock.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                mreq
            )
        else:
            # --- CONFIGURAÇÃO UNICAST (ex: 127.0.0.1) ---
            # Para Unicast, fazemos o bind direto no IP específico
            sock.bind((self.receiver_ip, self.receiver_port))

        return sock

    def close(self):
        self.receiver_socket.close()