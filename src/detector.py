# ==========================================================================================
# MÓDULO DE FUNÇÕES PARA ALGORÍTMO DE DETECÇÃO VSS
#===========================================================================================
'''
    Obs: O módulo é divido em três tipos de funções de identificação, em ordem de Hierarquia:
    1- Funções Principais
    2- Funções Modulares
    3- Funções Auxiliares.
    
    Funções principais são construídas à partir de funções modulares que são construídas com
    Funções auxiliares (o grau mais baixo).
    
    Funções principais executam tarefas gerais em específico, como identificar todos os robôs
    e suas equipes, Identificar a bola, identificar os extremos do campo. Além de tratamento
    de erros.
    
    Além da definição dos módulo, também é definido os objetos que irão funcionar como abstração
    com o mundo real: robôs, bola e campo.
'''
#importando bibliotecas necessárias para o código
import cv2
import numpy as np

#======================|| DEFINIÇÕES DE CLASSES ||======================================#

class Robot:
    def __init__(self, id, team, x, y, r, image):
        self.id = id
        self.team = team
        self.position = np.array([round(x, 2), round(y, 2)])
        self.radius = round(r, 2)
        self.direction = np.array([0, 0])
        self.detected = False
        self.image = cv2.imread('src/images/dark_screen.png')

    def update_position(self, x, y, r, image):
        self.position = np.array([round(x, 2), round(y, 2)])
        self.radius = round(r, 2)
        self.image = image

    def update_direction(self, dirX, dirY):
        self.direction = np.array([dirX, dirY])

    def set_status(self, status):
        self.detected = status


    # def __init__(self, id, equipe="default", posX=0, posY=0, raio=0):
    #     #Setando atributos necessários para gerar um objeto do tipo robô
    #     self.id = id                                                 #Identificador do robô
    #     self.team = str(equipe)                                           #Nome da Equipe
    #     self.pos = np.array([int(posX), int(posY)])                       #Vetor posição na imagem
    #     self.vel = np.array([0, 0])                                       #Vetor velocidade na imagem
    #     self.radio = int(raio)                                            #Raio do circulo envolvente
    #     self.dir = np.array([0, 0])                                       #Vetor direção na imagem
    #     self.team_center = np.array([0, 0])                               #Centro da cor da equipe
    #     self.window = np.array([[0,0], [0, 0], [0,0], [0,0]])             #Coordenadas da janela na imagem original
    #     self.CV2Perspective = None                                        #Perspectiva do openCV do carro
    
    # #Atualizando a posição do robô
    # def update_position(self, posX, posY, colorX, colorY):
    #     self.pos = np.array([int(posX), int(posY)])
    #     self.team_center = np.array([int(colorX), int(colorY)])
        
    #     #Atualizando a direção do robô
    #     #(x,y) é o vetor diferença entre a posição da cor do robô e a posição centrla do robô
    #     x = abs(posX - colorX)
    #     y = abs(posY - colorY)

    #     #Aplicando transformação para definir a direção real do robô
    #     dirX = (x+y)*np.sqrt(2)/2*5
    #     dirY = (-x+y)*np.sqrt(2)/2*5
        
    #     #Observação: Aqui é preciso transformar num vetor unitário
        
    #     #Definindo a direção atual em que o robô se encontra
    #     self.dir = np.array([int(dirX), int(dirY)])
        
    #Adicionando as informações da perspectiva do OpenCV
    #Informações da perspectiva para o openCV
    # def set_cv2Perspective(self, perspective):                              
    #     self.CV2Perspective = perspective
    
    # #Função de debug para imprimir informações do robô
    # def infos(self):
    #     info_str='''
    #         =======================
    #         |Informações do robô {}|
    #         Equipe: {}
    #         Posição: {}
    #         Velocidade: {}
    #         Raio: {}
    #         =======================
    #     '''.format(self.id, self.team,self.pos, self.vel, self.radio)
    #     print(info_str)
    
    # #Adicionando a informação da janela na imagem cuja posição está o robô
    # def set_window(self, x, y, w, h):
    #     self.window = np.array([[x, y], [x, y+h], [x+w, y+h], [x+w, y]])
        
        
#classe que identifica a bola
class Ball:
    def __init__(self, x, y, r):
        self.position = np.array([int(x), int(y)])
        self.radius = int(r)
        self.direction = np.array([0, 0])

    def update_position(self, x, y, r):
        self.position = np.array([int(x), int(y)])
        self.radius = r

    def set_direction(self, last_position, current_position):
        dx = current_position[0] - last_position[0]
        dy = current_position[1] - last_position[1]
        mod = np.sqrt(dx**2 + dy**2)

        dx = dx/mod
        dy = dy/mod

        self.direction = np.array([dx, dy])

#Definição da classe campo
class Field:

    #Métodos
    def __init__(self,):
        self.window = np.array([[0,0], [0, 0], [0,0], [0,0]])             #Coordenadas da janela na imagem original
    
    #mudar a posição
    def updatePosition(self, ):
        return 0

#======================|| FUNÇÕES AUXILIARES ||=========================================#
'''
    Obs: Funções auxiliares são funções que realizam tarefas básicas que serão
    repetidas diversas vezes no código. Portanto, utilizando elas, será possível gerar
    funções mais complexas que terão um nível mais alto, facilitando a leitura do código.
'''
#Carregar imagem
def load_image(imagePath):
    return cv2.imread(imagePath)

#Transformar em tons de cinza (que seja inicialmente RGB)
def gray_scale(img):
    return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

#Aplicar o filtro mediana para possíveis ruídos
def median_blur(image, kernelSize=3):
    return cv2.medianBlur(image, kernelSize)

#Binariza a imagem indo de um limiar até 255
def binarize_Up(image, threshold=150):
    _, binarized = cv2.threshold(image, threshold, 255, cv2.THRESH_BINARY)
    return binarized

#Tratar ruídos da imagem binarizada
def treat_noise(img, it=1):
    #Elemento estruturante
    elementoEstruturante = cv2.getStructuringElement(cv2.MORPH_CROSS,(3,3))
    
    #Processando imagem
    imagemProcessada = cv2.erode(img, elementoEstruturante, iterations = it)
    
    return imagemProcessada

#Recuperando o objeto de maior área
def get_object(image):
    contours, _ = cv2.findContours(image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    return contours[0]

#Recuperando coordenadas extremas que englobam o maior objeto
def get_perspective(object):
    x,y,w,h = cv2.boundingRect(object)
    return x,y,x+w,y+h
        
#Função para realçar objetos brilhantes na imagem (campo)
def highlight_image(img, dim=25):
    #Operação de topHat para itensificar contrástes
    elementoEstruturante = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dim,dim))

    imgProcessada = cv2.morphologyEx(img, cv2.MORPH_TOPHAT, elementoEstruturante)

    #ajuste de contraste
    imagemTratada = cv2.add(imgProcessada, imgProcessada)
    imagemTratada = cv2.add(imgProcessada, imgProcessada)
    
    return imagemTratada

#Função que irá reduzir a imagem original para pegar o tamanho do campo
## PROBLEMA NESSA FUNÇÃO, POIS AO REDUZIR SURGE ALGUNS BUGS
def reduce_field(BinImg, Img, fieldWidth, prop_px_cm, d=10):
    #Diminuindo a dimensão da imagem para caber apenas o campo
    cont, __ = cv2.findContours(BinImg, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    #objT = cont[0] #Encontra o objeto maior, nesse caso o campo, e então filtrarei a imagem para esse ponto
    objT = max(cont, key=cv2.contourArea)
    contour_area = cv2.contourArea(objT)

    threshold = 50
    
    # print(f"Área do contorno encontrado: {contour_area}")
    if not cont:
        # print("Nenhum contorno encontrado.")
        return BinImg, Img, [0, 0, 0, 0], 1
    
    # if(contour_area > 100000):
    #     bin_Reduce = BinImg
    #     img_Reduce = Img

    try:
        #Obtendo os vértices do retângulo'
        x,y,w,h = cv2.boundingRect(objT) #Coordenadas da noav imagem
        # print(f"Coordenadas da nova imagem: {x},  {y},  {w}, {h}")
        # print(f"offset: {d}")
        #Vetor das coordenadas
        cooVetor = [x,y,w,h]
        pontosIniciais = np.float32([[x-d,y-d],[x+w+d,y-d],[x-d,y+h+d],[x+w+d,y+h+d]])
        novosExtremos = np.float32([[0,0],[w,0],[0,h],[w,h]])

        #Matriz de transformação para nova perspectiva
        matrizPerspectiva = cv2.getPerspectiveTransform(pontosIniciais,novosExtremos)

        #revisando nova imagem para processamento
        img_Reduce = cv2.warpPerspective(Img, matrizPerspectiva, (w,h))
        bin_Reduce = cv2.warpPerspective(BinImg, matrizPerspectiva, (w,h))

    except:
        #Se ele não conseguir, retorna a imagem inicial...
        bin_Reduce = BinImg
        img_Reduce = Img
        prop_px_cm = 1

    hImg = img_Reduce.shape[0]
    wImg = img_Reduce.shape[1]

    if w > threshold and h > threshold:
        pixelWidth = min(w, h)
        prop_px_cm = convert_measures(fieldWidth, pixelWidth)
        # print(f"Largura do campo: {w}. Largura da imagem: {wImg}")
        # print(f"Altura do campo: {h}. Altura da imagem: {hImg}")

    else:
        prop_px_cm = prop_px_cm


    #Retornando a imagem binária e a imagem original já reduzida.
    # print(f"Altura da imagem reduzida: {hImg}")
    # print(f"Largura da imagem reduzida: {wImg}")    
    print("########################################")
    print("w = ", wImg, "h = ", hImg)
    print("Proporção: ", prop_px_cm, " px/cm")
    # print("Altura: ", hImg/prop_px_cm, " cm (28 cm)")

    return bin_Reduce, img_Reduce, cooVetor, prop_px_cm

def convert_measures(w_cm, w_px):

    prop_px_cm = w_px/w_cm

    return prop_px_cm

#Essa função a partir de pontos irá reduzir a imagem original nessa reduzida.
def reduce_window(img, coorVetor, d=10):
    try:
        #recuperando dados do vetor coordenada
        x,y,w,h = coorVetor[0],coorVetor[1],coorVetor[2],coorVetor[3];

        pontosIniciais = np.float32([[x-d,y-d],[x+w+d,y-d],[x-d,y+h+d],[x+w+d,y+h+d]])
        novosExtremos = np.float32([[0,0],[w,0],[0,h],[w,h]])

        #Matriz de transformação para nova perspectiva
        matrizPerspectiva = cv2.getPerspectiveTransform(pontosIniciais,novosExtremos)


        #revisando nova imagem para processamento
        img_Reduce = cv2.warpPerspective(img, matrizPerspectiva, (w,h))

        return img_Reduce
    except:
        #Ocorreu um erro, então retorna a janela já inicial
        return img
    
    
def list_players(teamList):
    amount = len(teamList)

    for i in range(amount):
        print(teamList[i].team, teamList[i].id)
        print("Posição: x =", teamList[i].pos[0], " y =", teamList[i].pos[1])
    
    print("====================")

#Função para identificar equipe
def find_team(windowsCar, colorTeam, colorEnemy):
    #Irá a partir da imagem descobrir se é ou não um carro aliado e inimigo
    # Verifica a cor, e dependendo disso irá retornar 2 valores:
    # 1 -> Aliado
    # 0 -> Inimigo
    # Além disso, retorna o objeto Robô com as informações necessárias.
    
    #Processo de filtragem
    
    return 0

def create_color_bounds(color_array):
    h = color_array[0]
    s = color_array[1]
    v = color_array[2]

    hue_tolerance = 10
    saturation_tolerance = 50
    value_tolerance = 50

    lower_bound = np.array([h - hue_tolerance, max(0, s - saturation_tolerance), max(0, v - value_tolerance)])
    upper_bound = np.array([h + hue_tolerance, min(255, s + saturation_tolerance), min(255, v + value_tolerance)])

    return lower_bound, upper_bound

def find_binary_contours(image, lower_bound, upper_bound):

    imageHSV = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    binaryImage = cv2.inRange(imageHSV, lower_bound, upper_bound)
    #Operações de fechamento e erosão
    structuringElement = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5)) #(20,20) // (5,5)
    binaryImage = cv2.morphologyEx(binaryImage, cv2.MORPH_CLOSE, structuringElement)
    binaryImage = cv2.erode(binaryImage, structuringElement, iterations=1)

    #Encontrando contorno da cor principal
    contours, _ = cv2.findContours(binaryImage, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    return contours

def draw_player_circle(imgDegub, robot, prop_px_cm=1):
    x = robot.position[0]
    y = robot.position[1]
    r = robot.radius

    id = robot.id
    team = robot.team

    xi = int(x*prop_px_cm)
    yi = int(y*prop_px_cm)
    ri = int(r*prop_px_cm)

    if(team == "Aliado"):
        color = (255, 0, 0)
    elif(team == "Inimigo"):
        color = (0, 0, 255)
    else:
        color = (0, 200, 200)

    cv2.circle(imgDegub, (xi, yi), (ri + 5), color, 2)
    text = f"{team} {id}: {str(x)}, {str(y)}"
    cv2.putText(imgDegub, text , (int(xi),int(yi+ri+20)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

#======================|| FUNÇÕES MODULARES ||=========================#
'''
    Obs: Funções módulares são funções mais complexas construídas com
    funções auxiliares. Essas funções módulares funcionarão como blocos
    de código para exercer uma determinada função no algorítmo principal
    definido na função main().
    
    As funções modulares principais são:
    1. detect_field() - Identificar as bordas do campo, e reduz a imagem
    2. detect_cars() - Identificar os carros na figura
    3. detect_ball() - Identificar a bola no campo
    4. detect_team() - Uma função associada a DetectCars() que irá detectar o time
    do robô, para então guardar as informações
    5. detect_direction() - Identificar qual o vetor direção do robô.
    
    
'''

'''
    - Essa função deve a partir da imagem inicial, detectar o campo, e quando detectar deve retornar os pontos
    do campo na imagem original, bem como os pontos do menor retângulo que envolve o campo.
    - Executa até encontrar uma área superior a um valor experimental 100000.
    - Retorna então os vértices desse polígono, bem como o retângulo enclausulante.
'''
#Função para detectar o campo e retornar os pontos extremos dele
def detect_field(img, debug, fieldDimensions, offSetWindow=10, offSetErode=0, dimMatrix=25, Trashhold = 235):

    fieldWidth = fieldDimensions[0] #largura do campo em cm
    fieldHeight = fieldDimensions[1] #altura do campo em cm

    h = img.shape[0]
    w = img.shape[1]

    pixelWidth = min(w, h)
    prop_px_cm = convert_measures(fieldWidth, pixelWidth)
    
    print("################## Antes da função de redução ######################")
    print("w = ", w, "h = ", h)
    print("Proporção: ", prop_px_cm, " px/cm")
    # print("Altura: ", h/prop_px_cm, " cm (28 cm)")

    while offSetErode <20:
        try:
            #frame original
            frameOrig = img.copy()

            #Tomando a imagem em tons de cinza
            gray = gray_scale(frameOrig)

            #Aplica filtro de mediana para diminuir ruídos
            blur = median_blur(gray, 3)

            #Realça objetos brilhantes, que nesse caso é o campo
            imagemTratada = highlight_image(blur, dimMatrix)

            #Binarizando a imagem num limiar
            binary = binarize_Up(imagemTratada,Trashhold)

            #Tratando ruídos da imagem binarizada
            binary_treat = treat_noise(binary,offSetErode)
            
            #Reduzindo imagem:
            binary_treat_reduce, frame_reduce, coorVetor, prop_px_cm = reduce_field(binary_treat, frameOrig, fieldWidth, prop_px_cm, offSetWindow)

            #Encontra extremos do paralelogramo
            contours, _ = cv2.findContours(binary_treat_reduce, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            #Variável para retornar os vértices
            rect_vertices = np.array([0,0,0,0], dtype=np.int32)

            # Loop através dos contornos encontrados
            for contour in contours:
                # print("Contornos encontrados")
                # Aproximar o contorno para um polígono com poucos vértices
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)

                # Se o polígono tem 4 vértices, então é um retângulo
                if len(approx) == 4:
                    try:
                        # Extrair os vértices do retângulo [1 2 3 4]
                        rect_vertices = np.array([approx[0][0], approx[1][0], approx[2][0], approx[3][0]], dtype=np.int32)
                        
                        # pontosIniciais = np.float32([[x-d,y-d],[x+w+d,y-d],[x-d,y+h+d],[x+w+d,y+h+d]])
                        # novosExtremos = np.float32([[0,0],[w,0],[0,h],[w,h]])
                        #coor vetor: [x,y,w,h]
                        dd = offSetWindow
                        #Vértices reais na imagem real
                        rect_vertices_true = rect_vertices+np.array([[coorVetor[0]-dd,coorVetor[1]-dd], [coorVetor[0]-dd,coorVetor[1]+dd], [coorVetor[0]+dd,coorVetor[1]+dd], [coorVetor[0]+dd,coorVetor[1]-dd]], dtype=np.int32)
                    
                        if(debug == 'true'):
                            # Desenhar os vértices do retângulo na imagem original
                            cv2.polylines(frameOrig, [rect_vertices_true], True, (0, 0, 255), 4)
                            # print("Vértices:")
                            # Desenhar círculos nos vértices do retângulo
                            for vertex in rect_vertices_true:
                                x, y = vertex
                                # print(f"x = {x}, y = {y}")
                                cv2.circle(frameOrig, (x, y), 4, (0, 255, 0), -1)

                    except:
                        print("não consguiu desenhar")
                        pass
            # Se chegou até aqui sem erros, retorna os vértices do retângulo
            return binary_treat, frameOrig, rect_vertices_true, frame_reduce, prop_px_cm
        
        except: #Trata os erros em geral... Provavelmente gerará um bug!
            # Se ocorrer algum erro, incrementa o valor de offSetErode e tenta novamente
            offSetErode += 1
            return binary_treat, frameOrig, np.array([-1,-1,-1,-1],dtype=np.int32), img, prop_px_cm

#Função para detectar bola
def detect_ball(img, color, ball, prop_px_cm, debug):
    
    frameOrig = img.copy()

    #Cor laranja da bola - depois colocar fora da função
    h = color[0]
    s = color[1]
    v = color[2]

    hue_tolerance = 6
    saturation_tolerance = 50
    value_tolerance = 50

    ball_lower_bound = np.array([h - hue_tolerance, max(0, s - saturation_tolerance), max(0, v - value_tolerance)])
    ball_upper_bound = np.array([h + hue_tolerance, min(255, s + saturation_tolerance), min(255, v + value_tolerance)])

    imgHSV = cv2.cvtColor(frameOrig, cv2.COLOR_BGR2HSV)
    binaryBall = cv2.inRange(imgHSV, ball_lower_bound, ball_upper_bound)

    #Operações de erosão e fechamento
    structuringElement = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)) #(8,8)
    binaryBall = cv2.morphologyEx(binaryBall, cv2.MORPH_CLOSE, structuringElement)
    binaryBall = cv2.erode(binaryBall, structuringElement, iterations=1 )
    
    #Encontrando contornos da bola
    contours, _ = cv2.findContours(binaryBall, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        ballContour = max(contours, key=cv2.contourArea)
        (xb, yb), rb = cv2.minEnclosingCircle(ballContour)

        xcm = xb/prop_px_cm
        ycm = yb/prop_px_cm
        rcm = rb/prop_px_cm

        if ball is None:
            ball = Ball(xcm, ycm, rcm)
        else:
            ball.set_direction(ball.position, np.array([xcm, ycm]))
            ball.update_position(xcm, ycm, rcm)

        if (debug == 'true'):

            rb = int(rb)
            xb = int(xb)
            yb = int(yb)

            # Circulando bola
            cv2.circle(frameOrig, (xb, yb), (rb + 2), (0, 0, 255), 2)
            text = f"Bola: {str(ball.position[0])}, {str(ball.position[1])}"
            cv2.putText(frameOrig, text, (int(xb),int(yb+rb+15)), cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,255), 1)
            cv2.arrowedLine(frameOrig, (xb, yb), ((xb + int(ball.direction[0])), (yb + int(ball.direction[1]))), (0, 255, 0), 2)
            
    else:
        ball = Ball(0, 0, 0)
                   
    return frameOrig, ball, binaryBall

#Função para detectar carros
def detect_players(img, ballImg, binaryBall, binaryField, alliesColor, enemiesColor, playersAllColors, prop_px_cm, ball_object, allies_list, enemies_list, d, rect_vertices, debug):
    
    #==========================================================================================
    #Cria uma cópia da imagem reduzida para debug 
    imgDegub = ballImg

    # print(rect_vertices)
    # cv2.circle(imgDegub, (rect_vertices[0][0], rect_vertices[0][1]), (5), (0, 0, 255), 2)
    # cv2.circle(imgDegub, (d, d), (5), (0, 0, 255), 2)
    # cv2.circle(imgDegub, (d, d), (5), (0, 0, 255), 2)
    # cv2.circle(imgDegub, (d, d), (5), (0, 0, 255), 2)

    initial = [30*prop_px_cm, 30*prop_px_cm]
    final = [30*prop_px_cm, 37.5*prop_px_cm]

    cv2.line(imgDegub, (int(initial[0]), int(initial[1])), (int(final[0]), int(final[1])), (255, 0, 0), 2)
    #==========================================================================================
    #Cria variáveis e vetores de contagem dos jogadores 
    #Janela dos jogadores
    playersWindows = [None, None, None, None, None, None]
    playersWindowsBinary = []

    alliesWindows = [None, None, None]
    enimiesWindows = [None, None, None]

    robots = [None, None, None, None, None, None]

    playersCount = 0
    alliesCount = 0
    enemiesCount = 0

    for i in range(3):
        if allies_list[i] is not None:
            allies_list[i].set_status(False)

    for i in range(3):
        if enemies_list[i] is not None:
            enemies_list[i].set_status(False)
                
    #==========================================================================================
    #Carrega os vetores de cores claras e escuras de objetos gerais 
    objectsDarkColor = np.array([0,10,130]) #[0,10,150]
    objectsLightColor = np.array([179,255,255])

    #==========================================================================================
    #Carrega os vetores de cores claras e escuras do time aliado

    ally_lower_bound, ally_upper_bound = create_color_bounds(alliesColor)
    enemy_lower_bound, enemy_upper_bound = create_color_bounds(enemiesColor)

    #==========================================================================================
    #Converte a imagem para o espaço HSV
    imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    #==========================================================================================
    #Cria uma máscara para os objetos da imagem
    objects = cv2.inRange(imgHSV, objectsDarkColor, objectsLightColor)

    #==========================================================================================
    #Exclui a bola dos objetos identificados
    binaryPlayers = cv2.subtract(objects, binaryBall)
    
    #==========================================================================================
    #Realiza operações de fechamento e erosão para melhorar os jogadores detectados

    structuringElement = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binaryPlayers = cv2.erode(binaryPlayers, structuringElement, iterations=1)

    structuringElement = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
    binaryPlayers = cv2.morphologyEx(binaryPlayers, cv2.MORPH_CLOSE, structuringElement)

    binaryTeam = binaryPlayers

    #Reconhecimento de jogadores
    binaryAllTeam = cv2.inRange(imgHSV, ally_lower_bound, ally_upper_bound) #Por enquanto, isso  não faz nada, só exibe na tela de debug todo o time reconhecido

    #==========================================================================================
    #Encontra os contornos de todos os jogadores
    structuringElement = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5)) #(20,20) // (5,5)
    # binaryPlayers = cv2.morphologyEx(binaryPlayers, cv2.MORPH_CLOSE, structuringElement)
    players, _ = cv2.findContours(binaryPlayers, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    #NOVA FUNÇÃO PARA RECONHECIMENTO DE JOGADORES

    playerRadius = (7.5/2)*np.sqrt(2)*prop_px_cm
    mainColorRadius = (7.5/4)*np.sqrt(5)*prop_px_cm
    secColorRadius = (playerRadius/2)

    # print("Raio do jogador: ", playerRadius)
    # print("Raio da cor principal: ", mainColorRadius)

    for currentPlayer in players:
        #Encontrando posição de cada um dos carros identificados
        (xi,yi), ri = cv2.minEnclosingCircle(currentPlayer)

        # xcm = xi/prop_px_cm
        # ycm = yi/prop_px_cm
        # rcm = ri/prop_px_cm


        # playerRadius = 24
        # secColorRadius = playerRadius/2

        # print("Raio do jogador: ", playerRadius)
        # print("Raio encontrado: ", ri/prop_px_cm)


        #Objetos com raios maiores que certo valor serão considerados como jogadores
        if(ri > 0.75*playerRadius and ri < 1.5*playerRadius and playersCount < 6): #4*prop_px_cm
            cv2.circle(imgDegub, (int(xi), int(yi)), (int(ri) + 5), (0, 255, 0), 2)

            #Traçando janelas (winSize x winSize)
            # winSize = int(200) #18*prop_px_cm
            winSize = int(18*prop_px_cm) #18*prop_px_cm
            # print("Tamanho da janela: ", winSize)
            initPt = np.float32([[xi-(winSize/2),yi-(winSize/2)],[xi+(winSize/2),yi-(winSize/2)],[xi-(winSize/2),yi+(winSize/2)],[xi+(winSize/2),yi+(winSize/2)]])
            endPt = np.float32([[0,0],[winSize,0],[0,winSize],[winSize,winSize]])

            #Matriz de transformação para nova perspectiva
            perspecMatrix = cv2.getPerspectiveTransform(initPt, endPt)

            playersWindows[playersCount] = (cv2.warpPerspective(img, perspecMatrix, (winSize,winSize)))

            mainColorContours = find_binary_contours(playersWindows[playersCount], ally_lower_bound, ally_upper_bound)
            enemyColorContours = find_binary_contours(playersWindows[playersCount], enemy_lower_bound, enemy_upper_bound)

            # print(f"Quantidade de contornos de inimigos: {len(enemyColorContours)}")
            
            if not mainColorContours:
                
                if enemyColorContours:
                    enemyColorContour = max(enemyColorContours, key=cv2.contourArea)
                    (xc, yc), rc = cv2.minEnclosingCircle(enemyColorContour)

                    # print("Raio da cor principal inimigo: ", rc)

                    xc = int(xc)
                    yc = int(yc)
                    rc = int(rc)

                    if(rc >= 0.5*mainColorRadius and enemiesCount < 3):

                        xcm = xi/prop_px_cm
                        ycm = yi/prop_px_cm
                        rcm = ri/prop_px_cm

                        id = "1"+str(enemiesCount+1)
                        if enemies_list[enemiesCount] is None:
                            robot = Robot(id, "Inimigo", xcm, ycm, rcm, playersWindows[playersCount])
                            robot.set_status(True)
                            enemies_list[enemiesCount] = robot
                        
                        else:
                            robot = enemies_list[enemiesCount]
                            robot.update_position(xcm, ycm, rcm, playersWindows[playersCount])
                            robot.set_status(True)

                        robots[playersCount] = (robot)
                        enimiesWindows[enemiesCount] = (playersWindows[playersCount])

                        playerCenterX = winSize/2
                        playerCenterY = winSize/2

                        dx = playerCenterX - xc
                        dy = playerCenterY - yc

                        robot.update_direction(dx, dy)
                        
                        xi = int(xi)
                        yi = int(yi)
                        ri = int(ri)

                        # cv2.circle(imgDegub, (xi, yi), (ri + 5), (0, 0, 255), 3)
                        # text = "Inimigo: " + str(xi) + ", " + str(yi)
                        # cv2.putText(imgDegub, text , (int(xi),int(yi+ri+20)), cv2.FONT_HERSHEY_SIMPLEX,0.4,(0, 0, 255), 1)

                        if(debug == 'true'): draw_player_circle(imgDegub, robot, prop_px_cm)

                        enemiesCount += 1

            else:
                mainColorContour = max(mainColorContours, key=cv2.contourArea)

                #for currentMainColor in mainColorContour:
                (xc, yc), rc = cv2.minEnclosingCircle(mainColorContour)

                # print("Raio da cor principal: ", rc)

                xc = int(xc)
                yc = int(yc)
                rc = int(rc)

                print(f"Raio da cor principal: {mainColorRadius} - {rc}")

                if(rc >= 0.5*mainColorRadius and alliesCount < 3):
                    #Aqui deve se iniciar a busca por jogadores únicos, verificando suas cores secundárias
                    ally_id = 0
                    for i in range(3):
                        firstColorFound = False
                        secondColorFound = False

                        first_lower_bound, first_upper_bound = create_color_bounds(playersAllColors[i][0])
                        firstColorContours = find_binary_contours(playersWindows[playersCount], first_lower_bound, first_upper_bound)
                        if firstColorContours:
                            firstColorContour = max(firstColorContours, key=cv2.contourArea)
                            (xc1, yc1), rc1 = cv2.minEnclosingCircle(firstColorContour)
                            print(f"rc1: {rc1}")
                            print(f"seccolorradiu: {secColorRadius}")
                            if rc1 >= 0.4*secColorRadius: firstColorFound = True

                        second_lower_bound, second_upper_bound = create_color_bounds(playersAllColors[i][1])
                        secondColorContours = find_binary_contours(playersWindows[playersCount], second_lower_bound, second_upper_bound)
                        if secondColorContours:
                            secondColorContour = max(secondColorContours, key=cv2.contourArea)
                            (xc2, yc2), rc2 = cv2.minEnclosingCircle(secondColorContour)
                            if rc2 >= 0.4*secColorRadius: secondColorFound = True

                        if firstColorFound and secondColorFound: ally_id = (i+1)

                    
                    id = "0"+str(ally_id)
                    xcm = xi/prop_px_cm
                    ycm = yi/prop_px_cm
                    rcm = ri/prop_px_cm

                    if ally_id != 0:
                        if allies_list[ally_id-1] is None:
                            robot = Robot(id,  "Aliado", xcm, ycm, rcm, playersWindows[playersCount])
                            robot.set_status(True)
                            allies_list[ally_id-1] = robot
                        
                        else:
                            robot = allies_list[ally_id-1]
                            robot.update_position(xcm, ycm, rcm, playersWindows[playersCount])
                            robot.set_status(True)

                        robots[playersCount] = (robot)
                        alliesWindows[alliesCount] = (playersWindows[playersCount])

                        #Conversão de coordenadas, da janela para a geral
                        xi = int(xi)
                        yi = int(yi)
                        ri = int(ri)

                        xci = int(xi - (winSize/2) + xc)
                        yci = int(yi - (winSize/2) + yc)

                        if(debug == 'true'): draw_player_circle(imgDegub, robot, prop_px_cm)

                        # cv2.circle(imgDegub, (xci, yci), (rc + 5), (0, 255, 0), 2)
                        # cv2.putText(imgDegub,"Cor", (int(xci+5),int(yci+5)), cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,255,0), 1)

                        # xb = ball_object.position[0]
                        # yb = ball_object.position[1]
                        # cv2.arrowedLine(imgDegub, (xi, yi), (xb, yb), (0, 50, 200), 2)

                        #Calculando centro da janela de cada jogador
                        playerCenterX = winSize/2
                        playerCenterY = winSize/2

                        dx = playerCenterX - xc
                        dy = playerCenterY - yc

                        robot.update_direction(dx, dy)

                        h = 50
                        if(dx > 0):
                            angular_coef = dy/dx
                            theta = np.arctan(angular_coef)
                            Dx = h*np.cos(theta)
                            Dy = h*np.sin(theta)
                        elif(dx < 0):
                            angular_coef = dy/dx
                            theta = np.arctan(angular_coef)
                            Dx = -(h*np.cos(theta))
                            Dy = -(h*np.sin(theta))
                        else:
                            Dx = 0
                            Dy = h

                        xi = int(xi)
                        yi = int(yi)
                        ri = int(ri)

                        if(debug == 'true'):
                            cv2.arrowedLine(imgDegub, (xi, yi), (xi+int(Dx), yi+int(Dy)), (0,255,0), 2)
                            # cv2.circle(imgDegub, (xi, yi), (ri + 5), (255, 0, 0), 2)

                        alliesCount += 1

                else:

                    if enemyColorContours:
                        enemyColorContour = max(enemyColorContours, key=cv2.contourArea)
                        (xc, yc), rc = cv2.minEnclosingCircle(enemyColorContour)

                        # print("Raio da cor principal inimigo: ", rc)

                        xc = int(xc)
                        yc = int(yc)
                        rc = int(rc)

                        if(rc >= 0.5*mainColorRadius and enemiesCount < 3):

                            id = "1"+str(enemiesCount+1)
                            xcm = xi/prop_px_cm
                            ycm = yi/prop_px_cm
                            rcm = ri/prop_px_cm

                            if enemies_list[enemiesCount] is None:
                                robot = Robot(id,  "Inimigo", xcm, ycm, rcm, playersWindows[playersCount])
                                robot.set_status(True)
                                enemies_list[enemiesCount] = robot
                            
                            else:
                                robot = enemies_list[enemiesCount]
                                robot.update_position(xcm, ycm, rcm, playersWindows[playersCount])
                                robot.set_status(True)

                            robots[playersCount] = (robot)
                            enimiesWindows[enemiesCount] = (playersWindows[playersCount])

                            playerCenterX = winSize/2
                            playerCenterY = winSize/2

                            dx = playerCenterX - xc
                            dy = playerCenterY - yc

                            robot.update_direction(dx, dy)
                        
                            xi = int(xi)
                            yi = int(yi)
                            ri = int(ri)

                            # cv2.circle(imgDegub, (xi, yi), (ri + 5), (0, 0, 255), 3)
                            # text = "Inimigo: " + str(xi) + ", " + str(yi)
                            # cv2.putText(imgDegub, text , (int(xi),int(yi+ri+20)), cv2.FONT_HERSHEY_SIMPLEX,0.4,(0, 0, 255), 1)

                            if(debug == 'true'): draw_player_circle(imgDegub, robot, prop_px_cm)

                            enemiesCount += 1
            
            # print(f"QUANTIDADE DE JOGADORES: {playersCount}")
            playersCount += 1

    return imgDegub, binaryPlayers, binaryAllTeam, playersCount, alliesCount, enemiesCount, playersWindows, alliesWindows, enimiesWindows, allies_list, enemies_list, robots

#Identificando se o bloco está sendo utilizado como script e não módulo
if  __name__=='__main__':
    print("O módulo está sendo executado como principal")