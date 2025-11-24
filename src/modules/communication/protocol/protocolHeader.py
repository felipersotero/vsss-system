import struct
from enum import IntEnum
from typing import List

# =========================
# CRC16-CCITT (polinômio 0x1021)
# =========================
def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc

# =========================
# Endereços
# =========================
class Address(IntEnum):
    PC = 0x00
    ROBOT1 = 0x01
    ROBOT2 = 0x02
    ROBOT3 = 0x03
    ESPMAIN = 0xFE
    BROADCAST = 0xFF

# =========================
# Tipos de Mensagem
# =========================
class MsgType(IntEnum):
    CMD_SET_SPEED = 0x10
    CMD_FLOW_CTRL = 0x11
    ACK = 0x20
    STATUS = 0x30
    HEARTBEAT = 0x40
    ERROR = 0x50

# Nome para debug/log
MSG_TYPE_NAMES = {t.value: t.name for t in MsgType}

# =========================
# Pacote PFOX
# =========================
class PFOXPacket:
    PREAMBLE = 0xF0
    VERSION = 0x01

    def __init__(self, src: Address, dst: Address, msg_type: MsgType, seq: int, payload: List[int]):
        self.preamble = PFOXPacket.PREAMBLE
        self.version = PFOXPacket.VERSION
        self.src = src
        self.dst = dst
        self.type = msg_type
        self.seq = seq
        self.len = len(payload)
        self.payload = payload
        self.crc16 = 0  # Calculado ao codificar

    def encode(self) -> bytes:
        """Codifica o pacote em bytes e calcula CRC16."""
        header = struct.pack(
            '>BBBBBBB',
            self.preamble,
            self.version,
            self.src.value,
            self.dst.value,
            self.type.value,
            self.seq,
            self.len
        )
        payload_bytes = bytes(self.payload)
        crc = crc16_ccitt(header + payload_bytes)
        self.crc16 = crc
        packet = header + payload_bytes + struct.pack('>H', crc)
        return packet

    @classmethod
    def decode(cls, data: bytes):
        """Decodifica bytes em um objeto PFOXPacket. Lança ValueError se CRC inválido."""
        if len(data) < 9:
            raise ValueError("Pacote muito curto")

        preamble, version, src, dst, msg_type, seq, length = struct.unpack('>BBBBBBB', data[:7])
        payload = list(data[7:7+length])
        crc_received = struct.unpack('>H', data[7+length:9+length])[0]

        # Valida CRC
        crc_calc = crc16_ccitt(data[:7+length])
        if crc_calc != crc_received:
            raise ValueError(f"CRC inválido: recebido {crc_received:04X}, calculado {crc_calc:04X}")

        packet = cls(Address(src), Address(dst), MsgType(msg_type), seq, payload)
        packet.crc16 = crc_received
        return packet

    def __repr__(self):
        return (f"PFOXPacket(src={self.src.name}, dst={self.dst.name}, type={self.type.name}, "
                f"seq={self.seq}, len={self.len}, payload={self.payload}, crc=0x{self.crc16:04X})")


# =========================
# Controlador de Pacotes
# =========================
class PFOXController:
    def __init__(self):
        self.seq_counter = 0

    def next_seq(self) -> int:
        self.seq_counter = (self.seq_counter + 1) % 256
        return self.seq_counter

    # ============================================================
    # 🔹 MÉTODO GENÉRICO (BASE) – cria QUALQUER pacote PFOX
    # ============================================================
    def create_packet(self, dst: Address, msg_type: MsgType, payload: List[int]) -> PFOXPacket:
        packet = PFOXPacket(
            src=Address.PC,      # PC sempre é a origem
            dst=dst,
            msg_type=msg_type,
            seq=self.next_seq(),
            payload=payload
        )
        return packet

    # ============================================================
    # 🔹 ENVIO GENÉRICO — qualquer destino, qualquer payload
    # ============================================================
    def send_custom(self, dst: Address, msg_type: MsgType, payload: List[int]) -> PFOXPacket:
        """
        Cria qualquer tipo de mensagem com payload arbitrário.
        Ex: send_custom(Address.ROBOT1, MsgType.STATUS, [10,20,30])
        """
        return self.create_packet(dst, msg_type, payload)

    # ============================================================
    # 🔹 BROADCAST – qualquer mensagem para todos os robôs
    # ============================================================
    def send_broadcast(self, msg_type: MsgType, payload: List[int]) -> PFOXPacket:
        """
        Envia para todos os dispositivos no barramento.
        """
        return self.create_packet(Address.BROADCAST, msg_type, payload)

    # ============================================================
    # 🔹 ACK – resposta comum
    # ============================================================
    def send_ack(self, dst: Address, ack_code: int = 0x00) -> PFOXPacket:
        """
        ack_code é um código opcional de confirmação.
        """
        return self.create_packet(dst, MsgType.ACK, [ack_code & 0xFF])

    # ============================================================
    # 🔹 HEARTBEAT (ping)
    # ============================================================
    def send_heartbeat(self, dst: Address = Address.BROADCAST) -> PFOXPacket:
        """
        Heartbeat pode ser enviado para um robô específico ou broadcast.
        """
        return self.create_packet(dst, MsgType.HEARTBEAT, [])

    # ============================================================
    # 🔹 ERROR – envia código de erro
    # ============================================================
    def send_error(self, dst: Address, error_code: int) -> PFOXPacket:
        return self.create_packet(dst, MsgType.ERROR, [error_code & 0xFF])

    # ============================================================
    # 🔹 FLOW CONTROL (ex: iniciar/pausar motor)
    # ============================================================
    def send_flow_control(self, dst: Address, value: int) -> PFOXPacket:
        """
        value pode ser: 0x00 = STOP, 0x01 = RUN, etc.
        """
        return self.create_packet(dst, MsgType.CMD_FLOW_CTRL, [value & 0xFF])

    # ============================================================
    # 🔹 SEU PACOTE ORIGINAL: SET SPEED
    # ============================================================
    def send_speed_command(self, robot_id: Address, left_speed_real: int, left_speed_desired: int,
                           right_speed_real: int, right_speed_desired: int) -> PFOXPacket:

        payload = [
            robot_id.value,
            left_speed_real & 0xFF,
            left_speed_desired & 0xFF,
            right_speed_real & 0xFF,
            right_speed_desired & 0xFF
        ]

        return self.create_packet(robot_id, MsgType.CMD_SET_SPEED, payload)



# =========================
# Exemplo de uso
# =========================
if __name__ == "__main__":
    controller = PFOXController()

    # Criar pacote para Robô 1
    pkt = controller.send_speed_command(
        robot_id=Address.ROBOT1,
        left_speed_real=195,
        left_speed_desired=200,
        right_speed_real=145,
        right_speed_desired=150
    )

    raw = pkt.encode()
    print(f"Pacote codificado: {raw.hex()}")

    decoded = PFOXPacket.decode(raw)
    print(f"Pacote decodificado: {decoded}")
