#include "Control.h"

// ================= HARDWARE DO SEU ROBÔ (L298N) =================

// MOTOR A (Esquerdo)
#define PIN_A_IN1  2
#define PIN_A_IN2  4
#define PIN_A_EN   15  // PWM

// MOTOR B (Direito)
#define PIN_B_IN1  25
#define PIN_B_IN2  26
#define PIN_B_EN   32  // PWM

// CONSTANTES DO PID 
// Ajuste estes valores na prática. 
// Kp: Força da reação imediata.
// Ki: Corrige erros acumulados (se o robô não chega na velocidade, aumente devagar).
// Kd: Amortece oscilações (se o robô tremer, aumente).
#define K_P  2.0  
#define K_I  0.5
#define K_D  0.1

// ================= IMPLEMENTAÇÃO PID (Completo) =================
PID::PID(float p, float i, float d, float minV, float maxV)
    : kp(p), ki(i), kd(d), minVal(minV), maxVal(maxV), integral(0), prevError(0), lastTime(0) {}

float PID::compute(float setpoint, float measured) {
    unsigned long now = millis();
    float dt = (now - lastTime) / 1000.0; // Tempo em segundos
    
    // Proteção contra dt inválido na primeira execução
    if (dt <= 0 || dt > 1.0) dt = 0.1;

    // 1. Erro
    float error = setpoint - measured;

    // 2. Proporcional
    float P = kp * error;

    // 3. Integral (com proteção anti-windup)
    integral += error * dt;
    if (integral > maxVal) integral = maxVal;
    else if (integral < minVal) integral = minVal;
    float I = ki * integral;

    // 4. Derivativo
    float derivative = (error - prevError) / dt;
    float D = kd * derivative;

    // Soma final
    float output = P + I + D;

    // Limites de saída (PWM)
    if (output > maxVal) output = maxVal;
    else if (output < minVal) output = minVal;

    prevError = error;
    lastTime = now;

    return output;
}

void PID::reset() {
    integral = 0;
    prevError = 0;
    lastTime = millis();
}

// ================= IMPLEMENTAÇÃO MOTOR (L298N) =================

Motor::Motor(int pinIn1, int pinIn2, int pinEnable)
    : pin1(pinIn1), pin2(pinIn2), pinEn(pinEnable) {}

void Motor::begin() {
    pinMode(pin1, OUTPUT);
    pinMode(pin2, OUTPUT);
    
    // Configura PWM (ESP32 v3.0+)
    if (!ledcAttach(pinEn, PWM_FREQ, PWM_RES)) {
        Serial.println("Erro PWM Motor");
    }
}

void Motor::drive(int speed) {
    // Clampa valores
    if (speed > PWM_MAX) speed = PWM_MAX;
    if (speed < -PWM_MAX) speed = -PWM_MAX;

    if (speed > 0) {
        // Frente
        digitalWrite(pin1, HIGH);
        digitalWrite(pin2, LOW);
        ledcWrite(pinEn, abs(speed));
    } 
    else if (speed < 0) {
        // Ré
        digitalWrite(pin1, LOW);
        digitalWrite(pin2, HIGH);
        ledcWrite(pinEn, abs(speed));
    } 
    else {
        // Ponto morto / Freio
        digitalWrite(pin1, LOW);
        digitalWrite(pin2, LOW);
        ledcWrite(pinEn, 0);
    }
}

// ================= ROBOT CONTROL =================

RobotControl::RobotControl() 
    : motorLeft(PIN_A_IN1, PIN_A_IN2, PIN_A_EN),
      motorRight(PIN_B_IN1, PIN_B_IN2, PIN_B_EN),
      pidLeft(K_P, K_I, K_D, -PWM_MAX, PWM_MAX),
      pidRight(K_P, K_I, K_D, -PWM_MAX, PWM_MAX)
{
}

void RobotControl::begin() {
    motorLeft.begin();
    motorRight.begin();
    pidLeft.reset();
    pidRight.reset();
}

void RobotControl::update(int16_t leftReal, int16_t leftDes, int16_t rightReal, int16_t rightDes) {
    
    // Motor Esquerdo
    if (leftDes == 0) {
        motorLeft.drive(0);
        pidLeft.reset(); // Zera integral se parou
    } else {
        float pwmLeft = pidLeft.compute((float)leftDes, (float)leftReal);
        motorLeft.drive((int)pwmLeft);
    }

    // Motor Direito
    if (rightDes == 0) {
        motorRight.drive(0);
        pidRight.reset();
    } else {
        float pwmRight = pidRight.compute((float)rightDes, (float)rightReal);
        motorRight.drive((int)pwmRight);
    }
}

void RobotControl::stop() {
    motorLeft.drive(0);
    motorRight.drive(0);
    pidLeft.reset();
    pidRight.reset();
}