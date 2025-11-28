#pragma once

#include <Arduino.h>
#include <esp_now.h>
#include <WiFi.h>
#include <vector>

#include "PacketQueue.h"
#include "RobotChannel.h"
#include "PFOXPacket.h"

class ESPHub {
public:
    ESPHub();
    ~ESPHub() = default;

    void begin();
    void loop();

    // Serial handling
    void receiveSerial();
    void processSerialBytes();

    // PC <-> HUB
    void sendAckToPC(const PFOXPacket& original_pkt);
    void forwardToPC(const PFOXPacket& pkt);

    // outgoing (to robots)
    void sendToRobot(const PFOXPacket& pkt);      // Envia via ESP-NOW
    void addToQueue(uint8_t robotId, const PFOXPacket& pkt);

    // tick / timeouts
    void tickRobotChannels();
    void processTimeouts(); // opcional, chamado por loop()

    // util
    bool getRobotMac(PFOXAddress robot_id, uint8_t mac[6]);

    // Callbacks (estáticos) - registro no esp_now
    static void onESPNOWSent(const wifi_tx_info_t *info, esp_now_send_status_t status);
    static void onESPNOWRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len);

private:
    // filas de entrada/saida PFOX
    PacketQueue incoming;   // já existia no seu código
    PacketQueue outgoing;   // ainda pode ser usado para broadcast / logs

    // serial buffer
    std::vector<uint8_t> serialBuffer;

    // canais por robô (index 1..3)
    RobotChannel robots[4];

    // debug / instance
    static ESPHub* instance;

    // configurações
    static constexpr uint32_t ACK_TIMEOUT_MS = 60;  // ms (ajustar conforme teste)
    static constexpr uint8_t MAX_RETRY = 3;

    // helpers internos
    void processIncomingFromPC(const PFOXPacket& pkt);
    void handleIncomingFromRobot(const PFOXPacket& pkt, const esp_now_recv_info_t *info);

    // proibir cópia
    ESPHub(const ESPHub&) = delete;
    ESPHub& operator=(const ESPHub&) = delete;
};
