#include "ESPHub.h"
#include <Arduino.h>
#include <cstring>


// Devem ser iguais aos que gravamos nos códigos dos robôs
static const uint8_t ROBOT_MACS[][6] = {
    {0x94, 0xB9, 0x7E, 0xC2, 0xCA, 0xA8}, // Robô 1 real
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, // Robô 2 (preencher quando tiver)
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x01}  // Robô 3 (preencher quando tiver)
};


ESPHub* ESPHub::instance = nullptr;


ESPHub::ESPHub()
    : incoming(100), outgoing(100), robots{ RobotChannel(20), RobotChannel(20), RobotChannel(20), RobotChannel(20) }
{
    serialBuffer.reserve(256);
    instance = this;
}

void ESPHub::begin() {

    // Inicializar WiFi adequadamente antes de tentar ler MAC
    WiFi.mode(WIFI_MODE_STA);
    esp_wifi_start();     // <<< IMPORTANTE
    esp_wifi_set_promiscuous(true);
    delay(100);

    // Ler MAC real do HUB
    if (esp_wifi_get_mac(WIFI_IF_STA, hubMac) == ESP_OK) {
        Serial.printf("[INIT] MAC real do HUB: %02X:%02X:%02X:%02X:%02X:%02X\n",
            hubMac[0], hubMac[1], hubMac[2], hubMac[3], hubMac[4], hubMac[5]);
    } else {
        Serial.println("[ERRO] Falha ao obter MAC do HUB! (driver nao iniciado?)");
    }

    delay(50);

    // Inicializar ESPNOW
    if (esp_now_init() != ESP_OK) {
        Serial.println("ESPNOW init failed!");
        return;
    }

    esp_now_register_send_cb(ESPHub::onESPNOWSent);
    esp_now_register_recv_cb(ESPHub::onESPNOWRecv);

    // Registrar peers
    for (int i = 0; i < 3; ++i) {
        esp_now_peer_info_t peerInfo;
        memset(&peerInfo, 0, sizeof(peerInfo));

        memcpy(peerInfo.peer_addr, ROBOT_MACS[i], 6);
        peerInfo.channel = 0;
        peerInfo.encrypt = false;
        peerInfo.ifidx = WIFI_IF_STA;

        if (esp_now_add_peer(&peerInfo) != ESP_OK) {
            Serial.printf("[ERRO] Falha ao adicionar peer Robo %d\n", i + 1);
        } else {
            Serial.printf("[INIT] Robo %d registrado\n", i + 1);
        }
    }
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
    // 1. Sempre confirma o recebimento para o PC (Handshake Serial)
    sendAckToPC(pkt);

    // 2. Verifica se é um Broadcast (Para todos)
    if (pkt.dst == PFOXAddress::BROADCAST) {

        // CASO A: Pedido de STATUS (Network Discovery)
        // O Hub intercepta e responde com o que ele sabe. Não envia via rádio.
        if (pkt.type == PFOXMsgType::STATUS) {
            PFOXPacket report;
            report.preamble = PFOXPacket::PREAMBLE;
            report.version  = PFOXPacket::VERSION;
            report.src      = PFOXAddress::ESPMAIN; // Fonte: Hub
            report.dst      = PFOXAddress::PC;      // Destino: PC
            report.type     = PFOXMsgType::STATUS;
            report.seq24    = pkt.seq24;            // Mantém sync
            
            // Payload: [Status_R1, Status_R2, Status_R3]
            // 0x01 = Online, 0x00 = Offline
            report.payload.push_back(robots[1].online ? 0x01 : 0x00);
            report.payload.push_back(robots[2].online ? 0x01 : 0x00);
            report.payload.push_back(robots[3].online ? 0x01 : 0x00);
            report.len = 3;

            // Envia resposta pela Serial
            auto bytes = report.encode();
            Serial.write(bytes.data(), bytes.size());
            return; 
        }

        // NOVO CASO: Heartbeat ou Comandos Críticos que exigem confirmação de todos
        if (pkt.type == PFOXMsgType::HEARTBEAT || pkt.type == PFOXMsgType::CMD_FLOW_CTRL) {
            for (int r = 1; r <= 3; ++r) {
                PFOXPacket copy = pkt;
                copy.dst = (PFOXAddress)r; // Transforma o Broadcast em 3 Unicasts
                addToQueue(r, copy);       // Coloca na fila com retry e espera de ACK
            }
            return;
        }

        // CASO B: Comandos de ação (STOP, START, FLOW_CTRL, SET_SPEED...)
        // O Hub repassa imediatamente para todos (Fire-and-Forget)
        for (int r = 1; r <= 3; ++r) {
            PFOXPacket copy = pkt;
            copy.dst = (PFOXAddress)r; // Altera o destino lógico
            sendToRobot(copy);         // Envia via ESP-NOW (sem esperar ACK)
        }
        return;
    }

    // 3. Se não for Broadcast, segue fluxo normal (Unicast com fila e ACK)
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
    uint8_t id = (uint8_t)pkt.src;
    
    // Filtro básico de segurança
    if (id < 1 || id > 3) return;

    // 1. ATUALIZAÇÃO DE ESTADO INTERNO
    // Qualquer pacote vindo de um ID válido prova que o robô está online
    robots[id].online = true;
    robots[id].lastSeen = millis();

    // 2. FORWARD PARA O PC (Watchdog da Interface)
    // Encaminhamos TODO pacote válido para o PC. Assim, o 'communication.py'
    // atualiza o 'robot_last_seen' e mantém o robô como "OK" na interface.
    forwardToPC(pkt);

    // 3. LÓGICA DE FILA DO HUB (ACK)
    if (pkt.type == PFOXMsgType::ACK) {
        RobotChannel& ch = robots[id];
        // Se este for o ACK que estávamos esperando, liberamos o canal para o próximo pacote
        if (ch.waitingAck && pkt.seq24 == ch.lastPacket.seq24) {
            ch.waitingAck = false;
            ch.retryCount = 0;
        }
    }
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