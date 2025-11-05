import numpy as np
import matplotlib.pyplot as plt

# Parâmetros
dt = 0.1  # intervalo de tempo
A = np.array([[1, 0, dt, 0],
              [0, 1, 0, dt],
              [0, 0, 1, 0],
              [0, 0, 0, 1]])

H = np.array([[1, 0, 0, 0],
              [0, 1, 0, 0]])

Q = np.eye(4) * 0.001  # ruído do processo (movimento)
R = np.eye(2) * 0.1    # ruído da medição
P = np.eye(4)           # covariância inicial

x = np.array([[0], [0], [1], [0.3]])  # estado inicial [x, y, vx, vy]

# Simulação
num_steps = 200
true_positions = []
measurements = []
estimates = []

# Define intervalos sem medições (por exemplo, 50–70 e 120–150)
missing_intervals = [(50, 70), (120, 150)]

for k in range(num_steps):
    # Movimento real (posição e velocidade)
    x_real = A @ x + np.random.randn(4, 1) * 0.01

    # Verifica se há medição nesse passo
    in_gap = any(start <= k <= end for start, end in missing_intervals)

    if in_gap:
        z = None  # sem medição
    else:
        z = H @ x_real + np.random.randn(2, 1) * 0.1  # medição ruidosa

    # --- Previsão ---
    x_pred = A @ x
    P_pred = A @ P @ A.T + Q

    # --- Atualização (se houver medição) ---
    if z is not None:
        K = P_pred @ H.T @ np.linalg.inv(H @ P_pred @ H.T + R)
        x = x_pred + K @ (z - H @ x_pred)
        P = (np.eye(4) - K @ H) @ P_pred
    else:
        x = x_pred
        P = P_pred

    # Armazena
    true_positions.append(x_real[:2].flatten())
    measurements.append(z.flatten() if z is not None else [np.nan, np.nan])
    estimates.append(x[:2].flatten())

# --- Plot ---
true_positions = np.array(true_positions)
measurements = np.array(measurements)
estimates = np.array(estimates)

plt.figure(figsize=(10, 6))
plt.plot(true_positions[:, 0], true_positions[:, 1], label="Trajetória real", linewidth=2)
plt.scatter(measurements[:, 0], measurements[:, 1], color='r', s=20, alpha=0.6, label="Medições (com lacunas)")
plt.plot(estimates[:, 0], estimates[:, 1], color='g', linewidth=2, label="Estimativa Kalman")
plt.legend()
plt.xlabel("x")
plt.ylabel("y")
plt.title("Filtro de Kalman com trechos sem medições (previsão livre)")
plt.grid(True)

# Marcar intervalos sem medição
for start, end in missing_intervals:
    plt.axvspan(estimates[start, 0], estimates[end-1, 0], color='gray', alpha=0.2, label="Sem medição" if start == missing_intervals[0][0] else "")

plt.show()
