#pragma once

#include <Arduino.h>
#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include "PFOXPacket.h"
#include "PFOXQueue.h"
#include "Control.h"

// Estrutura para os dados do robô diferencial
struct DiffRobotData {
    int16_t leftReal;
    int16_t leftDes;   // Desired (Setpoint)
    int16_t rightReal;
    int16_t rightDes;  // Desired (Setpoint)
};

class ESPSlave {
public:
    ESPSlave(PFOXAddress id, uint8_t* hubMacAddress);

    void begin();
    void loop();

    // Funções de Hardware (Robô Diferencial)
    // Recebe velocidade esquerda e direita (int16: -32768 a 32767)
    void setMotors(int16_t leftSpeed, int16_t rightSpeed);
    void stopMotors();

private:
    PFOXAddress myId;
    uint8_t hubMac[6];
    
    PacketQueue incomingQueue;
    static ESPSlave* instance;
    bool running;

    static void onDataRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len);
    static void onDataSent(const wifi_tx_info_t *info, esp_now_send_status_t status);

    void processPacket(const PFOXPacket& pkt);
    void sendAck(const PFOXPacket& originalPkt);
    void sendStatus(uint32_t seq);

    RobotControl robotCtrl;
};