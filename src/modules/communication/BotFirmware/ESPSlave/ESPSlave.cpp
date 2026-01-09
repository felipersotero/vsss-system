#include "ESPSlave.h"

ESPSlave* ESPSlave::instance = nullptr;

// Defina as configurações padrão aqui ou no .h
MotorPins leftP = {2, 4, 15};
MotorPins rightP = {25, 26, 32};
PIDConfig pidC = {2.0f, 0.5f, 0.1f};

ESPSlave::ESPSlave(PFOXAddress id, uint8_t* hubAddress) 
    : myId(id), incomingQueue(50), running(true), robotCtrl(leftP, rightP, pidC){
    
    memset(hubMac, 0, sizeof(hubMac));
    if (hubAddress != nullptr) {
        memcpy(hubMac, hubAddress, 6);
    }
    instance = this;
}

void ESPSlave::begin() {
    // Configura o LED como saída e inicia desligado
    pinMode(LED_PIN, OUTPUT); 
    digitalWrite(LED_PIN, LOW);

    WiFi.mode(WIFI_MODE_STA);
    delay(100);

    robotCtrl.begin();

    if (esp_now_init() != ESP_OK) {
        Serial.println("[SLAVE] Erro ESP-NOW");
        return;
    }

    esp_now_register_recv_cb(ESPSlave::onDataRecv);
    esp_now_register_send_cb(ESPSlave::onDataSent);

    // Configuração do Peer (Hub)
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
    }

    _lastControlCycle = millis();
}

void ESPSlave::loop() {
    PFOXPacket pkt;
    uint32_t now = millis();

    // 1. PROCESSAMENTO DE COMUNICAÇÃO
    while (incomingQueue.pop(pkt)) {
        processPacket(pkt);
    }

    // 2. CICLO DE CONTROLE FIXO (100Hz)
    // Executa o PID a cada 10ms usando os últimos valores salvos
    if (now - _lastControlCycle >= CONTROL_INTERVAL_MS) {
        _lastControlCycle = now;
        
        if (running) {
            robotCtrl.update(_currentL, _targetL, _currentR, _targetR);
        }
    }

    // 3. LÓGICA DO LED (Indicador de Recebimento)
    // O LED fica aceso enquanto o tempo atual for menor que o tempo de fim do "blink"
    if (now < blinkEndTime) {
        digitalWrite(LED_PIN, HIGH);
    } else {
        digitalWrite(LED_PIN, LOW);
    }

    // 4. WATCHDOG DE SEGURANÇA
    // Se ficar mais de 1 segundo sem receber pacotes, para os motores por segurança
    if (running && (now - lastPacketTime > 1000)) { 
        stopMotors();
    }
}

void ESPSlave::processPacket(const PFOXPacket& pkt) {
    // Toda vez que entra aqui, atualizamos o tempo para manter o LED aceso por 20ms
    // Isso cria o efeito de "piscar" conforme os pacotes chegam
    lastPacketTime = millis();
    blinkEndTime = lastPacketTime + 20; 

    switch (pkt.type) {
        case PFOXMsgType::CMD_SET_SPEED: {
            if (pkt.payload.size() >= 9) {
                const uint8_t* p = pkt.payload.data();
                
                // Apenas guarda os valores para o ciclo de controle do loop()
                _currentL = (int16_t)((p[1] << 8) | p[2]);
                _targetL  = (int16_t)((p[3] << 8) | p[4]);
                _currentR = (int16_t)((p[5] << 8) | p[6]);
                _targetR  = (int16_t)((p[7] << 8) | p[8]);
            }
            break;
        }

        case PFOXMsgType::CMD_FLOW_CTRL: {
            if (!pkt.payload.empty()) {
                uint8_t cmd = pkt.payload[0];
                if (cmd == (uint8_t)PFOXFlowType::STOP) {
                    stopMotors();
                } else if (cmd == (uint8_t)PFOXFlowType::RUN) {
                    running = true;
                }
            }
            if (pkt.dst == myId) sendAck(pkt);
            break;
        }

        case PFOXMsgType::STATUS: {
            sendStatus(pkt.seq24);
            break;
        }

        default: break;
    }
    
    // Envia confirmação para pacotes direcionados (unicast)
    if (pkt.dst == myId && pkt.type != PFOXMsgType::ACK && 
        pkt.type != PFOXMsgType::STATUS && pkt.type != PFOXMsgType::CMD_FLOW_CTRL) {
        sendAck(pkt);
    }
}

void ESPSlave::stopMotors() {
    running = false;
    _targetL = 0; 
    _targetR = 0;
    robotCtrl.stop();
}

void ESPSlave::onDataRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
    if (!instance) return;
    try {
        PFOXPacket pkt(data, (size_t)len);
        // Filtra se o pacote é para este robô ou para todos (Broadcast)
        if (pkt.dst == instance->myId || pkt.dst == PFOXAddress::BROADCAST) {
            instance->incomingQueue.push(pkt);
        }
    } catch (...) {
        // Ignora pacotes malformados
    }
}

void ESPSlave::onDataSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
    // Callback opcional para monitorar sucesso de envio
}

void ESPSlave::sendAck(const PFOXPacket& originalPkt) {
    PFOXPacket ack;
    ack.src = myId;
    ack.dst = originalPkt.src;
    ack.type = PFOXMsgType::ACK;
    ack.seq24 = originalPkt.seq24;
    
    std::vector<uint8_t> data = ack.encode();
    esp_now_send(hubMac, data.data(), data.size());
}

void ESPSlave::sendStatus(uint32_t seq) {
    PFOXPacket statusPkt;
    statusPkt.src = myId;
    statusPkt.dst = PFOXAddress::PC;
    statusPkt.type = PFOXMsgType::STATUS;
    statusPkt.seq24 = seq;
    
    // Exemplo: Enviando nível de bateria fixo ou lido de um pino ADC
    float battery = 12.0f; 
    uint8_t* b = (uint8_t*)&battery;
    statusPkt.payload.insert(statusPkt.payload.end(), b, b + 4);
    statusPkt.len = 4;

    std::vector<uint8_t> data = statusPkt.encode();
    esp_now_send(hubMac, data.data(), data.size());
}