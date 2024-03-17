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

#Classe principal do sistema de visão que irá executar as funções
class VisionSystem:
    #Inicializando objeto do sistema de detecção
    def __init__(self,config: EConfig, capture: Capture, UseCuda:bool, GPUType:GPUType):
        #Configurando objetos
        self.createObjs()

        #Carregando as configurações do sistema de visão
        self.config = config

        #Pegando a imagem de origem
        self.imgOrigim = capture.getImage()

        #váriaveis que serão utilizadas pelo compilador


        #verifica se existe suporte ao CUDA
        self.hasCuda = UseCuda 
        self.GPUType = GPUType

    #Métodos (método run e o método stop)
    def init(self):
        a = 1

#Criando os objetos
    def createObjs(self):
        #Construção dos objetos necessários para realizar a análise
        #Objeto da bola
        self.ball = Ball()
        
        #Objeto dos robôs,
        #robôs aliados
        self.robotAllyG = Robot(id=ID_Robots.ROBOT_ALLY_GOAL, team=ID_Robots.TEAM_ALLY)
        self.robotAlly1 = Robot(id=ID_Robots.ROBOT_ALLY_1,team=ID_Robots.TEAM_ALLY)
        self.robotAlly2 = Robot(id=ID_Robots.ROBOT_ALLY_2,team=ID_Robots.TEAM_ALLY)
        
        #robôs inimigos
        self.robotEnemyG = Robot(id=ID_Robots.ROBOT_ENEMY_GOAL,team=ID_Robots.TEAM_ENEMY)
        self.robotEnemy1 = Robot(id=ID_Robots.ROBOT_ENEMY_1,team=ID_Robots.TEAM_ENEMY)
        self.robotEnemy2 = Robot(id=ID_Robots.ROBOT_ENEMY_2,team=ID_Robots.TEAM_ENEMY)

        #Dividindo times
        #time aliado
        self.allyTeam = [self.robotAllyG, self.robotAlly1, self.robotAlly2]

        #time inimigo
        self.enemyTeam = [self.robotEnemyG,self.robotEnemy1,self.robotEnemy2]

        #gerando objeto para representar o campo
        self.field = Field()
    #Método para retornar o processamento
    def getResult(self):
        b = 1

    #Verifica se o computador tem GPU compatível
    def hasGPUDevice(self):
        return True
    
    #verifica se o computador tem suporte CUDA
    def hasCUDADevice(self):
        return False
    
    #método para retornar o processamento
    def getViewCapture(self):
        return 0
    
