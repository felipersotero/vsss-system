import numpy as np
from modules.VisionSys.components.objects import *

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
