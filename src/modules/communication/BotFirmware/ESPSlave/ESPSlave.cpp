#include "ESPSlave.h"

// Garante que o linker encontre a instância
ESPSlave* ESPSlave::instance = nullptr;

// CORREÇÃO 1: Removido 'const' para bater com o arquivo .h (uint8_t* hubMacAddress)
ESPSlave::ESPSlave(PFOXAddress id, uint8_t* hubAddress) 
    : myId(id), incomingQueue(50), running(true) {
    
    // Inicializa MAC do hub com zeros por segurança
    memset(hubMac, 0, sizeof(hubMac));
    if (hubAddress != nullptr) {
        memcpy(hubMac, hubAddress, 6);
    }
    instance = this;
}

void ESPSlave::begin() {
    // Modo STA e garante que não haja conexão que interfira
    WiFi.mode(WIFI_MODE_STA);
    WiFi.disconnect(true);

    // Inicializa driver WiFi
    esp_err_t err = esp_wifi_start();
    if (err != ESP_OK && err != ESP_ERR_WIFI_NOT_STARTED) {
        Serial.printf("[SLAVE] falha esp_wifi_start(): 0x%02X\n", err);
    }

    // Inicializa controle do robô
    robotCtrl.begin();

    // Inicializa ESP-NOW
    if (esp_now_init() != ESP_OK) {
        Serial.println("[SLAVE] Erro ESP-NOW");
        return;
    }

    esp_now_register_recv_cb(ESPSlave::onDataRecv);
    esp_now_register_send_cb(ESPSlave::onDataSent);

    // Se MAC do hub for todo zero, não tenta adicionar peer
    bool macAllZero = true;
    for (int i = 0; i < 6; ++i) {
        if (hubMac[i] != 0) { macAllZero = false; break; }
    }

    if (!macAllZero) {
        esp_now_peer_info_t peerInfo;
        memset(&peerInfo, 0, sizeof(peerInfo));
        memcpy(peerInfo.peer_addr, hubMac, 6);

        // CORREÇÃO 2: Mudado de int para uint8_t
        uint8_t current_channel = 0;
        wifi_second_chan_t second_ch = WIFI_SECOND_CHAN_NONE;
        
        if (esp_wifi_get_channel(&current_channel, &second_ch) == ESP_OK) {
            peerInfo.channel = current_channel;
        } else {
            peerInfo.channel = 0; // fallback
        }

        peerInfo.encrypt = false;
        peerInfo.ifidx = WIFI_IF_STA;

        if (esp_now_add_peer(&peerInfo) != ESP_OK) {
            Serial.println("[SLAVE] Erro add Peer HUB");
        } else {
            Serial.println("[SLAVE] Peer HUB adicionado");
        }
    } else {
        Serial.println("[SLAVE] Aviso: MAC do HUB não definido — não adicionando peer");
    }

    Serial.printf("[SLAVE] Iniciado ID: 0x%02X\n", (uint8_t)myId);
}

void ESPSlave::loop() {
    PFOXPacket pkt;
    // Processa todos os pacotes da fila
    while (incomingQueue.pop(pkt)) {
        processPacket(pkt);
    }
}

void ESPSlave::onDataRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
    if (!instance) return;
    if (!data || len <= 0) return;

    try {
        PFOXPacket pkt(data, (size_t)len);
        if (pkt.dst == instance->myId || pkt.dst == PFOXAddress::BROADCAST) {
            instance->incomingQueue.push(pkt);
        }
    } catch (...) {
        // Serial.println("[SLAVE] Erro pct");
    }
}

// CORREÇÃO 3: Atualizado para a API do ESP32 v3.0 (recebe wifi_tx_info_t*)
void ESPSlave::onDataSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
    if (status != ESP_NOW_SEND_SUCCESS) {
        // Serial.println("[SLAVE] Falha envio!");
    } else {
        // Se quiser ver o MAC de destino, use info->des_addr
        // const uint8_t *mac_addr = info->des_addr;
    }
}

void ESPSlave::processPacket(const PFOXPacket& pkt) {
    // Se destinatário for este nó e não for ACK, responde com ACK
    if (pkt.dst == myId && pkt.type != PFOXMsgType::ACK) {
        sendAck(pkt);
    }

    switch (pkt.type) {
        case PFOXMsgType::CMD_SET_SPEED: {
            if (pkt.payload.size() >= 9) {
                const uint8_t* p = pkt.payload.data();

                // Big-endian (MSB primeiro)
                int16_t leftReal  = (int16_t)((p[1] << 8) | p[2]);
                int16_t leftDes   = (int16_t)((p[3] << 8) | p[4]);
                int16_t rightReal = (int16_t)((p[5] << 8) | p[6]);
                int16_t rightDes  = (int16_t)((p[7] << 8) | p[8]);

                if (running) {
                    robotCtrl.update(leftReal, leftDes, rightReal, rightDes);
                }
            }
            break;
        }

        case PFOXMsgType::CMD_FLOW_CTRL: {
            if (!pkt.payload.empty()) {
                uint8_t cmd = pkt.payload[0];
                if (cmd == (uint8_t)PFOXFlowType::STOP) {
                    running = false;
                    robotCtrl.stop();
                } else if (cmd == (uint8_t)PFOXFlowType::RUN) {
                    running = true;
                }
            }
            break;
        }

        case PFOXMsgType::STATUS: {
            if (pkt.dst == myId) sendStatus(pkt.seq24);
            break;
        }

        default: break;
    }
}

void ESPSlave::sendAck(const PFOXPacket& originalPkt) {
    PFOXPacket ack;
    ack.preamble = PFOXPacket::PREAMBLE;
    ack.version  = PFOXPacket::VERSION;
    ack.src      = myId;
    ack.dst      = originalPkt.src;
    ack.type     = PFOXMsgType::ACK;
    ack.seq24    = originalPkt.seq24;
    ack.len      = 0;
    ack.payload.clear();

    std::vector<uint8_t> data = ack.encode();

    bool macAllZero = true;
    for (int i = 0; i < 6; ++i) if (hubMac[i] != 0) { macAllZero = false; break; }

    if (!macAllZero) {
        esp_now_send(hubMac, data.data(), data.size());
    }
}

void ESPSlave::sendStatus(uint32_t seq) {
    PFOXPacket statusPkt;
    statusPkt.preamble = PFOXPacket::PREAMBLE;
    statusPkt.version  = PFOXPacket::VERSION;
    statusPkt.src   = myId;
    statusPkt.dst   = PFOXAddress::PC;
    statusPkt.type  = PFOXMsgType::STATUS;
    statusPkt.seq24 = seq;
    statusPkt.payload.clear();

    union {
        float f;
        uint8_t b[sizeof(float)];
    } u;
    u.f = 12.0f; // Mock tensão

    statusPkt.payload.insert(statusPkt.payload.end(), u.b, u.b + sizeof(u.b));
    statusPkt.len = (uint8_t)statusPkt.payload.size();

    std::vector<uint8_t> data = statusPkt.encode();

    bool macAllZero = true;
    for (int i = 0; i < 6; ++i) if (hubMac[i] != 0) { macAllZero = false; break; }

    if (!macAllZero) {
        esp_now_send(hubMac, data.data(), data.size());
    }
}

// Funções mock removidas
void ESPSlave::setMotors(int16_t l, int16_t r) {}
void ESPSlave::stopMotors() {}