#pragma once
#include "PacketQueue.h"
#include <Arduino.h>
#include <esp_now.h>
#include <WiFi.h>

class ESPHub {
private:
    PacketQueue incoming;
    PacketQueue outgoing;

    std::vector<uint8_t> serialBuffer;

    struct PendingAck {
        uint8_t seq;
        uint8_t dst;
        uint32_t timestamp;
        PFOXPacket pkt;
    };

    std::vector<PendingAck> pendingAcks;

    static void onESPNOWSent(const uint8_t *mac, esp_now_send_status_t status);
    static void onESPNOWRecv(const uint8_t *mac, const uint8_t *data, int len);

    void processSerialBytes();
    void sendToRobot(const PFOXPacket& pkt);
    void sendAckToPC(const PFOXPacket& pkt);
    void forwardToPC(const PFOXPacket& pkt);

    void processOutgoing();
    void processTimeouts();

    bool getRobotMac(PFOXAddress robot_id, uint8_t mac[6]);
    
    void logToPC(const String& msg);

public:
    ESPHub();
    void begin();
    void loop();
    void receiveSerial();

    // usado pelos callbacks estáticos
    static ESPHub* instance;
};
