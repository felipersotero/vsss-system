#pragma once
#include <Arduino.h>

// Configurações PWM (Mantendo compatibilidade com ESP32 v3.0)
#define PWM_FREQ 5000  // 5kHz (padrão L298N)
#define PWM_RES  8     // 8 bits = 0 a 255
#define PWM_MAX  255

// ================= CLASSE PID =================
class PID {
public:
    PID(float kp, float ki, float kd, float outMin, float outMax);
    float compute(float setpoint, float measured);
    void reset();

private:
    float kp, ki, kd;
    float minVal, maxVal;
    float integral;
    float prevError;
    unsigned long lastTime;
};

// ================= CLASSE MOTOR (L298N - 3 PINOS) =================
class Motor {
public:
    // CORREÇÃO: Construtor agora aceita 3 argumentos (IN1, IN2, ENABLE)
    Motor(int pinIn1, int pinIn2, int pinEnable);
    
    void begin();
    
    // speed: -255 a +255
    void drive(int speed);

private:
    int pin1, pin2, pinEn;
};

// ================= CLASSE ROBOT (Main) =================
class RobotControl {
public:
    RobotControl();

    // Inicializa Pinos e PWM
    void begin();

    // Método principal: Recebe velocidades reais e desejadas
    void update(int16_t leftReal, int16_t leftDes, int16_t rightReal, int16_t rightDes);

    // Parada de emergência
    void stop();

private:
    Motor motorLeft;
    Motor motorRight;
    PID pidLeft;
    PID pidRight;
};