#pragma once

#include <Arduino.h>
#include "PFOXPacket.h"
#include "PacketQueue.h"

struct RobotChannel {
    RobotChannel(size_t queue_size = 20) : queue(queue_size) {}

    PacketQueue queue;      // fila de comandos pendentes para o robô
    bool waitingAck = false;

    PFOXPacket lastPacket;  // último pacote enviado e aguardando ACK
    uint8_t retryCount = 0;

    uint32_t lastSendTime = 0; // millis() da última tentativa de envio
    uint32_t lastSeen     = 0; // millis() da última vez que recebeu algo do robô

    bool online = false;   // flag de conexão/online do robô
};
