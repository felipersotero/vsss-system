# ==========================================================================================
# MÓDULO DE FUNÇÕES PARA ALGORÍTMO DE DETECÇÃO VSS (version v2.2.40)
#==========================================================================================
'''
    @GNOMIO: O algorítmo de detecção terá agora uma nova lógica de programação, no qual ele é conti-
    tuído de uma classe 'detector' responsável por realizar.
    Os cálculos serão acelerados utilizando a GPU. Para isso utiliza a bibliteca OpenCV com 
    base na plataforma cuda, e usa também a cupy para realizar cálulos da biblioteca
    numpy na GPU do computador.

    Necessário configurar CMAKE e etc para utilizar essa interface.
'''
#importando bibliotecas necessárias para o código
import cv2
import numpy as np
from timer import *
import threading
import queue
import imports
from modules.VisionSys.objects import *
import traceback
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

#======================|| DEFINIÇÕES DE CLASSES ||======================================#

# ====================== DEFINIÇÕES DAS CLASSES DE OBJETO DO SISTEMA ==================

#Classe do robô
class Robot:
    def __init__(self, id:ID_Robots, team:ID_Team, x=0, y=0, r=0, image=cv2.imread('src/images/dark_screen.png'),colorTeam = None,colorCar1 = None, colorCar2=None):
        '''
        @GNOMIO: Classe Robot que será utilizada no algorítmo de detecção para representar os robôs
        As características do robô são:
            * id - identificador do robô;
            * team - time do robô
            * position - Posição do robô no campo
            * radius - Seria necessário para o procedimento de detectar colisão
            * direction - direção na qual o robô está apontando
            * image - imagem que representa o robô no momento que foi detectado;

        '''
        #informando identificador
        self.id = id 

        #informando time
        self.team = team
        self.position = np.array([round(x, 2), round(y, 2)])

        #informação do jogador na imagem
        self.xi =   0            # posição na imagem reduzida
        self.yi =   0            # posição y na imagem reduzida
        self.ri =   0            # raio relativo a imagem original

        #informações de posição para cálculo da velocidade
        self.lastPosition = self.position
        self.newPosition = self.position 
        self.direction = np.array([round(x, 2), round(y, 2)])
        self.velocity = np.array([0,0])


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
        self.image = image
        self.dimMatrix = image.shape[1]

        #Janela que informa a posição do jogador
        #informando raio de border box 
        self.viewRect = ViewBot(Point2D(self.position[0],self.position[1]), self.dimMatrix)

        #informando cor (Em código HSV, falta converter)
        self.colorTeam = colorTeam
        self.colorCar1 = colorCar1
        self.colorCar2 = colorCar2

        #o objeto precisa ter ideia de tempo para realizar suas operaçõe
        self.lastTimestamp  = 0 
        self.newTimestamp   = 0
        self.dT             = 0 


        # Parâmetros para o filtro de Kalman
        #Matriz de observação H 
        self.H = np.eye(3) 
        #self.x = np.array([[self.xi], [self.yi], [self.theta]])


        # Velocidade das rodas enviadas para o robô pelo sistema de comando 
        self.wl = 0     # velocidade da roda esquerda
        self.wr = 0     # velocidade angular da roda direita 



    #definindo uma função para setar a posição do robô
    def setPosition(self,x,y,r,image, time):
        '''
        Atualiza a posição do robô, passando as coordenadas x, y e o raio do robô
        bem como uma imagem que representa a posição do robô naquele momento.
        '''
        #atribuindo tempo
        self.lastTimestamp = time 
        self.newTimestamp = time
        self.dT =self.newTimestamp - self.lastTimestamp

        #calcula valores
        if np.sqrt((x-self.lastPosition[0])**2 + (y-self.lastPosition[1])**2) > 0.5:
            self.position = np.array([round(x, 1), round(y, 1)])
        else:
            self.position = self.lastPosition

        self.radius = round(r, 1)
        self.image = image

        dim= image.shape[1]
        self.viewRect.setDimension(dim)

        #Atualiza nova posição
        self.newPosition = self.position 
        #Atualiza ultima posição
        self.lastPosition = self.position

        #Calcula o vetor deslocamento (direção)
        self.direction = self.newPosition - self.lastPosition
        
        # atualizando limites do objeto
        self.objLimit = Circle(self.radius,Point2D(x,y))

        #setando viewRect do robô
        self.viewRect.updateViewBot(Point2D(x,y))

        #Atualizando posição da borderbox
        self.updateBbox()



    #Atualizar posição do robô
    def updatePosition(self, x, y, r, image, time):
        '''
        Atualiza a posição do robô, passando as coordenadas x, y e o raio do robô
        bem como uma imagem que representa a posição do robô naquele momento.
        '''
        #atribuindo tempo
        self.lastTimestamp = time 
        self.newTimestamp = self.lastTimestamp
        self.dT =self.newTimestamp - self.lastTimestamp


        #avalia se ocorreu uma variação significativa
        #Atualiza ultima posição
        self.lastPosition = self.position

        if np.sqrt((x-self.lastPosition[0])**2 + (y-self.lastPosition[1])**2) > 0.5:
            self.position = np.array([round(x, 1), round(y, 1)])
        else:
            self.position = self.lastPosition
    
        self.radius = round(r, 2)
        self.image = image

        dim= image.shape[1]
        self.viewRect.setDimension(dim)

        #Atualiza nova posição
        self.newPosition = self.position 

        #Calcula o vetor deslocamento (direção)
        self.direction = self.newPosition - self.lastPosition
        
        #ideia de tempo
        self.oldTimestamp = 0
        self.newTimeStamp = 0
        self.dT           = 0 

        # atualizando limites do objeto
        self.objLimit = Circle(self.radius,Point2D(x,y))

        #setando viewRect do robô
        self.viewRect.updateViewBot(Point2D(x,y))

        #Atualizando posição da borderbox
        self.updateBbox()

    def updtPositionImg(self,xi, yi, ri):
        self.xi = xi
        self.yi = yi 
        self.ri = ri 

    #Atualizar informações do robÕ
    def setStatus(self, status):
        '''
            Seta um estado para o robô, informando se ele foi ou não detectado
        '''
        self.detected = status

    #informando cores do carro
    def setColor(self, colorTeam, colorCar1, colorCar2):
        '''
            Seta as cores configuradas para reconhecer esse robô. A cor do time e
            a cor secundária dele.
        '''
        self.colorTeam = colorTeam

        #Cor primária e secundária do robô
        self.colorCar1 = colorCar1
        self.colorCar2 = colorCar2

    #informando raio da borda do carro
    def setRadius(self, radius):
        '''
            Função responsável por setar o raio do objeto robô na imagem.
        '''
        self.radio = round(radius, 2)

    #informando qual a velocidade do objeto
    def getVelocity(self, timestamp):
        '''
            Puxa a velocidade do robô, no momento que foi chamada.
        '''
        #Vejo quanto tempo se passou
        self.oldTimestamp = self.newTimeStamp
        self.newTimeStamp = timestamp
        self.dT = self.newTimeStamp - self.oldTimestamp

        if timestamp != 0: 
            if self.dT > 0.01:  # mínimo de 10ms
                self.velocity = self.direction / self.dT
            else:
                self.velocity = np.array([0, 0])
        else:
            self.velocity = np.array[0,0]

        return self.velocity
    
    #Atualiza borderbox
    def updateBbox(self):
        '''
            Atualiza posição da borda que delimita colisões do robô.
        '''
        #Gerando objeto de informações
        self.objLimit = Circle(Point2D(self.position[0],self.position[1]),self.radius)

        #Gerando uma bbox para sistema de colisões
        self.bbox.attPosition(self.objLimit)

    # prever posição do carro com base na velocidade dele
    # timestamp é o tempo que se passou do ultimo processamento até agora
    # necessário uma classe time para realizar essa lógica
        
    #atualiza quadro de predição do robô
    def predictPosition(self, timestamp):
        '''
            Prevê a posição do robô de acordo com o intervalo de tempo que se pasosu
            Assim ele procura na imagem onde mais provável dele estar.
        '''
        self.getVelocity(timestamp=timestamp)

        #passo para transport a tela que representa a posição do robô
        stepPosition = self.velocity * self.dT

        #transfiro os pontos de identificação para a posição prevista
        self.viewRect.translateViewBot(Point2D(stepPosition[0],stepPosition[1]))

    #recupera o ponto que devo procurar na imagem para encontrar o carro
    # levando em consideração o passo interno do viewRect (dimMatrix)
    def getPredictPosition(self):
        '''
            Retorna o indice da imagem e a dimensão da janela onde estará o robô
        '''
        return self.viewRect.Pe1, self.viewRect.DimMatrix
    
    #função para retornar o status do robô
    def getStatus(self):
        return self.detected

    #puxar as cores do robô para poder realizar o processamento
    def getColors(self):
        return self.colorTeam, self.colorCar1, self.colorCar2


    #setando as cores do time
    def setColor(self, colorT=None, colorP=None, colorS=None ):
        ''' definindo as corres do carro'''
        time = "ALLY" if self.team == ID_Team.TEAM_ALLY else "ENEMY"
        #print("Setando a cor do carro", id, "do time", time)
        self.colorCar1 = colorP 
        self.colorCar2 = colorS
        self.colorTeam = colorT

    #definindo setar cor apenas para o robô
    def setTeamColor(self, colorTeam=None):
        self.colorTeam = colorTeam

class Ball:
    '''
    @GNOMIO: A classe bola é responsável por pegar informações do objeto bola que será utilizado no processo de detecção
    '''
    def __init__(self, x=0, y=0, r=0):
        #posição, raio e direção da boal
        self.position = np.array([x, x])
        self.radius = r
        self.direction = np.array([0, 0])

        #gerando bbox para sistema de colisão
        self.objLimit = Circle(Point2D(x,y),self.radius)
        self.bbox = BorderBox(GeometryType.CIRCLE, self.objLimit)

        #posições da bola na imagem de origem reduzida
        self.xi = 0
        self.yi = 0
        self.ri = 0


        #definindo uma viewBot para a bola
        self.viewBall = ViewBot(Point2D(self.position[0], self.position[1]),int(r+14))

        #Informações do tipo de objeto no sistema
        self.ObjType = ObjTypeMove.MOVING
        self.objTypeSystem = ObjTypeVision.BALL
        
        #informações de posição para cálculo da velocidade
        self.lastPosition = self.position
        self.newPosition = self.position 

        #ideia de tempo
        #novo horário
        self.newTimestamp = 0 

        #antigo horário
        self.oldTimestamp = 0

        #intervalo de tempo atual
        self.dT = 0


        #status de se foi encontrada
        self.status = False 

    #setando posição da bola
    def setPosition(self,x,y,r, timestamp=0):
        '''
        Função responsável para setar o objeto no projeto
        nesse caso o deslocamento se torna nulo
        '''
        #atribuindo tempo
        self.newTimeStamp = timestamp
        self.lastTimestamp = timestamp

        #Atualizando raio
        self.radius = r

        #Atualizando posições do sistema
        self.newPosition = np.array([x, y])
        self.position = self.newPosition 

        self.lastPosition = self.position

        #calculando a direção. No set a direção é 0
        self.direction = self.newPosition - self.lastPosition

        #atualizando tempo
        self.oldTimestamp = self.newTimeStamp
        self.newTimestamp = timestamp
        self.dT = self.newTimestamp - self.oldTimestamp

        #Atualizando posição da borderbox
        self.updateBbox()

        self.status = True 

    #atualizando posição da bola
    def updatePosition(self, x, y,r, timestamp):
        '''
        Função responsável por atualizar a posição do objeto.
        '''

        #Atualizando raio
        self.radius = r

        #Atualizando posições do sistema
        self.lastPosition = self.position
        self.newPosition = np.array([x, y])
        self.position = self.newPosition 
        
        #atualizando direção
        self.direction = self.newPosition - self.lastPosition

        self.oldTimestamp = self.newTimeStamp
        self.newTimestamp = timestamp
        self.dT = self.newTimestamp - self.oldTimestamp

        #Atualizando posição da borderbox
        self.updateBbox()

        self.status = True 

    #recuperando a velocidade da bola
    def getVelocity(self, timestamp):
        '''
            Retorna a velocidade da bola no instante que foi chamada.
        '''
        #Vejo quanto tempo se passou
        self.oldTimestamp = self.newTimeStamp
        self.newTimeStamp = timestamp
        self.dT = self.newTimeStamp - self.oldTimestamp

        #calculo a velocidade 
        if timestamp != 0: 
            if self.dT > 0.01:  # mínimo de 10ms
                self.velocity = self.direction / self.dT
            else:
                self.velocity = np.array([0, 0])
        else:
            self.velocity = np.array[0,0]

        return self.velocity
    
    #Atualiza borderbox
    def updateBbox(self):
        '''
            Essa função é responsável por atualizar a borderbox do objeto bola
            apenas é necessário chamar ela .
        '''
        #Gerando objeto de informações
        self.objLimit = Circle(Point2D(self.position[0],self.position[1]),self.radius)

        #Gerando uma bbox para sistema de colisões
        self.bbox = BorderBox(GeometryType.CIRCLE,self.objLimit)

    #viewbot da bola
    def predictPosition(self,timestamp):
        '''
        Prevê a posição do robô com base no tempo que se passou, para atualizar os valores
        
        Aproximação da posição do robô
        '''
        self.getVelocity(timestamp=timestamp)
        
        #passo para mover a tela
        stepPosition = self.velocity*self.dT

        #transfiro os pontos de identificação
        self.viewBall.translateViewBot(Point2D(stepPosition[0],stepPosition[1]))

    def getPredictPosition(self):
        '''
            Retorna o indice da imagem e a dimensão da janela onde estará a bola
        '''
        return self.viewBall.Pe1, self.viewBall.DimMatrix

    #verificando estado da bola
    def getStatus(self):
        return self.status

    #...
    def setImgPosition(self,xb, yb, rb):
        self.xb = xb
        self.yb = yb 
        self.rb = rb 

    #definindo função para setar a cor da bola para pesquisa
    def setBallColor(self, colorBall):
        self.color = colorBall 
#Definição da classe campo

#Classe do campo
class Field:
    '''
    @GNOMIO: A classe campo é responsável por dar uma visão geral ao sistema de detecção, para poder enquadrar o campo dentro da lógica
    O objeto field terá informações dos jogadores e dos extremos do campos


    É necessário entender que o campo e os objetos detectados nele serão as coordenadas
    em relação ao sistema virtualizado que irá "representar" a situação real.
    '''
    def __init__(self, master):
        '''
            Inicializando o objeto campo com os pontos que serão utilizados
            na lógica dos jogadores. Importante saber que são pontos com coordenadas em cm.
        '''
        #sistema de visão dono do campo
        self.master = master

        #pontos importantes no campo
        self.pivots = [Pivot(id=ID_Pivots.CENTER),Pivot(id=ID_Pivots.PA1),Pivot(id=ID_Pivots.PA2),Pivot(id=ID_Pivots.PA3),Pivot(id=ID_Pivots.PE1),Pivot(id=ID_Pivots.PE2),Pivot(id=ID_Pivots.PE3)]
        
        #áreas dos gols dos jogadores
        self.goalArea =[AreaField(id=ID_Field.GOAL_ALLY),AreaField(id=ID_Field.GOAL_ENEMY)]

        #Área dos goleiros
        self.goalRobotArea = [AreaField(id=ID_Field.GOAL_AREA_ALLY),AreaField(id=ID_Field.GOAL_AREA_ENEMY)]

        #@GNOMIO: As posições do Field são em relações à ViewCapture

        #Setando parâmetros do campo na imagem real
        self.extrems = Quad(Point2D(0,0),Point2D(0,0),Point2D(0,0),Point2D(0,0))
        
        #extremos do campo no ambiente virtual
        self.extremsVirtual = Quad(Point2D(0,0),Point2D(0,0),Point2D(0,0),Point2D(0,0))

        #matrix de homografia
        self.mHomography    = None
        self.invMHomography = None 
        
        #parâmetros relacionados a imagem original
        # aqui irá conter os indices em relação a imagem reduzida!
        self.center = None 
        self.PA1    = None 
        self.PA2    = None 
        self.PA3    = None 
        self.PE1    = None 
        self.PE2    = None 
        self.PE3    = None 

        #Informações do tipo de objeto
        self.ObjType = ObjTypeMove.STATIC
        self.objTypeSystem = ObjTypeVision.FIELD

        #tamanho e comprimento do campo
        self.height: int = 0 
        self.width: int = 0 

        # Inicializar o ambiente OpenCL
        if cv2.ocl.haveOpenCL(): cv2.ocl.setUseOpenCL(True)
        else: print("[VS]: Não foi possível otimizar com OpenCL")

    #Atualizar extremos do campo na imagem original, para realizar cálculos
    def updatePos(self,quad:Quad,width:int,height:int):
        '''
            Atualiza novas posições do campo
        '''
        self.extrems = quad
        self.width = width
        self.height = height

    #atribuindo a matrix de homografia
    def setHomographyMatrix(self,mHomography, invHomo):
        self.mHomography = mHomography
        self.invMHomography = invHomo 

    #setar cada um dos pontos de interesse do campo
    def setPivotPos(self,id:ID_Pivots,px,py):
        '''
            Ajusta a posição de um PIVOT do campo, que são pontos importantes do processamento

        '''
        self.pivots[id].updatePos(px,py)

    #Seta as áreas de gol dos jogadores
    def setAreaGoal(self, id:ID_Field, rect:Quad):
        '''
            Área Útil que contabiliza os gols. Ou seja, a área interna do gol
        '''
        self.goalArea[id].setRect(rect)
        
    #Seta a posição dos goleiros do jogo
    def setAreaRobotGoal(self, id:ID_Field,rect:Quad):
        '''
            Seta a área onde o robô com função de goleiro irá
        '''
        self.goalRobotArea[id].setRect(rect)


    #puxar o valor 
    def getExtrems(self):
        return self.extrems.getPoint()
    
    #definir extremos virtuais
    def virtualExtrems(self, extrems:Quad):
        self.extremsVirtual = extrems 


    #função para desenhar o círculo na imagem
    def drawPointsField(self):
        #desenhar extremos
        pts = self.extrems.getPoint()

        for pt in pts:
            if isinstance(pt, Point2D):
                x,y = pt.getPos()
                x = int(x)
                y = int(x)
            else:
                x,y = pt[0], pt[1]
                x = int(x)
                y = int(x)

            w,h, _ = self.master.frameResult.shape 
            cv2.circle(self.master.frameResult, (x,y),6,(0,0,255),-1)

        #desenhar centro
        #cv2.circle(self.master.frameResult, self.center,6,(0,0,255),-1)
        
        #desenhar pivots

#======================|| Sistema de detecção POO||======================================#
#Vista capturada pelo processamento, que contem a imagem base
class ViewCapture: 
    '''
        Esse classe representa a "vista" capturada pelo sistema de visão com base na imagem
        enviada. Ela irá representar, portanto, um retângulo útil na imagem total, no qual será realizado
        o processamento
    '''
    def __init__(self, Extremes:Quad = Quad(Point2D(0,0),Point2D(0,0),Point2D(0,0),Point2D(0,0))):
        '''
            Esse classe representa a "vista" capturada pelo sistema de visão com base na imagem
            enviada. Ela irá representar, portanto, um retângulo útil na imagem total, no qual será realizado
            o processamento

            Necessário, portanto, enviar as informações do retângulo e o objeto de captura
        '''
        self.Extremes = Extremes        # Extremos da view na imagem reduzida
        self.cooVetor = None            # pontos de interesse 'x,y,w,h' relacionados ao tamanho da janela, que são uma forma rápida de acessar os dados.

    #Modificando os extremos em relação à imagem original
    def setViewCapture(self, Extremes:Quad, cooVetor):
        '''
            Forma indireta de informar quais são os pontos de interesse para o processamento
        '''
        self.Extremes = Extremes
        self.cooVetor = cooVetor

    #Retornar os extremos do ViewCapture
    def getExtremes(self):
        '''
            Retorna os pontos extremos do viewcapture. No caso, um vetor numpy [[a,b],[a,b1],[a,b],[a,b]]
        '''
        return self.Extremes.points

    #puxar as coordenadas da janela
    def getCoorVetor(self):
        return self.cooVetor 
#===============================================================================================
#Classe principal do sistema de visão que irá executar as funções
class VisionSystem:
    '''
    É a classe principal do sistema de visão. Ela é responsável por processar uma imagem
    que pode vim de vários meios e extrair as informações pertinentes que serão utilizadas
    no sistema de visão.

    Ela funciona através de configurações enviadas pelo emulador, um objeto de captura e informar
    se vai ou não utilziar a GPU para agilizar o processamento.
    '''
    #Inicializando objeto do sistema de detecção
    def __init__(self,config: EConfig = EConfig(), debug:bool = False, capture: Capture = None, UseCuda:bool = False, GPUType:GPUType = None):
        '''
            Inicializando o sistema de visão para realizar a captura de dados e tradução.
            Para isso é necessário passar as configurações do emulador (EConfig), o objeto de captura
            (capture) se ele tem ou não cuda  (useCuda) e qual o tipo de GPU (GPUType).
        '''
        #Configurando objetos
        self.createObjs()

        self._countProcess = 0

        #variável que me dirá quantas vezes o sistema de visão foi chamado
        self._count: int            = 0 
        ''' Variável responsavel por dizer quantas vezes foi executado o sistema '''
        self._firstTimeExec: int    = 0 
        ''' Variável que diz quanto tempo se passou desde a primeira execução do código'''
        #Carregando as configurações do sistema de visão
        self.config:EConfig    = config
        
        #objeto de captura internas
        self._capture:Capture  = capture

        #verifica se existe suporte ao CUDA
        self._hasCuda           = UseCuda 
        self._GPUType           = GPUType

        if not self._capture:
            self._capture.GPUMode(self._hasCuda)

        #Verifica 
        self.GPUimg         = None
        self.CPUimg         = None 
        self.emulatorMode   = MODE_IMAGE                #supõe que é imagem

        #verifica o timer necessário para realizar as previsões
        self.timer: HighPrecisionTimer    = None 

        #tempos necessários
        self.dT = 0 
        ''' Aqui é o intervalo de tempo que leva para processar'''


        #gera o objeto para utilizar o cuda
        if(self._hasCuda):
            #variável para guardar o endereço da imagem principal
            self.GPUimg = cv2.cuda.GpuMat()


        #configurações do campo comprimento e largura
        self.fieldWidth             = 0                     # largura do campo
        self.fieldHeight            = 0                     # altura do campo
        self.prop_px_cm             = 1                     # proporção pixel para cm
        self.prop_px_cm_virtual     = 3                     # proporção pixel para cm na imagem virtual

        self.homography_matrix      = None                  # matrix de homografia entre imagem real e virtual
        self.inv_homography_matrix  = None                  # matrix inversa de homografia, relação entre a imagem virtual e a imagem real (caso necessário)

        #variável de debug
        self.debug:bool   = debug                                  # verifica se o processamento usará ou não o debug

        # Coordenada do ponto de origem do novo sistema de coordenadas
        self.xnv     = 67                    
        self.ynv     = 402        

        self.coordOrigin = np.array([67,402])

        #variáveis de controle de tempo de execução
        self.lastMajorTime = 0 
        self.currentTime   = 0                  # tempo atual de execução


        #Tamanho padrão da bola
        self.ballRadiusP = 2.135 #cm

        #tamanho do campo para utilizar
        self.modDpCm     = 0        
        #coordenadas dos pontos importantes na imagem virtual
        #Essas coordenadas são em pixels, para passar para o sistema de coordenadas O'
        #Necessário utilizar a função getVirtualPoint()

        #extremos do campo virtual
        self.fieldP1v  =   np.array([97,12])
        self.fieldP2v  =   np.array([547,12])
        self.fieldP3v  =   np.array([547,402])
        self.fieldP4v  =   np.array([97,402])
        
        #centro do campo virtual
        self.fieldCenterv  =   np.array([322,207])

        #pivots virtual
        self.PA1v   =   np.array([210,87])
        self.PA2v   =   np.array([210,207])
        self.PA3v   =   np.array([210,327])
        self.PE1v   =   np.array([435,87])
        self.PE2v   =   np.array([435,207])
        self.PE3v   =   np.array([435,327])

        #area goleiro aliado virtual
        self.GA1v   =   np.array([97,102])
        self.GA2v   =   np.array([142,102])    
        self.GA3v   =   np.array([142,312])  
        self.GA4v   =   np.array([97,312])

        #area interna do goleiro aliado virtual
        self.GAI1v  =   np.array([67,147])
        self.GAI2v  =   np.array([97,147])
        self.GAI3v  =   np.array([97,267])
        self.GAI4v  =   np.array([67,267])
        
        #area goleiro aliado virtual
        self.GE1v   =   np.array([502,102])
        self.GE2v   =   np.array([547,102])    
        self.GE3v   =   np.array([547,312])  
        self.GE4v   =   np.array([502,312])

        #area interna do goleiro aliado virtual
        self.GEI1v  =   np.array([547,147])
        self.GEI2v  =   np.array([577,147])
        self.GEI3v  =   np.array([577,267])
        self.GEI4v  =   np.array([547,267])

        # área aliada
        #meios dos lados virtual
        self.fieldP12v  =   np.array([322,12])
        self.fieldP34v  =   np.array([322,402])



        #Variáveis internas do sistema de visão que serão importantes para o processamento
        #Configurações
        self.offSetWindow       = 10                 
        '''Tamanho extra de janela utilizada'''
        self.offSetErode        = 0                    
        '''Quantidade padrão de erosões na imagem'''
        self.dimMatrix          = 25                     
        '''Dimensão da matriz de convolução na imagem'''
        self.Thrashhold         = 235                   
        '''Limiar de binarização da imagem'''
        self.pixelWidth         = 1
        '''Tamanho de um pixel normal'''

        #Imagens
        self.frameOrigin        = None             
        '''responsável por guardar a imagem do campo'''
        self.ballImg            = None 
        ''' Imagem da bola que é utilizada para processar e procurar os jogadores'''
        self.fieldReduce        = None              
        '''Imagem do campo reduzida'''
        self.frameResult        = None              
        '''Imagem final já reduzida e processada'''
        self.imgReduce          = None              
        '''Imagem reduzida para utilizar no processamento'''
        self.binaryAllTeam      = None 

        #Imagem virtual que será utilizada para o processamenot
        self.virtual            = cv2.imread("src/images/CampoVirtual.png")
        self.virtualImg         = self.virtual.copy()   #As manipulações da imagem serão feitas nessa aqui

        #Imagens binarizadas utilizadas no código
        self.binaryObjects      = None              # Imagem binária dos objetos
        self.binaryPlayers      = None              # Imagem Binária dos Jogadores
        self.binaryTeam         = None              # Imagem Binária do Time
        self.binaryBall         = None              # Imagem binária da bola
        self.binReduceField     = None              # Imagem binarizada do campo reduzido tratada
        self.binField           = None              # Imagem binarizada do campo original tratada


        #Cores dos jogadores salvas para salvar nos jogadores
        self.ballColor          = None              # Cor da bola
        self.allyColor          = None              # Cor do time aliado
        self.enemyColor         = None              # Cor do time inimigo
        self.goalAllyColor1     = None              # cor 1 do goleiro aliado
        self.goalAllyColor2     = None              # cor 2 do goleiro aliado
        self.atk1AllyColor1     = None              # cor 1 do atacante 1
        self.atk1AllyColor2     = None              # cor 2 do atacante 1
        self.atk2AllyColor1     = None              # cor 1 do atacante 2
        self.atk2AllyColor2     = None              # cor 2 do atacante 2

        #cores padrões dos objetos para o sistema:    #Carrega os vetores de cores claras e escuras de objetos gerais 
        self.objectsDarkColor   = np.array([0,10,130]) #[0,10,150]
        self.objectsLightColor  = np.array([179,255,255])

        #definições estruturais do código
        self.playerRadius       = 0
        self.mainColorRadius    = 0
        self.secColorRadius     = 0

        #definições úteis dentro do código
        self.ally_lower_bound   = None          # valor mínimo para detectar aliados
        self.ally_upper_bound   = None          # valor máximo para detectar os aliados
        self.enemy_lower_bound  = None          # valor mínimo para detectar inimigos
        self.enemy_upper_bound  = None          # valor máximo para detectar inimigos

        # variáveis internas para realizar o tratamento de dados
        self.playersCount       = 0
        self.alliesCount        = 0
        self.enemiesCount       = 0

        self.playersWindows     = [None, None, None, None, None, None]

        self.alliesWindows      = [None, None, None]
        self.enimiesWindows     = [None, None, None]

        #lista de threads a serem utilizadas pelo objeto
        self._threads           = []
        self._lockThread        = threading.Lock() #trava para controle de acesso por threads
        self._lockProc          = threading.Lock()

        #Variável importante para ditar quanto tempo até a próxima atualização de dados
        self.newProcTime        = 10
        #Extrai os dados do objeto de configuração 
        self.toMineData()

        #Atualiza as funções com base no modo que foi determinado para elas
        self.choseModeFunctions()

        #construir o campo
        self.buildField()
    
    # Implementação da lógica de processamento para várias coisas
    # Esse é o PROC MAIOR
    def proc(self, img, debug,isT=False):
        self.lastMajorTime = self.timer.getElapsedTime()

        #temporizador
        self._firstTimeExec = (self.currentTime - self.lastMajorTime)/1000.0

        # realizo o processamento na imagem
        self.debug = debug 

        #zerando a imagem de virtualização
        self.virtualImg = self.virtual.copy()

            #imagem utilizada 
        imgP = img.copy()
        if img is not None:
            # Detectando o campo
            wbCmField = self.detect_field(imgP,debug)
            '''
                OBS: A ideia é que ele apenas busque as outras coisas quando detectar um 
                campo de tamanho considerável na imagem, caso contrário, ele não realiza os cálculos
            '''
            if wbCmField != -1 and np.abs(wbCmField - self.fieldWidth) <= 30: #margem de erro
                #sessão apra tentar corrigir o erro de cvtColor
                if self.fieldReduce is None or self.fieldReduce.shape[1] < 100:
                    print("FieldReduce é none ou muito pequeno")
                    self.fieldReduce = self.frameOrigin
                    

                    #detectando bola
                try:
                    self.detect_ball(self.fieldReduce, self.ballColor, debug)
                except:
                    try: 
                        self.detect_ball(self.fieldReduce, self.ballColor, debug)
                    except Exception as e:
                            print("[VS]: Não foi possível detectar a bola, pois:\n",e)

                #detectando jogadores
                try:
                    self.detect_players(self.fieldReduce, debug,isT=isT)

                except:

                    traceback.print_exc()
                    try:
                        self.detect_players(self.fieldReduce, debug, isT=isT)
                    except Exception as e:
                        print("[VS]: Não foi possível detectar os players, pois: \n",e)
                        traceback.print_exc()
                #desenhar o campo, caso esteja na opção debug
                if debug:
                    self.field.drawPointsField()
                        
                    #imprimindo pontos no virtual
                    cv2.circle(self.virtualImg, self.fieldP1v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.fieldP2v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.fieldP3v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.fieldP4v,2,(0,0,255),-1)
                        
                    cv2.circle(self.virtualImg, self.fieldCenterv,2,(0,0,255),-1)

                    cv2.circle(self.virtualImg, self.PA1v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.PA2v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.PA3v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.PE1v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.PE2v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.PE3v,2,(0,0,255),-1)

                    cv2.circle(self.virtualImg, self.GA1v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.GA2v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.GA3v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.GA4v,2,(0,0,255),-1)

                    cv2.circle(self.virtualImg, self.GAI1v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.GAI2v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.GAI3v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.GAI4v,2,(0,0,255),-1)

                    cv2.circle(self.virtualImg, self.GE1v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.GE2v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.GE3v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.GE4v,2,(0,0,255),-1)

                    cv2.circle(self.virtualImg, self.GEI1v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.GEI2v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.GEI3v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.GEI4v,2,(0,0,255),-1)

                    cv2.circle(self.virtualImg, self.fieldP12v,2,(0,0,255),-1)
                    cv2.circle(self.virtualImg, self.fieldP34v,2,(0,0,255),-1)

                    #ponto de referência O´
                    cv2.circle(self.virtualImg, (self.xnv, self.ynv),3,(0,255,255),-1)
                    #desenhando todos os pontos na imagem virtual
                
                self.drawAllRobots()

                #testanto função de detectar jogadores
                return self.frameResult
            else:
                self.drawAllRobots()
                return img
        else:
            self.drawAllRobots()
            return img


    #função para prever posição dos jogadores e encontrar onde estão
    # Esse é um PROC MENOR
    def predictObjects(self, img, tms):
        '''
            O objetivo desta função é prever qual a posição dos jogadores, para isso é necessário que ele
            tenha informações de tempo guardadas para que possa verificar isso.

            imgOrigin é a imagem que vem da câmera, ela será recortada de acordo com o ViewRect
        '''

        #preciso puxar a imagem original
        x_w = self.viewCapture.cooVetor[0]
        y_w = self.viewCapture.cooVetor[1]
        w_w = self.viewCapture.cooVetor[2]
        h_w = self.viewCapture.cooVetor[3]
        
        #Imagem para processamento é uma janela da imagem original passada
        self.fieldReduce = img[y_w:y_w+h_w,x_w:x_w+w_w]
        self.frameResult = self.fieldReduce

        #só criando outra variável
        timestamp = tms 

        if not hasattr(self, 'executor'):
            self.executor = ThreadPoolExecutor(max_workers=2)

        tasks =[
            (self._processAlliesAndBall, timestamp),
            (self._processEnemies, timestamp)
        ]

        results = self.executor.map(lambda task: task[0](*task[1]), tasks)
        
        self.drawAllRobots()

    #função para processar os aliados e a bola
    def _processAlliesAndBall(self, timestamp):
        # Processa a bola e todos os aliados
        self.predictBall(timestamp)
        self.predictRobot(ID_Team.TEAM_ALLY, ID_Robots.ROBOT_ALLY_GOAL, timestamp)
        self.predictRobot(ID_Team.TEAM_ALLY, ID_Robots.ROBOT_ALLY_1, timestamp)
        self.predictRobot(ID_Team.TEAM_ALLY, ID_Robots.ROBOT_ALLY_2, timestamp)

    #função para processar os inimigos
    def _processEnemies(self, timestamp):
        # Processa todos os inimigos
        self.predictRobot(ID_Team.TEAM_ENEMY, ID_Robots.ROBOT_ENEMY_GOAL, timestamp)
        self.predictRobot(ID_Team.TEAM_ENEMY, ID_Robots.ROBOT_ENEMY_1, timestamp)
        self.predictRobot(ID_Team.TEAM_ENEMY, ID_Robots.ROBOT_ENEMY_2, timestamp) 
    
    #lógica completa de processamento do sistema de visão
    def processImg(self, img, debug):
        '''
            Contém a lógica completa de processamento da imagem, considerando 
            a quantidade de execuções.
        '''
        self.debug = debug 

        #Reseta informações
        if self.emulatorMode == MODE_IMAGE:
            self._count = 0

        #self.frameOrigin = self.upSaturation_noCuda(img) 
        self.frameOrigin = img 

        #puxa o tempo
        self.currentTime  = self.timer.getElapsedTime()
        
        #verifica se suporta otimização com a GPU
        if self._hasCuda:
            self.choseModeFunctions()

        #verifica contagem de tempo interna da função 
        if  self._firstTimeExec < self.newProcTime: #segundos
            #somando contador

            self._count = self._count +1

            if self._count <=3:
                #processamento maior
                self.proc(img,debug)
                
            else:
                print("Execução com processamento menor")
                #atualizo contador
                self._firstTimeExec = (self.currentTime - self.lastMajorTime)/1000.0
                
                #processamento menor 
                self.predictObjects(img,tms = self.currentTime)
            
        else: 
            #zera a contagem
            self._count = 0 

            #zerando a imagem de virtualização
            self.virtualImg = self.virtual.copy()

            self.majorTime = self.timer.getElapsedTime()
            
            #processamento maior 
            self.proc(img, debug)

        tmf = self.timer.getElapsedTime()
        self.dT = tmf - self.currentTime
                
        #Exibir qual o tempo atual, e exibirzd
        #retorno da função

        return self.frameResult


    #Puxando as imagens de debug
    def getDebugImages(self):
        if self.debug:
            return self.binaryObjects, self.binaryBall, self.binaryPlayers, self.binaryAllTeam
        else:
            #não está em debug
            return None, None, None, None 
        
        
    #Inicializando os objetos do sistema
    def createObjs(self):
        '''
            @GNOMIO: função responsável por criar os objetos do sistema de visão.
            Sendo eles a bola, os robôs, o campo e as áreas do campo.

            Esses objetos são inicializados sem informação, e só são cadastrados dps
        '''
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
        self.field = Field(self)

        #gerando a viewCapture
        self.viewCapture = ViewCapture()

    # atribuindo os valores dos pontos do campo
    def buildField(self):
        '''
            Atribuindo os valores do campo que já foram carregados no campo

            Necessário converter dados para cm e nas coordenadas de O' (xn,yn)
        '''
        #adicionando extremidades virtuais 
        virtualExtrems = Quad(P1 = self.getPointVirtual(Point2D(self.fieldP1v[0],self.fieldP1v[1])),
                              P2 = self.getPointVirtual(Point2D(self.fieldP2v[0],self.fieldP2v[1])),
                              P3 = self.getPointVirtual(Point2D(self.fieldP3v[0],self.fieldP3v[1])),
                              P4 = self.getPointVirtual(Point2D(self.fieldP4v[0],self.fieldP4v[1])))

        self.field.virtualExtrems(virtualExtrems)

        #adicionando pivots (Convertendo todos para cm)
        x, y = self.getPointVirtual(self.PA1v)
        self.field.setPivotPos(ID_Pivots.PA1, x,y)

        x, y = self.getPointVirtual(self.PA2v)
        self.field.setPivotPos(ID_Pivots.PA2, x,y)

        x, y = self.getPointVirtual(self.PA3v)
        self.field.setPivotPos(ID_Pivots.PA3, x,y)

        x, y = self.getPointVirtual(self.PE1v)
        self.field.setPivotPos(ID_Pivots.PE1, x,y)

        x, y = self.getPointVirtual(self.PE2v)
        self.field.setPivotPos(ID_Pivots.PE2, x,y)

        x, y = self.getPointVirtual(self.PE3v)
        self.field.setPivotPos(ID_Pivots.PE3, x,y)

        x, y = self.getPointVirtual(self.fieldCenterv)
        self.field.setPivotPos(ID_Pivots.CENTER, x,y)
        
        
        #gerando áreas do gol onde os goleiros ficarão
        #areas do goleiro aliado
        goalAllyArea = Quad(P1 = self.getPointVirtual(Point2D(self.GA1v[0],self.GA1v[1])),
                              P2 = self.getPointVirtual(Point2D(self.GA2v[0],self.GA2v[1])),
                              P3 = self.getPointVirtual(Point2D(self.GA3v[0],self.GA3v[1])),
                              P4 = self.getPointVirtual(Point2D(self.GA4v[0],self.GA4v[1])))
        
        self.field.setAreaRobotGoal(id=ID_Field.GOAL_AREA_ALLY,rect= goalAllyArea)


        #áreas do goleiro inimigo
        goalEnemyArea = Quad(P1 = self.getPointVirtual(Point2D(self.GE1v[0],self.GE1v[1])),
                              P2 = self.getPointVirtual(Point2D(self.GE2v[0],self.GE2v[1])),
                              P3 = self.getPointVirtual(Point2D(self.GE3v[0],self.GE3v[1])),
                              P4 = self.getPointVirtual(Point2D(self.GE4v[0],self.GE4v[1])))
        
        self.field.setAreaRobotGoal(id=ID_Field.GOAL_AREA_ENEMY, rect=goalEnemyArea)

        #gerando áreas internas dos gols onde serão pontuados
        #areas do goleiro aliado
        goalAlly = Quad(P1 = self.getPointVirtual(Point2D(self.GAI1v[0],self.GAI1v[1])),
                        P2 = self.getPointVirtual(Point2D(self.GAI2v[0],self.GAI2v[1])),
                        P3 = self.getPointVirtual(Point2D(self.GAI3v[0],self.GAI3v[1])),
                        P4 = self.getPointVirtual(Point2D(self.GAI4v[0],self.GAI4v[1])))
        
        self.field.setAreaGoal(id=ID_Field.GOAL_ALLY, rect=goalAlly)


        #áreas do goleiro inimigo
        goalEnemy = Quad(P1 = self.getPointVirtual(Point2D(self.GEI1v[0],self.GEI1v[1])),
                         P2 = self.getPointVirtual(Point2D(self.GEI2v[0],self.GEI2v[1])),
                         P3 = self.getPointVirtual(Point2D(self.GEI3v[0],self.GEI3v[1])),
                         P4 = self.getPointVirtual(Point2D(self.GEI4v[0],self.GEI4v[1])))
        
        self.field.setAreaGoal(id=ID_Field.GOAL_ENEMY, rect=goalEnemy)


    #extrair dados vindos do emulador 
    def toMineData(self):
        '''
        Essa função extrai as informações vindas do Emulador no objeto EConfig.
        '''
        print("[VisionSystem]: Configurações carregadas")
        #puxando valores do objeto de configuração
        self.offSetWindow   = self.config.offSetWindow  
        self.offSetErode    = self.config.offSetErode   
        self.dimMatrix      = self.config.dimMatrix     
        self.Trashhold      = self.config.Trashhold     
        self.fieldWidth     = self.config.fieldWidth    
        self.fieldHeight    = self.config.fieldHeight   
        self.ballColor      = self.config.ballColor     
        self.allyColor      = self.config.allyColor     
        self.enemyColor     = self.config.enemyColor     
        self.goalAllyColor1 = self.config.goalAllyColor1
        self.goalAllyColor2 = self.config.goalAllyColor2
        self.atk1AllyColor1 = self.config.atk1AllyColor1
        self.atk1AllyColor2 = self.config.atk1AllyColor2 
        self.atk2AllyColor1 = self.config.atk2AllyColor1
        self.atk2AllyColor2 = self.config.atk2AllyColor2
        self.emulatorMode   = self.config.emulatorMode
        self.timer          = self.config.timer

        #atribuindo cores principais aos robôs
        self.robotAlly1.setTeamColor(self.allyColor)
        self.robotAlly2.setTeamColor(self.allyColor)
        self.robotAllyG.setTeamColor(self.allyColor)

        self.robotEnemy1.setTeamColor(self.enemyColor)
        self.robotEnemy2.setTeamColor(self.enemyColor)
        self.robotEnemyG.setTeamColor(self.enemyColor)


        #atribuindo cores principais aos robôs
    #definir novas configurações
    def setConfigEmulator(self, config:EConfig):
        '''
            Essa função seta uma nova configuração para o sistema de visão pelo emulador
        '''
        self.config = config
        self.toMineData()

    
    #método para retornar o processamento
    def getViewCapture(self):
        '''
            Retorna a janela de interesse do sistema de visão
        '''
        return self.viewCapture
    
    #definindo modo para resetar configurações
    def _resetVs(self):
        '''
            Responsável por resetar as configurações do Sistema de Visão, sendo necessário
            recarregar o código do Emulador.
        '''
        #recria objetos para não ter problema na próxima execução
        self.createObjs()

        #Verifica 
        self.GPUimg         = None
        self.CPUimg         = None 
        self.emulatorMode   = MODE_IMAGE                #supõe que é imagem

        #gera o objeto para utilizar o cuda
        if(self._hasCuda):
            #variável para guardar o endereço da imagem principal
            self.GPUimg = cv2.cuda.GpuMat()


        #configurações do campo comprimento e largura
        self.fieldWidth     = 0                     # largura do campo
        self.fieldHeight    = 0                     # altura do campo
        self.prop_px_cm     = 1                     # proporção pixel para cm
               

        #variáel de debug
        self.debug = False                          # verifica se o processamento usará ou não o debug

        #Variáveis internas do sistema de visão que serão importantes para o processamento
        #Configurações
        self.offSetWindow   = 10                 
        '''Tamanho extra de janela utilizada'''
        self.offSetErode    = 0                    
        '''Quantidade padrão de erosões na imagem'''
        self.dimMatrix      = 25                     
        '''Dimensão da matriz de convolução na imagem'''
        self.Thrashhold     = 235                   
        '''Limiar de binarização da imagem'''
        self.pixelWidth     = 1
        '''Tamanho de um pixel normal'''

        #Imagens
        self.frameOrigin    = None             
        '''responsável por guardar a imagem do campo'''
        self.ballImg        = None 
        ''' Imagem da bola que é utilizada para processar e procurar os jogadores'''
        self.fieldReduce    = None              
        '''Imagem do campo reduzida'''
        self.frameResult    = None              
        '''Imagem final já reduzida e processada'''
        self.imgReduce      = None              
        '''Imagem reduzida para utilizar no processamento'''
        
        #informações úteis para o processamento
        #Imagens binarizadas utilizadas no código
        self.binaryObjects  = None              # Imagem binária dos objetos
        self.binaryPlayers  = None              # Imagem Binária dos Jogadores
        self.binaryTeam     = None              # Imagem Binária do Time
        self.binaryBall     = None              # Imagem binária da bola
        self.binReduceField = None              # Imagem binarizada do campo reduzido tratada
        self.binField       = None              # Imagem binarizada do campo original tratada


        #Cores dos jogadores salvas para salvar nos jogadores
        self.ballColor          = None              # Cor da bola
        self.allyColor          = None              # Cor do time aliado
        self.enemyColor         = None              # Cor do time inimigo
        self.goalAllyColor1     = None              # cor 1 do goleiro aliado
        self.goalAllyColor2     = None              # cor 2 do goleiro aliado
        self.atk1AllyColor1     = None              # cor 1 do atacante 1
        self.atk1AllyColor2     = None              # cor 2 do atacante 1
        self.atk2AllyColor1     = None              # cor 1 do atacante 2
        self.atk2AllyColor2     = None              # cor 2 do atacante 2

        #cores padrões dos objetos para o sistema:    #Carrega os vetores de cores claras e escuras de objetos gerais 
        self.objectsDarkColor = np.array([0,10,130]) #[0,10,150]
        self.objectsLightColor = np.array([169,255,255])

        #definições estruturais do código
        self.playerRadius       = 0
        self.mainColorRadius    = 0
        self.secColorRadius     = 0

        #definições úteis dentro do código
        self.ally_lower_bound   = None          # valor mínimo para detectar aliados
        self.ally_upper_bound   = None          # valor máximo para detectar os aliados
        self.enemy_lower_bound  = None          # valor mínimo para detectar inimigos
        self.enemy_upper_bound  = None          # valor máximo para detectar inimigos

        # variáveis internas para realizar o tratamento de dados
        self.playersCount   = 0
        self.alliesCount    = 0
        self.enemiesCount   = 0

        self.playersWindows = [None, None, None, None, None, None]

        self.alliesWindows  = [None, None, None]
        self.enimiesWindows = [None, None, None]

        self._threads       = []

    #função para gerenciar threads na CPU
    def addThreadsPredict(self):
        ''' Adiciono uma nova thread a fila de processamento'''
        with ThreadPoolExecutor(max_workers=8) as executor:
            self._threads.append(executor.submit(self.predictBall, self.timestamp))
    
    #iniciar as threads
    def startThreads(self):
        '''Inicia todas as threads e espera elas finalizar'''
        for threads in self._threads:
            threads.result()

    # escolhe as funções da classe caso tenha ou não suporte ao cuda
    def choseModeFunctions(self):
        '''
            Atualiza as referências de função para as implementações disponíveis.
            Removidas as versões CUDA — todas apontam para as implementações CPU (sem sufixo).
        '''
        print("[VisionSystem]: Configurando as funções para o método solicitado")
        # Apontar para as versões sem sufixo (CPU)
        self.gray_scale     = self.gray_scale
        self.median_blur    = self.median_blur
        self.highlight_img  = self.highlight_img
        self.binarize_up    = self.binarize_up
        self.treat_noise    = self.treat_noise
        self.reduce_field   = self.reduce_field
        self.detect_ball    = self.detect_ball
        self.detect_field   = self.detect_field
        self.detect_players = self.detect_players

    #função para retornar homografia entre dois sistemas de pontos
    def getHomographyMatrix(self, ptsSrc, ptsFinal):
        '''
            Essa função retorna a matrix 3x3 de homografia entre dois planos
            nesse caso, a imagem de detecção e uma imagem virtual. Nesse caso, a matrix vai mapear os pontos de entrada nos pontos de saída.

            Obs: A imagem de saída tem as dimensões de 645 por 413 px, e a proporção px/cm = 3
            Além disso, já foi configurado para esse calculo ser realizado com os pontos extremos do campo.

            Essa matrix fica salva no sistema de visão para poder realizar as devidas operações
            
            ### Variáveis
            - ptsSrc: conjunto de quatro pontos de entrada da imagem original
            - ptsFinal: Conjunto de pontos correspondentes na imagem final

            # Necessário que essas variáveis sejam vetores array.
        '''
        ptsSrc = np.array(ptsSrc, dtype='float32')
        ptsFinal = np.array(ptsFinal, dtype='float32')

        self.homography_matrix, _   =   cv2.findHomography(ptsSrc, ptsFinal)

        if self.homography_matrix is not None and np.linalg.cond(self.homography_matrix) < 1 / np.finfo(self.homography_matrix.dtype).eps:
            self.inv_homography_matrix  =   np.linalg.inv(self.homography_matrix)
        else:
            # A matriz de homografia é singular e não pode ser invertida
            self.inv_homography_matrix = np.eye(3)  # Matriz identidade 3x3
            print("[ERROR]: Matriz de homografia singular e foi substituída por uma matriz identidade.")

    #Transformar valores 
    def transformPoint(self, ptSrc):
        '''
            Ela utiliza a matrix de homografia para transformar um ponto da imagem original num ponto da imagem
            virtual. Realizando essa conversão é possível saber uma boa aproximação, e desconsidera as distorções.
        '''

        ptSrc = np.array([[[ptSrc[0], ptSrc[1]]]], dtype=np.float32)
        ponto_transformado = cv2.perspectiveTransform(ptSrc, self.homography_matrix)
        return ponto_transformado[0][0]

    #aplica transformação inversa no ponto para recuperar o valor
    def invTransformPoint(self, ptSrc):
        '''
            Realiza o trabalho inverso no TransformPoint, retornando para o espaço original da imagem.
        '''
        ptSrc = np.array([[[ptSrc[0], ptSrc[1]]]], dtype=np.float32)
        ponto_transformado = cv2.perspectiveTransform(ptSrc, self.inv_homography_matrix)
        return ponto_transformado[0][0]
        
    #Passa os indices da matrix final e transforma em valores em cm
    def getPointVirtual(self, ptSrc):
        '''
            Com o "ptSrc" da imagem virtual é encontrado sua posição em relação ao
            novo sistema de coordenadas
        
            x = ptSrc[0]
            y = ptSrc[1]

            #   coordenada final
            x_f = (x - self.xnv)/3
            y_f = (self.ynv - y)/3
        '''

        #   transforma o ponto no novo sistema de coordenadas
        x = ptSrc[0]
        y = ptSrc[1]

        #   coordenada final
        x_f = (x - self.xnv)/3
        y_f = (self.ynv - y)/3

        #caso a função seja utilizada num objeto Point2D, ela funciona assim:

        return x_f,y_f

    #com a posição em O' (em cm), transforma num índice na imagem:
    def getImageIndice(self,ptSrc):
        '''
            Pega o valor do ponto em cm, e transforma em índices para a imagem virtual
            para poder, então desenhar-lo.
        '''

        x_f =int(ptSrc[0]*3 +self.xnv)
        y_f = int(self.ynv-ptSrc[1]*3)

        return x_f, y_f

    #definindo uma função para retornar a coordenada na imagem reduzida
    def getImageRealIndice(self, ptSrc):
        '''
            Função responsável por retornar o ponto para a dimensão da imagem reduzida, com o indice

        '''
        #pego os valores dos indices na imagem virtual
        x_i, y_i = self.getImageIndice(ptSrc)
    
        #pego os valores dos indices na imagem virtual e aplica a homografia inversa
        #retornando a imagem reduzida
        return self.invTransformPoint([x_i, y_i])



    def getObjects(self):
        '''
            Função responsável por retornar os objetos do sistema de visão

        '''
        #construindo dicionário com os objetos 
        objects = {
            ID_Objects.ALLIES:self.allyTeam,
            ID_Objects.ENEMIES: self.enemyTeam,
            ID_Objects.BALL:self.ball,
            ID_Objects.FIELD:self.field,
            'timestamp': self.dT 
        }

        return objects 
    
    #===============| Definindo funções básicas|==============================
    # ============= métodos sem suporte ao CUDA =====================
    #puxando imagem
    def load_image(self, imgPath):
        '''
            Função que carrega imagem na CPU por meio de um caminho (imgPath). Sem usar a GPU
        '''
        self.imgOrigim = cv2.imread(imgPath)
        if(self._hasCuda):
            has = cv2.cuda.GpuMat()
            self.imgOrigi_gpu = has.upload(self.imgOrigim)
            return self.imgOrigi_gpu
        else:
            return self.imgOrigim        
    
    #transformando imagem em tons de cinza
    def gray_scale(self,img):
        '''
            Coloca a imagem passada em tons de cinza, Sem usar a GPU
        '''
        return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    #aplicando o filtro mediana para possíveis ruídos
    def median_blur(self, img, kernelSize = 3):
        '''
            Aplica o filtro de mediana para reduzir ruídos. Sem usar a GPU.
        '''
        return cv2.medianBlur(img, kernelSize)
    
    #binarizando a imagem indo de um limir até 255
    def binarize_up(self, img, threshold=150):
        '''
            Binariza a imagem por meio de um threshold, ou seja, um limiar
            de intensidade dos pixels. Para isso, a imagem tem que estar em
            tons de cinza. Tratada pela função median_blur().
        '''
        _,bin = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY)
        return bin

    #trata ruídos da imagem binarizada
    def treat_noise(self, binImg, it=1):
        '''
            Trata o ruído de imagens binarizadas.
        '''
        structElem = cv2.getStructuringElement(cv2.MORPH_CROSS, (3,3))
        binImgProc = cv2.erode(binImg, structElem, iterations=it)
        return binImgProc
    
    #recuperando objeto de maior área
    def get_object(self,img):
        '''
            Retorna o maior objeto encontrado
        '''
        contours, _ = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        return contours[0]
    
    #recuperando coordenadas extremas que englobam o objeto maior 
    def get_perspective(self, obj):
        '''
            Retorna um retângulo que envolve o objeto passado, e a partir disso
            retorna x,y, x+w e y+h
        '''
        x,y,w,h = cv2.boundingRect(obj)
        return x,y,x+w,y+h
    
    #função para realçar objetos brilhantes na imagem
    def highlight_img(self, img, dim = 25):
        '''
            Realça objetos brilhantes na imagem. Contudo, a imagem deve estar em
            tons de cinza.
        '''
        structElem = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(dim,dim))
        imgProc = cv2.morphologyEx(img, cv2.MORPH_TOPHAT, structElem)
        imgProc = cv2.morphologyEx(imgProc, cv2.MORPH_TOPHAT, structElem)

        #ajuste de contraste
        imgTrat = cv2.add(imgProc, imgProc)
        imgTrat = cv2.add(imgTrat, imgTrat)
        return imgTrat
    
    #função para reduzir a imagem original
    def reduce_window(self, img, coorVetor, d=10):
        '''
            Reduz a imagem numa parte dela com base nas coordenadas x,y,x+w,y+h
            Pegando assim uma menor parte da imagem para processar
        '''
        try:
            #recuperando dados do vetor coordenada
            x,y,w,h = coorVetor[0],coorVetor[1],coorVetor[2],coorVetor[3]

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
    def reduce_field(self, BinImg, Img, fieldWidth, d=10):
        '''
            Função responsável por reduzir a imagem tomando como base a imagem do campo
            e então realizar o processamento nela
        '''
        #Diminuindo a dimensão da imagem para caber apenas o campo
        cont, __ = cv2.findContours(BinImg, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                
        # print(f"Área do contorno encontrado: {contour_area}")
        if not cont:
            print("[SystemVision]/[REDUCE_FIELD]: Nenhum contorno encontrado.")
            return BinImg, Img, [0, 0, 0, 0]
        

        try:
            #objT = cont[0] #Encontra o objeto maior, nesse caso o campo, e então filtrarei a imagem para esse ponto
            objT = max(cont, key=cv2.contourArea)
            
            threshold = 50

            #Obtendo os vértices do retângulo'
            x,y,w,h = cv2.boundingRect(objT) #Coordenadas da nova imagem

            #Esse valor x,y,w,h corresponde  
            #Vetor das coordenadas
            cooVetor = [x,y,w,h]

            #Os pontos iniciais são dentro de uma janela com um "offset"
            #pontos iniciais
            if x-d < 0 or y-d < 0:
                d= 10


            pi = np.float32([[x-d,y-d],[x+w+d,y-d],[x-d,y+h+d],[x+w+d,y+h+d]])
            # Extrair região de interesse da imagem
            img_Reduce = Img[int(y-d):int(y+h+d), int(x-d):int(x+w+d)]
            bin_Reduce = BinImg[int(y-d):int(y+h+d), int(x-d):int(x+w+d)]

            #@saulo: Essas imagens reduzidas seriam o meu ponto de partida para a detecção
            #@saulo: terá várias conversões no meio do código para deixar mais precisos

            #Pontos extremos da viewCapture
            rect = Quad(Point2D(pi[0, 0], pi[0, 1]), Point2D(pi[1, 0], pi[1, 1]),
                 Point2D(pi[3, 0], pi[3, 1]), Point2D(pi[2, 0], pi[2, 1]))
            
            #Gerando o objeto ViewRect (Retângulo envolvente)
            self.viewCapture.setViewCapture(rect, cooVetor) 

        except Exception as e: 
            print("[SystemVision]F[REDUCE_FIELD]: Erro ao reduzir o campo.\n",e)
            #Se ele não conseguir, retorna a imagem inicial...
            bin_Reduce = BinImg
            img_Reduce = Img
            self.prop_px_cm = 1

        if w > threshold and h > threshold:
            pixelWidth = min(w, h)
            self.convert_measures(fieldWidth, pixelWidth)
            
        else:
            self.prop_px_cm = self.prop_px_cm



        return bin_Reduce, img_Reduce, cooVetor

    #sort values
    def sort_points(self, points):
        # Ordena os pontos primeiro pelo y (crescente) e depois pelo x (crescente)
        points = sorted(points, key=lambda p: (p[1], p[0]))
        
        # Identificar os dois pontos superiores e os dois pontos inferiores
        top_points = points[:2]
        bottom_points = points[2:]
        
        # Ordenar os pontos superiores por x (crescente)
        top_points = sorted(top_points, key=lambda p: p[0])
        
        # Ordenar os pontos inferiores por x (crescente)
        bottom_points = sorted(bottom_points, key=lambda p: p[0])
        
        # Retornar os pontos na ordem desejada: [top_right, top_left, bottom_left, bottom_right]
        sorted_points = np.array([top_points[0], top_points[1], bottom_points[1], bottom_points[0]], dtype=np.int32)
        
        return sorted_points

    #puxando intervalos de cores
    def create_color_bounds(self, color_array):
        '''
            Cria as bandas inferior e superior em HSV por meio de um array
            que passa a informação em HSV dada pelo usuário
        '''
        h = color_array[0]
        s = color_array[1]
        v = color_array[2]

        hue_tolerance = 10
        saturation_tolerance = 50
        value_tolerance = 50

        lower_bound = np.array([h - hue_tolerance, max(0, s - saturation_tolerance), max(0, v - value_tolerance)])
        upper_bound = np.array([h + hue_tolerance, min(255, s + saturation_tolerance), min(255, v + value_tolerance)])

        return lower_bound, upper_bound
    
    #Encontrar contornos numa imagem binarizada
    def find_binary_contours(self, image, lower_bound, upper_bound):
        '''
            Encontra contornos na imagem capturada filtrnado com HSV
        '''
        lower = np.array(lower_bound)
        upper = np.array(upper_bound)

        if image is None:
            print("[VisionSystem]: Em find_binary_contours() a Imagem é None")
            return [],None

        if image.shape[1] < 30:
            print("[VisionSystem]: Em find_binary_contours() a  janela é muito pequena, provável que nem exista")
            return [],None
        
        imageHSV = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        binaryImage = cv2.inRange(imageHSV, lower, upper)
        
        #Operações de fechamento e erosão
        structuringElement = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5)) #(20,20) // (5,5)
        binaryImage = cv2.morphologyEx(binaryImage, cv2.MORPH_CLOSE, structuringElement)
        binaryImage = cv2.erode(binaryImage, structuringElement, iterations=1)

        #Encontrando contorno da cor principal
        contours, _ = cv2.findContours(binaryImage, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        return contours

    #Desenhar circulos na imagem onde estão os jogadores
    def draw_player_circle(self, imgDegub, robot:Robot):
        '''
            Desenha um círculo no jogador
        '''
        xi = int(robot.xi)
        yi = int(robot.yi)
        ri = int(robot.ri)

        #Configurando prints
        if robot.team == ID_Team.TEAM_ALLY:
            team = "A"
            color = (255,0,0)
            if robot.id == ID_Robots.ROBOT_ALLY_GOAL:
                id = "G"
            elif robot.id == ID_Robots.ROBOT_ALLY_1:
                id = "A1"
            elif robot.id == ID_Robots.ROBOT_ALLY_2:
                id = "A2"
        elif robot.team == ID_Team.TEAM_ENEMY:
            team = "E"
            color = (0,0,255)
            if robot.id == ID_Robots.ROBOT_ENEMY_GOAL:
                id = "G"
            elif robot.id == ID_Robots.ROBOT_ENEMY_1:
                id = "A1"
            elif robot.id == ID_Robots.ROBOT_ENEMY_2:
                id = "A2"
        else:
            team = "N/A"
            id = "N/A"
            color = (0,255,0)
        

        cv2.circle(imgDegub, (xi, yi), (ri + 5), color, 2)
        text = f"{team}{id}"
        cv2.putText(imgDegub, text , (int(xi-10),int(yi-ri-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        '''pos =f"({str(xi)},{str(yi)})"
        cv2.putText(imgDegub, pos , (int(xi-30),int(yi+ri+20)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)'''

    #Desenhar circulos na imagem onde estão os jogadores
    def draw_player_virtual(self, robot:Robot):
        '''
            Desenha um círculo no jogador
        '''
        xi = int(robot.position[0])
        yi = int(robot.position[1])
        ri = int(robot.radius)

        #converter para dimensões da imagem
        xi, yi = self.getImageIndice(np.array([xi,yi]))

        #Configurando prints
        if robot.team == ID_Team.TEAM_ALLY:
            team = "A"
            color = (255, 255, 0)
            if robot.id == ID_Robots.ROBOT_ALLY_GOAL:
                id = "G"
            elif robot.id == ID_Robots.ROBOT_ALLY_1:
                id = "A1"
            elif robot.id == ID_Robots.ROBOT_ALLY_2:
                id = "A2"
        elif robot.team == ID_Team.TEAM_ENEMY:
            team = "E"
            color = (0,0,255)
            if robot.id == ID_Robots.ROBOT_ENEMY_GOAL:
                id = "G"
            elif robot.id == ID_Robots.ROBOT_ENEMY_1:
                id = "A1"
            elif robot.id == ID_Robots.ROBOT_ENEMY_2:
                id = "A2"
        else:
            team = "N/A"
            id = "N/A"
            color = (0,255,0)
        

        cv2.circle(self.virtualImg, (xi, yi), 4, color, -1)
        text = f"{team}{id}"

        # px/cm = 3  => 3cm = 1 px => 10px = 30 cm  Dcm = Dpx/3
        if self.debug:
            #desenhando circulo do tamanho do raio do ojeto
            cv2.circle(self.virtualImg, (xi, yi), int(3*robot.radius),color, 1)
            cv2.putText(self.virtualImg, text , (int(xi-8),int(yi-3*robot.radius - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        else:
            cv2.circle(self.virtualImg, (xi, yi), int(3*robot.radius),color, 1)
            cv2.putText(self.virtualImg, text , (int(xi-8),int(yi-14)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
   

    #função para tratar imagem e retornar os objetos mais próximos de quadrados
    def detect_squares(self, imgBin):
        '''
            Essa função trata uma imagem e verifica se ele é um robô e não um ruído.
            Isso é realizado verificando se é ou não próximo de um quadrado.
        '''
        contours, _ = cv2.findContours(imgBin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        try:
            # Criar uma máscara em branco para os quadrados
            mascara = None
            mascara = np.zeros_like(imgBin)

            contours_treat = []
            # Iterar sobre os contornos encontrados para encontrar os quadrados
            for contorno in contours:
                perimetro = cv2.arcLength(contorno, True)
                approx = cv2.approxPolyDP(contorno, 0.04 * perimetro, True)
                if len(approx) == 4:
                    # Verificar se é um quadrado
                    x, y, w, h = cv2.boundingRect(approx)
                    aspect_ratio = float(w) / h
                    if 0.7 <= aspect_ratio <= 1.3: #Esses valores foram chutados
                        # Desenhar contorno do quadrado na máscara
                        cv2.drawContours(mascara, [contorno], 0, 255, -1)
                        contours_treat.append(contorno)

            # Aplicar a máscara na imagem binarizada
            bin_res = cv2.bitwise_and(imgBin, imgBin, mask=mascara)

            # Retorna a imagem tratada
            return bin_res, contours_treat

        except Exception as e:
            print("Erro ao processar imagem:", e)
            return imgBin, contours

    # método para verificar se numa janela tem um robô com as cores configuradas
    def detect_ally_robot(self, window, colorP, colorS):
        '''
        #### Função sem suporte ao CUDA
        Função responsável por verificar se há um robô aliado dentro de uma janela, com base na cor primária e na secundária.

        Ela retorna TRUE quando as cores são detectadas e retorna FALSE quando nenhuma ou apenas uma das cores é detectada

        ### Variáveis:
        - window: imagem que deseja ser processada
        - colorP: cor principal em HSV, na forma de array [H,S,V]
        - colorS: cor secundária em HSV, na forma de array [H,S,V]
        - ColorT: Cor do time em HSV, na forma de array [H,S,V]
        '''

        # Criando limites das cores
        first_lower_bound, first_upper_bound = self.create_color_bounds(colorP)
        second_lower_bound, second_upper_bound = self.create_color_bounds(colorS)

        # Procurando cores na janela
        firstColorContours = self.find_binary_contours(window, first_lower_bound, first_upper_bound)
        secondColorContours = self.find_binary_contours(window, second_lower_bound, second_upper_bound)

        # Verificando se as cores foram encontradas
        primaryFound = any(cv2.minEnclosingCircle(contour)[1] >= 0.1* self.secColorRadius for contour in firstColorContours)
        secundaryFound = any(cv2.minEnclosingCircle(contour)[1] >= 0.1 * self.secColorRadius for contour in secondColorContours)

        return primaryFound and secundaryFound
    
    #função para aumentar a saturação de uma imagem
    def upSaturation(self, img):
        '''
            Essa função aumenta a saturação de uma imagem
        '''
        imagem_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Separar os canais H, S e V
        h, s, v = cv2.split(imagem_hsv)

        # Aumentar a saturação (por exemplo, aumentar 50% da saturação original)
        s = cv2.add(s, 50)
        s = np.clip(s, 0, 255)  # Certifique-se de que os valores estejam no intervalo [0, 255]

        # Reunir os canais H, S e V
        imagem_hsv_aumentada = cv2.merge([h, s, v])

        # Converter a imagem de volta para o espaço de cor BGR
        imagem_resultante = cv2.cvtColor(imagem_hsv_aumentada, cv2.COLOR_HSV2BGR)

        return imagem_resultante