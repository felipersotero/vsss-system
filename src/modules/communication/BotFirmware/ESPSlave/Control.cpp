#include "Control.h"

// ================= IMPLEMENTAÇÃO PID =================

PID::PID(PIDConfig config, float minV, float maxV)
    : _kp(config.kp), _ki(config.ki), _kd(config.kd), 
      _minVal(minV), _maxVal(maxV), _integral(0), _prevError(0) {
    _lastTime = millis();
}

float PID::compute(float setpoint, float measured) {
    unsigned long now = millis();
    float dt = (now - _lastTime) / 1000.0f; // Tempo em segundos
    
    // Proteção contra dt zero ou muito alto (latência de rede)
    if (dt <= 0) return 0; 
    if (dt > 0.5f) dt = 0.01f; // Evita picos em quedas de conexão

    float error = setpoint - measured;

    // Termo Proporcional
    float P = _kp * error;

    // Termo Integral com Anti-Windup (limita a acumulação do erro)
    _integral += error * dt;
    float I = _ki * _integral;
    
    // Clamp preventivo na integral para evitar saturação
    if (I > _maxVal) { _integral = _maxVal / _ki; I = _maxVal; }
    else if (I < _minVal) { _integral = _minVal / _ki; I = _minVal; }

    // Termo Derivativo (reage à velocidade de mudança do erro)
    float derivative = (error - _prevError) / dt;
    float D = _kd * derivative;

    float output = P + I + D;

    // Salva estado para o próximo ciclo
    _prevError = error;
    _lastTime = now;

    return constrain(output, _minVal, _maxVal);
}

void PID::reset() {
    _integral = 0;
    _prevError = 0;
    _lastTime = millis();
}

void PID::setGains(PIDConfig config) {
    _kp = config.kp; _ki = config.ki; _kd = config.kd;
}

// ================= IMPLEMENTAÇÃO MOTOR =================

Motor::Motor(MotorPins pins) : _pins(pins) {}

void Motor::begin() {
    pinMode(_pins.in1, OUTPUT);
    pinMode(_pins.in2, OUTPUT);
    ledcAttach(_pins.enable, PWM_FREQ, PWM_RES);
}

void Motor::drive(int16_t speed) {
    speed = constrain(speed, -PWM_MAX, PWM_MAX);

    if (speed > 0) {
        digitalWrite(_pins.in1, HIGH);
        digitalWrite(_pins.in2, LOW);
        ledcWrite(_pins.enable, (uint32_t)abs(speed));
    } else if (speed < 0) {
        digitalWrite(_pins.in1, LOW);
        digitalWrite(_pins.in2, HIGH);
        ledcWrite(_pins.enable, (uint32_t)abs(speed));
    } else {
        digitalWrite(_pins.in1, LOW);
        digitalWrite(_pins.in2, LOW);
        ledcWrite(_pins.enable, 0);
    }
}

// ================= IMPLEMENTAÇÃO ROBOTCONTROL =================

RobotControl::RobotControl(MotorPins pinsLeft, MotorPins pinsRight, PIDConfig pidCfg)
    : _motorLeft(pinsLeft), _motorRight(pinsRight),
      _pidLeft(pidCfg, -PWM_MAX, PWM_MAX), _pidRight(pidCfg, -PWM_MAX, PWM_MAX) {}

void RobotControl::begin() {
    _motorLeft.begin();
    _motorRight.begin();
    this->stop();
}

void RobotControl::update(int16_t leftReal, int16_t leftDes, int16_t rightReal, int16_t rightDes) {
    // Se o comando for zero e o robô estiver parado, reseta para evitar zumbido nos motores
    if (leftDes == 0 && abs(leftReal) < 2) {
        _motorLeft.drive(0);
        _pidLeft.reset();
    } else {
        _motorLeft.drive((int16_t)_pidLeft.compute((float)leftDes, (float)leftReal));
    }

    if (rightDes == 0 && abs(rightReal) < 2) {
        _motorRight.drive(0);
        _pidRight.reset();
    } else {
        _motorRight.drive((int16_t)_pidRight.compute((float)rightDes, (float)rightReal));
    }
}

void RobotControl::stop() {
    _motorLeft.drive(0); _motorRight.drive(0);
    _pidLeft.reset(); _pidRight.reset();
}