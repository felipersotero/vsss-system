# ==========================================================================================
#  Variáveis, objetos e constantes padrões do código
#==========================================================================================
'''
    @GNOMIO: Definições que serão utilizadas como base no código, para serem utilizadas durante o processamento do sistema de visão.
'''
import numpy as np
import time
from modules import *
from viewer import MyViewer

# =============== CONTROLE DE IDENTIFICADORES ===============================
#identificadores padrões dos robôs
class ID_Robots:
    ROBOT_ALLY_GOAL:int = 0
    ROBOT_ALLY_1:int = 1
    ROBOT_ALLY_2:int = 2


    ROBOT_ENEMY_GOAL:int = 4
    ROBOT_ENEMY_1:int = 5
    ROBOT_ENEMY_2:int = 6


#Identificadores padrões para os pivots
class ID_Pivots:
    #Centro do campo
    CENTER: int = 0
    
    #Ponto de referência lado aliado
    PA1: int = 1
    PA2: int = 2
    PA3: int = 3

    #Ponto de referência lado inimigo
    PE1: int = 4
    PE2: int = 5
    PE3: int = 6

    

#identificadores padrões para o campo
class ID_Field:
    #Identificador da área que contabiliza gol
    GOAL_ALLY: int = 0
    GOAL_ENEMY: int = 1
    
    #Identificador da área dos goleiros
    GOAL_AREA_ALLY: int = 0
    GOAL_AREA_ENEMY: int = 1


#Identificadores dos times
class ID_Team:
    TEAM_ALLY: int = 0
    TEAM_ENEMY: int = 1


#Identificador de geometria
class GeometryType:
    POINT2D: int = 0
    RECT: int = 1
    CIRCLE: int =2 

# PROTOTIPO DE CLASSES BÁSICAS PARA UM SISTEMA DE COLISÃO
#Tipos de objetos para o sistema de colisão
class ObjTypeVision:
    BALL: int = 0
    ROBOT: int = 1
    FIELD: int = 2
    PIVOT: int = 3
    GOALFIELD: int = 4

#Tipos de objetos (que se movem, ou que ficam parados):
'''
@GNOMIO:
    STATIC: FIELD, PIVOT, GOALFIELD
    MOVING: ROBOT, BALL

    Objetos estáticos (STATIC) são pontos fixos no processo
    que não irão "colidir entre si". Objetos que se movem
    (MOVING) são aqueles que se movem na imagem e podem colidir
    tanto com outros objetos MOVING como objetos STATICS. 
    Exemplo:
        Ball = colide com o campo
'''
class ObjTypeMove:
    STATIC: int = 0
    MOVING: int = 1

#identificador do tipo de GPU
class GPUType:
    NVidia: int = 0
    AMD: int = 1
    DONTHAVE: int = -1


#identificador de serviço cuda para o emulador utilizar
class CUDADevice:
    #Gerando o objeto de serviço CUDA
    def __init__(self, GPU:GPUType,Version:str):
        self.GPU = GPU
        self.version = Version

# =============== VARIAVEIS GLOBAIS DE EMULAÇÃO ===============================

#Modo de Emulação do aplicativo
MODE_DEFAULT:int = 0
MODE_USB_CAM: int= 1
MODE_VIDEO_CAM:int = 3
MODE_IMAGE:int = 2
MODE_CONTROL_ROBOT: int = 4


#Modos de execução da janela de controle
class ModeControlW:
    MANUAL: int = 1
    POINTER: int = 2
    DEFAULT: int = 0
    
# ================== CONTROLE DE ESTRUTURA DE DADOS ========================
#Configurações da Emulação que serão inviadas para o sistema de visão realizar os cálculos
class EConfig:
    def __init__(self, offSetWindow =10, offSetErode = 0 ,dimMatrix = 25, Trashhold = 235 ):
        self.offSetWindow = offSetWindow
        self.offSetErode = offSetErode
        self.dimMatrix = dimMatrix
        self.Trashhold = Trashhold

    #Deletar este objeto em tempo de execução
    def delete(self):
        del self

# =============== CONTROLE DE CLASSES ===============================
#Classe auxiliar para configurar os pontos extremos que irão reconhecer o robô, para análise de colisão.
# [ ] Atualizar para modo GPU com Cupy e Numpy
        

# /// CLASSES GEOMÉTRICAS BÁSICAS (utilizando como base a biblioteca numpy)
#Definição de um ponto 2D no sistema
class Point2D:
    def __init__(self, px,py):
        self.px = px        #Coordenada x 
        self.py = py        #Coordenada y

        #ponto no formato array do numpy
        self.pos = np.array([px,py])

#Definição de um retângulo 
class Rectangle:
    def __init__(self, P1:Point2D, P2:Point2D, P3:Point2D, P4:Point2D):
        self.p1 = P1            #Ponto extremo 1
        self.p2 = P2            #Ponto extremo 2
        self.p3 = P3            #Ponto extremo 3
        self.p4 = P4            #Ponto extremo 4

        #Pontos no formato array do numpy
        self.points = np.array([P1.pos,P2.pos,P3.pos,P4.pos])

#Definição de um círculo
class Circle:
    def __init__(self,Center:Point2D, radius:int):
        self.center = Center
        self.radius = radius


#========================= /// CLASSES SEMÂNTICAS DO CÓDIGO // ===================
#Classe responsável por guardar as informações dos pontos de apoio
class Pivot:
    def __init__(self, id:ID_Pivots, Point:Point2D):
        self.id = id                #identificador
        self.posX = Point.px        #posição x
        self.posY = Point.py        #posição y
        self.pos = Point.pos        #formato array do numpy

        #Informações internas do tipo de objeto
        self.ObjType = ObjTypeMove.STATIC
        self.objTypeSystem = ObjTypeVision.PIVOT

    #Atualizar a posição do ponto de referência
    def updatePos(self,px,py): 
        self.posX=px 
        self.posY=py

#Objeto para representar a borda de um robô que será utilizada para análisar colisão
class BorderBox:
    def __init__(self, type:GeometryType, Infos):
        #Adquire o tipo do bbox
        self.type = type

        #Informa como o objeto deve guardar suas informações
        if(self.type == GeometryType.CIRCLE): #verifica se é um círculo
            self.Center = Infos.center
            self.radius = Infos.radius

        elif(self.type == GeometryType.RECT): #verifica se é um retângulo
            self.p1 = Infos.p1
            self.p2 = Infos.p2
            self.p3 = Infos.p3
            self.p4 = Infos.p4

        elif(self.type == GeometryType.POINT2D): #verifica se é um ponto 2D
            self.px = Infos.px
            self.py = Infos.py

#Classe responsável por organizar as áreas no campo
class AreaField:
    def __init__(self, id:ID_Field,rect:Rectangle):
        #Setando identificador da área
        self.Id = id
        self.rect = rect

        #Gerando uma bbox para sistema de colisões
        self.ObjType = ObjTypeMove.STATIC
        self.objTypeSystem = ObjTypeVision.GOALFIELD

        #configurando a border box da área
        self.bbox = BorderBox(GeometryType.RECT,rect)

    #Setando o retângulo que o representa
    def setRect(self,rect:Rectangle):
        self.rect = rect


#definindo classe de view para o robô, que irá armazenar a posição de uma
#janela que informa onde o robô estará, para reduzir o processamento
class ViewBot:
    def __init__(self, Position:Point2D, DimMatrix: int):
        #Centro (x,y)
        self.center = Position.pos

        #passo
        self.DimMatrix = DimMatrix
        self.step = self.DimMatrix/2.0

        #Encontrando pontos
        self.Pe1 = self.center + np.array([-1,-1])*self.step
        self.Pe2 = self.center + np.array([1,-1])*self.step
        self.Pe3 = self.center + np.array([1,1])*self.step
        self.Pe4 = self.center + np.array([-1,1])*self.step

        #Gerando retângulo para guardar as informações
        self.rect = Rectangle(self.Pe1, self.Pe2, self.Pe3, self.Pe4)

    #atualizando a posição da ViewBot pela posição central
    def updateViewBot(self, newPosition: Point2D):
        #Centro (x,y)
        self.center = newPosition.pos
        #Encontrando pontos
        self.Pe1 = self.center + np.array([-1,-1])*self.step
        self.Pe2 = self.center + np.array([1,-1])*self.step
        self.Pe3 = self.center + np.array([1,1])*self.step
        self.Pe4 = self.center + np.array([-1,1])*self.step

        #Gerando retângulo para guardar as informações
        self.rect = Rectangle(self.Pe1, self.Pe2, self.Pe3, self.Pe4)

    #atualizando posição do ViewBot por um passo
    def translateViewBot(self, stepView:Point2D):
        #Centro (x,y) é passado por um passo (pa, pb) => (x+pa, y+pb)
        self.center = self.center + stepView.pos

        #Encontrando pontos
        self.Pe1 = self.center + np.array([-1,-1])*self.step
        self.Pe2 = self.center + np.array([1,-1])*self.step
        self.Pe3 = self.center + np.array([1,1])*self.step
        self.Pe4 = self.center + np.array([-1,1])*self.step

        #Gerando retângulo para guardar as informações
        self.rect = Rectangle(self.Pe1, self.Pe2, self.Pe3, self.Pe4)
    
    #retornando os pontos que estão guardados na variável retângulo
    def getPoints(self):
        return self.rect.points
    
#========================| Gerando classe Timer | ==============================

#configurando objeto timer de alta precisão para pegar o passar do tempo de processamento
class HighPrecisionTimer:
    def __init__(self, master):
        self.master = master
        self.start_time = None
        self.elapsed_time = 0
        self._isRunning = False
        
    def run(self):
        self._isRunning = True
        self.start_time = time.time()
    
    def stop(self):
        if self.start_time is not None:
            current_time = time.time()
            self.elapsed_time += (current_time - self.start_time)*1000  # Multiplica por 1000 para obter milissegundos
            self.start_time = None
            self._isRunning = False
        else:
            print("O timer ainda não foi iniciado...")
            
    def reset(self):
        self.start_time = None
        self.elapsed_time = 0
        self._isRunning = False
        
    def getElapsedTime(self):
        if self.start_time is not None:
            current_time = time.time()
            elapsed_ms = (self.elapsed_time + (current_time - self.start_time)*1000)
            return elapsed_ms
        else:
            return self.elapsed_time
    
    def isRunning(self):
        return self._isRunning

#========================= /// CLASSE BÁSICA DE EXECUÇÃO // =====================
'''
 @GNOMIO: Essa estrutura deveria representar de forma simples a forma de captura de imagens, sendo elas tanto por câmera, ou por arquivos. E funcionará de forma a simplificar a parte semâtica do código, contudo, ainda está em fase de estruturar
'''
#Representa o hardware ou software de captura de imagens
#PertenceAoEmulador
class Capture:
    def __init__(self, mode):
        self.mode = mode
        self.image = None           # representa a imagem que foi capturada
        self.isCamRunning = False   # Para o caso de uma câmera de verdade
        self.FPS = 15               # Taxa de quadro

        #Endereços para imagem e vídeo
        self.imgPath = None
        self.videoPath = None

        #Imagem que será utilizada
        self.img = None

    #Mudar o modo de execução
    def SetMode(self,mode):
        self.mode = mode

    #Informar o identificador da câmera
    def setIdCam(self, id):
        self.idCam = id

    #Informar o endereço das imagens e dos vídeos
    def setImagePath(self, pathImg):
        self.imgPath = pathImg

    #Informar o endereço dos vídeos
    def setVideoPath(self, pathVideo):
        self.videoPath = pathVideo

    #Retorna a imagem da captura
    def getImage(self):
        return self.img
    
    #Resetar captura
    def reset(self):
        self.mode = MODE_DEFAULT    #Modo que representa a imagem
        self.image = None           # representa a imagem que foi capturada
        self.isCamRunning = False   # Para o caso de uma câmera de verdade
        self.FPS = None             # Taxa de quadro

        #Endereços para imagem e vídeo
        self.imgPath = None
        self.videoPath = None

        #Imagem que será utilizada
        self.img = None
    
    #Destruindo o objeto de captura
    def delete(self):
        del self
