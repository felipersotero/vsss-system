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
    def __init__(self, id:ID_Robots, team:ID_Team, x, y, r, image=cv2.imread('src/images/dark_screen.png')):
        self.id = id
        self.team = team
        self.position = np.array([round(x, 2), round(y, 2)])
        self.radius = round(r, 2)
        self.direction = np.array([0, 0])
        self.detected = False
        self.image = image

    def update_position(self, x, y, r, image):
        self.position = np.array([round(x, 2), round(y, 2)])
        self.radius = round(r, 2)
        self.image = image

    def update_direction(self, dirX, dirY):
        self.direction = np.array([dirX, dirY])

    def set_status(self, status):
        self.detected = status

    def set_Radius(self, radius):
        self.radio = radius

'''
@GNOMIO:A classe bola é responsável por pegar informações do objeto bola que será utilizado no processo de detecção
'''
class Ball:
    def __init__(self, x, y, r):
        self.position = np.array([int(x), int(y)])
        self.radius = int(r)
        self.direction = np.array([0, 0])

    def update_position(self, x, y, r):
        self.position = np.array([int(x), int(y)])
        self.radius = r

    def set_direction(self, last_position, current_position):
        self.direction = np.array([10*(current_position[0] - last_position[0]), 10*(current_position[1] - last_position[1])])

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
    def __init__(self, Extremes:Rectangle, capture):
        self.Extremes = Extremes
        self.img = capture


#Classe principal do sistema de visão que irá executar as funções
class VisionSystem:
    #Inicializando objeto do sistema de detecção
    def __init__(self,config: EConfig, capture):
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

        #Carregando as configurações do sistema de visão
        self.config = config

        #Pegando a imagem de origem
        self.imgOrigin = capture

        #Variáveis que serão utilizadas pelo Emulador
        
        
    #Métodos (método run e o método stop)
    def run(self):
        a = 1
    def stop(self):
        b = 2