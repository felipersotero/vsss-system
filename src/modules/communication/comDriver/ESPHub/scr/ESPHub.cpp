#include "ESPHub.h"

ESPHub::ESPHub() : incoming(100), outgoing(100) {}

void ESPHub::receiveSerial() {
    while (Serial.available()) {
        serialBuffer.push_back(Serial.read());
    }
}

void ESPHub::processSerialBytes() {
    while (serialBuffer.size() >= 7) {
        uint8_t len = serialBuffer[6];
        size_t total = 7 + len + 2;
        if (serialBuffer.size() < total) break;

        try {
            PFOXPacket pkt(serialBuffer.data(), total);
            incoming.push(pkt);
        } catch (...) {
            // CRC inválido, descarta primeiro byte
            serialBuffer.erase(serialBuffer.begin());
            continue;
        }

        serialBuffer.erase(serialBuffer.begin(), serialBuffer.begin() + total);
    }
}

void ESPHub::sendToRobot(const PFOXPacket& pkt) {
    if (pkt.dst == PFOXAddress::BROADCAST) {
        logToPC("Broadcast to all robots");
    } else {
        logToPC("Sending to robot " + String((int)pkt.dst));
    }
    outgoing.push(pkt);
}

void ESPHub::sendAckToPC(const PFOXPacket& pkt) {
    PFOXPacket ack;
    ack.src = PFOXAddress::ESPMAIN;
    ack.dst = pkt.src;
    ack.type = PFOXMsgType::ACK;
    ack.seq = pkt.seq;
    ack.len = 1;
    ack.payload = {0x00};
    Serial.write(ack.encode().data(), ack.encode().size());
}

void ESPHub::logToPC(const String& message) {
    Serial.print("[HUB LOG] ");
    Serial.println(message);
}

void ESPHub::loop() {
    receiveSerial();
    processSerialBytes();

    PFOXPacket pkt;
    while (incoming.pop(pkt)) {
        // Envia pacote para robô(s)
        sendToRobot(pkt);

        // Envia ACK ao PC
        sendAckToPC(pkt);
    }

    // Aqui você poderia processar fila outgoing, enviar via ESPNOW
}
