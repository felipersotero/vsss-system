#include <Arduino.h>
#include "ESPSlave.h"

// ================== CONFIGURAÇÃO ==================

// 1. Defina qual robô é este (ROBOT1, ROBOT2 ou ROBOT3)
#define MY_IDENTITY  PFOXAddress::ROBOT1 

// 2. Coloque o MAC Address do ESP32 que está rodando o ESPHub
//    (O Hub imprime o MAC dele na Serial ao iniciar: "MAC real do HUB: ...")
uint8_t HUB_MAC_ADDR[] = {0x94, 0xB9, 0x7E, 0xE4, 0xAC, 0x54}; 

// ==================================================

ESPSlave slave(MY_IDENTITY, HUB_MAC_ADDR);

void setup() {
    Serial.begin(115200);
    

    slave.begin();
}

void loop() {
    slave.loop();

}