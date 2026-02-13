#include "Control.h"

// ================= IMPLEMENTAÇÃO PID =================

PID::PID(PIDConfig config, float minV, float maxV)
    : _kp(config.kp), _ki(config.ki), _kd(config.kd), 
      _minVal(minV), _maxVal(maxV), _integral(0), _prevError(0) {
    _lastTime = millis();
}

float PID::compute(float setpoint, float measured) {
    unsigned long now = millis();
    float dt = (now - _lastTime) / 1000.0f; 
    
    if (dt <= 0) return 0; 
    if (dt > 0.5f) dt = 0.01f; // Proteção contra saltos de tempo

    float error = setpoint - measured;

    // Proporcional
    float P = _kp * error;

    // Integral
    _integral += error * dt;
    // Anti-windup simples
    if (_integral > _maxVal) _integral = _maxVal;
    else if (_integral < _minVal) _integral = _minVal;
    
    float I = _ki * _integral;

    // Derivativo
    float derivative = (error - _prevError) / dt;
    float D = _kd * derivative;

    float output = P + I + D;

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
    // Para ESP32 v3.0+
    ledcAttach(_pins.enable, PWM_FREQ, PWM_RES);
}

void Motor::drive(int16_t speed) {
    // Garante que o PWM não exceda os limites físicos
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
      _pidLeft(pidCfg, -PWM_MAX, PWM_MAX), _pidRight(pidCfg, -PWM_MAX, PWM_MAX),
      _usePID(true) // Padrão inicia COM PID (pode mudar no begin se quiser)
{}

void RobotControl::begin() {
    _motorLeft.begin();
    _motorRight.begin();
    this->stop();
}

void RobotControl::setControlMode(bool usePID) {
    _usePID = usePID;
    // Quando mudamos de modo, é bom resetar o PID para limpar acumuladores
    if (_usePID) {
        _pidLeft.reset();
        _pidRight.reset();
    }
}

void RobotControl::update(int16_t leftReal, int16_t leftDes, int16_t rightReal, int16_t rightDes) {
    int16_t outL, outR;

    if (_usePID) {
        // --- MODO PID (Malha Fechada) ---
        // Usa o feedback enviado pelo mestre para calcular correção
        
        // Se target é 0 e velocidade real é baixa, força parada para evitar zumbido
        if (leftDes == 0 && abs(leftReal) < 5) {
            outL = 0;
            _pidLeft.reset();
        } else {
            outL = (int16_t)_pidLeft.compute((float)leftDes, (float)leftReal);
        }

        if (rightDes == 0 && abs(rightReal) < 5) {
            outR = 0;
            _pidRight.reset();
        } else {
            outR = (int16_t)_pidRight.compute((float)rightDes, (float)rightReal);
        }

    } else {
        // --- MODO PWM DIRETO (Malha Aberta) ---
        // Ignora leftReal/rightReal.
        // O valor desejado é passado diretamente como PWM.
        
        outL = leftDes;
        outR = rightDes;
        
        // Mantemos o reset do PID em background para não acumular erro 
        // caso troque de modo repentinamente
        _pidLeft.reset();
        _pidRight.reset();
    }

    _motorLeft.drive(outL);
    _motorRight.drive(outR);
}

void RobotControl::stop() {
    _motorLeft.drive(0); 
    _motorRight.drive(0);
    _pidLeft.reset(); 
    _pidRight.reset();
}