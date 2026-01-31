from ..receiver import Receiver
from ..protocols import command_pb2
from ...core.command import TeamCommand
import logging

# Configuração de Log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [RX_CMD] - %(message)s')

class CommandsReceiver(Receiver):
    def __init__(self, ip='224.0.0.1', port=10003):
        # Chama o construtor da sua classe Receiver fornecida
        super().__init__(ip, port) #
        logging.info(f"Monitorando comandos em {ip}:{port}")

    def receive_and_convert(self):
        """Recebe pacote UDP e converte para TeamCommand."""
        try:
            # Usa o método receive() da sua classe base Receiver
            data = self.receive() #
            
            if not data:
                return None

            # Decodifica Protobuf
            pb_commands = command_pb2.Commands()
            pb_commands.ParseFromString(data)

            # Instancia sua classe TeamCommand
            new_team_command = TeamCommand() #

            for cmd in pb_commands.robot_commands:
                # Filtra time (assumindo que somos Blue, então yellowteam deve ser False)
                if not cmd.yellowteam:
                    if 0 <= cmd.id < 3:
                        # Acessa os comandos internos do TeamCommand
                        robot_cmd = new_team_command.commands[cmd.id] #
                        robot_cmd.left_speed = cmd.wheel_left
                        robot_cmd.right_speed = cmd.wheel_right
            
            return new_team_command

        except Exception as e:
            logging.error(f"Erro no parse: {e}")
            return None
      

if __name__ == "__main__":
    receiver = CommandsReceiver()
    
    while True:
        try:
            team_cmd = receiver.receive_and_convert()
            if team_cmd:
                # Exibe usando o __str__ da sua classe TeamCommand
                print(team_cmd) #
        except KeyboardInterrupt:
            logging.info("Encerrando receiver.")
            receiver.close() #
            break