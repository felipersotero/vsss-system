#include <WiFi.h>

// Este sketch deve ser carregado em CADA um dos seus ESPs (Robô 1, 2 e 3).
// Ele irá imprimir o MAC Address de cada placa no Monitor Serial.

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n--- Leitura do Endereco MAC ---");

  // 1. Configura o modo Wi-Fi
  // Mesmo que voce use ESP-NOW, a inicializacao do WiFi e necessaria
  // para obter o MAC. O modo STATION (WIFI_STA) e o padrao mais comum.
  WiFi.mode(WIFI_STA); 

  // 2. Obtem o endereco MAC
  String macAddress = WiFi.macAddress();
  
  Serial.print("MAC Address da Placa: ");
  Serial.println(macAddress);

  // 3. Imprime no formato do array (para copiar facilmente)
  Serial.println("\nFormato para array ROBOT_MACS (ESPHUB.cpp):");
  Serial.printf("{0x%02X, 0x%02X, 0x%02X, 0x%02X, 0x%02X, 0x%02X}\n",
                macAddress[0], macAddress[3], macAddress[6], 
                macAddress[9], macAddress[12], macAddress[15]);
  
  // Imprime os bytes separados (para debug visual)
  Serial.printf("Bytes: %02X:%02X:%02X:%02X:%02X:%02X\n",
                macAddress[0], macAddress[3], macAddress[6], 
                macAddress[9], macAddress[12], macAddress[15]);
                
  Serial.println("------------------------------------");
  Serial.println("ANOTE ESTE ENDERECO E ATUALIZE O ESPHUB.cpp");
}

void loop() {
  // Nada para fazer no loop, a informacao ja foi impressa
  delay(5000); 
}