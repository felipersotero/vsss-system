import math
from ..thread_job import Job
from ..protocols import common_pb2

class StateTransmitterJob(Job):
    def __init__(self, transmitter, get_field_data_callback):
        super().__init__(job_function=self._run_step)
        self.transmitter = transmitter
        self.get_field_data = get_field_data_callback

    def _run_step(self):
        field_data = self.get_field_data()
        if not field_data:
            return

        frame = common_pb2.Frame()
        
        # Mapeamento da Bola: [x, y, theta, vx, vy]
        # O proto da bola não tem theta, usamos vx e vy diretamente
        frame.ball.x = field_data.ball.position.x
        frame.ball.y = field_data.ball.position.y
        frame.ball.vx = field_data.ball.velocity.x
        frame.ball.vy = field_data.ball.velocity.y

        # Mapeamento dos Robôs: [x, y, theta, v_left, v_right, omega]
        for i in range(3):
            self._add_robot(frame.robots_blue.add(), i, field_data.robots[i])
            self._add_robot(frame.robots_yellow.add(), i, field_data.foes[i])

        self.transmitter.transmit(frame) #

    def _add_robot(self, pb_robot, robot_id, internal_robot):
        pb_robot.robot_id = robot_id
        pb_robot.x = internal_robot.position.x
        pb_robot.y = internal_robot.position.y
        pb_robot.orientation = internal_robot.position.theta # Direção do robô
        
        # Conversão de Velocidade Diferencial para Linear (v_x, v_y)
        # v_linear = (v_left + v_right) / 2
        v_left = internal_robot.velocity.x # Usando x para v_left conforme sua definição
        v_right = internal_robot.velocity.y # Usando y para v_right conforme sua definição
        v_linear = (v_left + v_right) / 2.0
        
        pb_robot.vx = v_linear * math.cos(internal_robot.position.theta)
        pb_robot.vy = v_linear * math.sin(internal_robot.position.theta)
        pb_robot.vorientation = internal_robot.velocity.theta # omega/v_theta