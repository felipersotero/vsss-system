#pragma once
#include "PacketQueue.h"
#include "PFOXPacket.h" // Adicionado para garantir o PFOXAddress/MsgType
#include <Arduino.h>
#include <esp_now.h>
#include <WiFi.h>
#include <vector>

class ESPSlave {
private:
    static ESPSlave* instance;
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

    // Métodos estáticos (Callbacks)
    static void onESPNOWSent(const wifi_tx_info_t* info, esp_now_send_status_t status);
    static void onESPNOWRecv(const esp_now_recv_info_t* info, const uint8_t* data, int len);

    // Métodos de processamento
    void processSerialBytes();
    void sendAckToHUB(const PFOXPacket& pkt);
    void forwardToHUB(const PFOXPacket& pkt);

    void processOutgoing();
    void processTimeouts();


public:
    ESPSlave();
    void begin();
    void loop();
    void receiveSerial();

    // usado pelos callbacks estáticos
    static ESPSlave* getInstance() { return instance; }
};