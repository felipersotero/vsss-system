    def detect_players(self, img, debug=False, isT=False):
        """
        Detecta robôs na imagem
        """
        # Reset de contadores e status
        self.playersCount = self.enemiesCount = self.alliesCount = 0
        for bot in (*self.enemyTeam, *self.allyTeam):
            bot.setStatus(False)

        # Garante a forma da máscara da bola
        if getattr(self, "binaryBall", None) is None or self.binaryBall.size == 0:
            self.binaryBall = np.zeros(img.shape[:2], dtype=np.uint8)
        elif self.binaryBall.shape != img.shape[:2]:
            self.binaryBall = cv2.resize(self.binaryBall, (img.shape[1], img.shape[0]))

        # Conversão e máscaras
        imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        Objects = cv2.inRange(imgHSV, self.objectsDarkColor, self.objectsLightColor)
        self.binaryPlayers = cv2.subtract(Objects, self.binaryBall)

        # Filtragem morfológica
        ellipse5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        rect11 = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
        self.binaryPlayers = cv2.erode(self.binaryPlayers, ellipse5, iterations=1)
        self.binaryPlayers = cv2.morphologyEx(self.binaryPlayers, cv2.MORPH_CLOSE, rect11)

        # Limites de cor
        self.ally_lower_bound, self.ally_upper_bound = self.create_color_bounds(self.allyColor)
        self.enemy_lower_bound, self.enemy_upper_bound = self.create_color_bounds(self.enemyColor)

        # Reconhecimento de objetos
        self.binaryPlayers, players = self.detect_squares(self.binaryPlayers)

        # Pré-cálculos
        winSize = int(18 * self.prop_px_cm)
        playerRadius = (7.5 / 2) * np.sqrt(2) * self.prop_px_cm
        mainColorRadius = (7.5 / 4) * np.sqrt(5) * self.prop_px_cm

        # Flags de controle
        AgoalFlag = Aatk1Flag = Aatk2Flag = False
        flags = [AgoalFlag, Aatk1Flag,Aatk2Flag]

        for currentPlayer in players:
            (xi, yi), ri = cv2.minEnclosingCircle(currentPlayer)
            if not (0.2 * playerRadius < ri < 2 * playerRadius and self.playersCount < 6):
                continue  # ignora objetos fora do intervalo

            if debug:
                cv2.circle(self.frameResult, (int(xi), int(yi)), int(ri) + 5, (0, 255, 0), 2)

            # recorta área de interesse
            half_win = winSize // 2
            x1, y1 = max(0, int(xi - half_win)), max(0, int(yi - half_win))
            x2, y2 = min(img.shape[1], int(xi + half_win)), min(img.shape[0], int(yi + half_win))
            windowActual = img[y1:y2, x1:x2]

            # encontra cores de aliados e inimigos
            mainColorContours = self.find_binary_contours(windowActual, self.ally_lower_bound, self.ally_upper_bound)
            enemyColorContours = self.find_binary_contours(windowActual, self.enemy_lower_bound, self.enemy_upper_bound)

            tm = self.timer.getElapsedTime()
            xcm, ycm = self.getPointVirtual(self.transformPoint(np.array([xi, yi])))
            rcm = 5.30

            # --- INIMIGOS ---
            if enemyColorContours and self.enemiesCount < 3:
                contour = max(enemyColorContours, key=cv2.contourArea)
                (x_m,y_m), rc = cv2.minEnclosingCircle(contour)

                x_vm, y_vm =self.getPointVirtual(self.transformPoint(np.array([x_m, y_m])))
                if rc >= 0.5 * mainColorRadius:
                    bot = self.enemyTeam[self.enemiesCount]
                    bot.setPosition(x=xcm, y=ycm, r=rcm, image=windowActual, time=tm)
                    bot.updtPositionImg(xi=xi, yi=yi, ri=ri)
                    bot.setStatus(True)
                    bot.setColor(colorT=self.enemyColor)
                    self.draw_player_circle(self.frameResult, bot)
                    self.draw_player_virtual(bot)
                    self.enemiesCount += 1

            # --- ALIADOS ---
            elif mainColorContours and self.alliesCount < 3:
                contour = max(mainColorContours, key=cv2.contourArea)
                (_, _), rc = cv2.minEnclosingCircle(contour)
                if rc >= 0.3 * mainColorRadius:
                    tim = self.timer.getElapsedTime()
                    # checa qual tipo de robô aliado é
                    ally_checks = [
                        (not AgoalFlag, self.goalAllyColor1, self.goalAllyColor2, ID_Robots.ROBOT_ALLY_GOAL, "Goleiro"),
                        (not Aatk1Flag, self.atk1AllyColor1, self.atk1AllyColor2, ID_Robots.ROBOT_ALLY_1, "Atacante 1"),
                        (not Aatk2Flag, self.atk2AllyColor1, self.atk2AllyColor2, ID_Robots.ROBOT_ALLY_2, "Atacante 2"),
                    ]

                    for flag, c1, c2, bot_id, _ in ally_checks:
                        if flag and self.detect_ally_robot(windowActual, c1, c2):
                            bot = self.allyTeam[bot_id]
                            bot.setPosition(xcm, ycm, rcm, windowActual, time=tim)
                            bot.updtPositionImg(xi, yi, ri)
                            bot.setStatus(True)
                            bot.setColor(colorT=self.allyColor, colorP=c1, colorS=c2)
                            self.draw_player_circle(self.frameResult, bot)
                            self.draw_player_virtual(bot)
                            if bot_id == ID_Robots.ROBOT_ALLY_GOAL:
                                AgoalFlag = True
                            elif bot_id == ID_Robots.ROBOT_ALLY_1:
                                Aatk1Flag = True
                            else:
                                Aatk2Flag = True
                            break  # evita detectar o mesmo robô mais de uma vez

                    # debug: seta de direção
                    if debug and self.allyTeam[self.alliesCount].getStatus():
                        dx, dy = self.allyTeam[self.alliesCount].direction[:2]
                        h = 30
                        if dx == 0 and dy == 0:
                            Dx = Dy = 0
                        else:
                            theta = np.arctan2(dy, dx)
                            Dx, Dy = h * np.cos(theta), h * np.sin(theta)
                        cv2.arrowedLine(self.frameResult, (int(xi), int(yi)), (int(xi + Dx), int(yi + Dy)), (0, 255, 0), 2)

                    self.alliesCount = min(self.alliesCount + 1, 3)

            self.playersCount += 1

        # Incrementa contador de processamento
        self._countProcess += 1





        def detect_ally_robot(self, window, colorP, colorS):
        """
        Verifica se há um robô aliado dentro de uma janela (BGR),
        com base em duas cores (primária e secundária) definidas em HSV.

        Retorna:
            bool: True se ambas as cores forem detectadas, False caso contrário.
        """
        try:
            if window is None or window.size == 0:
                print("[detect_ally_robot] Janela inválida ou vazia.")
                return False

            # Conversão BGR -> HSV apenas uma vez
            windowHSV = cv2.cvtColor(window, cv2.COLOR_BGR2HSV)

            # Cria limites HSV das duas cores
            p_lower, p_upper = self.create_color_bounds(colorP)
            s_lower, s_upper = self.create_color_bounds(colorS)

            # Máscaras das duas cores
            binaryP = cv2.inRange(windowHSV, np.array(p_lower), np.array(p_upper))
            binaryS = cv2.inRange(windowHSV, np.array(s_lower), np.array(s_upper))

            # Elemento estruturante
            structuringElement = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

            # Fechamento para unir regiões próximas (sem erosão inicial)
            binaryP = cv2.morphologyEx(binaryP, cv2.MORPH_CLOSE, structuringElement)
            binaryS = cv2.morphologyEx(binaryS, cv2.MORPH_CLOSE, structuringElement)

            # Erosão leve apenas se houver ruído (muitos contornos pequenos)
            for mask in [binaryP, binaryS]:
                contours_tmp, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if len(contours_tmp) > 15:
                    mask = cv2.erode(mask, structuringElement, iterations=1)

            # Encontra contornos finais
            contoursP, _ = cv2.findContours(binaryP, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contoursS, _ = cv2.findContours(binaryS, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Raio mínimo adaptativo (evita perder marcadores pequenos como o do goleiro)
            min_radius = max(2, 0.08 * getattr(self, "secColorRadius", 10))

            # Verifica se há contornos válidos
            primaryFound = any(cv2.minEnclosingCircle(c)[1] >= min_radius for c in contoursP)
            secondaryFound = any(cv2.minEnclosingCircle(c)[1] >= min_radius for c in contoursS)

            return primaryFound and secondaryFound

        except Exception as e:
            print(f"[detect_ally_robot] Erro ao processar imagem: {e}")
            return False