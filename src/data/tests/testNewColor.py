
# cor aliada: [109 210 255] HSV
# cor inimigo [ 28  77 255] HSV
    def is_square(self, contour, min_diag=20):
        """
        Verifica se o contorno corresponde aproximadamente a um quadrado.
        Retorna True se for quadrado, False caso contrário.
        """
        perimetro = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * perimetro, True)

        # Precisa ter 4 lados
        if len(approx) != 4:
            return False

        x, y, w, h = cv2.boundingRect(approx)
        aspect_ratio = w / float(h)
        diag = np.hypot(w, h)

        # Aproximadamente quadrado e com tamanho mínimo
        return 0.7 <= aspect_ratio <= 1.3 and diag >= min_diag
    
    
    def detect_squares(,img_bin, min_diag=20):
        """
        Processa uma imagem binarizada e retorna apenas os objetos com formato próximo de quadrado.

        Retorna:
            - bin_res: imagem binarizada com apenas os quadrados;
            - contours_treat: lista de contornos correspondentes aos quadrados.
        """
        contours, _ = cv2.findContours(img_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return img_bin, []

        mask = np.zeros_like(img_bin)
        contours_treat = []

        for contour in contours:
            if .is_square(contour, min_diag):
                cv2.drawContours(mask, [contour], -1, 255, -1)
                contours_treat.append(contour)

        bin_res = cv2.bitwise_and(img_bin, mask)
        return bin_res, contours_treat

# Carregar imagem 

    # Conversão e máscaras
    imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    Objects = cv2.inRange(imgHSV, .objectsDarkColor, .objectsLightColor)
    .binaryPlayers = cv2.subtract(Objects, .binaryBall)

    # Filtragem morfológica
    ellipse5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    rect11 = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
    .binaryPlayers = cv2.erode(.binaryPlayers, ellipse5, iterations=1)
    .binaryPlayers = cv2.morphologyEx(.binaryPlayers, cv2.MORPH_CLOSE, rect11)
    
    # Limites de cor
    .ally_lower_bound, .ally_upper_bound = .create_color_bounds(.allyColor)
    .enemy_lower_bound, .enemy_upper_bound = .create_color_bounds(.enemyColor)
    
    # Reconhecimento de objetos
    .binaryPlayers, players = .detect_squares(.binaryPlayers)

    # puxa filtro com as cores aliadas e inimigas

    # recupera o centro do circulo que engloba o player completo
