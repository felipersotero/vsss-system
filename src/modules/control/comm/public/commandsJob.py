from ..thread_job import Job
from ..protocols import command_pb2

class CommandsReceiverJob(Job):
    def __init__(self, receiver, team_command_instance):
        super().__init__(job_function=self._run_step)
        self.receiver = receiver
        self.team_command = team_command_instance # Instância global de TeamCommand

    def _run_step(self):
        data = self.receiver.receive() # Bloqueia até receber bytes
        if not data:
            return

        pb_commands = command_pb2.Commands()
        pb_commands.ParseFromString(data)

        for cmd in pb_commands.robot_commands:
            # Filtra apenas os comandos para a nossa equipe (ex: Blue)
            if not cmd.yellowteam and 0 <= cmd.id < 3:
                # Atualiza diretamente o objeto interno
                self.team_command.commands[cmd.id].left_speed = cmd.wheel_left
                self.team_command.commands[cmd.id].right_speed = cmd.wheel_right