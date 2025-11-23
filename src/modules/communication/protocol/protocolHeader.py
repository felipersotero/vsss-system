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

    def send_speed_command(self, robot_id: Address, left_speed_real: int, left_speed_desired: int,
                           right_speed_real: int, right_speed_desired: int) -> PFOXPacket:
        """
        Cria um pacote CMD_SET_SPEED com velocidades reais e desejadas para cada roda.
        Payload: [robot_id, left_real, left_desired, right_real, right_desired]
        """
        payload = [
            robot_id.value,
            left_speed_real & 0xFF,
            left_speed_desired & 0xFF,
            right_speed_real & 0xFF,
            right_speed_desired & 0xFF
        ]
        packet = PFOXPacket(
            src=Address.PC,
            dst=robot_id,
            msg_type=MsgType.CMD_SET_SPEED,
            seq=self.next_seq(),
            payload=payload
        )
        return packet


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
