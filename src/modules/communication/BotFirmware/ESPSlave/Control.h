#pragma once
#include <Arduino.h>

/**
 * @brief Estrutura para agrupar os ganhos do controlador PID.
 */
struct PIDConfig {
    float kp;
    float ki;
    float kd;
};

/**
 * @brief Estrutura para mapeamento de pinos da Ponte H L298N.
 */
struct MotorPins {
    int in1;
    int in2;
    int enable; // Pino PWM
};

// Configurações PWM (Mantendo compatibilidade com ESP32 v3.0)
#define PWM_FREQ 5000  // 5kHz (padrão L298N)
#define PWM_RES  8     // 8 bits = 0 a 255
#define PWM_MAX  255

// ================= CLASSE PID =================
class PID {
public:
    PID(PIDConfig config, float outMin, float outMax);

    float compute(float setpoint, float measured);
    void reset();
    void setGains(PIDConfig config);

private:
    float _kp, _ki, _kd;
    float _minVal, _maxVal;
    float _integral;
    float _prevError;
    unsigned long _lastTime;
};

// ================= CLASSE MOTOR (L298N) =================
class Motor {
public:
    Motor(MotorPins pins);
    
    void begin();
    
    // speed: -255 a +255
    void drive(int16_t speed);

private:
    MotorPins _pins;
};

// ================= CLASSE ROBOT (Main) =================
class RobotControl {
public:
    RobotControl(MotorPins pinsLeft, MotorPins pinsRight, PIDConfig pidCfg);

    void begin();

    /**
     * @brief Define se o robô deve usar o PID ou controle direto (PWM).
     * @param usePID true = Usa PID (Malha Fechada), false = PWM Direto (Malha Aberta)
     */
    void setControlMode(bool usePID);

    /**
     * @brief Atualiza os motores.
     * Se PID estiver ATIVO: Usa (Des - Real) para calcular erro.
     * Se PID estiver INATIVO: Usa apenas (Des) como PWM direto e ignora (Real).
     */
    void update(int16_t leftReal, int16_t leftDes, int16_t rightReal, int16_t rightDes);

    void stop();

private:
    Motor _motorLeft;
    Motor _motorRight;
    PID _pidLeft;
    PID _pidRight;
    
    bool _usePID; // Nova flag de controle
};