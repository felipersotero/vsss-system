#!/usr/bin/env python3
# ==========================================================================================
# DIAGNÓSTICO - Verifica se a comunicação está funcionando
# ==========================================================================================
"""
Script de diagnóstico para verificar problemas de comunicação.

Roda sender e mostra exatamente o que está acontecendo no receiver.
"""

import sys
import os
import time
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from control.vision_listener import ControlInterface
from lib.VSSProtoComm.comm.protocols import common_pb2
import socket
import threading

# Logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def send_test_data(duration=10):
    """Envia dados de teste para a porta 10003"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print("\n" + "="*80)
    print("SENDER - Iniciando envio")
    print("="*80)
    print(f"Enviando para 127.0.0.1:10003 por {duration} segundos\n")
    
    frame_num = 0
    start = time.time()
    
    try:
        while time.time() - start < duration:
            # Criar frame de teste
            frame = common_pb2.Frame()
            frame.ball.x = 1.5 + (frame_num * 0.01)
            frame.ball.y = 2.3 + (frame_num * 0.01)
            
            # Adicionar alguns robôs
            for i in range(3):
                robot = frame.robots_blue.add()
                robot.robot_id = i
                robot.x = i * 1.0
                robot.y = i * 1.5
            
            data = frame.SerializeToString()
            sock.sendto(data, ('127.0.0.1', 10003))
            
            frame_num += 1
            if frame_num % 10 == 0:
                print(f"  [SENDER] Enviados {frame_num} frames ({len(data)} bytes cada)")
            
            time.sleep(0.033)  # 30 fps
    finally:
        sock.close()
        print(f"\n  [SENDER] Total enviado: {frame_num} frames")


def main():
    print("\n" + "="*80)
    print(" DIAGNÓSTICO DE COMUNICAÇÃO - Receiver + Sender".center(80))
    print("="*80)
    
    print("\n1️⃣  Inicializando ControlInterface...")
    control = ControlInterface(
        tx_ip='127.0.0.1', tx_port=10002,
        rx_ip='127.0.0.1', rx_port=10003,
        use_multicast=False
    )
    
    print("\n2️⃣  Aguardando 2 segundos para receiver estar 100% pronto...")
    time.sleep(2)
    
    print("\n3️⃣  Iniciando sender em thread separada...")
    sender_thread = threading.Thread(target=send_test_data, kwargs={'duration': 10}, daemon=True)
    sender_thread.start()
    
    print("\n4️⃣  Monitorando recebimento...\n")
    print("="*80)
    print("RECEIVER - Monitorando")
    print("="*80 + "\n")
    
    iteration = 0
    received_count = 0
    last_ball_x = None
    
    try:
        while iteration < 120:  # 4 segundos @ 30fps
            # Atualizar receiver
            decisions = control.update()
            
            # Verificar se há frame recebido
            frame = control.last_frame
            
            if frame and frame.ball.x != last_ball_x:
                received_count += 1
                last_ball_x = frame.ball.x
                
                print(f"✓ Frame #{received_count} recebido:")
                print(f"    Ball: ({frame.ball.x:.3f}, {frame.ball.y:.3f})")
                print(f"    Blue robots: {len(frame.robots_blue)}")
                print(f"    Yellow robots: {len(frame.robots_yellow)}")
                print()
            
            iteration += 1
            time.sleep(0.033)
    
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        control.close()
        sender_thread.join(timeout=2)
    
    print("\n" + "="*80)
    print(f"RESULTADO: Recebidos {received_count} frames únicos")
    if received_count > 0:
        print("✓ SUCESSO: Comunicação funcionando!")
    else:
        print("✗ FALHA: Nenhum frame recebido")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
