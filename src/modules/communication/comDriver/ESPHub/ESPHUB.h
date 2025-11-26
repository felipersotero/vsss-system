#pragma once
#include "PacketQueue.h"
#include "PFOXPacket.h" // Adicionado para garantir o PFOXAddress/MsgType
#include <Arduino.h>
#include <esp_now.h>
#include <WiFi.h>
#include <vector>

class ESPHub {
private:
    static ESPHub* instance;
    PacketQueue incoming;
    PacketQueue outgoing;

    std::vector<uint8_t> serialBuffer;

    struct PendingAck {
        uint8_t seq24;
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
    void sendToRobot(const PFOXPacket& pkt);
    void sendAckToPC(const PFOXPacket& pkt);
    void forwardToPC(const PFOXPacket& pkt);

    void processOutgoing();
    void processTimeouts();

    bool getRobotMac(PFOXAddress robot_id, uint8_t mac[6]);
    
    // ** REMOVIDA: A função logToPC foi removida do header **

public:
    ESPHub();
    void begin();
    void loop();
    void receiveSerial();

    // usado pelos callbacks estáticos
    static ESPHub* getInstance() { return instance; }
};