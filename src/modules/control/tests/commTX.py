import socket
import time
import math
import logging
import sys
from pathlib import Path

try:
    from ..comm.protocols import command_pb2
except Exception:
    # Fallback para permitir execução direta do script (ex.: python commTX.py)
    # Adiciona 'src' ao sys.path para que o pacote 'modules' seja encontrado
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from modules.control.comm.protocols import command_pb2

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [TX_CMD] - %(message)s')

MCAST_GRP = '127.0.0.1'
MCAST_PORT = 10003

# Socket simples para envio (não precisa da classe Receiver)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

logging.info(f"Iniciando envio de comandos para {MCAST_GRP}:{MCAST_PORT}")

try:
    t = 0
    while True:
        packet = command_pb2.Commands()

        # Gera comandos para 3 robôs
        for i in range(3):
            cmd = packet.robot_commands.add()
            cmd.id = i
            cmd.yellowteam = False 
            
            # Gera movimento senoidal para teste
            cmd.wheel_left = math.sin(t + i) * 10
            cmd.wheel_right = math.cos(t + i) * 10

        data = packet.SerializeToString()
        sock.sendto(data, (MCAST_GRP, MCAST_PORT))
        
        logging.info(f"Enviado comando (t={t:.1f})")
        
        t += 0.1
        time.sleep(0.1) # 10Hz

except KeyboardInterrupt:
    logging.info("Parando envio.")
    sock.close()