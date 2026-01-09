import cv2
import numpy as np
import matplotlib.pyplot as plt

# 1. Carregar a imagem
# Se estiver usando um arquivo local, troque 'imagem.jpg' pelo seu caminho
img = cv2.imread('src/data/tests/flor_amarela.png')
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) # Para exibir corretamente no Matplotlib

# 2. Converter para o espaço de cores HSV
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# 3. Definir o intervalo da cor amarela no HSV
# Nota: Esses valores podem precisar de ajuste dependendo da iluminação
lower_yellow = np.array([20, 100, 100])
upper_yellow = np.array([35, 255, 255])

# 4. Criar a máscara binária (o "pixel vira 1" se estiver no intervalo)
mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

# 5. Aplicar a máscara na imagem original para ver o resultado colorido (opcional)
result = cv2.bitwise_and(img_rgb, img_rgb, mask=mask)

# 6. Exibir os resultados
plt.figure(figsize=(15, 5))

plt.subplot(1, 3, 1)
plt.title("Original")
plt.imshow(img_rgb)
plt.axis('off')

plt.subplot(1, 3, 2)
plt.title("Máscara Binária (Amarelo)")
plt.imshow(mask, cmap='gray')
plt.axis('off')

plt.subplot(1, 3, 3)
plt.title("Resultado da Segmentação")
plt.imshow(result)
plt.axis('off')

plt.show()