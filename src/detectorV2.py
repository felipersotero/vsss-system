# ==========================================================================================
# MÓDULO DE FUNÇÕES PARA ALGORÍTMO DE DETECÇÃO VSS (V2.0)
#==========================================================================================
'''
    @GNOMIO: O algorítmo de detecção terá agora uma nova lógica de programação, no qual ele é conti-
    tuído de uma classe 'detector' responsável por realizar.
    Os cálculos serão acelerados utilizando a GPU. Para isso utiliza a bibliteca OpenCV com 
    base na plataforma cuda, e usa também a cupy para realizar cálculos da biblioteca
    numpy na GPU do computador.

    Necessário configurar CMAKE e etc para utilizar essa interface.
'''
#importando bibliotecas necessárias para o código
import cv2
import numpy as np
from objects import *
from timer import *
import threading
import queue
import modules
#======================|| DEFINIÇÕES DE CLASSES ||======================================#
'''
@GNOMIO: Classe Robot que será utilizada no algorítmo de detecção para representar os robôs
As características do robô são:
    id - identificador do robô
    team - time do robô
    position - Posição do robô no campo
    radius - Seria necessário para o procedimento de detectar colisão
    direction - direção na qual o robô está apontando
    image - imagem que representa o robô no momento que foi detectado;

'''


# ====================== DEFINIÇÕES DAS CLASSES DE OBJETO DO SISTEMA ==================

#Classe do robô
class Robot:
    def __init__(self, id:ID_Robots, team:ID_Team, x, y, r, image=cv2.imread('src/images/dark_screen.png'),colorTeam = None,colorCar = None):
        #informando identificador
        self.id = id
        self.dimMatrix = 100
        #informando time
        self.team = team
        self.position = np.array([round(x, 2), round(y, 2)])

        #informações de posição para cálculo da velocidade
        self.lastPosition = self.position
        self.newPosition = self.position 
        self.direction = np.array([round(x, 2), round(y, 2)])
        self.velocity = np.array([0,0])

        #Janela que informa a posição do jogador
        #informando raio de border box 
        self.viewRect = ViewBot(Point2D(self.position[0],self.position[1]), self.dimMatrix)

        #"raio" associado à borda do jogador
        self.radius = round(r, 2)

        #Gerando objeto de informações
        self.objLimit = Circle(self.radius,Point2D(x,y))

        #Gerando uma bbox para sistema de colisões
        self.bbox = BorderBox(GeometryType.CIRCLE,self.objLimit)
        self.ObjType = ObjTypeMove.MOVING
        self.objTypeSystem = ObjTypeVision.ROBOT


        #informa se foi detectado pelo sistema
        self.detected = False

        #informa se o carro detem a bola
        self.possessionBall = False

        #imagem de detecção do carro
        self.botViewImg = image

        #informando cor (Em código HSV, falta converter)
        self.colorTeam = colorTeam
        self.colorCar = colorCar

    #Atualizar posição do robô
    def updatePosition(self, x, y, r, image):
        #Atualiza ultima posição
        self.lastPosition = self.position

        self.position = np.array([round(x, 2), round(y, 2)])
        self.radius = round(r, 2)
        self.image = image

        #Atualiza nova posição
        self.newPosition = self.position 

        #Calcula o vetor deslocamento (direção)
        self.direction = self.newPosition - self.lastPosition
        
        #Atualizando posição da borderbox
        self.updateBbox()

    #Atualizar informações do robÕ
    def setStatus(self, status):
        self.detected = status

    #informando cores do carro
    def setColor(self, colorTeam, colorCar):
        self.colorTeam = colorTeam
        self.colorCar = colorCar

    #informando raio da borda do carro
    def setRadius(self, radius):
        self.radio = radius

    #informando qual a velocidade do objeto
    def getVelocity(self, timestamp):
        if timestamp != 0: self.velocity = self.direction / timestamp
        else:
            self.velocity = 0

        return self.velocity
    
    #Atualiza borderbox
    def updateBbox(self):
        #Gerando objeto de informações
        self.objLimit = Circle(Point2D(self.position[0],self.position[1]),self.radius)

        #Gerando uma bbox para sistema de colisões
        self.bbox = BorderBox(GeometryType.CIRCLE,self.objLimit)

    # prever posição do carro com base na velocidade dele
    # timestamp é o tempo que se passou do ultimo processamento até agora
    # necessário uma classe time para realizar essa lógica
        
    #atualiza quadro de predição do robô
    def predictPosition(self, timestamp):
        #passo para transport a tela que representa a posição do robô
        stepPosition = self.velocity * timestamp

        #transfiro os pontos de identificação para a posição prevista
        self.viewRect.translateViewBot(Point2D(stepPosition[0],stepPosition[1]))

    #recupera o ponto que devo procurar na imagem para encontrar o carro
    # levando em consideração o passo interno do viewRect (dimMatrix)
    def getPredictPosition(self):
        return self.viewRect.Pe1
    
    
'''
@GNOMIO:A classe bola é responsável por pegar informações do objeto bola que será utilizado no processo de detecção
'''
class Ball:
    def __init__(self, x, y, r):
        #posição, raio e direção da boal
        self.position = np.array([int(x), int(y)])
        self.radius = int(r)
        self.direction = np.array([0, 0])

        #gerando bbox para sistema de colisão
        self.objLimit = Circle(Point2D(x,y),self.radius)
        self.bbox = BorderBox(GeometryType.CIRCLE, self.objLimit)

        #Informações do tipo de objeto no sistema
        self.ObjType = ObjTypeMove.MOVING
        self.objTypeSystem = ObjTypeVision.BALL
        
        #informações de posição para cálculo da velocidade
        self.lastPosition = self.position
        self.newPosition = self.position 

    #atualizando posição da bola
    def updatePosition(self, x, y,r):
        #Atualizando raio
        self.radius = int(r)

        #Atualizando posições do sistema
        self.lastPosition = self.position
        self.newPosition = np.array([int(x), int(y)])

        #atualizando direção
        self.direction = self.newPosition - self.lastPosition

        #Atualizando posição da borderbox
        self.updateBbox()

    #recuperando a velocidade da bola
    def getVelocity(self, timestamp):
        if timestamp != 0: self.velocity = self.direction / timestamp
        else:
            self.velocity = np.array[0,0]

        return self.velocity
    
    #Atualiza borderbox
    def updateBbox(self):
        #Gerando objeto de informações
        self.objLimit = Circle(Point2D(self.position[0],self.position[1]),self.radius)

        #Gerando uma bbox para sistema de colisões
        self.bbox = BorderBox(GeometryType.CIRCLE,self.objLimit)


#Definição da classe campo
'''
@GNOMIO: A classe campo é responsável por dar uma visão geral ao sistema de detecção, para poder enquadrar o campo dentro da lógica
O objeto field terá informações dos jogadores e dos extremos do campoa
'''
#Classe do campo
class Field:
    def __init__(self):
        #pontos importantes no campo
        self.pivots = [Pivot(id=ID_Pivots.CENTER),Pivot(id=ID_Pivots.PA1),Pivot(id=ID_Pivots.PA2),Pivot(id=ID_Pivots.PA3),Pivot(id=ID_Pivots.PE1),Pivot(id=ID_Pivots.PE3)]
        

        #áreas dos gols dos jogadores
        self.goalArea =[AreaField(id=ID_Field.GOAL_ALLY),AreaField(id=ID_Field.GOAL_ENEMY)]

        #Área dos goleiros
        self.goalRobotArea = [AreaField(id=ID_Field.GOAL_AREA_ALLY),AreaField(id=ID_Field.GOAL_AREA_ENEMY)]

        #@GNOMIO: As posições do Field são em relações à ViewCapture

        #Setando parâmetros do campo
        self.extrems = np.array([[0,0], [0, 0], [0,0], [0,0]])             

        #Informações do tipo de objeto
        self.ObjType = ObjTypeMove.STATIC
        self.objTypeSystem = ObjTypeVision.FIELD
        
    #Atualizar extremos do campo, para realizar cálculos
    def updatePos(self,pos,width,height):
        self.posX=pos[0]
        self.posY=pos[1]
        self.width = width
        self.height = height

    #setar cada um dos pontos de interesse do campo
    def setPivotPos(self,id:ID_Pivots,px,py):
        self.pivots[id].updatePos(px,py)

    #Seta as áreas de gol dos jogadores
    def setAreaGoal(self, id:ID_Field, rect:Rectangle):
        self.goalArea[id].setRect(rect)
        
    #Seta a posição dos goleiros do jogo
    def setAreaRobotGoal(self, id:ID_Field,rect:Rectangle):
        self.goalRobotArea[id].setRect(rect)

    
#======================|| Sistema de detecção POO||======================================#
'''
    Obs: Classe principal da detecção, responsável por realizar todas operações necessárias e métodos
    além do gerenciamento de threads, filas, objetos e memória para processar
    offSetWindow =10, offSetErode = 0 ,dimMatrix = 25, Trashhold = 235
'''
#Vista capturada pelo processamento, que contem a imagem base
class ViewCapture: 
    def __init__(self, Extremes:Rectangle, capture:Capture):
        self.Extremes = Extremes        # Extremos da view
        self.img = capture.img          # Imagem de origem

    #Modificando os extremos em relação à imagem original
    def setViewCapture(self, Extremes:Rectangle):
        self.Extremes = Extremes

    #Retornar os extremos do ViewCapture
    def getExtremes(self):
        return self.Extremes

#===============================================================================================
#Classe principal do sistema de visão que irá executar as funções
class VisionSystem:
    #Inicializando objeto do sistema de detecção
    def __init__(self,config: EConfig, capture: Capture, UseCuda:bool, GPUType:GPUType):
        #Configurando objetos
        self.createObjs()

        #Carregando as configurações do sistema de visão
        self.config = config
        
        #objeto de captura internas
        self._capture = capture

        #Pegando a imagem de origem
        self.imgOrigim = self._capture.getImage()

        #verifica se existe suporte ao CUDA
        self._hasCuda = UseCuda 
        self._GPUType = GPUType


        #variáveis internas utilizadas pela classe de visão 
        self.binImg = None                      # Imagem binarizada necessária
        self.binReduce = None                   # Imagem binarizada reduzida

        #configurações do campo comprimento e largura
        self.fieldWidth = None
        self.fieldHeight = None
        self.prop_px_cm = None                  # proporção pixel para cm


    #Processamento geral da imagem que irá pegar os valores necessários
    def process(self):
       pass

    #Criando os objetos
    def createObjs(self):
        #Construção dos objetos necessários para realizar a análise
        #Objeto da bola
        self.ball = Ball()
        
        #Objeto dos robôs,
        #robôs aliados
        self.robotAllyG = Robot(id=ID_Robots.ROBOT_ALLY_GOAL, team=ID_Team.TEAM_ALLY)
        self.robotAlly1 = Robot(id=ID_Robots.ROBOT_ALLY_1,team=ID_Team.TEAM_ALLY)
        self.robotAlly2 = Robot(id=ID_Robots.ROBOT_ALLY_2,team=ID_Team.TEAM_ALLY)
        
        #robôs inimigos
        self.robotEnemyG = Robot(id=ID_Robots.ROBOT_ENEMY_GOAL,team=ID_Team.TEAM_ENEMY)
        self.robotEnemy1 = Robot(id=ID_Robots.ROBOT_ENEMY_1,team=ID_Team.TEAM_ENEMY)
        self.robotEnemy2 = Robot(id=ID_Robots.ROBOT_ENEMY_2,team=ID_Team.TEAM_ENEMY)

        #Dividindo times
        #time aliado
        self.allyTeam = [self.robotAllyG, self.robotAlly1, self.robotAlly2]

        #time inimigo
        self.enemyTeam = [self.robotEnemyG,self.robotEnemy1,self.robotEnemy2]

        #gerando objeto para representar o campo
        self.field = Field()

        #gerando a viewCapture
        self.viewCapture = ViewCapture()

    #extrair dados vindos do emulador
    def toMineData(self):
        #extrai informações  passadas pelo emulador para poder iniciar o processamento
        pass
    #Método para retornar o processamento
    def getResult(self):
        return True
    
    #método para retornar o processamento
    def getViewCapture(self):
        return self.viewCapture
    
    #escolhe as funções da classe caso tenha ou não suporte ao cuda
    def choseModeFunctions(self):
        pass

    #===============| Definindo funções básicas|==============================
    # ============= métodos sem suporte ao CUDA =====================
    #puxando imagem
    def load_image_noCuda(self, imgPath):
        return cv2.imread(imgPath)
    
    #transformando imagem em tons de cinza
    def gray_scale_noCuda(self,img):
        return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    #aplicando o filtro mediana para possíveis ruídos
    def median_blur_noCuda(self, img, kernelSize = 3):
        return cv2.medianBlur(img, kernelSize)
    
    #binarizando a imagem indo de um limir até 255
    def binarize_up_noCuda(self, img, threshold=150):
        _,bin = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY)
        return bin

    #trata ruídos da imagem binarizada
    def trait_noise_noCuda(self, img, it=1):
        structElem = cv2.getStructuringElement(cv2.MORPH_CROSS, (3,3))

        imgProc = cv2.erode(img, structElem, iterations=it)

        return imgProc
    
    #recuperando objeto de maior área
    def get_object_noCuda(self,img):
        contours, _ = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        return contours[0]
    
    #recuperando coordenadas extremas que englobam o objeto maior 
    def get_perspective_noCuda(self, obj):
        x,y,w,h = cv2.boundingRect(obj)
        return x,y,x+w,y+h
    
    #função para realçar objetos brilhantes na imagem
    def highlight_img_noCuda(self, img, dim = 25):
        structElem = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(dim,dim))

        imgProc = cv2.morphologyEx(img, cv2.MORPH_TOPHAT, structElem)

        #ajuste de contraste
        imgTrat = cv2.add(imgProc, imgProc)
        imgTrat = cv2.add(imgTrat, imgTrat)

        return imgTrat
    
    #função para reduzir a imagem original
    def reduce_window_noCuda(self, img, coorVetor, d=10):
        try:
            #recuperando dados do vetor coordenada
            x,y,w,h = coorVetor[0],coorVetor[1],coorVetor[2],coorVetor[3];

            firstPoints = np.float32([[x-d,y-d],[x+w+d,y-d],[x-d,y+h+d],[x+w+d,y+h+d]])
            lastPoints = np.float32([[0,0],[w,0],[0,h],[w,h]])

            #Matriz de transformação para nova perspectiva
            matrizPerspectiva = cv2.getPerspectiveTransform(firstPoints,lastPoints)

            #revisando nova imagem para processamento
            img_Reduce = cv2.warpPerspective(img, matrizPerspectiva, (w,h))

            return img_Reduce
        except:
            #Ocorreu um erro, então retorna a janela já inicial
            return img
        
    #função responsável para reduzir a imagem para os contornos do campo
    def reduce_field_noCuda(self, BinImg, Img, fieldWidth, d=10):
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
        

        try:
            #Obtendo os vértices do retângulo'
            x,y,w,h = cv2.boundingRect(objT) #Coordenadas da noav imagem

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
            self.prop_px_cm = 1

        hImg = img_Reduce.shape[0]
        wImg = img_Reduce.shape[1]

        if w > threshold and h > threshold:
            pixelWidth = min(w, h)
            convert_measures(fieldWidth, pixelWidth)

        else:
            self.prop_px_cm = self.prop_px_cm


        return bin_Reduce, img_Reduce, cooVetor

    #função para converter medidas
    def convert_measures(self, w_cm, w_px):
        self.prop_px_cm = w_px / w_cm

    #função para listar os jogadores
    def list_players(self, teamList):
        amount = len(teamList)
        for i in range(amount):
            print(teamList[i].team, teamList[i].id)
            print("Posição: x =", teamList[i].pos[0], " y =", teamList[i].pos[1])
        
        print("====================")

    #puxando intervalos de cores
    def create_color_bounds(self, color_array):
        h = color_array[0]
        s = color_array[1]
        v = color_array[2]

        hue_tolerance = 10
        saturation_tolerance = 50
        value_tolerance = 50

        lower_bound = np.array([h - hue_tolerance, max(0, s - saturation_tolerance), max(0, v - value_tolerance)])
        upper_bound = np.array([h + hue_tolerance, min(255, s + saturation_tolerance), min(255, v + value_tolerance)])

        return lower_bound, upper_bound
    
    def find_binary_contours(self, image, lower_bound, upper_bound):

        imageHSV = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        binaryImage = cv2.inRange(imageHSV, lower_bound, upper_bound)
        #Operações de fechamento e erosão
        structuringElement = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5)) #(20,20) // (5,5)
        binaryImage = cv2.morphologyEx(binaryImage, cv2.MORPH_CLOSE, structuringElement)
        binaryImage = cv2.erode(binaryImage, structuringElement, iterations=1)

        #Encontrando contorno da cor principal
        contours, _ = cv2.findContours(binaryImage, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        return contours

    def draw_player_circle(self, imgDegub, robot):
        x = robot.position[0]
        y = robot.position[1]
        r = robot.radius

        id = robot.id
        team = robot.team

        xi = int(x*self.prop_px_cm)
        yi = int(y*self.prop_px_cm)
        ri = int(r*self.prop_px_cm)

        if(team == "Aliado"):
            color = (255, 0, 0)
        elif(team == "Inimigo"):
            color = (0, 0, 255)
        else:
            color = (0, 200, 200)

        cv2.circle(imgDegub, (xi, yi), (ri + 5), color, 2)
        text = f"{team} {id}: {str(x)}, {str(y)}"
        cv2.putText(imgDegub, text , (int(xi),int(yi+ri+20)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
    # ==================== métodos com suporte ao CUDA ===========



    #=============| Definindo funções módulares | ===========================
    #métodos sem suporte ao CUDA



    #métodos com suporte ao CUDA

    #===========| Definindo funções principais | ============================
    #Métodos sem suporte ao cuda




    #métodos com suporte ao cuda




# Testar função principal e nova lógica
if __name__ =='__main__':
    #executará o código de teste deste módulo com uma imagem padrão
    print("Executado como principal")