import cv2
import numpy as np

def detectar_x(image):
    # Converter a imagem para escala de cinza
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Aplicar uma transformação de Canny para detectar bordas
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Detectar linhas usando a transformada de Hough
    lines = cv2.HoughLines(edges, 1, np.pi/180, 200)

    # Verificar se existem pelo menos duas linhas detectadas
    if lines is not None and len(lines) >= 2:
        # Contador de linhas em forma de 'x'
        lines_x = 0
        
        # Iterar sobre todas as linhas detectadas
        for rho, theta in lines[:, 0]:
            # Calcular as coordenadas do ponto inicial e final da linha
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a * rho
            y0 = b * rho
            x1 = int(x0 + 1000 * (-b))
            y1 = int(y0 + 1000 * (a))
            x2 = int(x0 - 1000 * (-b))
            y2 = int(y0 - 1000 * (a))

            # Desenhar a linha detectada na imagem de saída (apenas para visualização)
            cv2.line(image, (x1, y1), (x2, y2), (0, 0, 255), 2)

            # Verificar se a linha está na diagonal esquerda ou direita
            if abs(theta - np.pi/4) < np.pi/8 or abs(theta - 3*np.pi/4) < np.pi/8:
                lines_x += 1

        # Verificar se foram detectadas duas linhas em forma de 'x'
        if lines_x >= 2:
            print("Desenho em forma de 'x' detectado!")
        else:
            print("Desenho em forma de 'x' não detectado.")

    else:
        print("Desenho em forma de 'x' não detectado.")

    # Exibir a imagem com as linhas detectadas (apenas para visualização)
    cv2.imshow('Detecção de X', image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# Carregar a imagem
image = cv2.imread('src\images\campo_real_03.png') # Substitua 'exemplo.jpg' pelo caminho da sua imagem
# Detectar o padrão 'x' na imagem
detectar_x(image)
