#include "PFOXPacket.h"
#include <cstring>

// CRC16-CCITT
uint16_t crc16_ccitt(const uint8_t* data, size_t length, uint16_t crc) {
    for (size_t i = 0; i < length; ++i) {
        crc ^= (uint16_t)data[i] << 8;
        for (int j = 0; j < 8; ++j) {
            if (crc & 0x8000) crc = (crc << 1) ^ 0x1021;
            else crc <<= 1;
            crc &= 0xFFFF;
        }
    }
    return crc;
}

// Construtor de decodificação
PFOXPacket::PFOXPacket(const uint8_t* data, size_t size) {
    if (size < 9) throw std::runtime_error("Pacote muito curto");

    preamble = data[0];
    version = data[1];
    src = static_cast<PFOXAddress>(data[2]);
    dst = static_cast<PFOXAddress>(data[3]);
    type = static_cast<PFOXMsgType>(data[4]);
    seq = data[5];
    len = data[6];

    if (size < 7 + len + 2) throw std::runtime_error("Pacote incompleto");

    payload.assign(data + 7, data + 7 + len);

    crc16 = (data[7 + len] << 8) | data[7 + len + 1];

    uint16_t calc_crc = crc16_ccitt(data, 7 + len);
    if (calc_crc != crc16) throw std::runtime_error("CRC inválido");
}

// Codifica pacote em bytes
std::vector<uint8_t> PFOXPacket::encode() const {
    std::vector<uint8_t> buf;
    buf.push_back(preamble);
    buf.push_back(version);
    buf.push_back(static_cast<uint8_t>(src));
    buf.push_back(static_cast<uint8_t>(dst));
    buf.push_back(static_cast<uint8_t>(type));
    buf.push_back(seq);
    buf.push_back(len);
    buf.insert(buf.end(), payload.begin(), payload.end());

    uint16_t crc = crc16_ccitt(buf.data(), buf.size());
    buf.push_back(crc >> 8);
    buf.push_back(crc & 0xFF);

    return buf;
}
