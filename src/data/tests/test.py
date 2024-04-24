import cv2
import numpy as np

# Carregar a imagem binarizada
imagem = cv2.imread('src/data/tests/carrosBin.png', cv2.IMREAD_GRAYSCALE)

# Encontrar contornos na imagem
contornos, _ = cv2.findContours(imagem, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Criar uma máscara em branco para os quadrados
mascara = np.zeros_like(imagem)

# Iterar sobre os contornos encontrados
for contorno in contornos:
    perimetro = cv2.arcLength(contorno, True)
    approx = cv2.approxPolyDP(contorno, 0.04 * perimetro, True)
    if len(approx) == 4:
        # Verificar se é um quadrado
        x, y, w, h = cv2.boundingRect(approx)
        aspect_ratio = float(w) / h
        if 0.7 <= aspect_ratio <= 1.3:
            # Desenhar contorno do quadrado na máscara
            cv2.drawContours(mascara, [contorno], 0, 255, -1)

# Garantir que a máscara seja do tipo uint8
mascara = np.uint8(mascara)

# Converter a máscara para o tipo cv2.UMat
mascara = cv2.UMat(mascara)

# Aplicar a máscara na imagem original para remover os objetos que não são quadrados
imagem_resultante = cv2.bitwise_and(imagem, imagem, mask=mascara)

# Mostrar a imagem resultante
cv2.imshow('Imagem Resultante', imagem_resultante)
cv2.imshow('Imagem original', imagem)
cv2.waitKey(0)
cv2.destroyAllWindows()
