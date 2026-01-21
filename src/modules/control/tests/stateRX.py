import sys 
import logging
from pathlib import Path

# --- Bloco de Importação Robusto ---
try:
    # Tenta importação relativa (caso esteja rodando como módulo)
    from ..protocols import common_pb2
    from ..receiver import Receiver
except Exception:
    # Fallback para execução direta (ex: python stateRX.py)
    # Adiciona a raiz 'src' ao path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from modules.control.comm.protocols import common_pb2
    from modules.control.comm.receiver import Receiver

# Configuração de Log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [RX_STATE] - %(message)s')

class StateMonitor(Receiver):
    def __init__(self, ip='224.0.0.1', port=10002):
        # O super().__init__ agora usa sua lógica inteligente (Multicast/Unicast)
        super().__init__(ip, port) 
        logging.info(f"Monitorando Field State em {ip}:{port}")

    def run(self):
        """Loop principal de recebimento."""
        while True:
            # receive() agora é seguro contra timeouts e erros de socket
            data = self.receive()
            if not data:
                continue
            
            try:
                # Decodifica o Frame usando o Protobuf
                frame = common_pb2.Frame()
                frame.ParseFromString(data)
                
                # Exibe resumo visual
                self.print_summary(frame)
                
            except Exception as e:
                logging.error(f"Erro decode: {e}")

    def print_summary(self, frame):
        # Código ANSI para limpar a tela e mover cursor para o topo (Linux/Mac/GitBash)
        # Se estiver no CMD do Windows puro, pode remover essa linha se ficar estranho
        print("\033[H\033[J", end="") 

        print(f"=== VSSS SIMULATOR STATE ===")
        print(f"BALL  | X: {frame.ball.x:6.3f}  Y: {frame.ball.y:6.3f}  vX: {frame.ball.vx:6.3f} vY: {frame.ball.vy:6.3f} ")
        print("-" * 40)
        print("      |  ID  |   X    |   Y    | THETA ")
        print("-" * 40)
        
        # Lista Robôs Azuis
        for r in frame.robots_blue:
            print(f"BLUE  |  {r.robot_id}   | {r.x:6.3f} | {r.y:6.3f} | {r.orientation:6.3f}")
            
        print("-" * 40)
        
        # Lista Robôs Amarelos
        for r in frame.robots_yellow:
            print(f"YEL   |  {r.robot_id}   | {r.x:6.3f} | {r.y:6.3f} | {r.orientation:6.3f}")
            
        print("=" * 40)
        print("Pressione Ctrl+C para sair...")

if __name__ == "__main__":
    # IMPORTANTE: Use "224.0.0.1" para Multicast Real ou "127.0.0.1" para Teste Local
    # Como sua classe Receiver agora suporta ambos, basta mudar aqui.
    receiver_ip = "127.0.0.1"  
    port = 10002
    monitor = StateMonitor(ip=receiver_ip, port=port)
    
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\nMonitoramento encerrado.")
        monitor.receiver_socket.close()