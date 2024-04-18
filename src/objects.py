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
import threading
import queue
import tkinter 
from collections import deque

# =============== CONTROLE DE IDENTIFICADORES ===============================
#identificadores padrões dos robôs
class ID_Robots:
    '''
        Identificador dos robôs da competição. Que são 3 no total;
        #### Equipe aliada
        * ROBOT_ALLY_GOAL: Goleiro aliado
        * ROBOT_ALLY_1: Primeiro atacante aliado
        * ROBOT_ALLY_2: Segundo atacante aliado
        #### Equipe inimigo
        * ROBOT_ENEMY_GOAL: Goleiro inimigo
        * ROBOT_ENEMY_1: Primeiro atacante inimigo
        * ROBOT_ENEMY_2: Segundo atacante inimigo
    '''
    ROBOT_ALLY_GOAL:int = 0
    ROBOT_ALLY_1:int = 1
    ROBOT_ALLY_2:int = 2


    ROBOT_ENEMY_GOAL:int = 4
    ROBOT_ENEMY_1:int = 5
    ROBOT_ENEMY_2:int = 6


#Identificadores padrões para os pivots
class ID_Pivots:
    ''' Identificador dos pivots
        * CENTER
        * PA1, PA2, PA3 -> Pontos de referÊncia do lado aliado
        * PE1, PE2, PE3 -> Pontos de referência do lado inimigo
    '''
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
    '''
        Identificador dos campos
        * GOAL_ALLY: Área do gol aliado que contabiliza ponto para o inimigo;
        * GOAL_ENEMY: Área do gol inimigo que contabiliza ponto para o aliado;

        * GOAL_AREA_ALLY: Área onde o robô goleiro aliado fica.
        * GOAL_AREA_ENEMY: Área onde o robÔ goleiro inimigo fica
    '''
    #Identificador da área que contabiliza gol
    GOAL_ALLY: int = 0
    GOAL_ENEMY: int = 1
    
    #Identificador da área dos goleiros
    GOAL_AREA_ALLY: int = 0
    GOAL_AREA_ENEMY: int = 1


#Identificadores dos times
class ID_Team:
    '''
        Identificador dos times
        * TEAM_ALLY: Time aliado
        * TEAM_ENEMY: Time inimigo
    '''
    TEAM_ALLY: int = 0
    TEAM_ENEMY: int = 1


#Identificador de geometria
class GeometryType:
    '''
        Identificador de tipo de geometria: 
        * POINT2D;
        * QUAD (Quadrilátero)
        * CIRCLE
    '''
    POINT2D: int = 0
    QUAD: int = 1
    CIRCLE: int =2 

# PROTOTIPO DE CLASSES BÁSICAS PARA UM SISTEMA DE COLISÃO
#Tipos de objetos para o sistema de colisão
class ObjTypeVision:
    '''
        Informa qual o tipo de objeto para o sistema de visão:
        * BALL: Bola
        * ROBOT: Robô
        * FIELD: Campo
        * PIVOT: Ponto de referência
        * GOALFIELD: Área dos goleiros ou gols
    '''
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
    '''
    Define os tipos de objetos que serão computados
    se são STATIC (estáticos) ou MOVING( móveis). Objetos estáticos não colidem entre si
    mas objetos MOVING colidem entre si e com os estáticos tbm.
    '''
    STATIC: int = 0
    MOVING: int = 1

#identificador do tipo de GPU
class GPUType:
    '''
        Identificador do tipo de GPU:
        * NVidia;
        * AMD;
        * DONTHAVE
    '''
    NVidia: int = 0
    AMD: int = 1
    DONTHAVE: int = -1


#identificador de serviço cuda para o emulador utilizar
class CUDADevice:
    '''
    Estrutura para representar o serviço cuda da máquina
    '''
    #Gerando o objeto de serviço CUDA
    def __init__(self, GPU:GPUType,Version:str):
        self.GPU = GPU
        self.version = Version

# =============== VARIAVEIS GLOBAIS DE EMULAÇÃO ===============================

#Modo de Emulação do aplicativo

MODE_DEFAULT:int = 0
''' Constante de emulação: Modo padrão '''
MODE_USB_CAM: int= 1
''' Constante de emulação:  Modo de emulação através de uma câmera USB ou interna'''
MODE_VIDEO_CAM:int = 3
''' Constante de emulação:  Modo de emulação por meio de um vídeo'''
MODE_IMAGE:int = 2
''' Constante de emulação:  Modo de emulação por meio de uma imagem'''
MODE_CONTROL_ROBOT: int = 4
''' Constante de emulação:  Emulador sendo utilizado na janela de controle'''

#Modos de execução da janela de controle
class ModeControlW:
    '''
        Modos de execução da janela de controle individual dos robôs
    '''
    MANUAL: int = 1
    POINTER: int = 2
    DEFAULT: int = 1
    
# ================== CONTROLE DE ESTRUTURA DE DADOS ========================
#Configurações da Emulação que serão inviadas para o sistema de visão realizar os cálculos
class EConfig:
    '''
        É uma estrutura com as informações passadas pelo emulador ao sistema de visão
        o sistema de visão irá pegar essas informações e se configurar da forma necessária
    '''
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
    ''' Classe para representar um ponto de 2 dimensões'''
    def __init__(self, px,py):
        self.px = px        #Coordenada x 
        self.py = py        #Coordenada y

        #ponto no formato array do numpy
        self.pos = np.array([px,py])

    #retornando posição central
    def getPos(self):
        '''
        Retorna posição do ponto (x,y)
        '''
        return self.pos 
    
#Definição de um Quadrilátero 
class Quad:
    '''
        Definição de um Quadrilátero para o código.
    '''
    def __init__(self, P1:Point2D, P2:Point2D, P3:Point2D, P4:Point2D):
        ''' Necessário informar 4 pontos para ele interpretar e juntar'''
        self.p1 = P1            #Ponto extremo 1
        self.p2 = P2            #Ponto extremo 2
        self.p3 = P3            #Ponto extremo 3
        self.p4 = P4            #Ponto extremo 4

        #Pontos no formato array do numpy
        self.points = np.array([P1,P2,P3,P4])

    def getPoint(self):
        '''
            Retorna os pontos associados a esse Quadrilátero num array
        '''
        return self.points
     
#Definição de um círculo
class Circle(GeometryType):
    '''
        Definição de uma estrutura para representar um círculo
    '''
    def __init__(self,Center:Point2D, radius:int):
        self.center = Center
        self.radius = radius

    #retornando raio do círculo
    def getRadius(self):
        '''
            Retorna o raio do círculo
        '''
        return self.center
    
    #retornando ponto central
    def getCenter(self):
        '''
            Retorna o centro do círculo
        '''
        return self.center.getPos()


#Definindo um polígono
'''...'''

#========================= /// CLASSES SEMÂNTICAS DO CÓDIGO // ===================
#Classe responsável por guardar as informações dos pontos de apoio
class Pivot:
    '''
    Representa um ponto com identificador, ou seja, um ponto importante no jogo.
    '''
    def __init__(self, id:ID_Pivots, Point:Point2D = Point2D(0,0)):
        self.id = id                #identificador
        self.posX = Point.px        #posição x
        self.posY = Point.py        #posição y
        self.pos = Point.pos        #formato array do numpy

        #Informações internas do tipo de objeto
        self.ObjType = ObjTypeMove.STATIC
        self.objTypeSystem = ObjTypeVision.PIVOT

    #Atualizar a posição do ponto de referência
    def updatePos(self,px,py):
        '''
            Atualiza a posição do ponto de referência
        ''' 
        self.posX=px 
        self.posY=py

#Objeto para representar a borda de um robô que será utilizada para análisar colisão
class BorderBox:

    def __init__(self, type:GeometryType, Infos):
        '''
        Essa classe representa a borda de colisão do objeto, podendo ser de três tipos:
        * Círculo (GeometryType.CIRCLE)
        * Quadrilátero (GeometryType.QUAD)
        * Ponto ((GeometryType.POINT2D)

        Cada tipo de borderbox terá um sistema de colisão diferente.
        '''
        #Adquire o tipo do bbox
        self.type = type

        #Informa como o objeto deve guardar suas informações
        if(self.type == GeometryType.CIRCLE): #verifica se é um círculo
            self.Center = Infos.center
            self.radius = Infos.radius

        elif(self.type == GeometryType.QUAD): #verifica se é um retângulo
            self.p1 = Infos.p1
            self.p2 = Infos.p2
            self.p3 = Infos.p3
            self.p4 = Infos.p4

        elif(self.type == GeometryType.POINT2D): #verifica se é um ponto 2D
            self.px = Infos.px
            self.py = Infos.py

#Classe responsável por organizar as áreas no campo
class AreaField:
    '''
        A classe representa uma área importante do campo, podendo ser a área
        do goleiro aliado ou inimigo, bem como  o próprio campo e o campo aliado e inimigo.
    '''
    def __init__(self, id:ID_Field,rect:Quad = Quad(Point2D(0,0),Point2D(0,0),Point2D(0,0),Point2D(0,0))):
        #Setando identificador da área
        self.Id = id
        self.rect = rect

        #Gerando uma bbox para sistema de colisões
        self.ObjType = ObjTypeMove.STATIC
        self.objTypeSystem = ObjTypeVision.GOALFIELD

        #configurando a border box da área
        self.bbox = BorderBox(GeometryType.QUAD,rect)

    #Setando o retângulo que o representa
    def setRect(self,rect:Quad):
        '''
            Informo qual o retângulo que será representado por essa área
        '''
        self.rect = rect

    def setId(self, id:ID_Field):
        '''
            Informo qual é o identificador novo dessa área.
        '''
        self.Id = id

#definindo classe de view para o robô, que irá armazenar a posição de uma
#janela que informa onde o robô estará, para reduzir o processamento
class ViewBot:
    '''
        Classe de view que representa uma janela da imagem onde o robô se encontra.
    '''
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
        self.rect = Quad(self.Pe1, self.Pe2, self.Pe3, self.Pe4)

    #atualizando a posição da ViewBot pela posição central
    def updateViewBot(self, newPosition: Point2D):
        '''
            Atualiza a viewBot com base na nova posição programada (xf, yf)
        '''
        #Centro (x,y)
        self.center = newPosition.pos
        #Encontrando pontos
        self.Pe1 = self.center + np.array([-1,-1])*self.step
        self.Pe2 = self.center + np.array([1,-1])*self.step
        self.Pe3 = self.center + np.array([1,1])*self.step
        self.Pe4 = self.center + np.array([-1,1])*self.step

        #Gerando retângulo para guardar as informações
        self.rect = Quad(self.Pe1, self.Pe2, self.Pe3, self.Pe4)

    #atualizando posição do ViewBot por um passo
    def translateViewBot(self, stepView:Point2D):
        '''
            Função responsável por translatar a view, sendo necessário passar o
            vetor de passo (stepView), que consiste de duas coordenadas (px,py)
        '''
        #Centro (x,y) é passado por um passo (pa, pb) => (x+pa, y+pb)
        self.center = self.center + stepView.pos

        #Encontrando pontos
        self.Pe1 = self.center + np.array([-1,-1])*self.step
        self.Pe2 = self.center + np.array([1,-1])*self.step
        self.Pe3 = self.center + np.array([1,1])*self.step
        self.Pe4 = self.center + np.array([-1,1])*self.step

        #Gerando retângulo para guardar as informações
        self.rect = Quad(self.Pe1, self.Pe2, self.Pe3, self.Pe4)
    
    #retornando os pontos que estão guardados na variável retângulo
    def getPoints(self):
        '''
            Retorna os pontos que caracterizam a view
        '''
        return self.rect.points
    
#========================| Gerando classe Timer | ==============================

#configurando objeto timer de alta precisão para pegar o passar do tempo de processamento
class HighPrecisionTimer:
    '''
        Classe para representar um timer de alta precisão que será utilizado
        no programa para recuperar informações tempo
    '''
    def __init__(self, master):
        self.master = master
        self.start_time = None
        self.elapsed_time = 0
        self._isRunning = False
        
    def run(self):
        '''
            Inicializar a contagem do timer
        '''
        self._isRunning = True
        self.start_time = time.time()
    
    def stop(self):
        '''
            Parar a contagem do timer.
        '''
        if self.start_time is not None:
            current_time = time.time()
            self.elapsed_time += (current_time - self.start_time)*1000  # Multiplica por 1000 para obter milissegundos
            self.start_time = None
            self._isRunning = False
        else:
            print("O timer ainda não foi iniciado...")
            
    def reset(self):
        '''
            Resetar o timer para 0.
        '''
        self.start_time = None
        self.elapsed_time = 0
        self._isRunning = False
        
    def getElapsedTime(self):
        '''
            Retorna o tempo que se passou desde que foi ligado, sem considerar o tempo 
            que passou pausado pela função stop()
        '''
        if self.start_time is not None:
            current_time = time.time()
            elapsed_ms = (self.elapsed_time + (current_time - self.start_time)*1000)
            return elapsed_ms
        else:
            return self.elapsed_time
    
    def isRunning(self):
        '''
            Retorna se o timer está ou não parado.
        '''
        return self._isRunning

#========================= /// CLASSE BÁSICA DE EXECUÇÃO // =====================
'''
 @GNOMIO: Essa estrutura deveria representar de forma simples a forma de captura de imagens, sendo elas tanto por câmera, ou por arquivos. E funcionará de forma a simplificar a parte semâtica do código, contudo, ainda está em fase de estruturar
'''
# Representa o hardware ou software de captura de imagens
class CaptureMode:
    '''
        Modos de captura da câmera: DEFAULT, CAM, IMG, VIDEO.
    '''
    DEFAULT: int = 0
    CAM: int = 1
    IMG: int = 2
    VIDEO: int = 3

#enumeração para o modo de focalização da câmera
class FocusMode:
    '''
        Representar qual o modo de foco da câmera, se é automático ou manual
    '''
    AUTO: int = 0
    MANUAL: int =1 


# PertenceAoEmulador
class Capture:
    '''
        Classe responsável por ser o intermédio entre a forma de capturar informações
        e o emulador.
    '''
    def __init__(self, mode: CaptureMode.DEFAULT, useGpu:BooleanVar):
        '''
            Inicializo o objeto informando o modo de captura: DEFAULT, CAM, IMG ou Video.
            E também informo se vou ou não utilizar GPU (True ou False)
        '''
        self.mode = mode
        self.image = None                               # Representa a imagem que foi capturada
        self.isCamRunning = False                       # Para o caso de uma câmera de verdade
        self.frameDelay = 14                            # Taxa de quadro (delay)
        self._hasGPU = useGpu                           # utiliza a GPU para processar
        self.cuda = None                                # Objeto para tratar o modo GPU
        self.idCam = 0                                  # identificador da câmera que será utilizada
        self.modeCam: FocusMode = FocusMode.AUTO        # ela é inicialmente feita no modo automático
        self.focusManual = 155                          # aqui eu guardo o valor 

        self._camHasFocusControl = False                # flag que indica se a câmera tem controle de foco
        self._hasCamera = False                         # Flag interna para avisar que existe uma câmera criada
        
        # Endereços para imagem e vídeo
        self.imgPath = None
        self.videoPath = None

        # Usa a câmera
        self.CAM = None             # Armazena o objeto de captura do OpenCV

        #Verifica logo se o modo de configuração é o de GPU
        self.GPUMode(self._hasGPU)

    # Mudar o modo de execução
    def setMode(self, mode: CaptureMode):
        '''
            Escolhe um modo de execução para captura da câmera.
            Esse modo pode ser vídeo, camera ou imagem.
        '''
        self.mode = mode

    # define qual a forma que a câmera irá tratar o foco
    def setModeFocus(self, mode:FocusMode = FocusMode.AUTO):
        if self.mode == CaptureMode.CAM and self._hasCamera and (self.CAM is not None):
            if mode == FocusMode.AUTO:
                if not self.CAM.set(cv2.CAP_PROP_AUTOFOCUS, 0):
                    print("[CAPTURA]: Câmera não suporta controle de foco")
                    return False
                else: #suporta controle de foco
                    self.modeCam = mode
                    self._camHasFocusControl = True

                    return True
            elif mode == FocusMode.MANUAL:
                if not self.CAM.set(cv2.CAP_PROP_FOCUS, self.focusManual):
                    print("[CAPTURA]: Câmera não suporta controle de foco")
                    return False
                else: #suporta controle de foco
                    self.modeCam = mode
                    self._camHasFocusControl = True
                    return True
            else:
                print("[CAPTURA]: Erro grave! Variável corrompida")
                return False 
        else:   
            print("[CAPTURA]: primeiro coloque no modo câmera!")
            return False

    #define qual o valor atribuído ao foco
    def setFocusManual(self, value:int):
        if self.mode == CaptureMode.CAM and self._hasCamera and self._camHasFocusControl:
            if self.modeCam == FocusMode.AUTO:
                print("[CAPTURE]: Modo configurado para automático. Essa ação não é possível")
            elif self.modeCam == FocusMode.MANUAL and (self.CAM is not None):
                self.focusManual = np.clip(value, 0, 255)
                self.CAM.set(cv2.CAP_PROP_FOCUS, self.focusManual)  # Altere este valor para ajustar o foco
        else:
            print("[CAPTURA]: A câmera não tem suporte ao controle, ou não foi configurada para câmera")

    #Seta a configura para o GPU
    def GPUMode(self, useGpu:BooleanVar):
        '''
            Função responsável por setar um modo da GPU.
            UseGPU é um booleano que irá dizer se irá ou não utilizar
            a GPU para agilizar os cálculos, nesse casso, ele carrega as funções pertinentes.
        '''
        self._hasGPU = useGpu
        if(self._hasGPU):
            self.cuda = cv2.cuda.GpuMat()
            if self.cuda is not None:
                print("[CAPTURA]: Construído com sucesso")
        else:
            self.cuda = None

    # Informar o identificador da câmera
    def setIdCam(self, id):
        '''
            Informa o identificador da câmera que será utilizada para o 
            processamento.
        '''
        self.idCam = id
        print("[CAPTURA]: Id da camera:", self.idCam)
        if(self.mode == CaptureMode.CAM):
            try:
                self.CAM = cv2.VideoCapture(self.idCam)

                #verifica se foi possível criar essa câmera
                if not self.CAM.isOpened():
                    print("[CAPTURA]: Ocorreu um erro ao abrir a câmera!")
                    self.CAM.release()
                    return False
                else:
                    self._hasCamera = True
                    print("[CAPTURA]: Criou a câmera:")
                    return True
            except:
                print("[CAPTURA]: Ocorreu um erro em abrir a câmera")
                return False
            
    # Informar o endereço das imagens e dos vídeos
    def setImagePath(self, pathImg):
        '''
        Informo o caminho para coletar a imagem
        
        '''
        self.imgPath = pathImg

    # Informar o endereço dos vídeos
    def setVideoPath(self, pathVideo):
        '''
            Informo o caminho para coletar o vídeo
        '''
        self.videoPath = pathVideo

    '''
    @GNOMIO: essa função "getImage" deve ser utilizada dentro dum loop quand oem vídeo
    '''
    # Retorna a imagem da captura
    def getImageNoCuda(self):
        ''' Função responsável por retornar a imagem do modo captura. 
        Ele funciona dependendo se está ou não utilizando a GPU.
        '''
        #print("[CAPTURA]: \nModo:",self.mode, "\n:Id:",self.idCam)
        if(not self._hasGPU):
            if self.mode == CaptureMode.IMG:
                self.image = cv2.imread(self.imgPath)
                return self.image
            elif self.mode == CaptureMode.CAM:
                ret, self.image = self.CAM.read()
                
                if ret:
                    return self.image
                else:
                    print("[CAPTURA]: Algum problema em adquirir a imagem")
                    return self.image
            else:
                print("[CAPTURA]: Não está configurado corretamente.")
                return None
        else:
            print("[CAPTURE]: Cuidado, vocÊ configurou para rodar com cuda!")
            return self.image
    
    #retorna a imagem da captura quando não é com cuda
    def getImageCuda(self):
        ''' Função responsável por retornar a imagem do modo captura. 
        Ele funciona dependendo se está ou não utilizando a GPU.

        Ela irá retornar um objeto para manipular a informação direto na GPU,
        um endereço, que será necessário utilizar o download() no objeto para utiliza-lo
        na CPU
        '''
        #print("[CAPTURA]: \nModo:",self.mode, "\n:Id:",self.idCam)
        if(self._hasGPU):
            if self.mode == CaptureMode.IMG:
                self.image = cv2.imread(self.imgPath)
                self.cuda.upload(self.image)
                return self.cuda
            elif self.mode == CaptureMode.CAM:
                ret, self.image = self.CAM.read()
                self.cuda.upload(self.image)
                if ret:
                    return self.cuda
                else:
                    print("[CAPTURA]: falha em recupera o endereço da GPU")
                    return None
            else:
                print("[CAPTURA]: Ocorreu um erro com os valores para a GPU")
                return None
        else:
            print("[CAPTURA]: Não configurado para rodar com CUDA")
            return None
    
    #Função única do capture
    def getImage(self):
        '''
            Recupera a imagem capturada!
        '''
        if self._hasGPU:
            return self.getImageCuda()
        else:
            return self.getImageNoCuda()
    # Resetar objeto de captura
    # Resetar objeto de captura
    def reset(self):
        '''
        Reseta as configurações da captura.
        '''
        #print("[CAPTURA]: As informações foram resetadas")
        self.mode = MODE_DEFAULT    # Modo que representa a imagem
        self.image = None           # Representa a imagem que foi capturada
        self.isCamRunning = False   # Para o caso de uma câmera de verdade
        self.FPS = None             # Taxa de quadro
        self.idCam = 0 

        # Endereços para imagem e vídeo
        self.imgPath = None
        self.videoPath = None
        self._hasGPU = False

        # Fechar a captura da câmera
        if self.CAM is not None:
            self.CAM.release()

        # Liberar memória da GPU
        if self.cuda is not None:
            self.cuda.release()

        self.modeCam: FocusMode = FocusMode.AUTO        # ela é inicialmente feita no modo automático
        self.focusManual = 155                          # aqui eu guardo o valor 
        
        self._hasCamera = False                         # Flag interna para avisar que existe uma câmera criada
        self._camHasFocusControl = False                # flag que indica se a câmera tem controle de foco

    # Destruindo o objeto de captura
    def __del__(self):
        self.reset()
        del self

#classe para gerenciar a thread de captura de dados
class CameraCaptureThread(threading.Thread):
    '''
        Essa classe é responsável por gerar a Thread que irá capturar imagens
        e salvar elas num deque, que será acessado pelo emulador.
    '''
    def __init__(self, main, capture_instance: Capture, deque:deque, interval=0.016):
        super().__init__()
        self.capture_instance = capture_instance
        self.interval = interval
        self._is_running = False
        self._main = main
        self.deque = deque
        self.daemon = True

    def run(self):
        self._is_running = True
        while self._is_running:
            new_image = self.capture_instance.getImage()
            if new_image is None:
                pass
            else:
                self.deque.append(new_image)  # Enviando a nova imagem para a fila
            #print(self.deque[-1])
            time.sleep(self.interval)

    def stop(self):
        #liberar recursos
        if self.capture_instance.mode == CaptureMode.CAM:
            self.capture_instance.CAM.release()
        print("Recursos liberados")
        #parando
        self._is_running = False

        

#==================================== CLASSES PARA INTERFACE =========================
#definindo função para indicar estado do controlador
class StateSquare(Frame):
    '''
        É apenas uma classe para representar um quadrado na interface.
    '''
    def __init__(self, master=None, variable=None, btn= None):
        super().__init__(master, bg="white")
        self.square_size = 10
        self.status = variable
        self.square = Canvas(self, width=self.square_size, height=self.square_size, bd=1, relief="solid", bg="red")
        self.square.grid(row=0, column=0, padx=5, pady=5)
        self.text_var = StringVar()
        self.text_var.set("Parado")
        self.text_label = Label(self, textvariable=self.text_var, bg="white")
        self.text_label.grid(row=0, column=1, padx=5, pady=5)
        self.button = btn

    #modificar estado
    def toggle_status(self):
        if self.status == True:
            self.set_status(False)
        else:
            self.set_status(True)


    #definir estado
    def set_status(self, status):
        self.status = status
        if self.status == True:
            self.square.config(bg="green")
            self.text_var.set("Em execução")
            self.button.config(text="Parar o processamento")
        elif self.status  == False:
            self.square.config(bg="red")
            self.text_var.set("Parado")
            self.button.config(text="Iniciar processamento")