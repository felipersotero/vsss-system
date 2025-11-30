import struct
from enum import IntEnum
from typing import List

# =========================
# CRC16-CCITT
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

class FlowType(IntEnum):
    STOP = 0x20
    RUN = 0x10
    PAUSE = 0x30

# Nome amigável
MSG_TYPE_NAMES = {t.value: t.name for t in MsgType}


# =========================
# Estrutura do Pacote PFOX
# =========================
class PFOXPacket:
    HEADER_LEN = 9
    START_BYTE = 0xF0

    def __init__(
        self,
        src: Address,
        dst: Address,
        msg_type: MsgType,
        payload: List[int],
        seq24: int = 0,
        version: int = 0x01
    ):
        self.start = self.START_BYTE
        self.version = version
        self.src = src
        self.dst = dst
        self.msg_type = msg_type
        self.seq24 = seq24 & 0xFFFFFF      # força 24-bit
        self.payload = bytes(payload)
        self.len = len(self.payload)
        self.crc = 0

    def __repr__(self) -> str:
        msg_name = MSG_TYPE_NAMES.get(self.msg_type.value, f"0x{self.msg_type.value:02X}")
        return (
            f"PKT(SRC={self.src.name}, DST={self.dst.name}, TYPE={msg_name}, "
            f"SEQ24={self.seq24}, LEN={self.len}, PAYLOAD={self.payload.hex()})"
        )

    # ============================
    # ENCODE
    # ============================
    def to_bytes(self) -> bytes:
        header = struct.pack(
            "!BBBBBBBBB",
            self.start,
            self.version,
            self.src.value,
            self.dst.value,
            self.msg_type.value,
            (self.seq24 >> 16) & 0xFF,
            (self.seq24 >> 8) & 0xFF,
            self.seq24 & 0xFF,
            self.len
        )

        pkt_no_crc = header + self.payload
        crc_val = crc16_ccitt(pkt_no_crc)
        return pkt_no_crc + struct.pack("!H", crc_val)

    # ============================
    # DECODE
    # ============================
    @classmethod
    def decode(cls, data: bytes) -> "PFOXPacket":

        if len(data) < cls.HEADER_LEN:
            raise ValueError("INCOMPLETE_HEADER")

        start, version, src, dst, type_, h, m, l, plen = struct.unpack(
            "!BBBBBBBBB", data[:cls.HEADER_LEN]
        )

        if start != cls.START_BYTE:
            raise ValueError("BAD_START")

        total_len = cls.HEADER_LEN + plen + 2
        if len(data) < total_len:
            raise ValueError("INCOMPLETE_PACKET")

        payload = data[cls.HEADER_LEN:cls.HEADER_LEN + plen]

        # Verifica CRC
        crc_recv = struct.unpack("!H", data[cls.HEADER_LEN + plen:total_len])[0]
        crc_calc = crc16_ccitt(data[:cls.HEADER_LEN + plen])

        if crc_recv != crc_calc:
            raise ValueError("BAD_CRC")

        seq24 = (h << 16) | (m << 8) | l

        pkt = cls(
            src=Address(src),
            dst=Address(dst),
            msg_type=MsgType(type_),
            payload=list(payload),
            seq24=seq24,
            version=version
        )
    

        return pkt, total_len


# =========================
# Controlador de Pacotes
# =========================
class PFOXController:
    def __init__(self, version: int = 0x01):
        self.seq_counter = 0
        self.version = version

    def next_seq(self) -> int:
        self.seq_counter = (self.seq_counter + 1) & 0xFFFFFF
        return self.seq_counter

    # Cria qualquer pacote
    def create_packet(self, dst: Address, msg_type: MsgType, payload: List[int]) -> PFOXPacket:
        seq = self.next_seq()
        return PFOXPacket(
            src=Address.PC,
            dst=dst,
            msg_type=msg_type,
            seq24=seq,
            payload=payload,
            version=self.version
        )

    def send_custom(self, dst: Address, msg_type: MsgType, payload: List[int]):
        return self.create_packet(dst, msg_type, payload)

    def send_broadcast(self, msg_type: MsgType, payload: List[int]):
        return self.create_packet(Address.BROADCAST, msg_type, payload)

    def send_ack(self, dst: Address):
        return self.create_packet(dst, MsgType.ACK, [])

    def send_heartbeat(self, dst: Address = Address.BROADCAST):
        return self.create_packet(dst, MsgType.HEARTBEAT, [])

    def send_error(self, dst: Address, err: int):
        return self.create_packet(dst, MsgType.ERROR, [err & 0xFF])

    def send_flow_control(self, dst: Address, value: int):
        return self.create_packet(dst, MsgType.CMD_FLOW_CTRL, [value & 0xFF])

    def request_status(self, dst: Address):
        return self.create_packet(dst,MsgType.STATUS,[])
    
    # =========================================
    # SPEED COMMAND (USO CORRETO DO PAYLOAD)
    # =========================================
    def send_speed_command(
        self,
        robot_id: Address,
        left_real: int,
        left_des: int,
        right_real: int,
        right_des: int
    ) -> PFOXPacket:

        def int16(x): return list(x.to_bytes(2, "big", signed=True))

        payload = [robot_id.value]
        payload += int16(left_real)
        payload += int16(left_des)
        payload += int16(right_real)
        payload += int16(right_des)

        return self.create_packet(robot_id, MsgType.CMD_SET_SPEED, payload)

# =========================
# Exemplo de uso
# =========================
if __name__ == "__main__":
    controller = PFOXController()

    # Criar pacote para Robô 1
    pkt = controller.send_speed_command(
        robot_id=Address.ROBOT1,
        left_real=195,
        left_des=200,
        right_real=145,
        right_des=150
    )

    raw = pkt.to_bytes()
    print(f"Pacote codificado: {raw.hex()}")

    decoded = PFOXPacket.decode(raw)
    print(f"Pacote decodificado: {decoded}")

    # Teste com HEARTBEAT (payload zero)
    hb_pkt = controller.send_heartbeat(Address.ROBOT2)
    raw_hb = hb_pkt.to_bytes()
    print(f"HEARTBEAT codificado: {raw_hb.hex()}")
    decoded_hb = PFOXPacket.decode(raw_hb)
    print(f"HEARTBEAT decodificado: {decoded_hb}")

