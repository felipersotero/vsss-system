#include "ESPHub.h"
#include <Arduino.h>
#include <cstring> // Para memcpy

ESPHub* ESPHub::instance = nullptr;

// 🚨 IMPORTANTE: SUBSTITUA ESTES ENDEREÇOS MAC PELOS REAIS!
static const uint8_t ROBOT_MACS[][6] = {
    {0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0x01}, 
    {0xBB, 0xBB, 0xBB, 0xBB, 0xBB, 0x02},
    {0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0x03}
};

ESPHub::ESPHub() : incoming(100), outgoing(100) {
    serialBuffer.reserve(256);
    instance = this;
}

void ESPHub::begin() {
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();      

    if (esp_now_init() != ESP_OK) {
        Serial.println("ESPNOW init failed!"); // Este log de erro permanece apenas para debug local (console)
        return;
    }

    esp_now_register_send_cb(ESPHub::onESPNOWSent);
    esp_now_register_recv_cb(ESPHub::onESPNOWRecv);

    // logToPC("ESPNOW iniciado"); // REMOVIDO: Hub começa em silêncio
}

void ESPHub::receiveSerial() {
    while (Serial.available()) {
        serialBuffer.push_back(Serial.read());

        if (serialBuffer.size() > 512) {
            serialBuffer.clear();
            // logToPC("Serial buffer overflow - cleared"); // REMOVIDO
        }
    }
}

void ESPHub::processSerialBytes() {
    while (serialBuffer.size() >= 9) {   // HEADER agora é 9 bytes

        if (serialBuffer[0] != PFOXPacket::PREAMBLE) {
            serialBuffer.erase(serialBuffer.begin());
            continue;
        }

        // Agora o LEN está em serialBuffer[8]
        uint8_t len = serialBuffer[8];

        // Tamanho total: 9 bytes cabeçalho + payload + 2 CRC
        size_t full_packet_size = 9 + len + 2;

        if (serialBuffer.size() < full_packet_size)
            break;

        try {
            PFOXPacket pkt(serialBuffer.data(), full_packet_size);

            incoming.push(pkt);

            serialBuffer.erase(serialBuffer.begin(),
                               serialBuffer.begin() + full_packet_size);

        } catch (...) {
            serialBuffer.erase(serialBuffer.begin()); // resync
        }
    }
}

/**
 * @brief Envia um pacote ACK binário (PFOX) para o PC.
 * Esta é a ÚNICA comunicação Serial (PC) esperada do Hub.
 * @param original_pkt Pacote original que gerou o ACK.
 */
void ESPHub::sendAckToPC(const PFOXPacket& original_pkt) {

    PFOXPacket ack_pkt;
    ack_pkt.preamble = PFOXPacket::PREAMBLE;
    ack_pkt.version  = PFOXPacket::VERSION;
    ack_pkt.src      = PFOXAddress::ESPMAIN;
    ack_pkt.dst      = PFOXAddress::PC;
    ack_pkt.type     = PFOXMsgType::ACK;

    // CORRIGIDO: 24 bits
    ack_pkt.seq24    = original_pkt.seq24;

    ack_pkt.len      = 0;
    ack_pkt.payload.clear();

    auto encoded = ack_pkt.encode();
    Serial.write(encoded.data(), encoded.size());
}


// ----------------------------------------------------------------------------------------------------
// CALLBACKS ESPNOW (Limpeza de Logs de DEBUG)
// ----------------------------------------------------------------------------------------------------

// ** logToPC foi removida do ESPHub.h e da implementação **

void ESPHub::onESPNOWSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
    if (!instance || info == nullptr) return;

    // String macStr = "";
    // for (int i = 0; i < 6; ++i) {
    //     macStr += String(info->des_addr[i], HEX);
    //     if (i < 5) macStr += ":";
    // }

    // if (status == ESP_NOW_SEND_SUCCESS) {
    //     instance->logToPC("ESPNOW Link-ACK: SUCESSO → " + macStr); // REMOVIDO
    // } else {
    //     instance->logToPC("ESPNOW Link-ACK: FALHA → " + macStr + 
    //         " (status=" + String(status) + ")"); // REMOVIDO
    // }
}

void ESPHub::onESPNOWRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
    if (!instance || info == nullptr) return;

    if (len < 11) return; // header = 9 bytes + CRC

    try {
        PFOXPacket pkt(data, len);

        // Se recebeu ACK do robô, não envia nada ao PC neste teste
        if (pkt.type == PFOXMsgType::ACK) {
            return;
        }

        // Envia ACK de volta ao robô
        PFOXPacket ack;
        ack.src   = PFOXAddress::ESPMAIN;
        ack.dst   = pkt.src;
        ack.type  = PFOXMsgType::ACK;
        ack.seq24 = pkt.seq24;
        ack.len   = 0;

        uint8_t mac[6];
        if (instance->getRobotMac(pkt.src, mac)) {
            auto enc = ack.encode();
            esp_now_send(mac, enc.data(), enc.size());
        }

        instance->incoming.push(pkt);

    } catch (...) {
        // ignorar erros
    }
}


// ----------------------------------------------------------------------------------------------------

bool ESPHub::getRobotMac(PFOXAddress robot_id, uint8_t mac[6]) {
    uint8_t idx = (uint8_t)robot_id;

    if (idx == 0 || idx > 3) return false;

    memcpy(mac, ROBOT_MACS[idx - 1], 6);
    return true;
}

// ----------------------------------------------------------------------------------------------------

void ESPHub::forwardToPC(const PFOXPacket& pkt) {
    // TODO: Implementar envio PFOX binário para o PC
    // Por enquanto, não é usado no loop de teste
}

void ESPHub::sendToRobot(const PFOXPacket& pkt) {
    // TODO: Implementar lógica de envio (e retry) para o ESP-NOW
    // Por enquanto, não é usado no loop de teste
}

void ESPHub::processOutgoing() {
    // TODO: Implementar lógica de processamento de fila de saída
}

void ESPHub::processTimeouts() {
    // TODO: Implementar lógica de timeout para pacotes ESP-NOW pendentes
}

// ----------------------------------------------------------------------------------------------------

void ESPHub::loop() {

    // 1. Ler bytes da Serial e armazenar no buffer
    receiveSerial();

    // 2. Decodificar pacotes completos do buffer da Serial
    processSerialBytes();

    PFOXPacket pkt;

    // 3. Processar todos os pacotes válidos que chegaram da Serial
    while (incoming.pop(pkt)) {

        // 4. Fluxo principal de teste: PC → HUB → ACK → PC
        if (pkt.src == PFOXAddress::PC) {

            // Envia ACK diretamente para o PC (como um pacote PFOX binário)
            sendAckToPC(pkt);
            
            // Nenhum log de texto é gerado aqui, a comunicação é estritamente binária (ACK)

            continue; // volta ao próximo pacote
        }

    }
    
    // Processamento de mensagens de robôs
    processOutgoing(); 
    processTimeouts();
}