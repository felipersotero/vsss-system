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
    pinMode(LED_PIN, OUTPUT); // <-- Adicione isso
    digitalWrite(2, LOW);

    // Modo STA e garante que não haja conexão que interfira
    WiFi.mode(WIFI_MODE_STA);

    delay(100);

    // Inicializa controle do robô
    robotCtrl.begin();

    // Inicializa ESP-NOW
    if (esp_now_init() != ESP_OK) {
        Serial.println("[SLAVE] Erro ESP-NOW");
        return;
    }

    esp_now_register_recv_cb(ESPSlave::onDataRecv);
    esp_now_register_send_cb(ESPSlave::onDataSent);

    // Registro do HUB (Peer)
    esp_now_peer_info_t peerInfo;
    memset(&peerInfo, 0, sizeof(peerInfo));
    memcpy(peerInfo.peer_addr, hubMac, 6);
    
    uint8_t channel = 0;
    wifi_second_chan_t second_ch = WIFI_SECOND_CHAN_NONE;
    esp_wifi_get_channel(&channel, &second_ch);
    
    peerInfo.channel = channel;
    peerInfo.encrypt = false;
    peerInfo.ifidx = WIFI_IF_STA;

    if (esp_now_add_peer(&peerInfo) != ESP_OK) {
        Serial.println("[SLAVE] Falha ao adicionar HUB");
    } else {
        Serial.println("[SLAVE] HUB registrado com sucesso");
    }

}

void ESPSlave::loop() {
    PFOXPacket pkt;
    uint32_t now = millis();

    // 1. Processa todos os pacotes da fila
    while (incomingQueue.pop(pkt)) {
        processPacket(pkt);
    }

    // 2. Lógica do LED (Aceso apenas quando recebe informação)
    // Se o tempo atual for menor que o tempo limite, mantém aceso.
    if (now < blinkEndTime) {
        digitalWrite(LED_PIN, HIGH); 
        ledState = true;
    } else {
        digitalWrite(LED_PIN, LOW);
        ledState = false;
    }

    // 3. LÓGICA DE SEGURANÇA (Watchdog)
    // Se o robô estiver em modo 'running' mas não receber NADA por mais de 1 segundo,
    // ele para os motores automaticamente.
    if (running && (now - lastPacketTime > 1000)) { 
        Serial.println("[TIMEOUT] Comunicação perdida! Parando robô...");
        running = false;
        robotCtrl.stop();
    }
}

void ESPSlave::onDataRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
    if (!instance) return;
    
    try {
        PFOXPacket pkt(data, (size_t)len);
        if (pkt.dst == instance->myId || pkt.dst == PFOXAddress::BROADCAST) {
            instance->incomingQueue.push(pkt);
        }
    } catch (const std::exception& e) {
        Serial.printf("[RADIO] Erro no pacote: %s\n", e.what());
    }
}

// CORREÇÃO 3: Atualizado para a API do ESP32 v3.0 (recebe wifi_tx_info_t*)
void ESPSlave::onDataSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
    // Callback de envio
}


void ESPSlave::processPacket(const PFOXPacket& pkt) {
    // Atualiza o tempo do último pacote recebido (Watchdog)
    lastPacketTime = millis();

    blinkEndTime = millis()+100;

    // 1. Identifica o nome do comando para o Serial
    const char* typeStr = "DESCONHECIDO";
    switch (pkt.type) {
        case PFOXMsgType::CMD_SET_SPEED: typeStr = "SET_SPEED (Motores)"; break;
        case PFOXMsgType::CMD_FLOW_CTRL: typeStr = "FLOW_CTRL (Run/Stop)"; break;
        case PFOXMsgType::STATUS:        typeStr = "STATUS (Telemetria)"; break;
        case PFOXMsgType::HEARTBEAT:     typeStr = "HEARTBEAT"; break;
        case PFOXMsgType::ACK:           typeStr = "ACK"; break;
        default:                         typeStr = "OUTRO"; break;
    }

    // 2. Print solicitado: Mostra Seq e o que a informação pede
    Serial.printf("\n[RX] Seq: %u | Tipo: %s | Origem: 0x%02X\n", pkt.seq24, typeStr, (uint8_t)pkt.src);

    // 3. Retorna o ACK (Apenas se NÃO for um pedido de STATUS, pois o STATUS já é uma resposta)
    if (pkt.dst == myId && pkt.type != PFOXMsgType::ACK && pkt.type != PFOXMsgType::STATUS) {
        sendAck(pkt);
    }

    // 4. Executa a lógica do comando
    switch (pkt.type) {
        case PFOXMsgType::CMD_SET_SPEED: {
            if (pkt.payload.size() >= 9) {
                const uint8_t* p = pkt.payload.data();
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
                    lastPacketTime = millis();
                }
            }
            break;
        }

        case PFOXMsgType::STATUS: {
            sendStatus(pkt.seq24);
            break;
        }

        case PFOXMsgType::HEARTBEAT:{
            
            break;
        }

        default:break;
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

    Serial.printf("[ACK] Respondendo ao HUB (Seq: %u)... ", originalPkt.seq24);

    bool macAllZero = true;
    for (int i = 0; i < 6; ++i) if (hubMac[i] != 0) { macAllZero = false; break; }

    if (!macAllZero) {
        esp_now_send(hubMac, data.data(), data.size());
    }
}

void ESPSlave::sendStatus(uint32_t seq) {
    Serial.printf("[ACK] Respondendo ao HUB (Seq: %u)... ", seq);
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

