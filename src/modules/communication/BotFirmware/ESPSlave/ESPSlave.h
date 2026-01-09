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

    static constexpr uint8_t LED_PIN = 2; 
    unsigned long blinkEndTime = 0;       
    uint32_t lastPacketTime = 0; 
    bool ledState = false;

    // --- NOVAS VARIÁVEIS PARA O DESACOPLAMENTO ---
    int16_t _targetL = 0, _targetR = 0;
    int16_t _currentL = 0, _currentR = 0;
    uint32_t _lastControlCycle = 0;
    const uint32_t CONTROL_INTERVAL_MS = 10; // Ciclo de 100Hz
};