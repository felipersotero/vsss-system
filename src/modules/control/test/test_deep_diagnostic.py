#!/usr/bin/env python3
# ==========================================================================================
# DIAGNÓSTICO DETALHADO - Investiga problema de sincronização
# ==========================================================================================
"""
Script para diagnosticar por que vision_listener.py não recebe dados quando 
rodado em terminal separado, mas test_diagnostic.py funciona.
"""

import sys
import os
import socket
import time
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s | %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


def test_socket_binding():
    """Testa se o socket consegue fazer bind na porta 10003"""
    print("\n" + "="*80)
    print("TESTE 1 - Verificar bind do socket")
    print("="*80)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', 10003))
        sock.settimeout(1.0)
        
        print("[OK] Socket fez bind em 127.0.0.1:10003")
        
        # Tentar receber algo
        print("\nAguardando dados por 3 segundos...")
        start = time.time()
        received = False
        
        try:
            while time.time() - start < 3:
                try:
                    data, addr = sock.recvfrom(65535)
                    print(f"[OK] Dados recebidos: {len(data)} bytes de {addr}")
                    received = True
                    break
                except socket.timeout:
                    continue
        except Exception as e:
            print(f"[ERRO] {e}")
        
        sock.close()
        
        if not received:
            print("[INFO] Nenhum dado recebido (esperado se ninguém está enviando)")
        
    except Exception as e:
        print(f"[ERRO] Falha ao fazer bind: {e}")


def test_receiver_class():
    """Testa a classe VisionReceiver diretamente"""
    print("\n" + "="*80)
    print("TESTE 2 - Testar VisionReceiver diretamente")
    print("="*80)
    
    try:
        from modules.control.vision_listener import VisionReceiver
        
        print("Criando VisionReceiver...")
        receiver = VisionReceiver(
            receiver_ip='127.0.0.1',
            receiver_port=10003,
            use_multicast=False
        )
        
        print("[OK] VisionReceiver criado")
        print(f"  - Socket: {receiver.receiver_socket}")
        print(f"  - Socket timeout: {receiver.receiver_socket.gettimeout()}")
        print(f"  - Socket bound: {receiver.receiver_socket.getsockname()}")
        
        # Verificar se socket está realmente escutando
        print("\nTentando receber dados por 3 segundos...")
        start = time.time()
        received = False
        
        while time.time() - start < 3:
            try:
                frame = receiver.receive()
                if frame:
                    print(f"[OK] Frame recebido!")
                    received = True
                    break
            except Exception as e:
                print(f"[DEBUG] {type(e).__name__}: {e}")
        
        if not received:
            print("[INFO] Nenhum frame recebido (esperado se ninguém está enviando)")
        
        receiver.close()
        
    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback
        traceback.print_exc()


def test_control_interface():
    """Testa ControlInterface como no vision_listener.py"""
    print("\n" + "="*80)
    print("TESTE 3 - Testar ControlInterface (como em vision_listener.py)")
    print("="*80)
    
    try:
        from modules.control.vision_listener import ControlInterface
        
        print("Criando ControlInterface...")
        control = ControlInterface(
            tx_ip='127.0.0.1', tx_port=10002,
            rx_ip='127.0.0.1', rx_port=10003,
            use_multicast=False
        )
        
        print("[OK] ControlInterface criado")
        print(f"  - Receiver Job: {control.receiver.job}")
        print(f"  - Receiver Job state: {control.receiver.job.is_alive() if control.receiver.job else 'None'}")
        
        print("\nTentando receber dados por 5 segundos...")
        start = time.time()
        frames_received = 0
        
        while time.time() - start < 5:
            frame = control.receive_frame(blocking=False)
            if frame:
                frames_received += 1
                print(f"  Frame #{frames_received} recebido")
            time.sleep(0.1)
        
        if frames_received == 0:
            print("[INFO] Nenhum frame recebido (esperado se ninguém está enviando)")
        
        control.close()
        
    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback
        traceback.print_exc()


def send_test_data():
    """Envia alguns frames de teste"""
    print("\n" + "="*80)
    print("TESTE 4 - Enviar dados de teste e verificar recebimento")
    print("="*80)
    
    try:
        from modules.control.vision_listener import ControlInterface
        from lib.VSSProtoComm.comm.protocols import common_pb2
        import threading
        
        def sender():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for i in range(10):
                frame = common_pb2.Frame()
                frame.ball.x = float(i)
                frame.ball.y = float(i)
                data = frame.SerializeToString()
                sock.sendto(data, ('127.0.0.1', 10003))
                print(f"  [SENDER] Frame {i+1} enviado ({len(data)} bytes)")
                time.sleep(0.1)
            sock.close()
        
        print("Criando ControlInterface...")
        control = ControlInterface(
            tx_ip='127.0.0.1', tx_port=10002,
            rx_ip='127.0.0.1', rx_port=10003,
            use_multicast=False
        )
        
        print("[OK] ControlInterface criado")
        print("\nIniciando sender em thread separada...")
        
        tx_thread = threading.Thread(target=sender, daemon=True)
        tx_thread.start()
        
        print("Tentando receber dados...")
        start = time.time()
        frames_received = 0
        
        while time.time() - start < 3:
            frame = control.receive_frame(blocking=False)
            if frame and frame.ball.x >= 0:
                frames_received += 1
                print(f"  [RECEIVER] Frame recebido | Ball: ({frame.ball.x}, {frame.ball.y})")
            time.sleep(0.05)
        
        print(f"\n[RESULTADO] {frames_received} frames recebidos")
        
        control.close()
        tx_thread.join(timeout=1)
        
    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback
        traceback.print_exc()


def main():
    print("\n" + "="*80)
    print(" DIAGNÓSTICO COMPLETO - Vision Listener".center(80))
    print("="*80)
    
    test_socket_binding()
    test_receiver_class()
    test_control_interface()
    send_test_data()
    
    print("\n" + "="*80)
    print("DIAGNÓSTICO COMPLETO")
    print("="*80)
    print("\nSe todos os testes passaram, então:")
    print("  1. O socket está funcionando corretamente")
    print("  2. O VisionReceiver está funcionando")
    print("  3. O ControlInterface está funcionando")
    print("  4. A comunicação UDP está funcionando")
    print("\nSe algo falhou, verifique as mensagens de erro acima.")
    print()


if __name__ == "__main__":
    main()
