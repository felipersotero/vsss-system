import numpy as np
from modules.VisionSys.components.objects import *
# NOVA CLASSE BALL (substituir a antiga)

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

