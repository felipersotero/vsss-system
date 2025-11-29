#include <WiFi.h>
#include <esp_wifi.h>

void printMac(const char* label) {
  uint8_t mac[6];
  WiFi.macAddress(mac);
  Serial.printf("%s: %02X:%02X:%02X:%02X:%02X:%02X\n",
                label,
                mac[0], mac[1], mac[2],
                mac[3], mac[4], mac[5]);
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n--- Teste de Atualização de MAC ---");

  // Inicializa WiFi em modo STA (necessário antes de mudar MAC)
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  delay(200);

  // --- 1. LER MAC ATUAL ---
  printMac("MAC original");

  // --- 2. DEFINIR UM NOVO MAC PARA TESTE ---
 uint8_t novoMac[6] = {0x30, 0xAE, 0xA4, 0x07, 0x0D, 0x55};


  Serial.print("Aplicando novo MAC: ");
  for (int i = 0; i < 6; i++) Serial.printf("%02X:", novoMac[i]);
  Serial.println();

  esp_err_t err = esp_wifi_set_mac(WIFI_IF_STA, novoMac);
  if (err != ESP_OK) {
    Serial.printf("[ERRO] esp_wifi_set_mac falhou! Codigo: %d\n", err);
  } else {
    Serial.println("[OK] Novo MAC aplicado!");
  }

  // --- 3. PRECISA REINICIAR WIFI PARA VALIDAR ---
  WiFi.disconnect(true);
  WiFi.mode(WIFI_STA);
  delay(200);

  // --- 4. LER NOVAMENTE ---
  printMac("MAC após atualização");

  // --- 5. Mostrar formato para copiar ---
  Serial.println("\nFormato para colar no ESPHUB.cpp:");
  Serial.printf("{0x%02X, 0x%02X, 0x%02X, 0x%02X, 0x%02X, 0x%02X}\n",
                novoMac[0], novoMac[1], novoMac[2],
                novoMac[3], novoMac[4], novoMac[5]);

  Serial.println("------------------------------------");
}

void loop() {
  delay(5000);
}
