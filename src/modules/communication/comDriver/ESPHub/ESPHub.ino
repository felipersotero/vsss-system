#include "ESPHub.h"

ESPHub hub;

void setup() {
    Serial.begin(115200);
    hub.logToPC("ESP HUB iniciado");
}

void loop() {
    hub.loop();
    delay(1);
}
