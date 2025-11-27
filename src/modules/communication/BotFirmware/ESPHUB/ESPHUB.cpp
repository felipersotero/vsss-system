#include "ESPHub.h"
#include <Arduino.h>
#include <cstring>

// Substitua pelos MACs reais
static const uint8_t ROBOT_MACS[][6] = {
    {0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0x01},
    {0xBB, 0xBB, 0xBB, 0xBB, 0xBB, 0x02},
    {0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0x03}
};

ESPHub* ESPHub::instance = nullptr;

ESPHub::ESPHub()
    : incoming(100), outgoing(100), robots{ RobotChannel(20), RobotChannel(20), RobotChannel(20), RobotChannel(20) }
{
    serialBuffer.reserve(256);
    instance = this;
}

void ESPHub::begin() {
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    if (esp_now_init() != ESP_OK) {
        Serial.println("ESPNOW init failed!");
        return;
    }

    esp_now_register_send_cb(ESPHub::onESPNOWSent);
    esp_now_register_recv_cb(ESPHub::onESPNOWRecv);
}

void ESPHub::receiveSerial() {
    while (Serial.available()) {
        serialBuffer.push_back((uint8_t)Serial.read());

        if (serialBuffer.size() > 1024) {
            serialBuffer.clear();
        }
    }
}

void ESPHub::processSerialBytes() {
    while (serialBuffer.size() >= 9) {
        if (serialBuffer[0] != PFOXPacket::PREAMBLE) {
            serialBuffer.erase(serialBuffer.begin());
            continue;
        }

        uint8_t len = serialBuffer[8];
        size_t full_packet_size = 9 + len + 2;

        if (serialBuffer.size() < full_packet_size) break;

        try {
            PFOXPacket pkt(serialBuffer.data(), full_packet_size);
            incoming.push(pkt);
            serialBuffer.erase(serialBuffer.begin(), serialBuffer.begin() + full_packet_size);
        } catch (...) {
            serialBuffer.erase(serialBuffer.begin());
        }
    }
}

void ESPHub::sendAckToPC(const PFOXPacket& original_pkt) {
    PFOXPacket ack_pkt;
    ack_pkt.preamble = PFOXPacket::PREAMBLE;
    ack_pkt.version  = PFOXPacket::VERSION;
    ack_pkt.src      = PFOXAddress::ESPMAIN;
    ack_pkt.dst      = PFOXAddress::PC;
    ack_pkt.type     = PFOXMsgType::ACK;
    ack_pkt.seq24    = original_pkt.seq24;
    ack_pkt.len      = 0;
    ack_pkt.payload.clear();

    auto encoded = ack_pkt.encode();
    Serial.write(encoded.data(), encoded.size());
}

void ESPHub::forwardToPC(const PFOXPacket& pkt) {
    // Encoda o PFOX binário e envia pela Serial para o PC
    auto bytes = pkt.encode();
    Serial.write(bytes.data(), bytes.size());
}

bool ESPHub::getRobotMac(PFOXAddress robot_id, uint8_t mac[6]) {
    uint8_t idx = (uint8_t)robot_id;
    if (idx == 0 || idx > 3) return false;
    memcpy(mac, ROBOT_MACS[idx - 1], 6);
    return true;
}

void ESPHub::sendToRobot(const PFOXPacket& pkt) {
    uint8_t mac[6];
    if (!getRobotMac(pkt.dst, mac)) return;

    auto bytes = pkt.encode();
    esp_err_t res = esp_now_send(mac, bytes.data(), bytes.size());
    (void)res; // opcional checar retorno em debug
}

void ESPHub::addToQueue(uint8_t robotId, const PFOXPacket& pkt) {
    if (robotId < 1 || robotId > 3) return;
    robots[robotId].queue.push(pkt);
}

/**
 * Tick das filas / lógica de ACK / timeout / retry
 */
void ESPHub::tickRobotChannels() {
    uint32_t now = millis();

    for (int id = 1; id <= 3; ++id) {
        RobotChannel& ch = robots[id];

        // Se aguardando ACK -> verificar timeout e retry
        if (ch.waitingAck) {
            if ((now - ch.lastSendTime) > ACK_TIMEOUT_MS) {

                if (ch.retryCount < MAX_RETRY) {
                    // reenviar
                    sendToRobot(ch.lastPacket);
                    ch.retryCount++;
                    ch.lastSendTime = now;
                } else {
                    // excedeu tentativas -> marcar offline e liberar canal
                    ch.waitingAck = false;
                    ch.online = false;
                    // opcional: avisar PC sobre falha (p.ex. enviar STATUS_FAIL)
                }
            }
            continue; // não tenta enviar novo pacote enquanto esperando ACK
        }

        // Se não está esperando ACK -> enviar próximo pacote da fila (se existir)
        if (!ch.queue.isEmpty()) {
            PFOXPacket pkt;
            if (ch.queue.pop(pkt)) {
                ch.lastPacket = pkt;
                ch.retryCount = 0;
                ch.lastSendTime = now;
                ch.waitingAck = true;
                sendToRobot(pkt);
            }
        }
    }
}

void ESPHub::processTimeouts() {
    // Aqui apenas mantemos checagem simples de estado; tickRobotChannels trata retries
    uint32_t now = millis();
    for (int id = 1; id <= 3; ++id) {
        if (robots[id].lastSeen > 0 && (now - robots[id].lastSeen > 3000)) {
            robots[id].online = false;
        }
    }
}

/**
 * Processar pacotes vindos do PC (via Serial)
 * - ACK para PC
 * - Se broadcast -> envia imediatamente
 * - Se destino robô -> coloca na fila do robô
 */
void ESPHub::processIncomingFromPC(const PFOXPacket& pkt) {
    sendAckToPC(pkt);

    // Broadcast para todos (não enfileira)
    if (pkt.dst == PFOXAddress::BROADCAST) {
        // Envia broadcast via ESP-NOW para cada MAC definido
        for (int r = 1; r <= 3; ++r) {
            PFOXPacket copy = pkt;
            copy.dst = (PFOXAddress)r;
            sendToRobot(copy);
        }
        return;
    }

    // Se destino é um robô -> enfileira
    uint8_t dst = (uint8_t)pkt.dst;
    if (dst >= 1 && dst <= 3) {
        addToQueue(dst, pkt);
    }
}

/**
 * Tratamento quando receber algo via ESPNOW (callback)
 * - Se for ACK -> valida e libera a fila do robô
 * - Se for STATUS_RESPONSE ou outros -> repassa para o PC (forwardToPC)
 *
 * Observação: esta é invocada dentro do callback static onESPNOWRecv
 */
void ESPHub::handleIncomingFromRobot(const PFOXPacket& pkt, const esp_now_recv_info_t *info) {

    // Se ACK do robô para comando → resolver fila
    if (pkt.type == PFOXMsgType::ACK) {
        uint8_t id = (uint8_t)pkt.src;
        if (id >= 1 && id <= 3) {
            RobotChannel& ch = robots[id];
            if (ch.waitingAck && pkt.seq24 == ch.lastPacket.seq24) {
                ch.waitingAck = false;
                ch.retryCount = 0;
                ch.online = true;
                ch.lastSeen = millis();
            }
        }
        return; // ACK não é repassado ao PC
    }

    // Se for status response -> marcar online e encaminhar
    if (pkt.type == PFOXMsgType::STATUS) {
        uint8_t id = (uint8_t)pkt.src;
        if (id >= 1 && id <= 3) {
            robots[id].online = true;
            robots[id].lastSeen = millis();
        }
    }

    // para qualquer pacote que não seja ACK, encaminhar ao PC
    forwardToPC(pkt);
}

// ----------------------------------------------------------------------
// Static callbacks (necessário adaptar assinatura conforme SDK/versão)
// ----------------------------------------------------------------------
void ESPHub::onESPNOWSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
    // Optional: monitoramento do sucesso de envio físico do frame (não do ACK de aplicação)
    (void)info; (void)status;
}

void ESPHub::onESPNOWRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
    if (!instance || info == nullptr || data == nullptr) return;
    if (len < 11) return; // mínimo 9 header + 2 crc

    try {
        PFOXPacket pkt(data, len);

        // já que ACKs de robô são tratados localmente,
        // trata-se o pacote e possivelmente repassa ao PC
        instance->handleIncomingFromRobot(pkt, info);

    } catch (...) {
        // ignorar pacotes inválidos
    }
}

// ----------------------------------------------------------------------
// loop principal
// ----------------------------------------------------------------------
void ESPHub::loop() {

    // 1) Ler Serial e montar pacotes vindos do PC
    receiveSerial();
    processSerialBytes();

    PFOXPacket pkt;

    // 2) Processar pacotes que vieram do PC via Serial
    while (incoming.pop(pkt)) {
        if (pkt.src == PFOXAddress::PC) {
            processIncomingFromPC(pkt);
        } else {
            // Pacotes vindos de robôs via ESPNOW são tratados no callback onESPNOWRecv
            // Mas, se alguma fonte empurrou aqui, repassar ao PC
            forwardToPC(pkt);
        }
    }

    // 3) Gerenciar filas por robô (envio, timeout e retry)
    tickRobotChannels();

    // 4) Timeout / marcação offline
    processTimeouts();

    // Pequena pausa para não monopolizar CPU
    delay(2);
}
