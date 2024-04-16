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

# ====================== DEFINIÇÕES DAS CLASSES DE OBJETO DO SISTEMA ==================

#Classe do robô
class Robot:
    def __init__(self, id:ID_Robots, team:ID_Team, x=0, y=0, r=0, image=cv2.imread('src/images/dark_screen.png'),colorTeam = None,colorCar = None):
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
        '''
        Atualiza a posição do robô, passando as coordenadas x, y e o raio do robô
        bem como uma imagem que representa a posição do robô naquele momento.
        '''
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
        '''
            Seta um estado para o robô, informando se ele foi ou não detectado
        '''
        self.detected = status

    #informando cores do carro
    def setColor(self, colorTeam, colorCar):
        '''
            Seta as cores configuradas para reconhecer esse robô. A cor do time e
            a cor secundária dele.
        '''
        self.colorTeam = colorTeam
        self.colorCar = colorCar

    #informando raio da borda do carro
    def setRadius(self, radius):
        '''
            Função responsável por setar o raio do objeto robô na imagem.
        '''
        self.radio = radius

    #informando qual a velocidade do objeto
    def getVelocity(self, timestamp):
        '''
            Puxa a velocidade do robô, no momento que foi chamada.
        '''
        if timestamp != 0: self.velocity = self.direction / timestamp
        else:
            self.velocity = 0

        return self.velocity
    
    #Atualiza borderbox
    def updateBbox(self):
        '''
            Atualiza posição da borda que delimita colisões do robô.
        '''
        #Gerando objeto de informações
        self.objLimit = Circle(Point2D(self.position[0],self.position[1]),self.radius)

        #Gerando uma bbox para sistema de colisões
        self.bbox = BorderBox(GeometryType.CIRCLE,self.objLimit)

    # prever posição do carro com base na velocidade dele
    # timestamp é o tempo que se passou do ultimo processamento até agora
    # necessário uma classe time para realizar essa lógica
        
    #atualiza quadro de predição do robô
    def predictPosition(self, timestamp):
        '''
            Prevê a posição do robô de acordo com o intervalo de tempo que se pasosu
            Assim ele procura na imagem onde mais provável dele estar.
        '''
        #passo para transport a tela que representa a posição do robô
        stepPosition = self.velocity * timestamp

        #transfiro os pontos de identificação para a posição prevista
        self.viewRect.translateViewBot(Point2D(stepPosition[0],stepPosition[1]))

    #recupera o ponto que devo procurar na imagem para encontrar o carro
    # levando em consideração o passo interno do viewRect (dimMatrix)
    def getPredictPosition(self):
        return self.viewRect.Pe1
    
    
class Ball:
    '''
    @GNOMIO: A classe bola é responsável por pegar informações do objeto bola que será utilizado no processo de detecção
    '''
    def __init__(self, x=0, y=0, r=0):
        #posição, raio e direção da boal
        self.position = np.array([int(x), int(y)])
        self.radius = int(r)
        self.direction = np.array([0, 0])

        #gerando bbox para sistema de colisão
        self.objLimit = Circle(Point2D(x,y),self.radius)
        self.bbox = BorderBox(GeometryType.CIRCLE, self.objLimit)

        #definindo uma viewBot para a bola
        self.viewBall = ViewBot(Point2D(self.position[0], self.position[1]),int(r+14))

        #Informações do tipo de objeto no sistema
        self.ObjType = ObjTypeMove.MOVING
        self.objTypeSystem = ObjTypeVision.BALL
        
        #informações de posição para cálculo da velocidade
        self.lastPosition = self.position
        self.newPosition = self.position 

    #atualizando posição da bola
    def updatePosition(self, x, y,r):
        '''
        Função responsável por atualizar a posição do objeto.
        '''
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
        '''
            Retorna a velocidade da bola no instante que foi chamada.
        '''
        if timestamp != 0: self.velocity = self.direction / timestamp
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
        '''
        #passo para mover a tela
        stepPosition = self.velocity*timestamp

        #transfiro os pontos de identificação
        self.viewBall.translateViewBot(Point2D(stepPosition[0],stepPosition[1]))


#Definição da classe campo

#Classe do campo
class Field:
    '''
    @GNOMIO: A classe campo é responsável por dar uma visão geral ao sistema de detecção, para poder enquadrar o campo dentro da lógica
    O objeto field terá informações dos jogadores e dos extremos do campoa
    '''
    def __init__(self):
        #pontos importantes no campo
        self.pivots = [Pivot(id=ID_Pivots.CENTER),Pivot(id=ID_Pivots.PA1),Pivot(id=ID_Pivots.PA2),Pivot(id=ID_Pivots.PA3),Pivot(id=ID_Pivots.PE1),Pivot(id=ID_Pivots.PE3)]
        

        #áreas dos gols dos jogadores
        self.goalArea =[AreaField(id=ID_Field.GOAL_ALLY),AreaField(id=ID_Field.GOAL_ENEMY)]

        #Área dos goleiros
        self.goalRobotArea = [AreaField(id=ID_Field.GOAL_AREA_ALLY),AreaField(id=ID_Field.GOAL_AREA_ENEMY)]

        #@GNOMIO: As posições do Field são em relações à ViewCapture

        #Setando parâmetros do campo
        self.extrems = Quad(Point2D(0,0),Point2D(0,0),Point2D(0,0),Point2D(0,0))

        #Informações do tipo de objeto
        self.ObjType = ObjTypeMove.STATIC
        self.objTypeSystem = ObjTypeVision.FIELD
        
    #Atualizar extremos do campo, para realizar cálculos
    def updatePos(self,pos:Point2D,width,height):
        '''
            Atualiza posição do campo.
        '''
        self.posX=pos[0]
        self.posY=pos[1]
        self.width = width
        self.height = height

    #setar cada um dos pontos de interesse do campo
    def setPivotPos(self,id:ID_Pivots,px,py):
        '''
            Ajusta a posição de um PIVOT do campo, que são pontos importantes do processamento

        '''
        self.pivots[id].updatePos(px,py)

    #Seta as áreas de gol dos jogadores
    def setAreaGoal(self, id:ID_Field, rect:Quad):
        '''
        Função responsável por setar uma área do campo
        '''
        self.goalArea[id].setRect(rect)
        
    #Seta a posição dos goleiros do jogo
    def setAreaRobotGoal(self, id:ID_Field,rect:Quad):
        self.goalRobotArea[id].setRect(rect)

    
    #setando pontos extremos do campo
    def setPointsField(self, rect: Quad):
        self.extrems 
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
        self.Extremes = Extremes        # Extremos da view

    #Modificando os extremos em relação à imagem original
    def setViewCapture(self, Extremes:Quad):
        '''
            Forma indireta de informar quais são os pontos de interesse para o processamento
        '''
        self.Extremes = Extremes

    #Retornar os extremos do ViewCapture
    def getExtremes(self):
        '''
            Retorna os pontos extremos do viewcapture. No caso, um vetor numpy [[a,b],[a,b1],[a,b],[a,b]]
        '''
        return self.Extremes.points

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
    def __init__(self,config: EConfig, capture: Capture, UseCuda:bool, GPUType:GPUType):
        '''
            Inicializando o sistema de visão para realizar a captura de dados e tradução.
            Para isso é necessário passar as configurações do emulador (EConfig), o objeto de captura
            (capture) se ele tem ou não cuda  (useCuda) e qual o tipo de GPU (GPUType).
        '''
        #Configurando objetos
        self.createObjs()

        #Carregando as configurações do sistema de visão
        self.config = config
        
        #objeto de captura internas
        self._capture = capture

        #verifica se existe suporte ao CUDA
        self._hasCuda = UseCuda 
        self._GPUType = GPUType


        self._capture.GPUMode(self._hasCuda)

        #Verifica 
        self.GPUimg= None
        self.CPUimg = None 

        #gera o objeto para utilizar o cuda
        if(self._hasCuda):
            #variável para guardar o endereço da imagem principal
            self.GPUimg = cv2.cuda.GpuMat()


        #configurações do campo comprimento e largura
        self.fieldWidth = 0                     # largura do campo
        self.fieldHeight = 0                    # altura do campo
        self.prop_px_cm = 0                     # proporção pixel para cm
        self.debug = False                      # verifica se o processamento usará ou não o debug

        #Variáveis internas do sistema de visão que serão importantes para o processamento
        #Configurações
        self.offSetWindow = 10                 
        '''Tamanho extra de janela utilizada'''
        self.offSetErode = 0                    
        '''Quantidade padrão de erosões na imagem'''
        self.dimMatrix = 25                     
        '''Dimensão da matriz de convolução na imagem'''
        self.Thrashhold = 235                   
        '''Limiar de binarização da imagem'''
        self.pixelWidth = 1
        '''Tamanho de um pixel normal'''

        #Imagens
        self.frameOrigin    = None             
        '''responsável por guardar a imagem do campo'''
        self.fieldReduce    = None              
        '''Imagem do campo reduzida'''
        self.frameResult    = None              
        '''Imagem final já reduzida e processada'''
        self.imgReduce      = None              
        '''Imagem reduzida para utilizar no processamento'''

        #Imagens binarizadas
        self.binaryObjects  = None              # Imagem binária dos objetos
        self.binaryPlayers  = None              # Imagem Binária dos Jogadores
        self.binaryTeam     = None              # Imagem Binária do Time
        self.binaryBall     = None              # Imagem binária da bola
        self.binReduceField = None              # Imagem binarizada do campo reduzido tratada
        self.binField       = None              # Imagem binarizada do campo original tratada

        #Atualiza as funções com base no modo que foi determinado para elas
        self.choseModeFunctions()
    
    
    #Processamento geral da imagem que irá pegar os valores necessários
    #Envio primeiro a imagem, e ele irá tratar da forma certa
    def proc(self, img):
       '''
       Essa função executa o procedimento de tradução da imagem em informações pertinentes.
       '''
       pass


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
        self.field = Field()

        #gerando a viewCapture
        self.viewCapture = ViewCapture()

    #extrair dados vindos do emulador 
    def toMineData(self):
        '''
        Essa função extrai as informações vindas do Emulador no objeto EConfig.
        '''
        pass

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
    
    # escolhe as funções da classe caso tenha ou não suporte ao cuda
    def choseModeFunctions(self):
        '''
            Atualiza as funções que serão utilizadas pela GPU e pela CPU
            Além de deixar mais eficaz.
        '''
        print("[VisionSystem]: Configurando as funções para o método solicitado")
        #Se tiver utilizando o cuda no código para otimizar o processamento
        if self._hasCuda:
            #Métodos utilizando o CUDA
            self.gray_scale = self.gray_scale_Cuda
            self.median_blur = self.median_blur_Cuda
            self.highlight_img = self.highlight_img_Cuda
            self.binarize_up = self.binarize_up_Cuda
            self.treat_noise = self.trait_noise_Cuda
            self.reduce_field = self.reduce_field_Cuda
            self.detect_ball = self.detect_ball_Cuda
            self.detect_field = self.detect_field_Cuda
            self.detect_players = self.detect_players_Cuda
        else:
            #PROCESSAMENTO UTILIZANDO APENAS A CPU com aprimoramento em algumas partes
            self.gray_scale = self.gray_scale_noCuda
            self.median_blur = self.median_blur_noCuda
            self.highlight_img = self.highlight_img_noCuda
            self.binarize_up = self.binarize_up_noCuda
            self.treat_noise = self.trait_noise_noCuda
            self.reduce_field = self.reduce_field_noCuda
            self.detect_ball = self.detect_ball_noCuda
            self.detect_field = self.detect_ball_noCuda
            self.detect_players = self.detect_players_noCuda


    #===============| Definindo funções básicas|==============================
    # ============= métodos sem suporte ao CUDA =====================
    #puxando imagem
    def load_image_noCuda(self, imgPath):
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
    def gray_scale_noCuda(self,img):
        '''
            Coloca a imagem passada em tons de cinza, Sem usar a GPU
        '''
        return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    #aplicando o filtro mediana para possíveis ruídos
    def median_blur_noCuda(self, img, kernelSize = 3):
        '''
            Aplica o filtro de mediana para reduzir ruídos. Sem usar a GPU.
        '''
        return cv2.medianBlur(img, kernelSize)
    
    #binarizando a imagem indo de um limir até 255
    def binarize_up_noCuda(self, img, threshold=150):
        '''
            Binariza a imagem por meio de um threshold, ou seja, um limiar
            de intensidade dos pixels. Para isso, a imagem tem que estar em
            tons de cinza. Tratada pela função median_blur().
        '''
        _,bin = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY)
        return bin

    #trata ruídos da imagem binarizada
    def trait_noise_noCuda(self, binImg, it=1):
        '''
            Trata o ruído de imagens binarizadas.
        '''
        structElem = cv2.getStructuringElement(cv2.MORPH_CROSS, (3,3))
        binImgProc = cv2.erode(binImg, structElem, iterations=it)
        return binImgProc
    
    #recuperando objeto de maior área
    def get_object_noCuda(self,img):
        '''
            Retorna o maior objeto encontrado
        '''
        contours, _ = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        return contours[0]
    
    #recuperando coordenadas extremas que englobam o objeto maior 
    def get_perspective_noCuda(self, obj):
        '''
            Retorna um retângulo que envolve o objeto passado, e a partir disso
            retorna x,y, x+w e y+h
        '''
        x,y,w,h = cv2.boundingRect(obj)
        return x,y,x+w,y+h
    
    #função para realçar objetos brilhantes na imagem
    def highlight_img_noCuda(self, img, dim = 25):
        '''
            Realça objetos brilhantes na imagem. Contudo, a imagem deve estar em
            tons de cinza.
        '''
        structElem = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(dim,dim))
        imgProc = cv2.morphologyEx(img, cv2.MORPH_TOPHAT, structElem)

        #ajuste de contraste
        imgTrat = cv2.add(imgProc, imgProc)
        imgTrat = cv2.add(imgTrat, imgTrat)
        return imgTrat
    
    #função para reduzir a imagem original
    def reduce_window_noCuda(self, img, coorVetor, d=10):
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
    def reduce_field_noCuda(self, BinImg, Img, fieldWidth, d=10):
        '''
            Função responsável por reduzir a imagem tomando como base a imagem do campo
            e então realizar o processamento nela
        '''
        #Diminuindo a dimensão da imagem para caber apenas o campo
        cont, __ = cv2.findContours(BinImg, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        #objT = cont[0] #Encontra o objeto maior, nesse caso o campo, e então filtrarei a imagem para esse ponto
        objT = max(cont, key=cv2.contourArea)
        
        threshold = 50
        
        # print(f"Área do contorno encontrado: {contour_area}")
        if not cont:
            # print("Nenhum contorno encontrado.")
            return BinImg, Img, [0, 0, 0, 0], 1
        

        try:
            #Obtendo os vértices do retângulo'
            x,y,w,h = cv2.boundingRect(objT) #Coordenadas da nova imagem

            #Esse valor x,y,w,h corresponde  
            #Vetor das coordenadas
            cooVetor = [x,y,w,h]

            #Os pontos iniciais são dentro de uma janela com um "offset"
            #pontos iniciais
            pi = np.float32([[x-d,y-d],[x+w+d,y-d],[x-d,y+h+d],[x+w+d,y+h+d]])

            #pontos finais
            pf = np.float32([[0,0],[w,0],[0,h],[w,h]])

            #Matriz de transformação para nova perspectiva
            matrizPerspectiva = cv2.getPerspectiveTransform(pi,pf)

            #revisando nova imagem para processamento
            img_Reduce = cv2.warpPerspective(Img, matrizPerspectiva, (w,h))
            bin_Reduce = cv2.warpPerspective(BinImg, matrizPerspectiva, (w,h))

            #Pontos extremos da viewCapture
            rect = Quad(Point2D(pi[0, 0], pi[0, 1]), Point2D(pi[1, 0], pi[1, 1]),
                 Point2D(pi[3, 0], pi[3, 1]), Point2D(pi[2, 0], pi[2, 1]))
            

            #Gerando o objeto ViewRect (Retângulo envolvente)
            self.viewCapture.setViewCapture(rect) 


        except: 
            #Se ele não conseguir, retorna a imagem inicial...
            bin_Reduce = BinImg
            img_Reduce = Img
            self.prop_px_cm = 1

        if w > threshold and h > threshold:
            pixelWidth = min(w, h)
            convert_measures(fieldWidth, pixelWidth)

        else:
            self.prop_px_cm = self.prop_px_cm


        return bin_Reduce, img_Reduce, cooVetor

    #função para converter medidas
    def convert_measures(self, w_cm, w_px):
        '''
            Ajusto a constante de proporcionaldiade de px para cm. 
            Representada pela variável: prop_px_cm
        '''
        self.prop_px_cm = w_px / w_cm

    #função para listar os jogadores
    def list_players(self, teamList):
        '''
            Simplesmente lista os jogadores detectados
        '''
        amount = len(teamList)
        for i in range(amount):
            print(teamList[i].team, teamList[i].id)
            print("Posição: x =", teamList[i].pos[0], " y =", teamList[i].pos[1])
        
        print("====================")

    #puxando intervalos de cores
    def create_color_bounds_noCuda(self, color_array):
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
    def find_binary_contours_noCuda(self, image, lower_bound, upper_bound):
        '''
            Encontra contornos na imagem capturada filtrnado com HSV
        '''
        imageHSV = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        binaryImage = cv2.inRange(imageHSV, lower_bound, upper_bound)
        #Operações de fechamento e erosão
        structuringElement = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5)) #(20,20) // (5,5)
        binaryImage = cv2.morphologyEx(binaryImage, cv2.MORPH_CLOSE, structuringElement)
        binaryImage = cv2.erode(binaryImage, structuringElement, iterations=1)

        #Encontrando contorno da cor principal
        contours, _ = cv2.findContours(binaryImage, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        return contours

    #Desenhar circulos na imagem onde estão os jogadores
    def draw_player_circle_noCuda(self, imgDegub, robot):
        '''
            Desenha um círculo no jogador
        '''
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
        
    # ==================== métodos com suporte ao CUDA ===============================
    '''
        As funções com suporte ao CUDA e programação na GPU tem uma lógica diferente
        de processamento, necessário jogando informações na GPU e puxando devolta quando necessário.
    
        O funcionamento dessas funções dependem de uma Stream, para determinar o fluxo do programa
        assim a GPU irá executar várias operações até recuperar os valores necessários.

        Uma Stream é como se fosse uma lista de instruções.
    
    '''
    #carrega a imagem na GPU
    def load_image_Cuda(self, imgPath):
        '''
            #### Utilizando a GPU pelo suporte cuda. 
            Essa função carrega uma imagem na GPU para ser tratada pelas outras funções.
            O retorno é o objeto de referência a essa imagem.

            Retonra o objeto de controle da imagem
        '''
        img = cv2.imread(imgPath)
        img_gpu = cv2.cuda.GpuMat()
        img_gpu.upload(img)
        return img_gpu
    
    #convert a Imagem para o Cuda
    def conv_img_Cuda(self, img):
        '''
            #### Utilizando a GPU pelo suporte cuda. 
            Função para passar uma image da CPU para a GPU e retorna o endereço do objeto de
            controle dessa imagem

        '''
        img_gpu = cv2.cuda.GpuMat()
        img_gpu.upload(img)
        return img_gpu
    
    #transformando imagem em tons de cinza
    def gray_scale_Cuda(self,img, stream=None):
        '''
            #### Utilizando a GPU pelo suporte cuda. 
            Função que passa uma imagem para tons de cinza na GPU
        '''
        return cv2.cuda.cvtColor(img, cv2.COLOR_RGB2GRAY, stream=stream)
    
    #aplicando o filtro mediana para possíveis ruídos
    def median_blur_Cuda(self, img, kernelSize = 3,stream=None):
        '''
            #### Utilizando a GPU pelo suporte cuda. 
            Filtro de mediana para eliminar possíveis ruídos, processamento na GPU
        '''
        medianFiler = cv2.cuda.createMedianFilter(cv2.CV_8UC1, cv2.CV_8UC1, kernelSize)
        return medianFiler.apply(img,stream=stream)
    
    #binarizando a imagem indo de um limir até 255
    def binarize_up_Cuda(self, img, threshold=150,stream=None):
        '''
            #### Utilizando a GPU pelo suporte cuda. 
            Aplica uma binarização na imagem utilizando o GPU. Necessário a imagem
            estar em tons de cinza pela função median_blur(). Essa função retorna o endereço
            da GPU associada a essa imagem.
        '''
        _,bin = cv2.cuda.threshold(img, threshold, 255, cv2.THRESH_BINARY,stream=stream)
        return bin

    #tratar ruidos com o cuda (A imagem aqui tem que já estar na GPU)
    def trait_noise_Cuda(self, img, it=1, stream = None):
        '''
            #### Utilizando a GPU pelo suporte cuda. 
            Função que irá tratar ruídos na binarização. Portanto, a imagem tem que ser binarizada pela
            função binarize_up(), que funciona encima de tons de cinza
        '''
        # Criar um elemento estruturante na GPU
        struct_elem = cv2.getStructuringElement(cv2.MORPH_CROSS, (3,3))
        d_struct_elem = cv2.cuda.createMorphologyFilter(cv2.MORPH_ERODE, img.depth(), struct_elem)

        d_img = img
        # Realizar a operação de erosão na GPU
        for i in range(it):
            d_img = d_struct_elem.apply(d_img, stream=stream)

        return d_img
    
    #recuperando objeto de maior área
    def get_object_Cuda(self,img):
        '''
            #### Utilizando a GPU pelo suporte cuda. 
            Retorna o objeto de maior área dos contornos utilizando o cuda, porém,
            essa função quando utilizada com suporte cuda é necessário uma imagem da CPU.
        '''
        contours, _ = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        return contours[0]
    
    #recuperando coordenadas extremas que englobam o objeto maior 
    def get_perspective_Cuda(self, obj):
        '''
            #### Utilizando a GPU pelo suporte cuda.  
            Retorna os extremos do retângulo que envolve o objeto com maior área
            x, y, w e h.

            * (X,Y) => Indices do ponto a extrema esquerda superior da imagem.
            * w e h => comprimento e largura (respectivamente)

            O retorno da função é (X,y, x+w, y+h)

            OBS: NECESSÁRIO UMA IMAGEM NA CPU!
        '''
        x,y,w,h = cv2.boundingRect(obj)
        return x,y,x+w,y+h
    
    #função para realçar objetos brilhantes na imagem
    def highlight_img_Cuda(self, img, dim = 25,stream=None):
        '''
            #### Utilizando a GPU pelo suporte cuda. 
            função para realçar objetos brilhantes na imagem.
            Retorna um endereço na GPU para o objeto relacionado.
        '''
        structElem = cv2.cuda.createMorphologyFilter(cv2.MORPH_ELLIPSE,cv2.CV_8UC1,(dim,dim))
        imgProc = structElem.apply(img)

        #ajuste de contraste
        imgTrat = cv2.cuda.add(imgProc, imgProc,stream=stream)
        imgTrat = cv2.cuda.add(imgTrat, imgTrat, stream=stream)
        return imgTrat
    
    #Exemplo de função utilizando o pipeline da GPU
    def pipelineGPU(self, img_gpu):
        # Inicializa um objeto de pipeline na GPU
        stream = cv2.cuda.Stream()

        # Executa a operação de conversão para tons de cinza
        img_gray_gpu = cv2.cuda.cvtColor(img_gpu, cv2.COLOR_BGR2GRAY, stream=stream)

        # Executa a operação de binarização
        _, img_bin_gpu = cv2.cuda.threshold(img_gray_gpu, 128, 255, cv2.THRESH_BINARY, stream=stream)

        # Executa a operação de tratamento de ruído
        img_bin_gpu_traty = vs.trait_noise_Cuda(img_bin_gpu, stream=stream)

        # Espera a conclusão de todas as operações no pipeline
        stream.waitForCompletion()

        return img_bin_gpu_traty
    #função para reduzir a imagem original
    def reduce_window_Cuda(self, img, coorVetor, d=10, stream=None):
        '''
        #### Utilizando a GPU pelo suporte cuda. 
        Função utilizada para reduzir a imagem a um tamanho menor.
        Necessário informar o endereço da imagem na GPU, as coordenadas do 
        vetor menor 
        '''
        try:
            #recuperando dados do vetor coordenada
            x,y,w,h = coorVetor[0],coorVetor[1],coorVetor[2],coorVetor[3]

            src_points = cv2.cuda.GpuMat(1,4,cv2.CV_32FC2)
            dst_points = cv2.cuda.GpuMat(1,4,cv2.CV_32FC2)

            src_points.upload([[x-d,y-d],[x+w+d,y-d],[x-d,y+h+d],[x+w+d,y+h+d]])
            dst_points.upload([[0,0],[w,0],[0,h],[w,h]])

            #Matriz de transformação para nova perspectiva
            matrix_gpu = cv2.cuda.GpuMat(3,3,cv2.CV_32F)

            #calculando a matriz de transformação de perspectiva na CPU
            matrix_cpu = cv2.getPerspectiveTransform(src_points.download(),dst_points.download(),stream=stream)

            #aplicando transformação na GPU
            matrix_gpu.upload(matrix_cpu)

            #revisando nova imagem para processamento
            img_Reduce = cv2.cuda.warpPerspective(img, matrix_gpu, (w,h),stream=stream)

            #retornando imagem reduzidaa
            return img_Reduce
        except:
            #Ocorreu um erro, então retorna a janela já inicial
            return img
        
    #função responsável para reduzir a imagem para os contornos do campo
    def reduce_field_Cuda(self, BinImg_gpu, Img_gpu, fieldWidth, d=10,stream=None):
        '''
            #### Utilizando a GPU pelo suporte cuda. 
            Essa função reduz a imagem original a uma imagem com base no campo detectado
            portanto, ela precisa inicialmente da imagem Binarizada para detectar o campo
            o tamanho do campo e um valor d que irá representar uma borda.

            - "binImg" é um imagem na GPU e "Img" é uma imagem na GPU.
            - fieldWidth é o comprimento do campo
            - "d" é o tamanho da borda da janela.

            - O retorno da função são em matrizes na GPU

        '''
        #baixando imagem
        img_cpu = BinImg_gpu.download()
        binImg_cpu = Img_gpu.donwload()

        #Diminuindo a dimensão da imagem para caber apenas o campo
        cont, __ = cv2.findContours(binImg_cpu, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        #objT = cont[0] #Encontra o objeto maior, nesse caso o campo, e então filtrarei a imagem para esse ponto
        objT = max(cont, key=cv2.contourArea)
        contour_area = cv2.contourArea(objT)

        threshold = 50
        
        # print(f"Área do contorno encontrado: {contour_area}")
        if not cont:
            # print("Nenhum contorno encontrado.")
            return binImg_cpu, img_cpu, [0, 0, 0, 0], 1
        

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
            img_Reduce = cv2.warpPerspective(img_cpu, matrizPerspectiva, (w,h))
            bin_Reduce = cv2.warpPerspective(binImg_cpu, matrizPerspectiva, (w,h))

        except:
            #Se ele não conseguir, retorna a imagem inicial...
            bin_Reduce = binImg_cpu
            img_Reduce = img_cpu
            self.prop_px_cm = 1

        #hImg = img_Reduce.shape[0]
        #wImg = img_Reduce.shape[1]

        if w > threshold and h > threshold:
            pixelWidth = min(w, h)
            convert_measures(fieldWidth, pixelWidth)

        else:
            self.prop_px_cm = self.prop_px_cm


        return bin_Reduce, img_Reduce, cooVetor

    #puxando intervalos de cores
    def create_color_bounds_Cuda(self, color_array):
        '''
            #### Utilizando a GPU pelo suporte cuda. 
            Cria os intervalos de cores para realizar o processamento na GPU
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
    def find_binary_contours_Cuda(self, image, lower_bound, upper_bound):
        '''
            #### Utilizando a GPU pelo suporte cuda. 
            Encontra os contornos com base nos intervalos de cores solicitados
        '''
        imageHSV = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        binaryImage = cv2.inRange(imageHSV, lower_bound, upper_bound)
        #Operações de fechamento e erosão
        structuringElement = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5)) #(20,20) // (5,5)
        binaryImage = cv2.morphologyEx(binaryImage, cv2.MORPH_CLOSE, structuringElement)
        binaryImage = cv2.erode(binaryImage, structuringElement, iterations=1)

        #Encontrando contorno da cor principal
        contours, _ = cv2.findContours(binaryImage, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        return contours

    #Desenhar circulos na imagem onde estão os jogadores
    def draw_player_circle_Cuda(self, imgDegub, robot):
        '''
            #### Utilizando a GPU pelo suporte cuda. 
            Desenha círculos nos robôs.
        '''
        x = robot.position[0]
        y = robot.position[1]
        r = robot.radius

        id = robot.id
        team = robot.team

        xi = int(x*self.prop_px_cm)
        yi = int(y*self.prop_px_cm)
        ri = int(r*self.prop_px_cm)

        if(team == ID_Team.TEAM_ALLY):
            color = (255, 0, 0)
        elif(team == ID_Team.TEAM_ENEMY):
            color = (0, 0, 255)
        else:
            color = (0, 200, 200)

        cv2.circle(imgDegub, (xi, yi), (ri + 5), color, 2)
        text = f"{team} {id}: {str(x)}, {str(y)}"
        cv2.putText(imgDegub, text , (int(xi),int(yi+ri+20)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        

    #=============| Definindo funções módulares | ===========================
    #métodos sem suporte ao CUDA
    def detect_field_noCuda(self, img, debug=False):
        '''
            Função responsável por detectar o campo na imagem e gerar um ViewRect com as coordenadas
            do campo que foi reduzido. Salvando o objeto em Field.

            Os argumentos da função são configurações vindas do emulador.
        '''

        h = img.shape[0]
        w = img.shape[0]
        debug = self.debug

        self.pixelWidth = min(w,h)

        #conversão da imagem para pixels
        convert_measures(self.fieldWidth, self.pixelWidth)

        #looping principal
        while self.offSetErode < 20:
            try:
                #imagem original
                self.frameOrigin = img.copy()

                #tomando imagem em tons de cinza
                gray = self.gray_scale(self.frameOrigin)

                #aplica filtro de mediana para diminuir ruídos
                blur = self.median_blur(gray, 3)

                #realça objetos brilhantes, que nesse caso é o campo
                imgProc = self.highlight_img(blur, self.dimMatrix)

                #binarizando a imagem num limiar
                binary = self.binarize_up(imgProc, self.Thrashhold)

                #tratando ruídos da imagem binarizada
                binary_treat = self.treat_noise(binary, self.offSetErode)

                #reduzindo imagem e gerando ViewRect
                self.binReduceFIled, self.fieldReduce, coorVetor = self.reduce_field(binary_treat, self.frameOrigin, self.fieldWidth, self.offSetWindow)
            
                #encontra extremos do paralelogramo
                contours, _ = cv2.findContours(self.binReduceFIled, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

                #gerando os vertices que serão guardados na classe ViewRect
                rectVer = np.array([0,0,0,0], dtype=np.int32)

                #loop através dos contornos encontrados
                for contour in contours:
                    #aproximar o contorno para um polígono com poucos vértices
                    epsilon = 0.02*cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)

                    #Se o polígono tem 4 vértices então é um retângulo
                    if len(approx) == 4:
                        try:
                            #extrair os vértices do retângulo que é gerada na imagem reduzida! rectVer é a coordenada do paralelepípedo na imagem reduzida

                            rectVer = np.array([approx[0][0], approx[1][0], approx[2][0], approx[3][0]], dtype=np.int32)
                            
                            #coorVetor tem as coordenadas x,y iniciais do retângulo que envolve o campo detectado, portanto, ele é da forma coorVetor = [x,y,w,h], 

                            #offset da janela
                            dd = self.offSetWindow
                            
                            #Vértices reais na imagem real
                            rv = rectVer+np.array([[coorVetor[0]-dd,coorVetor[1]-dd], [coorVetor[0]-dd,coorVetor[1]+dd], [coorVetor[0]+dd,coorVetor[1]+dd], [coorVetor[0]+dd,coorVetor[1]-dd]], dtype=np.int32)
                            

                            #rv é a janela com um "offset" de valor dd na imagem original.

                            rect = Quad(Point2D(rv[0, 0], rv[0, 1]), Point2D(rv[1, 0], rv[1, 1]),
                 Point2D(rv[2, 0], rv[2, 1]), Point2D(rv[3, 0], rv[3, 1]))

                            
                            
                            #salvando extremos do objeto campo
                            self.field.updatePos()



                            if(debug):
                                #Desenhar os vértices do retângulo na imagem original (Desenhando os retângulos no campo)
                                cv2.polylines(self.frameOrigin, [rv], True, (0,0,255), 4)

                                for vertex in rv:
                                    x,y = vertex 
                                    cv2.circle(self.frameOrigin, (x,y),4,(0,255,0),-1)
                        except:
                            print("[VisionSystem]: Não conseguiu desenhar na imagem")
                            pass
            except:
                self.offSetErode += 1
                #retornaria as variáveis, mas ele vai atualizar as variáveis internas
                self.fieldReduce = self.frameOrigin


    #Detectar a imagem da bola na imagem
    def detect_ball_noCuda(self, img, debug):
        '''
            Função responsável por detectar a bola na imagem, sem usar o suporte ao Cuda.
        '''
        pass


    #Método para detectar os robôs com suporte ao Cuda
    def detect_players_noCuda(self, img, debug):
        '''
            Função responsável por detectar os robôs na imagem, sem usar o suporte ao Cuda.
        '''
        pass

    #métodos com suporte ao CUDA

    #===========| Definindo funções principais | ============================
    #Métodos sem suporte ao cuda
    #método para detectar o campo na imagem utilizar a GPU com o suporte ao CUDA
    def detect_field_Cuda(self, img, debug):
        '''
        #### Utilizando a GPU pelo suporte cuda. 
        Função responsável por detectar o campo na imagem e gerar um ViewRect com as coordenadas do campo que foi reduzido. Salvando o objeto em Field.
        
        '''
        pass
    
    #Método para detectar a bola utilizando a GPU com o suporte ao CUDA
    def detect_ball_Cuda(self,img, debug):
        '''
        #### Utilizando a GPU pelo suporte cuda. 
        Função responsável por detectar a bola na imagem.
        '''
        pass
    
    #Método para detectar os robôs com suporte ao Cuda
    def detect_players_Cuda(self, img, debug):
        '''
        #### Utilizando a GPU pelo suporte cuda. 
        Função responsável por detectar os robôs na imagem.
        '''
        pass




    #métodos com suporte ao cuda







# Testar função principal e nova lógica
if __name__ =='__main__':
    #executará o código de teste deste módulo com uma imagem padrão
    capture = Capture(CaptureMode.CAM, True)
    capture.setIdCam(0)
    
    #gerar objeto de sistema de detectção
    vs = VisionSystem(None, capture, True, GPUType.NVidia)

    #gerar um timer
    timer = HighPrecisionTimer(None)
    timer.run()
    while True:
        #processamento

        img_gpu = capture.getImageCuda()
        if img_gpu is None:
            print("Falha ao capturar imagem da câmera.")
            break
        else:
            t1 = timer.getElapsedTime()
            img_proc = vs.pipelineGPU(img_gpu)
            t2 = timer.getElapsedTime()

            img = img_proc.download()


            d = t2-t1
            print(d)
            cv2.imshow("Imagem-GPU", img)

        if cv2.waitKey(1) & 0xFF == ord('q'):  # Espera 1 milissegundo e verifica se a tecla 'q' foi pressionada para sair do loop
            cv2.destroyAllWindows()
            break





