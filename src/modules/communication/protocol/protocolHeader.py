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
    # 💡 CORREÇÃO CRÍTICA: Trocando 'id_pkt' por 'seq' para compatibilidade com PFOXController
    def __init__(self, src: Address, dst: Address, msg_type: MsgType, 
                 payload: List[int], seq: int = 0): 
        self.start = 0xF0
        self.src = src
        self.dst = dst
        self.type = msg_type
        self.id = seq # O número de sequência/ID do pacote
        self.payload = bytes(payload)
        self.len = len(self.payload)
        self.crc = 0 # Inicialmente 0, será calculado na serialização
        
    def __repr__(self) -> str:
        """Representação amigável para debug (usada no log RX)"""
        msg_name = MSG_TYPE_NAMES.get(self.type.value, f"0x{self.type.value:02X}")
        return (f"PKT(SRC={self.src.name}, DST={self.dst.name}, TYPE={msg_name}, "
                f"ID={self.id}, LEN={self.len}, PAYLOAD={self.payload.hex()})")

    # =================================================================
    # Método para Serializar o Pacote (TX)
    # =================================================================
    def to_bytes(self) -> bytes:
        """Serializa o objeto PFOXPacket em uma sequência de bytes com CRC16."""
        # O cabeçalho é: START(0xF0), SRC, DST, TYPE, ID, LEN
        header = struct.pack('!BBBBBB', 
            self.start, 
            self.src.value, 
            self.dst.value, 
            self.type.value, 
            self.id, 
            self.len
        )
        
        packet_without_crc = header + self.payload
        crc_value = crc16_ccitt(packet_without_crc)
        crc_bytes = struct.pack('!H', crc_value)
        
        return packet_without_crc + crc_bytes

    @classmethod
    def decode(cls, data: bytes) -> 'PFOXPacket':
        """Decodifica bytes brutos em um objeto PFOXPacket e verifica o CRC."""
        if len(data) < 9 or data[0] != 0xF0:
            raise ValueError("Pacote PFOX incompleto ou inválido.")

        header_len = 6
        # Desempacota Header: START(B), SRC(B), DST(B), TYPE(B), ID(B), LEN(B)
        start, src_val, dst_val, type_val, id_pkt, payload_len = struct.unpack('!BBBBBB', data[:header_len])
        
        total_len = header_len + payload_len + 2 # Header + Payload + CRC
        
        if len(data) != total_len:
            raise ValueError(f"Tamanho do pacote ({len(data)}) não corresponde ao LEN reportado ({total_len}).")

        # Verifica CRC
        received_crc = struct.unpack('!H', data[-2:])[0]
        calculated_crc = crc16_ccitt(data[:-2])
        
        if received_crc != calculated_crc:
            raise ValueError(f"Falha na verificação CRC. Recebido: 0x{received_crc:04X}, Calculado: 0x{calculated_crc:04X}.")

        # Extrai Payload
        payload = list(data[header_len:-2]) # Converte para List[int] para compatibilidade
        
        # Cria e retorna o objeto. Usamos 'seq=id_pkt' para manter o novo nome do parâmetro.
        return cls(
            src=Address(src_val), 
            dst=Address(dst_val), 
            msg_type=MsgType(type_val), 
            payload=payload, 
            seq=id_pkt 
        )
    
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
