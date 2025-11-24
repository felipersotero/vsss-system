#include "ESPHub.h"

ESPHub* ESPHub::instance = nullptr;

ESPHub::ESPHub() : incoming(100), outgoing(100) {
    serialBuffer.reserve(256);
    instance = this;
}

void ESPHub::begin() {
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();      // obrigatório para ESPNOW

    if (esp_now_init() != ESP_OK) {
        Serial.println("ESPNOW init failed!");
        return;
    }

    esp_now_register_send_cb(ESPHub::onESPNOWSent);
    esp_now_register_recv_cb(ESPHub::onESPNOWRecv);

    logToPC("ESPNOW iniciado");
}

void ESPHub::receiveSerial() {
    while (Serial.available()) {
        serialBuffer.push_back(Serial.read());

        if (serialBuffer.size() > 512) {
            serialBuffer.clear();
            logToPC("Serial buffer overflow - cleared");
        }
    }
}

// ESPHub.cpp

void ESPHub::processSerialBytes() {
    // Otimização: Evitar chamadas repetidas a erase(begin()) que são lentas.
    while (serialBuffer.size() >= 7) {
        
        // 1. Descartar bytes inválidos antes do preâmbulo
        if (serialBuffer[0] != PFOXPacket::PREAMBLE) {
            // Encontra o próximo preâmbulo. Se não encontrar, limpa o buffer
            auto it = std::find(serialBuffer.begin() + 1, serialBuffer.end(), PFOXPacket::PREAMBLE);
            
            if (it == serialBuffer.end()) {
                // Preâmbulo não encontrado. Limpa tudo para evitar buffer overflow.
                serialBuffer.clear();
                logToPC("ERRO: Preambulo nao encontrado. Buffer limpo.");
                return;
            }
            
            // Move o buffer para começar no preâmbulo encontrado (mais rápido que descarte 1 a 1)
            size_t bytes_to_shift = std::distance(serialBuffer.begin(), it);
            std::copy(it, serialBuffer.end(), serialBuffer.begin());
            serialBuffer.resize(serialBuffer.size() - bytes_to_shift);
            
            continue; // Recomeça a verificação com o preâmbulo agora em [0]
        }

        uint8_t len = serialBuffer[6];
        size_t total_len = 7 + len + 2; // Cabeçalho + Payload + CRC

        if (serialBuffer.size() < total_len) {
            // Pacote incompleto, esperar mais bytes
            break; 
        }

        // 2. Decodificação e Processamento
        try {
            PFOXPacket pkt(serialBuffer.data(), total_len);
            if (incoming.push(pkt)) {
                logToPC("Pacote recebido do PC: T" + String(static_cast<uint8_t>(pkt.type)) + " S" + String(pkt.seq));
            } else {
                logToPC("AVISO: Fila de entrada cheia, pacote do PC descartado.");
            }

        } catch (const std::runtime_error& e) {
            // Erro de CRC ou formato: move o ponteiro para descartar o pacote corrompido
            logToPC("ERRO PFOX (PC): " + String(e.what()));
        }

        // 3. Limpar o pacote processado do buffer (otimizado)
        // Move os dados restantes para o início para liberar o buffer
        std::copy(serialBuffer.begin() + total_len, serialBuffer.end(), serialBuffer.begin());
        serialBuffer.resize(serialBuffer.size() - total_len);
    }
}

// ESPHub.cpp

void ESPHub::sendToRobot(const PFOXPacket& pkt) {
    uint8_t mac[6];
    
    // Tenta obter o MAC. Se falhar, não faz nada.
    if (getRobotMac(pkt.dst, mac)) { 
        // 1. Coloca na fila de saída (mesmo que o ESP-NOW falhe imediatamente, ele deve ser tentado)
        outgoing.push(pkt); 
        
        // 2. Adiciona o pendingAck para controle de timeout
        PendingAck p;
        p.seq = pkt.seq;
        p.dst = static_cast<uint8_t>(pkt.dst);
        p.timestamp = millis();
        p.pkt = pkt; 
        pendingAcks.push_back(p);
        
        // 3. Envia o pacote imediatamente (o retorno será tratado no callback onESPNOWSent)
        auto data = pkt.encode();
        esp_now_send(mac, data.data(), data.size());

        // Opcional: Aqui você pode verificar o retorno de esp_now_send e, se falhar, 
        // remover p do pendingAcks e enviar um erro ao PC.
        
    } else {
        logToPC("ERRO: MAC do robo " + String(static_cast<uint8_t>(pkt.dst)) + " nao mapeado ou desconhecido.");
        // Opcional: Envie PFOXMsgType::ERROR ao PC para avisar sobre o robô inválido/desconhecido.
    }
}

void ESPHub::processOutgoing() {
    PFOXPacket pkt;
    while (outgoing.pop(pkt)) {

        uint8_t mac[6];
        getRobotMac(pkt.dst, mac); // <-- você cria isso (mapeamento ID->MAC)

        auto data = pkt.encode();
        esp_now_send(mac, data.data(), data.size());
    }
}

void ESPHub::onESPNOWSent(const uint8_t *mac, esp_now_send_status_t status) {
    if (!instance) return;

    instance->logToPC(
        String("ESPNOW enviado: ") + (status == ESP_NOW_SEND_SUCCESS ? "OK" : "FAIL")
    );
}

void ESPHub::onESPNOWRecv(const uint8_t *mac, const uint8_t *data, int len) {
    if (!instance) return;

    try {
        PFOXPacket pkt(data, len);
        instance->incoming.push(pkt);
    }
    catch (...) {
        instance->logToPC("Pacote ESPNOW inválido");
    }
}

void ESPHub::sendAckToPC(const PFOXPacket& pkt) {
    PFOXPacket ack;
    ack.src = PFOXAddress::ESPMAIN;
    ack.dst = pkt.src;
    ack.type = PFOXMsgType::ACK;
    ack.seq = pkt.seq;
    ack.payload = {0x00};
    ack.len = 1;

    auto enc = ack.encode();
    Serial.write(enc.data(), enc.size());
}

void ESPHub::forwardToPC(const PFOXPacket& pkt) {
    auto enc = pkt.encode();
    Serial.write(enc.data(), enc.size());
}

void ESPHub::processTimeouts() {
    uint32_t now = millis();
    for (int i = pendingAcks.size() - 1; i >= 0; i--) {
        auto& p = pendingAcks[i];

        if (now - p.timestamp > 150) { // 150 ms timeout
            logToPC("ACK TIMEOUT do robô " + String(p.dst));

            // envie erro ao PC
            PFOXPacket err;
            err.src = PFOXAddress::ESPMAIN;
            err.dst = p.pkt.src;
            err.type = PFOXMsgType::ERROR;
            err.seq = p.pkt.seq;
            err.len = 1;
            err.payload = {0x01}; // código de timeout

            forwardToPC(err);

            pendingAcks.erase(pendingAcks.begin() + i);
        }
    }
}

void ESPHub::logToPC(const String& msg) {
    Serial.print("[HUB] ");
    Serial.println(msg);
}

// ESPHub.cpp

void ESPHub::loop() {
    // 1. Recebe bytes disponíveis da Serial
    receiveSerial();
    
    // 2. Processa e decodifica os bytes recebidos em pacotes PFOX (versão otimizada)
    processSerialBytes();
    
    // 3. Verifica se há pacotes ESP-NOW enviados que excederam o tempo de espera por um ACK
    processTimeouts();

    PFOXPacket pkt;
    // 4. Processa todos os pacotes bufferizados na fila 'incoming'
    while (incoming.pop(pkt)) {

        // se veio do PC (0x00), envia para o robô
        if (pkt.src == PFOXAddress::PC) {
            sendToRobot(pkt);
            sendAckToPC(pkt); // ACK de recebimento Serial para o PC
            continue;
        }

        // CORREÇÃO: se veio de um robô (verificação de range usando os enums)
        // O range usado considera todos os IDs de robô definidos (ROBOT1 a ROBOT3)
        if (static_cast<uint8_t>(pkt.src) >= static_cast<uint8_t>(PFOXAddress::ROBOT1) && 
            static_cast<uint8_t>(pkt.src) <= static_cast<uint8_t>(PFOXAddress::ROBOT3)) 
        {
            
            // se for ACK, remove o pacote correspondente da lista de pendentes
            if (pkt.type == PFOXMsgType::ACK) {
                // Percorre a lista de trás para frente para remover eficientemente
                for (int i = pendingAcks.size() - 1; i >= 0; --i) {
                    const auto& p = pendingAcks[i];
                    // O ACK deve coincidir com a sequência do pacote e ter como origem o robô correto
                    if (p.seq == pkt.seq && p.dst == static_cast<uint8_t>(pkt.src)) {
                        logToPC("ACK recebido do robo " + String(p.dst) + " (Seq " + String(p.seq) + ")");
                        pendingAcks.erase(pendingAcks.begin() + i);
                        break;
                    }
                }
            }
            
            // Pacotes de robôs (STATUS, HEARTBEAT, etc.) são sempre encaminhados para o PC
            forwardToPC(pkt);
            continue;
        }

        // se o pacote é do ESPMAIN (0xFE) e precisa ser encaminhado para o PC (e.g., logs internos, erros)
        if (pkt.src == PFOXAddress::ESPMAIN) {
            forwardToPC(pkt);
            continue;
        }
    }
}

// 🚨 IMPORTANTE: SUBSTITUA ESTES ENDEREÇOS MAC PELOS ENDEREÇOS REAIS DOS SEUS ROBÔS!
// Os IDs (0x01, 0x02, 0x03) devem corresponder à ordem na tabela.
static const uint8_t ROBOT_MACS[][6] = {
    // Endereço MAC do ROBOT1 (ID 0x01)
    {0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0x01}, 
    // Endereço MAC do ROBOT2 (ID 0x02)
    {0xBB, 0xBB, 0xBB, 0xBB, 0xBB, 0x02},
    // Endereço MAC do ROBOT3 (ID 0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0x03}
    {0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0x03}
};
static constexpr size_t NUM_ROBOTS = sizeof(ROBOT_MACS) / sizeof(ROBOT_MACS[0]);

// NOVO: Função para obter o MAC do robô pelo ID (0x01, 0x02, 0x03)
bool ESPHub::getRobotMac(PFOXAddress robot_id, uint8_t mac[6]) {
    // Converte o enum para o índice do array (ex: ROBOT1 (0x01) -> índice 0)
    int index = static_cast<uint8_t>(robot_id) - static_cast<uint8_t>(PFOXAddress::ROBOT1);

    if (index >= 0 && index < NUM_ROBOTS) {
        memcpy(mac, ROBOT_MACS[index], 6);
        return true;
    }
    return false;
}