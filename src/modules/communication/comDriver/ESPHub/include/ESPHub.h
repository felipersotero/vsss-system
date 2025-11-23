#pragma once
#include "PacketQueue.h"
#include <Arduino.h>

class ESPHub {
private:
    PacketQueue incoming;
    PacketQueue outgoing;
    std::vector<uint8_t> serialBuffer;

    void processSerialBytes();
    void sendToRobot(const PFOXPacket& pkt);
    void sendAckToPC(const PFOXPacket& pkt);
    void logToPC(const String& message);

public:
    ESPHub();
    void loop();
    void receiveSerial();
};
