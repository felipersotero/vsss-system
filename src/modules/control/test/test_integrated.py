#!/usr/bin/env python3
# ==========================================================================================
# TESTE INTEGRADO - Sender + Receiver no mesmo processo
# ==========================================================================================
"""
Teste integrado para diagnóstico da comunicação UDP/Protobuff.

Roda sender e receiver em threads separadas para verificar se a comunicação funciona.
"""

import socket
import time
import sys
import os
import threading
import logging

# Adiciona o path do projeto para importar módulos
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../'))

from lib.VSSProtoComm.comm.protocols import common_pb2

# Logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s [%(name)s] %(message)s')
logger = logging.getLogger(__name__)


def create_test_frame(frame_num):
    """Cria um frame de teste com dados variáveis"""
    frame = common_pb2.Frame()
    
    # Bola (posição varia a cada frame)
    frame.ball.x = 1.5 + (frame_num * 0.01)
    frame.ball.y = 2.3 + (frame_num * 0.01)
    frame.ball.z = 0.0
    
    # Robôs aliados (azuis)
    for i in range(3):
        robot = frame.robots_blue.add()
        robot.robot_id = i
        robot.x = (i * 1.0) + (frame_num * 0.001)
        robot.y = (i * 1.5) + (frame_num * 0.001)
        robot.orientation = i * 0.5
    
    # Robôs inimigos (amarelos)
    for i in range(3):
        robot = frame.robots_yellow.add()
        robot.robot_id = i
        robot.x = (i * 1.0) + 3.0 + (frame_num * 0.001)
        robot.y = (i * 1.5) + 3.0 + (frame_num * 0.001)
        robot.orientation = i * 0.5
    
    return frame


def receiver_thread():
    """Thread que recebe dados UDP"""
    RX_IP = '127.0.0.1'
    RX_PORT = 10003
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((RX_IP, RX_PORT))
    sock.settimeout(1.0)
    
    logger.info(f"Receiver escutando em {RX_IP}:{RX_PORT}")
    
    frames_received = 0
    total_bytes = 0
    
    try:
        while frames_received < 50:  # Recebe 50 frames
            try:
                data, addr = sock.recvfrom(65535)
                frames_received += 1
                total_bytes += len(data)
                
                # Desserializa o frame
                frame = common_pb2.Frame()
                frame.ParseFromString(data)
                
                if frames_received % 10 == 0:
                    logger.info(f"[RX] Frame #{frames_received}: {len(data)} bytes | "
                              f"Ball: ({frame.ball.x:.2f}, {frame.ball.y:.2f}) | "
                              f"Blue: {len(frame.robots_blue)}, Yellow: {len(frame.robots_yellow)}")
                
            except socket.timeout:
                logger.warning("Timeout no receiver - nenhum dado recebido")
                continue
                
    except Exception as e:
        logger.error(f"Erro no receiver: {e}")
    finally:
        sock.close()
        logger.info(f"Receiver finalizado | Total: {frames_received} frames, {total_bytes} bytes")


def sender_thread():
    """Thread que envia dados UDP"""
    TX_IP = '127.0.0.1'
    TX_PORT = 10003
    
    logger.info(f"Sender enviando para {TX_IP}:{TX_PORT}")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        for frame_num in range(50):
            frame = create_test_frame(frame_num)
            data = frame.SerializeToString()
            
            sock.sendto(data, (TX_IP, TX_PORT))
            
            if (frame_num + 1) % 10 == 0:
                logger.info(f"[TX] Frame #{frame_num + 1} enviado ({len(data)} bytes)")
            
            time.sleep(0.033)  # 30 fps
            
    except Exception as e:
        logger.error(f"Erro no sender: {e}")
    finally:
        sock.close()
        logger.info("Sender finalizado")


def main():
    print("\n" + "="*70)
    print("TESTE INTEGRADO - Sender + Receiver")
    print("="*70)
    print("\nTestando comunicação UDP Protobuff...")
    print("- TX/RX: 127.0.0.1:10003")
    print("- Protocolo: UDP (sem multicast)")
    print("- Esperado: 50 frames enviados e recebidos\n")
    
    # Criar threads
    rx = threading.Thread(target=receiver_thread, daemon=False, name="Receiver")
    
    # Aguardar receiver ficar pronto
    time.sleep(0.5)
    
    tx = threading.Thread(target=sender_thread, daemon=False, name="Sender")
    
    # Iniciar threads
    rx.start()
    time.sleep(0.2)  # Garantir que receiver está listening
    tx.start()
    
    # Aguardar conclusão
    rx.join()
    tx.join()
    
    print("\n" + "="*70)
    print("✓ Teste finalizado")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
