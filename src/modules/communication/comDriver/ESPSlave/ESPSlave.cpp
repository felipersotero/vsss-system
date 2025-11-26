#include "ESPSlave.h"
#include <Arduino.h>
#include <cstring> // Para memcpy

ESPSlave* ESPSlave::instance = nullptr;

// 🚨 IMPORTANTE: SUBSTITUA ESTES ENDEREÇOS MAC PELOS REAIS!
static const uint8_t ROBOT_MACS[][6] = {
    {0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0x01}, 
    {0xBB, 0xBB, 0xBB, 0xBB, 0xBB, 0x02},
    {0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0x03}
};

ESPSlave::ESPSlave() : incoming(100), outgoing(100) {
    serialBuffer.reserve(256);
    instance = this;
}

void ESPSlave::begin() {
  //Iniciando a coneção com o espnow
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();      

    if (esp_now_init() != ESP_OK) {
        Serial.println("ESPNOW init failed!"); // Este log de erro permanece apenas para debug local (console)
        return;
    }

    esp_now_register_send_cb(ESPSlave::onESPNOWSent);
    esp_now_register_recv_cb(ESPSlave::onESPNOWRecv);

    // logToPC("ESPNOW iniciado"); // REMOVIDO: Hub começa em silêncio
}

void ESPSlave::receiveSerial() {
    while (Serial.available()) {
        serialBuffer.push_back(Serial.read());

        if (serialBuffer.size() > 512) {
            serialBuffer.clear();
            // logToPC("Serial buffer overflow - cleared"); // REMOVIDO
        }
    }
}

void ESPSlave::processSerialBytes() {
    while (serialBuffer.size() >= 7) {
        
        if (serialBuffer[0] != PFOXPacket::PREAMBLE) {
            // Tenta ressincronizar (apaga 1 byte e tenta de novo)
            serialBuffer.erase(serialBuffer.begin());
            continue;
        }

        uint8_t len = serialBuffer[6];
        size_t full_packet_size = 7 + len + 2;

        if (serialBuffer.size() < full_packet_size) {
            break; // Pacote incompleto, espera mais bytes
        }

        try {
            PFOXPacket pkt(serialBuffer.data(), full_packet_size);
            
            if (!incoming.push(pkt)) {
                // logToPC("Pacote Serial descartado: fila cheia."); // REMOVIDO
            }

            // Pacote OK, remove do buffer
            serialBuffer.erase(serialBuffer.begin(), serialBuffer.begin() + full_packet_size);
            
        } catch (const std::runtime_error& e) {
            // logToPC("PFOX Erro de decodificação: " + String(e.what())); // REMOVIDO: Apenas resincroniza
            // Remove apenas o byte de PREAMBLE para tentar resincronizar
            serialBuffer.erase(serialBuffer.begin());
        }
    }
}

/**
 * @brief Envia um pacote ACK binário (PFOX) para o PC.
 * Esta é a ÚNICA comunicação Serial (PC) esperada do Hub.
 * @param original_pkt Pacote original que gerou o ACK.
 */
void ESPSlave::sendAckToPC(const PFOXPacket& original_pkt) {
    PFOXPacket ack_pkt;

    ack_pkt.preamble = PFOXPacket::PREAMBLE;
    ack_pkt.version  = PFOXPacket::VERSION;
    ack_pkt.src      = PFOXAddress::ESPMAIN;
    ack_pkt.dst      = PFOXAddress::PC;
    ack_pkt.type     = PFOXMsgType::ACK;
    ack_pkt.seq      = original_pkt.seq;
    ack_pkt.len      = 0;
    // O payload é zero para o ACK
    // ack_pkt.payload.clear(); // O construtor padrão ou clear() fará isso

    std::vector<uint8_t> encoded = ack_pkt.encode();
    Serial.write(encoded.data(), encoded.size());
}

// ----------------------------------------------------------------------------------------------------
// CALLBACKS ESPNOW (Limpeza de Logs de DEBUG)
// ----------------------------------------------------------------------------------------------------

// ** logToPC foi removida do ESPSlave.h e da implementação **

void ESPSlave::onESPNOWSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
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

void ESPSlave::onESPNOWRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
    if (!instance || info == nullptr) return;

    const uint8_t* mac = info->src_addr;

    if (len < 9) {
        // instance->logToPC("ESPNOW Recv: Pacote muito curto (" + String(len) + ")"); // REMOVIDO
        return;
    }

    try {
        PFOXPacket pkt(data, len);

        // ACK de robô (PFOX)
        if (pkt.type == PFOXMsgType::ACK) {
            // instance->logToPC("ACK PFOX de Robo. Seq=" + String(pkt.seq)); // REMOVIDO
            return;
        }

        // Enviar ACK de volta ao robô
        PFOXPacket ack;
        ack.src = PFOXAddress::ESPMAIN;
        ack.dst = pkt.src;
        ack.type = PFOXMsgType::ACK;
        ack.seq = pkt.seq;
        ack.len = 0;

        uint8_t dest_mac[6];
        if (instance->getRobotMac(pkt.src, dest_mac)) {
            auto encoded = ack.encode();
            esp_now_send(dest_mac, encoded.data(), encoded.size());
        }

        // Enfileira o pacote
        if (instance->incoming.push(pkt)) {
            // instance->logToPC("PKT de Robo enfileirado"); // REMOVIDO
        }

    } catch (const std::runtime_error& e) {
        // instance->logToPC("Erro ao decodificar ESP-NOW: " + String(e.what())); // REMOVIDO
    }
}

// ----------------------------------------------------------------------------------------------------

bool ESPSlave::getRobotMac(PFOXAddress robot_id, uint8_t mac[6]) {
    uint8_t idx = (uint8_t)robot_id;

    if (idx == 0 || idx > 3) return false;

    memcpy(mac, ROBOT_MACS[idx - 1], 6);
    return true;
}

// ----------------------------------------------------------------------------------------------------

void ESPSlave::forwardToPC(const PFOXPacket& pkt) {
    // TODO: Implementar envio PFOX binário para o PC
    // Por enquanto, não é usado no loop de teste
}

void ESPSlave::sendToRobot(const PFOXPacket& pkt) {
    // TODO: Implementar lógica de envio (e retry) para o ESP-NOW
    // Por enquanto, não é usado no loop de teste
}

void ESPSlave::processOutgoing() {
    // TODO: Implementar lógica de processamento de fila de saída
}

void ESPSlave::processTimeouts() {
    // TODO: Implementar lógica de timeout para pacotes ESP-NOW pendentes
}

// ----------------------------------------------------------------------------------------------------

void ESPSlave::loop() {

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
    // processOutgoing(); 
    // processTimeouts();
}