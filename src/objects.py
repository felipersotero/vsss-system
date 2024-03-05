# ==========================================================================================
#  Variáveis, objetos e constantes padrões do código
#==========================================================================================
'''
    @GNOMIO: Definições que serão utilizadas como base no código, para serem utilizadas du-
    rante o processamento do sistema de visão.
'''
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

# =============== VARIAVEIS GLOBAIS DE EMULAÇÃO ===============================

#Modo de Emulação do aplicativo
MODE_DEFAULT:int = 1
MODE_USB_CAM: int= 2
MODE_VIDEO_CAM:int = 3
MODE_IMAGE:int = 4

# ================== CONTROLE DE ESTRUTURA DE DADOS ========================
#Configurações da Emulação que serão inviadas para o sistema de visão realizar os cálculos
class EConfig:
    def __init__(self, offSetWindow =10, offSetErode = 0 ,dimMatrix = 25, Trashhold = 235 ):
        self.offSetWindow = offSetWindow
        self.offSetErode = offSetErode
        self.dimMatrix = dimMatrix
        self.Trashhold = Trashhold


# =============== CONTROLE DE CLASSES ===============================
#Classe auxiliar para configurar os pontos extremos que irão reconhecer o robô, para análise de colisão.
# [ ] Atualizar para modo GPU com Cupy e Numpy
        

# /// CLASSES GEOMÉTRICAS BÁSICAS
#Definição de um ponto 2D no sistema
class Point2D:
    def __init__(self, px,py):
        self.px = px
        self.py = py

#Definição de um retângulo 
class Rectangle:
    def __init__(self, P1:Point2D, P2:Point2D, P3:Point2D, P4:Point2D):
        self.p1 = P1
        self.p2 = P2
        self.p3 = P3
        self.p4 = P4

#Definição de um círculo
class Circle:
    def __init__(self,Center:Point2D, radius:int):
        self.center = Center
        self.radius = radius


#========================= /// CLASSES SEMÂNTICAS DO CÓDIGO // ===================
#Classe responsável por guardar as informações dos pontos de apoio
class Pivot:
    def __init__(self, id:ID_Pivots, Point:Point2D):
        self.id = id            
        self.posX = Point.px      
        self.posY = Point.py

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
        #configurando a border box da área
        self.bbox = BorderBox(GeometryType.RECT,rect)

    #Setando o retângulo que o representa
    def setRect(self,rect:Rectangle):
        self.rect = rect


#========================= /// CLASSE BÁSICA DE EXECUÇÃO // =====================
'''
 @GNOMIO: Essa estrutura deveria representar de forma simples a forma de captura de imagens, sendo elas tanto por câmera, ou por arquivos. E funcionará de forma a simplificar a parte semâtica do código, contudo, ainda está em fase de estruturar
'''
#Representa o tipo de aquisição de dados do emulador
class Capture:
    def __init__(self, mode):
        self.mode = mode
        self.image = None           # representa a imagem que foi capturada
        self.isCamRunning = False   # Para o caso de uma câmera de verdade
        
    def setIdCam(self, id):
        self.idCam = id

    def show(self):
        #Coloca forma de capturar imagem
        return self.Image
    
