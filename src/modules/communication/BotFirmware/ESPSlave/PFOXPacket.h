#pragma once
#include <vector>
#include <cstdint>
#include <stdexcept>

// CRC16-CCITT
uint16_t crc16_ccitt(const uint8_t* data, size_t length, uint16_t crc = 0xFFFF);

enum class PFOXAddress : uint8_t {
    PC = 0x00,
    ROBOT1 = 0x01,
    ROBOT2 = 0x02,
    ROBOT3 = 0x03,
    ESPMAIN = 0xFE,
    BROADCAST = 0xFF
};

enum class PFOXMsgType : uint8_t {
    CMD_SET_SPEED = 0x10,
    CMD_FLOW_CTRL = 0x11,
    ACK = 0x20,
    STATUS = 0x30,
    HEARTBEAT = 0x40,
    ERROR = 0x50
};

enum class PFOXFlowType : uint8_t {
    RUN = 0x10,
    STOP = 0x20,
    PAUSE = 0x30
};

struct PFOXPacket {
    static constexpr uint8_t PREAMBLE = 0xF0;
    static constexpr uint8_t VERSION = 0x01;

    uint8_t preamble;
    uint8_t version;
    PFOXAddress src;
    PFOXAddress dst;
    PFOXMsgType type;

    uint32_t seq24; //agora usa uma SEQ de 3 bytes (24 bits)

    uint8_t len;
    std::vector<uint8_t> payload;
    uint16_t crc16;

    PFOXPacket() : preamble(PREAMBLE), version(VERSION), seq24(0), len(0), crc16(0) {}

    // Construtor a partir de dados recebidos
    PFOXPacket(const uint8_t* data, size_t size);

    // Codifica em bytes
    std::vector<uint8_t> encode() const;
};
