#!/usr/bin/env python3
# ==========================================================================================
# TESTE SENDER - Envia frames protobuff via UDP
# ==========================================================================================
"""
Script simples para testar envio de frames protobuff via UDP.

Executar com:
    python test_vision_sender.py

Em outro terminal, execute o receiver:
    python exemple_vision_receiver.py
"""

import socket
import time
import sys
import os

# Adiciona o path do projeto para importar módulos
# test_vision_sender.py está em: src/modules/control/test/
# Precisa chegar em: src/ (onde está lib/)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../'))

from lib.VSSProtoComm.comm.protocols import common_pb2


def format_frame_sent(frame, frame_num):
    """Formata e exibe um frame sendo enviado"""
    output = f"\n{'='*80}\n"
    output += f"FRAME #{frame_num} ENVIADO\n"
    output += f"{'='*80}\n\n"
    
    # Bola
    output += f"BOLA:\n"
    output += f"  Posicao: ({frame.ball.x:.3f}, {frame.ball.y:.3f}, {frame.ball.z:.3f})\n"
    if hasattr(frame.ball, 'vx'):
        output += f"  Velocidade: ({frame.ball.vx:.3f}, {frame.ball.vy:.3f}, {frame.ball.vz:.3f})\n"
    output += "\n"
    
    # Robôs Azuis (Aliados)
    output += f"ROBOS ALIADOS (AZUIS): {len(frame.robots_blue)}\n"
    for i, robot in enumerate(frame.robots_blue):
        output += f"  [{i}] ID={robot.robot_id} | Pos: ({robot.x:.3f}, {robot.y:.3f}) | Orient: {robot.orientation:.3f}°\n"
        if hasattr(robot, 'vx'):
            output += f"      Vel: ({robot.vx:.3f}, {robot.vy:.3f}) | VelOrient: {robot.vorientation:.3f}\n"
    if len(frame.robots_blue) == 0:
        output += "  (nenhum)\n"
    output += "\n"
    
    # Robôs Amarelos (Inimigos)
    output += f"ROBOS INIMIGOS (AMARELOS): {len(frame.robots_yellow)}\n"
    for i, robot in enumerate(frame.robots_yellow):
        output += f"  [{i}] ID={robot.robot_id} | Pos: ({robot.x:.3f}, {robot.y:.3f}) | Orient: {robot.orientation:.3f}°\n"
        if hasattr(robot, 'vx'):
            output += f"      Vel: ({robot.vx:.3f}, {robot.vy:.3f}) | VelOrient: {robot.vorientation:.3f}\n"
    if len(frame.robots_yellow) == 0:
        output += "  (nenhum)\n"
    
    output += f"\n{'='*80}\n"
    return output


def create_test_frame(frame_num):
    """Cria um frame de teste com dados variáveis"""
    frame = common_pb2.Frame()
    
    # Bola (posição varia a cada frame)
    frame.ball.x = 1.5 + (frame_num * 0.01)
    frame.ball.y = 2.3 + (frame_num * 0.01)
    frame.ball.z = 0.0
    frame.ball.vx = 0.1
    frame.ball.vy = 0.2
    frame.ball.vz = 0.0
    
    # Robôs aliados (azuis)
    for i in range(3):
        robot = frame.robots_blue.add()
        robot.robot_id = i
        robot.x = (i * 1.0) + (frame_num * 0.001)
        robot.y = (i * 1.5) + (frame_num * 0.001)
        robot.orientation = i * 0.5
        robot.vx = 0.1
        robot.vy = 0.2
        robot.vorientation = 0.05
    
    # Robôs inimigos (amarelos)
    for i in range(3):
        robot = frame.robots_yellow.add()
        robot.robot_id = i
        robot.x = (i * 1.0) + 3.0 + (frame_num * 0.001)
        robot.y = (i * 1.5) + 3.0 + (frame_num * 0.001)
        robot.orientation = i * 0.5
        robot.vx = 0.05
        robot.vy = 0.15
        robot.vorientation = 0.02
    
    return frame


def send_frames():
    """Envia frames protobuff continuamente"""
    
    SEND_IP = '127.0.0.1'  # localhost
    SEND_PORT = 10003
    
    # Criar socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    frame_num = 0
    
    try:
        while True:
            # Cria frame de teste
            frame = create_test_frame(frame_num)
            
            # Serializa em bytes
            data = frame.SerializeToString()
            
            # Envia via UDP
            sock.sendto(data, (SEND_IP, SEND_PORT))
            
            print("enviado")
            
            frame_num += 1
            
            # 30 fps (0.033s = 33ms)
            time.sleep(0.033)
            
    except KeyboardInterrupt:
        pass
        
    except Exception as e:
        pass
        
    finally:
        sock.close()


if __name__ == "__main__":
    send_frames()
