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

# No arquivo protocolHeader.py (substituir a classe PFOXPacket)

# =========================
# Estrutura do Pacote PFOX
# =========================
class PFOXPacket:
    def __init__(self, src: Address, dst: Address, msg_type: MsgType, payload: List[int],
                 seq: int = 0, version: int = 0x01):
        self.start = 0xF0
        self.version = version
        self.src = src
        self.dst = dst
        self.msg_type = msg_type
        self.id = seq
        self.payload = bytes(payload)
        self.len = len(self.payload)
        self.crc = 0

    def __repr__(self) -> str:
        msg_name = MSG_TYPE_NAMES.get(self.msg_type.value, f"0x{self.msg_type.value:02X}")
        return (f"PKT(SRC={self.src.name}, DST={self.dst.name}, TYPE={msg_name}, "
                f"ID={self.id}, LEN={self.len}, PAYLOAD={self.payload.hex()})")

    def to_bytes(self) -> bytes:
        """Serializa o pacote incluindo Version e CRC16."""
        header = struct.pack(
            '!BBBBBBB',  # 7 bytes de header
            self.start,
            self.version,
            self.src.value,
            self.dst.value,
            self.msg_type.value,
            self.id,
            self.len
        )
        packet_without_crc = header + self.payload
        crc_value = crc16_ccitt(packet_without_crc)
        crc_bytes = struct.pack('!H', crc_value)
        return packet_without_crc + crc_bytes

    @classmethod
    def decode(cls, data: bytes) -> 'PFOXPacket':
        if len(data) < 9 or data[0] != 0xF0:  # 7 header + 2 CRC = 9 mínimo
            raise ValueError("Pacote PFOX incompleto ou inválido.")
        
        header_len = 7
        start, version, src_val, dst_val, type_val, seq, payload_len = struct.unpack(
            '!BBBBBBB', data[:header_len]
        )
        total_len = header_len + payload_len + 2
        if len(data) != total_len:
            raise ValueError("Tamanho do pacote não confere.")
        
        payload = data[header_len:header_len+payload_len]
        crc_received = struct.unpack('!H', data[header_len+payload_len:])[0]
        crc_calc = crc16_ccitt(data[:header_len+payload_len])
        if crc_received != crc_calc:
            raise ValueError("CRC inválido.")
        
        return cls(
            src=Address(src_val),
            dst=Address(dst_val),
            msg_type=MsgType(type_val),
            payload=list(payload),
            seq=seq,
            version=version
        )

# =========================
# Controlador de Pacotes
# =========================
class PFOXController:
    def __init__(self, version: int = 0x01):
        self.seq_counter = 0
        self.version = version  # Versão do protocolo

    def next_seq(self) -> int:
        self.seq_counter = (self.seq_counter + 1) % 256
        return self.seq_counter

    # ============================================================
    # 🔹 MÉTODO GENÉRICO (BASE) – cria QUALQUER pacote PFOX
    # ============================================================
    def create_packet(self, dst: Address, msg_type: MsgType, payload: List[int]) -> PFOXPacket:
        seq_to_use = self.next_seq()
        self.last_seq_used = seq_to_use  # Salva o último ID usado

        packet = PFOXPacket(
            src=Address.PC,  # PC sempre é a origem
            dst=dst,
            msg_type=msg_type,
            seq=seq_to_use,
            payload=payload,
            version=self.version  # ⚡ Propaga a versão
        )
        return packet

    # ============================================================
    # 🔹 ENVIO GENÉRICO — qualquer destino, qualquer payload
    # ============================================================
    def send_custom(self, dst: Address, msg_type: MsgType, payload: List[int]) -> PFOXPacket:
        return self.create_packet(dst, msg_type, payload)

    # ============================================================
    # 🔹 BROADCAST – qualquer mensagem para todos os robôs
    # ============================================================
    def send_broadcast(self, msg_type: MsgType, payload: List[int]) -> PFOXPacket:
        return self.create_packet(Address.BROADCAST, msg_type, payload)

    # ============================================================
    # 🔹 ACK – resposta comum
    # ============================================================
    def send_ack(self, dst: Address, ack_code: int = 0x00) -> PFOXPacket:
        return self.create_packet(dst, MsgType.ACK, [ack_code & 0xFF])

    # ============================================================
    # 🔹 HEARTBEAT (ping)
    # ============================================================
    def send_heartbeat(self, dst: Address = Address.BROADCAST) -> PFOXPacket:
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
        return self.create_packet(dst, MsgType.CMD_FLOW_CTRL, [value & 0xFF])

    # ============================================================
    # 🔹 SET SPEED
    # ============================================================
    def send_speed_command(
        self,
        robot_id: Address,
        left_speed_real: int,
        left_speed_desired: int,
        right_speed_real: int,
        right_speed_desired: int
    ) -> PFOXPacket:

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

