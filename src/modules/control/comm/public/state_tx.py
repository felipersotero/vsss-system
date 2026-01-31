from ..transmitter  import Transmitter
from ..protocols import common_pb2

class StatesTransmissor(Transmitter):
    def __init__(self, ip="224.0.0.1", port=10002):
        super().__init__(ip, port)

    def send_state(self, field_data):
        """Transforma FieldData interno em Frame Protobuf e envia[cite: 15]."""
        frame = common_pb2.Frame()
        
        # 1. Mapeamento da Bola [cite: 11]
        frame.ball.x = field_data.ball.position.x
        frame.ball.y = field_data.ball.position.y
        frame.ball.vx = field_data.ball.velocity.x
        frame.ball.vy = field_data.ball.velocity.y

        # 2. Mapeamento dos Nossos Robôs (Azul) [cite: 13, 16]
        for i in range(3):
            robot_in = field_data.robots[i]
            robot_out = frame.robots_blue.add()
            self._map_entity_to_proto(i, robot_in, robot_out)

        # 3. Mapeamento dos Adversários (Amarelo) [cite: 13, 16]
        for i in range(3):
            foe_in = field_data.foes[i]
            robot_out = frame.robots_yellow.add()
            self._map_entity_to_proto(i, foe_in, robot_out)

        self.transmit(frame) # Serializa e envia via UDP [cite: 15]

    def _map_entity_to_proto(self, robot_id, entity_in, pb_robot):
        """Helper para mapear EntityData para mensagem Robot[cite: 13]."""
        pb_robot.robot_id = robot_id
        pb_robot.x = entity_in.position.x
        pb_robot.y = entity_in.position.y
        pb_robot.orientation = entity_in.position.theta
        pb_robot.vx = entity_in.velocity.x
        pb_robot.vy = entity_in.velocity.y
        pb_robot.vorientation = entity_in.velocity.theta