import sys
import time
import random
import logging
from pathlib import Path

# --- Bloco de Importação Robusto ---
try:
    from ..protocols import common_pb2
    from ..transmitter import Transmitter
except Exception:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from modules.control.comm.protocols import common_pb2
    from modules.control.comm.transmitter import Transmitter

import math
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [TX_STATE] - %(message)s')

# --- MOCK DA CLASSE FIELD DATA (Simula o Core do VSSS) ---
class MockVector:
    def __init__(self, x=0, y=0, theta=0):
        self.x, self.y, self.theta = x, y, theta

class MockEntity:
    def __init__(self):
        self.position = MockVector()
        self.velocity = MockVector()

class MockFieldData:
    def __init__(self):
        self.ball = MockEntity()
        self.robots = [MockEntity() for _ in range(3)]
        self.foes = [MockEntity() for _ in range(3)]

# --- CLASSE TRANSMISSORA ---
class StatesTransmissor(Transmitter):
    def __init__(self, ip="224.0.0.1", port=10002):
        super().__init__(ip, port)

    def send_state(self, field_data):
        """Transforma FieldData interno em Frame Protobuf e envia."""
        frame = common_pb2.Frame()
        
        # 1. Mapeamento da Bola
        frame.ball.x = field_data.ball.position.x
        frame.ball.y = field_data.ball.position.y
        frame.ball.vx = field_data.ball.velocity.x
        frame.ball.vy = field_data.ball.velocity.y

        # 2. Mapeamento dos Nossos Robôs (Azul)
        for i in range(3):
            robot_in = field_data.robots[i]
            robot_out = frame.robots_blue.add()
            self._map_entity_to_proto(i, robot_in, robot_out)

        # 3. Mapeamento dos Adversários (Amarelo)
        for i in range(3):
            foe_in = field_data.foes[i]
            robot_out = frame.robots_yellow.add()
            self._map_entity_to_proto(i, foe_in, robot_out)

        self.transmit(frame) # Serializa e envia via UDP

    def _map_entity_to_proto(self, robot_id, entity_in, pb_robot):
        """Helper para preencher mensagem protobuf."""
        pb_robot.robot_id = robot_id
        pb_robot.x = entity_in.position.x
        pb_robot.y = entity_in.position.y
        pb_robot.orientation = entity_in.position.theta
        pb_robot.vx = entity_in.velocity.x
        pb_robot.vy = entity_in.velocity.y
        pb_robot.vorientation = entity_in.velocity.theta

if __name__ == "__main__":
    # Use "127.0.0.1" (Unicast) para teste local ou "224.0.0.1" (Multicast) para rede
    TARGET_IP = "127.0.0.1" 
    
    tx = StatesTransmissor(ip=TARGET_IP, port=10002)
    data = MockFieldData()
    
    logging.info(f"Iniciando simulação de FRAME COMPLETO para {TARGET_IP}:10002...")
    
    try:
        t_start = time.time()
        while True:
            t = time.time() - t_start

            # --- 1. BOLA (Movimento Circular no Centro) ---
            # A bola gira em um raio de 0.3m no centro do campo
            data.ball.position.x = 0.3 * math.cos(t)
            data.ball.position.y = 0.3 * math.sin(t)
            # Velocidade é a derivada da posição (tangente)
            data.ball.velocity.x = -0.3 * math.sin(t)
            data.ball.velocity.y = 0.3 * math.cos(t)

            # --- 2. TIME AZUL (Nós) ---
            
            # Robot 0: Goleiro (Move-se apenas no eixo Y, na defesa)
            data.robots[0].position.x = -0.65
            data.robots[0].position.y = 0.2 * math.sin(t * 2) 
            data.robots[0].position.theta = math.pi / 2  # 90 graus (olhando pra cima/lateral)

            # Robot 1: Atacante (Segue a bola com um pequeno atraso)
            data.robots[1].position.x = 0.3 * math.cos(t - 0.2)
            data.robots[1].position.y = 0.3 * math.sin(t - 0.2)
            data.robots[1].position.theta = math.atan2(data.ball.position.y, data.ball.position.x)

            # Robot 2: Zagueiro (Gira em torno do próprio eixo no meio da defesa)
            data.robots[2].position.x = -0.3
            data.robots[2].position.y = 0.0
            data.robots[2].position.theta = (t * 3) % (2 * math.pi) # Gira continuamente

            # --- 3. TIME AMARELO (Adversários) ---
            
            # Foe 0: Goleiro Adversário (Espelhado no lado positivo)
            data.foes[0].position.x = 0.65
            data.foes[0].position.y = 0.2 * math.cos(t * 2)
            data.foes[0].position.theta = -math.pi / 2

            # Foe 1: Movimento Linear (Vai e volta no meio)
            data.foes[1].position.x = 0.2
            data.foes[1].position.y = 0.4 * math.sin(t)

            # Foe 2: Estático (Parado no canto)
            data.foes[2].position.x = 0.5
            data.foes[2].position.y = -0.5
            data.foes[2].position.theta = 0

            tx.send_state(data)
            time.sleep(0.033) # ~30 FPS (Padrão de câmeras)
            
    except KeyboardInterrupt:
        logging.info("Parando transmissão.")
        tx.transmitter_socket.close()