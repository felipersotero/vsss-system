#!/usr/bin/env python3
# ==========================================================================================
# TESTE PARALELO - Roda receiver e sender em paralelo no MESMO terminal
# ==========================================================================================
"""
Script para testar o fluxo completo:
1. Inicia o ControlInterface (receiver)
2. Inicia sender de frames
3. Exibe dados recebidos em tempo real

Uso:
    python test_parallel.py
"""

import sys
import os
import time
import logging
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from control.vision_listener import ControlInterface, VisionReceiver
import threading
import socket
from lib.VSSProtoComm.comm.protocols import common_pb2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def create_test_frame(frame_num):
    """Cria frame de teste"""
    frame = common_pb2.Frame()
    
    frame.ball.x = 1.5 + (frame_num * 0.01)
    frame.ball.y = 2.3 + (frame_num * 0.01)
    frame.ball.z = 0.0
    
    for i in range(3):
        robot = frame.robots_blue.add()
        robot.robot_id = i
        robot.x = (i * 1.0) + (frame_num * 0.001)
        robot.y = (i * 1.5) + (frame_num * 0.001)
        robot.orientation = i * 0.5
    
    for i in range(3):
        robot = frame.robots_yellow.add()
        robot.robot_id = i
        robot.x = (i * 1.0) + 3.0 + (frame_num * 0.001)
        robot.y = (i * 1.5) + 3.0 + (frame_num * 0.001)
        robot.orientation = i * 0.5
    
    return frame


def sender_task(duration=30):
    """Envia frames por N segundos"""
    TX_IP = '127.0.0.1'
    TX_PORT = 10003
    
    logger.info(f"Sender iniciando | Enviando para {TX_IP}:{TX_PORT} por {duration}s")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    start_time = time.time()
    frame_num = 0
    
    try:
        while time.time() - start_time < duration:
            frame = create_test_frame(frame_num)
            data = frame.SerializeToString()
            sock.sendto(data, (TX_IP, TX_PORT))
            
            frame_num += 1
            if frame_num % 30 == 0:
                logger.debug(f"Sender: {frame_num} frames enviados ({len(data)} bytes)")
            
            time.sleep(0.033)  # 30 fps
    finally:
        sock.close()
        logger.info(f"Sender finalizado | Total: {frame_num} frames")


def main():
    print("\n" + "="*80)
    print(" TESTE PARALELO - ControlInterface + Sender".center(80))
    print("="*80)
    print("\n✓ Iniciando em modo de teste local (sem multicast)")
    print("  - TX: 127.0.0.1:10002")
    print("  - RX: 127.0.0.1:10003")
    print("  - Duração: 30 segundos\n")
    
    try:
        # Criar ControlInterface
        logger.info("Inicializando ControlInterface...")
        control = ControlInterface(
            tx_ip='127.0.0.1', tx_port=10002,
            rx_ip='127.0.0.1', rx_port=10003,
            use_multicast=False
        )
        
        # Aguardar receiver estar pronto
        time.sleep(0.5)
        
        # Iniciar sender em thread separada
        sender = threading.Thread(target=sender_task, kwargs={'duration': 30}, daemon=True)
        sender.start()
        
        # Loop de atualização (30 fps)
        iteration = 0
        start_time = time.time()
        last_received = 0
        
        print()
        logger.info("Aguardando frames...")
        print()
        
        while time.time() - start_time < 35:  # Um pouco mais que sender
            # Atualizar receiver e extrair decisões
            decisions = control.update()
            
            # Exibir a cada 30 frames
            iteration += 1
            if iteration % 30 == 0:
                current_time = time.time() - start_time
                elapsed = f"{current_time:.1f}s"
                
                if decisions:
                    last_received = iteration
                    logger.info(f"[{elapsed}] ✓ Recebido | Decisões: {decisions}")
                else:
                    logger.warning(f"[{elapsed}] ⚠ Nenhum frame ainda...")
            
            time.sleep(0.033)
        
        # Finalizar
        control.close()
        sender.join(timeout=2)
        
        print("\n" + "="*80)
        logger.info("✓ Teste finalizado com sucesso")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Erro durante teste: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
