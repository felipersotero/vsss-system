#include "ESPHub.h"

ESPHub hub;

void setup() {
    Serial.begin(115200);
    delay(300);
    hub.begin();
}

void loop() {
    hub.loop();
    delay(1);
}
