#!/usr/bin/env python3
# ==========================================================================================
# SIMULAÇÃO - Exatamente como vision_listener.py funciona
# ==========================================================================================
"""
Roda EXATAMENTE como vision_listener.py roda:
1. Inicia ControlInterface
2. Entra em loop aguardando frames
3. Exibe frames completos quando recebidos
"""

import sys
import os
import time
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.control.vision_listener import ControlInterface

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


def format_frame(frame, frame_num):
    """Formata e exibe um frame de forma legível"""
    output = f"\n{'='*80}\n"
    output += f"FRAME #{frame_num} RECEBIDO\n"
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*70)
    print("SIMULAÇÃO - vision_listener.py em modo aguardando")
    print("="*70)
    print("\nInstruções:")
    print("  1. Este script funciona EXATAMENTE como vision_listener.py")
    print("  2. Após iniciar, em OUTRO terminal execute:")
    print("     python src\\modules\\control\\test\\test_vision_sender.py")
    print("  3. Pressione ENTER no sender para iniciar envio")
    print("  4. Os frames completos serão exibidos aqui\n")
    
    try:
        # Criar interface de controle em modo teste (sem multicast)
        control = ControlInterface(
            tx_ip='127.0.0.1', tx_port=10002,
            rx_ip='127.0.0.1', rx_port=10003,
            use_multicast=False
        )
        
        print("Aguardando frames...")
        print("(Pressione CTRL+C para parar)\n")
        
        iteration = 0
        frames_received = 0
        last_frame_id = None
        
        for i in range(10000):  # Loop por muito tempo
            # Atualiza interface de controle
            decisions = control.update()
            
            # Verificar se frame foi recebido
            if control.last_frame is not None:
                # Criar um ID único para o frame (baseado em posição da bola)
                current_frame_id = (control.last_frame.ball.x, control.last_frame.ball.y)
                
                # Se é um frame novo (diferente do anterior)
                if current_frame_id != last_frame_id:
                    frames_received += 1
                    last_frame_id = current_frame_id
                    
                    # Exibir frame completo
                    frame_display = format_frame(control.last_frame, frames_received)
                    print(frame_display)
            
            iteration += 1
            time.sleep(0.1)  # 10 Hz loop (como em vision_listener.py)
            
    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuário.")
    except Exception as e:
        logger.error(f"Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            control.close()
            print("Interface fechada com sucesso.")
        except:
            pass
        print("Finalizado.")

