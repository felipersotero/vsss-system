# ==========================================================================================
# MÓDULO DE FUNÇÕES PARA ALGORÍTMO DE DETECÇÃO VSS (version v3.0.0)
#==========================================================================================
'''
    @GNOMIO: Aqui está toda a documentação do código de rastramento dos robôs que é utilizado no sistema 
    VSS-SYSTEM. Este código é responsável por detectar, rastrear e prever a posição dos robôs em um campo de jogo
    utilizando visão computacional. Ele implementa técnicas avançadas como filtro de Kalman, detecção de cores
    e análise de contornos para garantir uma detecção precisa e robusta.

    Versão: v3.0.0
    Data de modificação: 2024-06-20
    Autor: Saulo José Almeida Silva
'''
#importando bibliotecas necessárias para o código
import cv2
import numpy as np
from timer import *
import threading
import queue
import imports
from modules.VisionSys.components.objects import *
from modules.VisionSys.components.robot import *
from modules.VisionSys.components.ball import * 
from modules.VisionSys.components.field import * 
import traceback
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


#==========================================================================================
#======================// Classe PRINCIPAL do sistema de visão \\========================#
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

        # Dimensões dos robôs para ser contabilizado no sistema (em cm)
        self.botLength            = 7.5                  # comprimento do robô em cm
        self.botRadius            = (7.5/2)*np.sqrt(2)          # raio do robô em cm
        self.ballRadius           = 2.135                # raio da bola em cm



        #configurações do campo comprimento e largura
        self.fieldWidth             = 0                     # largura do campo
        self.fieldHeight            = 0                     # altura do campo
        self.prop_px_cm             = 1                     # proporção pixel para cm
        self.prop_px_cm_virtual     = 3                     # proporção pixel para cm na imagem virtual

        self.min_diag               = (7.5/2)*np.sqrt(2)                     # diagonal mínima para considerar objeto real =
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

        # Definindo lista de kernels morfológicos para utilizar
        self.kernels_cache = {}

        # variáveis internas para realizar o tratamento de dados
        self.playersCount       = 0
        self.alliesCount        = 0
        self.enemiesCount       = 0

        self.playersWindows     = [None, None, None, None, None, None]

        self.alliesWindows      = [None, None, None]
        self.enimiesWindows     = [None, None, None]

        #lista de threads a serem utilizadas pelo objeto
        self._threads           = []
        self._lockThread        = threading.Lock(), #trava para controle de acesso por threads
        self._lockProc          = threading.Lock()

        #Variável importante para ditar quanto tempo até a próxima atualização de dados
        self.newProcTime        = 10


        #Extrai os dados do objeto de configuração 
        self.toMineData()

        #construir o campo
        self.buildField()

    #===================================================================================================================================================
    #======================|| Métodos de criação de objetos interno ||========================================#
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

    def get_kernel(self, shape, dim):
        key = (shape, dim)
        if key not in self.kernel_cache:
            self.kernel_cache[key] = cv2.getStructuringElement(shape, (dim, dim))
        return self.kernel_cache[key]
    #=====================================================================================================
    #======================|| Métodos de manipulação de pontos ||========================================
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
            novo sistema de coordenadas O', esse valor em cm será o que será guardado nos objetos
            (bola, robô e campo). Assim será possível realizar os calculos apenas no mundo virtual

            Deve-se passar o índice correspondente a imagem virtualizada e ele retorna
            a posição com cm (m/100)

            O resultado é um ponto em centímetros (cm)
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
    #=================================================================================================================
    # Método para adquirir objetos do sistema
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
    
    #=================================================================================================================
    # =====================================| Método de manipulação de imagem |==========================================
    #função para converter medidas
    def convert_measures(self, w_cm, w_px):
        '''
            Ajusto a constante de proporcionaldiade de px para cm. 
            Representada pela variável: prop_px_cm
        '''
        #atualizando proporções para realizar os devidos cálculos
        self.prop_px_cm = w_px / w_cm

        self.min_diag = (7.5 / 4) * np.sqrt(2) * self.prop_px_cm

    def detect_squares(self,img_bin, min_diag=20):
        """
        Processa uma imagem binarizada e retorna apenas os objetos com formato próximo de quadrado.

        Retorna:
            - bin_res: imagem binarizada com apenas os quadrados;
            - contours_treat: lista de contornos correspondentes aos quadrados.
        """
        contours, _ = cv2.findContours(img_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return img_bin, []

        mask = np.zeros_like(img_bin)
        contours_treat = []

        for contour in contours:
            if self.is_square(contour, min_diag):
                cv2.drawContours(mask, [contour], -1, 255, -1)
                contours_treat.append(contour)

        bin_res = cv2.bitwise_and(img_bin, mask)
        return bin_res, contours_treat

    def is_square(self, contour, min_diag=20):
        """
        Verifica se o contorno corresponde aproximadamente a um quadrado.
        Retorna True se for quadrado, False caso contrário.
        """
        perimetro = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * perimetro, True)

        # Precisa ter 4 lados
        if len(approx) != 4:
            return False

        x, y, w, h = cv2.boundingRect(approx)
        aspect_ratio = w / float(h)
        diag = np.hypot(w, h)

        # Aproximadamente quadrado e com tamanho mínimo
        return 0.7 <= aspect_ratio <= 1.3 and diag >= min_diag

    def trait_noise(self, binImg, it=1):
        """
        Reduz ruídos em imagens binarizadas sem uso de CUDA.

        Parâmetros:
            binImg (np.ndarray): imagem binarizada (grayscale ou binária 0/255).
            it (int): número de iterações para operações morfológicas (default=1).

        Retorna:
            np.ndarray: imagem binarizada com menos ruído.
        """
        # Garante que a imagem esteja em 8 bits e com um único canal
        if binImg.ndim == 3:
            binImg = cv2.cvtColor(binImg, cv2.COLOR_BGR2GRAY)
        if binImg.dtype != np.uint8:
            binImg = cv2.convertScaleAbs(binImg)

        # Kernel cruzado pequeno — preserva arestas e remove ruídos pontuais
        kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))

        # Abertura (erosão + dilatação) remove ruídos brancos isolados
        opened = cv2.morphologyEx(binImg, cv2.MORPH_OPEN, kernel, iterations=it)

        # Fechamento (dilatação + erosão) remove buracos pequenos dentro dos objetos
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=1 if it < 2 else it - 1)

        return closed

    def get_max_contour(self, img):
        """
        Retorna o maior contorno encontrado em uma imagem binarizada.
        
        Parâmetros:
            img (np.ndarray): imagem binarizada (0 e 255).
        
        Retorna:
            np.ndarray | None: contorno com maior área ou None se não houver contornos válidos.
        """
        # Garante formato adequado: imagem em 8 bits, 1 canal
        if img.ndim == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if img.dtype != np.uint8:
            img = cv2.convertScaleAbs(img)

        # Busca apenas contornos externos (evita hierarquias desnecessárias)
        contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Retorna None se não houver contornos
        if not contours:
            return None

        # Seleciona o contorno com maior área acima de um limiar mínimo (evita ruído)
        max_contour = max(contours, key=cv2.contourArea)
        if cv2.contourArea(max_contour) < 10:  # limiar ajustável conforme a aplicação
            return None

        return max_contour

        #recuperando coordenadas extremas que englobam o objeto maior
     
    def get_perspective(self, contour):
        """
        Retorna as coordenadas (x1, y1, x2, y2) do retângulo delimitador
        do contorno fornecido.

        Parâmetros:
            contour (np.ndarray): contorno do objeto (como retornado por cv2.findContours).

        Retorna:
            tuple[int, int, int, int] | None:
                (x1, y1, x2, y2) → coordenadas dos cantos do retângulo.
                Retorna None se o contorno for inválido ou vazio.
        """
        # Verifica se o contorno é válido e não vazio
        if contour is None or len(contour) == 0:
            return None

        # Garante que o contorno tenha o formato adequado
        contour = np.array(contour).astype(np.int32)

        # Obtém o retângulo delimitador
        x, y, w, h = cv2.boundingRect(contour)

        # Retorna coordenadas absolutas (x1, y1, x2, y2)
        return x, y, x + w, y + h

    def enhance_gray_objects(self, grayImg):
        """
        Realça objetos em uma imagem em tons de cinza, melhorando contraste e definição
        antes da binarização (threshold). Ideal para destacar os robôs (quadrados ~7,5 cm).

        Parâmetros:
            grayImg (np.ndarray): imagem em escala de cinza (uint8).

        Retorna:
            np.ndarray: imagem realçada (uint8).
        """
        try:
            # Garante formato e tipo corretos
            if len(grayImg.shape) != 2:
                grayImg = cv2.cvtColor(grayImg, cv2.COLOR_BGR2GRAY)
            grayImg = cv2.convertScaleAbs(grayImg)

            # 1Equalização adaptativa do histograma (CLAHE)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            img_eq = clahe.apply(grayImg)

            # 2️ Filtro bilateral (suaviza sem perder bordas)
            img_smooth = cv2.bilateralFilter(img_eq, d=5, sigmaColor=75, sigmaSpace=75)

            # 3️ Realce de bordas com unsharp masking
            sharp = cv2.addWeighted(img_eq, 1.5, img_smooth, -0.5, 0)

            return sharp

        except Exception as e:
            print(f"[SystemVision][ENHANCE_GRAY]: Erro ao realçar imagem — {e}")
            return grayImg
        
    def binarize_up(self, img, threshold=150):
        '''
            Binariza a imagem por meio de um threshold, ou seja, um limiar
            de intensidade dos pixels. Para isso, a imagem tem que estar em
            tons de cinza. Tratada pela função median_blur().
        '''
        _,bin = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY)
        return bin

    def reduce_window(self, img, coorVetor, d=10):
        """
        Reduz a imagem para uma subjanela baseada nas coordenadas (x, y, w, h),
        adicionando uma margem opcional e mantendo performance elevada.

        Parâmetros:
            img (np.ndarray): imagem original (grayscale ou BGR).
            coorVetor (list | tuple): [x, y, w, h] delimitando a janela.
            d (int): margem adicional em pixels (default = 10).

        Retorna:
            np.ndarray: imagem recortada (ou original em caso de erro).
        """
        try:
            x, y, w, h = map(int, coorVetor)

            # Valida dimensões
            if w <= 0 or h <= 0:
                print("[SystemVision][REDUCE_WINDOW]: Dimensões inválidas de recorte.")
                return img

            # Calcula limites da janela com margem
            x1 = max(0, x - d)
            y1 = max(0, y - d)
            x2 = min(img.shape[1], x + w + d)
            y2 = min(img.shape[0], y + h + d)

            # Recorte direto — evita warpPerspective (muito mais rápido)
            subimg = img[y1:y2, x1:x2]

            # Retorna imagem recortada ou original se algo deu errado
            if subimg.size == 0:
                print("[SystemVision][REDUCE_WINDOW]: Subimagem vazia.")
                return img

            return subimg

        except Exception as e:
            print(f"[SystemVision][REDUCE_WINDOW]: Erro ao reduzir janela — {e}")
            return img
        

    def reduce_field(self, BinImg, Img, fieldWidth, d=10):
        """
        Reduz a imagem para a região do campo (maior contorno encontrado)
        e retorna as imagens recortadas + coordenadas do retângulo.

        Parâmetros:
            BinImg (np.ndarray): imagem binarizada do campo.
            Img (np.ndarray): imagem original colorida.
            fieldWidth (float): largura real do campo (em cm, por exemplo).
            d (int): margem adicional em pixels (default = 10).

        Retorna:
            tuple: (bin_Reduce, img_Reduce, cooVetor)
                - bin_Reduce: imagem binarizada reduzida
                - img_Reduce: imagem colorida reduzida
                - cooVetor: [x, y, w, h] do campo detectado
        """
        try:
            #  Encontra o maior contorno (presumido como o campo)
            contours, _ = cv2.findContours(BinImg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                print("[SystemVision][REDUCE_FIELD]: Nenhum contorno encontrado.")
                return BinImg, Img, [0, 0, 0, 0]

            objT = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(objT)

            #  Validação de dimensões
            if w <= 0 or h <= 0:
                print("[SystemVision][REDUCE_FIELD]: Contorno com dimensões inválidas.")
                return BinImg, Img, [0, 0, 0, 0]

            #  Define coordenadas com margem (sem ultrapassar bordas)
            x1 = max(0, x - d)
            y1 = max(0, y - d)
            x2 = min(BinImg.shape[1], x + w + d)
            y2 = min(BinImg.shape[0], y + h + d)

            #  Recorte eficiente
            bin_Reduce = BinImg[y1:y2, x1:x2]
            img_Reduce = Img[y1:y2, x1:x2]
            cooVetor = [x, y, w, h]

            #  Atualiza campo de visão
            rect = Quad(
                Point2D(x1, y1),
                Point2D(x2, y1),
                Point2D(x2, y2),
                Point2D(x1, y2)
            )
            self.viewCapture.setViewCapture(rect, cooVetor)

            #  Atualiza proporção pixel/cm
            if w > 50 and h > 50:
                pixelWidth = min(w, h)
                self.convert_measures(fieldWidth, pixelWidth)

            return bin_Reduce, img_Reduce, cooVetor

        except Exception as e:
            print(f"[SystemVision][REDUCE_FIELD]: Erro ao reduzir campo — {e}")
            self.prop_px_cm = 1
            return BinImg, Img, [0, 0, 0, 0]

    def create_color_bounds(self, hsv_color, hue_tol=10, sat_tol=50, val_tol=50):
        """
        Cria os limites inferior e superior em HSV a partir de uma cor base e tolerâncias.

        Parâmetros:
            hsv_color (iterable): cor base em HSV (H, S, V).
            hue_tol (int): tolerância para o matiz (H).
            sat_tol (int): tolerância para a saturação (S).
            val_tol (int): tolerância para o valor (V).

        Retorna:
            tuple[np.ndarray, np.ndarray]: (lower_bound, upper_bound)
        """
        try:
            h, s, v = map(int, hsv_color)

            # Limites com saturação e valor dentro do intervalo válido
            lower = np.array([
                max(0, h - hue_tol),
                max(0, s - sat_tol),
                max(0, v - val_tol)
            ], dtype=np.uint8)

            upper = np.array([
                min(179, h + hue_tol),   # H em OpenCV vai de 0 a 179
                min(255, s + sat_tol),
                min(255, v + val_tol)
            ], dtype=np.uint8)

            return lower, upper

        except Exception as e:
            print(f"[VisionSystem][COLOR_BOUNDS]: Erro ao criar limites HSV — {e}")
            return np.array([0, 0, 0], dtype=np.uint8), np.array([179, 255, 255], dtype=np.uint8)

    def find_binary_contours(self, image, lower_bound, upper_bound):
        """
        Encontra contornos numa imagem filtrando por faixa HSV.

        Parâmetros:
            image (np.ndarray): imagem BGR.
            lower_bound (np.ndarray): limite inferior em HSV.
            upper_bound (np.ndarray): limite superior em HSV.

        Retorna:
            list[np.ndarray]: lista de contornos encontrados.
        """
        try:
            #  Validações iniciais
            if image is None or image.size == 0:
                print("[VisionSystem][CONTOURS]: Imagem vazia ou None.")
                return []

            if image.shape[1] < 30 or image.shape[0] < 30:
                print("[VisionSystem][CONTOURS]: Janela muito pequena.")
                return []

            #  Conversão para HSV
            image_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            # Criação da máscara binária
            mask = cv2.inRange(image_hsv, lower_bound, upper_bound)

            # 🧹 Limpeza rápida (muito mais leve que morfologia pesada)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

            #  Encontrar contornos externos
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            return contours

        except Exception as e:
            print(f"[VisionSystem][CONTOURS]: Erro ao processar contornos — {e}")
            return []

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


    #======================================| Métodos de Depuração |==========================================

    def draw_player_circle(self, img_debug, robot: Robot):
        """
        Desenha um círculo no jogador com a cor e o identificador do time.

        Parâmetros:
            img_debug (np.ndarray): imagem onde o círculo será desenhado.
            robot (Robot): instância do robô com atributos (xi, yi, ri, team, id).
        """
        try:
            # Conversões rápidas para int
            xi, yi, ri = map(int, (robot.xi, robot.yi, robot.ri))

            # Define cor e prefixo do time
            team_colors = {
                ID_Team.TEAM_ALLY: (255, 0, 0),   # Azul
                ID_Team.TEAM_ENEMY: (0, 0, 255),  # Vermelho
            }
            color = team_colors.get(robot.team, (0, 255, 0))  # Verde para neutro

            # Mapeamento simples de IDs
            id_labels = {
                ID_Robots.ROBOT_ALLY_GOAL:  "G",
                ID_Robots.ROBOT_ALLY_1:     "A1",
                ID_Robots.ROBOT_ALLY_2:     "A2",
                ID_Robots.ROBOT_ENEMY_GOAL: "G",
                ID_Robots.ROBOT_ENEMY_1:    "A1",
                ID_Robots.ROBOT_ENEMY_2:    "A2"
            }

            # Texto (Ex.: "A1", "EG", etc.)
            prefix = "A" if robot.team == ID_Team.TEAM_ALLY else ("E" if robot.team == ID_Team.TEAM_ENEMY else "N")
            label = id_labels.get(robot.id, "?")
            text = f"{prefix}{label}"

            # Desenha o círculo e o texto
            cv2.circle(img_debug, (xi, yi), ri + 5, color, 2)
            cv2.putText(img_debug, text, (xi - 10, yi - ri - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

        except Exception as e:
            print(f"[VisionSystem][DRAW_CIRCLE]: Erro ao desenhar robô — {e}")


    def draw_player_virtual(self, robot: Robot):
        """
        Desenha um círculo representando o jogador na imagem virtual.

        Parâmetros:
            robot (Robot): instância do robô com atributos (position, radius, team, id).
        """
        try:
            # --- Conversões e coordenadas ---
            xi, yi = map(int, self.getImageIndice(np.array(robot.position)))
            ri = int(robot.radius)

            # --- Definição de cores e rótulos ---
            team_colors = {
                ID_Team.TEAM_ALLY: (255, 255, 0),  # Amarelo
                ID_Team.TEAM_ENEMY: (0, 0, 255),   # Vermelho
            }
            color = team_colors.get(robot.team, (0, 255, 0))  # Verde para neutro

            id_labels = {
                ID_Robots.ROBOT_ALLY_GOAL:  "G",
                ID_Robots.ROBOT_ALLY_1:     "A1",
                ID_Robots.ROBOT_ALLY_2:     "A2",
                ID_Robots.ROBOT_ENEMY_GOAL: "G",
                ID_Robots.ROBOT_ENEMY_1:    "A1",
                ID_Robots.ROBOT_ENEMY_2:    "A2"
            }

            prefix = "A" if robot.team == ID_Team.TEAM_ALLY else (
                    "E" if robot.team == ID_Team.TEAM_ENEMY else "N")
            label = id_labels.get(robot.id, "?")
            text = f"{prefix}{label}"

            # --- Desenho principal ---
            cv2.circle(self.virtualImg, (xi, yi), 4, color, -1)

            # Escala de 3 px/cm (ajuste do tamanho visual do robô)
            radius_scaled = int(3 * ri)
            cv2.circle(self.virtualImg, (xi, yi), radius_scaled, color, 1)

            # --- Texto ---
            if self.debug:
                text_pos = (xi - 8, yi - radius_scaled - 4)
            else:
                text_pos = (xi - 8, yi - 14)

            cv2.putText(self.virtualImg, text, text_pos,
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)

        except Exception as e:
            print(f"[VisionSystem][DRAW_PLAYER_VIRTUAL]: Erro ao desenhar robô virtual — {e}")

    #========================================|Métodos principais de processamento | ============================
    # Métodos pontuais de processamento podem ser adicionados aqui conforme necessário
    def detect_ally_robot(self, window: np.ndarray, colorP: list[int], colorS: list[int]) -> bool:
        """
        Verifica se há um robô aliado dentro de uma janela, com base em duas cores (primária e secundária).

        Retorna:
            bool: True se ambas as cores forem detectadas e próximas entre si, False caso contrário.

        Parâmetros:
            window (np.ndarray): subimagem em que será feita a busca.
            colorP (list[int]): cor primária em HSV (ex: [H, S, V]).
            colorS (list[int]): cor secundária em HSV (ex: [H, S, V]).
        """
        try:
            # Cria limites HSV para ambas as cores
            p_lower, p_upper = self.create_color_bounds(colorP)
            s_lower, s_upper = self.create_color_bounds(colorS)

            # Obtém contornos binários das cores
            contoursP = self.find_binary_contours(window, p_lower, p_upper)
            contoursS = self.find_binary_contours(window, s_lower, s_upper)

            # Raio mínimo válido para descartar ruídos
            min_radius = 0.1 * self.secColorRadius

            # Calcula centros válidos das duas cores
            centersP = [cv2.minEnclosingCircle(c)[0] for c in contoursP if cv2.minEnclosingCircle(c)[1] >= min_radius]
            centersS = [cv2.minEnclosingCircle(c)[0] for c in contoursS if cv2.minEnclosingCircle(c)[1] >= min_radius]

            if not centersP or not centersS:
                return False

            # Verifica se há pelo menos um par de centros próximos (cores do mesmo robô)
            max_dist = 2.5 * self.secColorRadius  # distância máxima aceitável entre as cores
            for (x1, y1) in centersP:
                for (x2, y2) in centersS:
                    if np.hypot(x1 - x2, y1 - y2) <= max_dist:
                        return True

            return False

        except Exception as e:
            print(f"[detect_ally_robot_noCuda] Erro ao processar imagem: {e}")
            return False


    #==================================| Métodos módulares do processo de detecção|=========================================
    def detect_field(self, img: np.ndarray, debug: bool = False) -> dict:
        """
        Detecta o campo na imagem e atualiza o objeto Field com as coordenadas e homografia.

        Parâmetros:
            img (np.ndarray): imagem original (frame da câmera).
            debug (bool): se True, desenha os vértices detectados na imagem.

        Retorna:
            dict: {
                "success": bool,                # True se o campo foi detectado
                "modDpCm": float | None,        # largura detectada em cm
                "frameResult": np.ndarray,      # imagem reduzida ou original
                "rect_vertices": np.ndarray | None, # vértices do campo
                "homography": np.ndarray | None,    # matriz de homografia
                "inv_homography": np.ndarray | None, # inversa da homografia
                "binary_field": np.ndarray | None,  # imagem binária processada
            }
        """
        result = {
            "success": False,
            "modDpCm": None,
            "frameResult": img.copy() if img is not None else None,
            "rect_vertices": None,
            "homography": None,
            "inv_homography": None,
            "binary_field": None,
        }

        try:
            if img is None:
                print("[VisionSystem] Erro: imagem recebida é nula.")
                return result

            h, w = img.shape[:2]
            self.pixelWidth = min(w, h)
            self.convert_measures(self.fieldWidth, self.pixelWidth)

            # pré-processamento inicial
            frame_origin = img.copy()
            gray = cv2.cvtColor(frame_origin, cv2.COLOR_RGB2GRAY)
            blur = cv2.medianBlur(gray, 3)
            img_proc = self.enhance_gray_objects(blur, self.dimMatrix)
            binary = self.binarize_up(img_proc, self.Thrashhold)

            # remove ruído inicial
            binary_objects = self.trait_noise(binary, self.offSetErode)
            bin_reduce_field, field_reduce, coor_vetor = self.reduce_field(
                binary_objects, frame_origin, self.fieldWidth, self.offSetWindow
            )

            if field_reduce is None:
                print("[VisionSystem] Campo não reduzido — fallback para imagem original.")
                bin_reduce_field, field_reduce = binary_objects, frame_origin.copy()

            result["binary_field"] = bin_reduce_field.copy()

            # encontra contornos externos
            contours, _ = cv2.findContours(bin_reduce_field, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            found_valid = False

            for contour in contours:
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)

                # apenas quadriláteros são aceitos
                if len(approx) != 4:
                    continue

                rect_ver = np.array([p[0] for p in approx], dtype=np.int32)
                rect_ver = self.sort_points(rect_ver)

                # verifica tamanho mínimo
                dp = rect_ver[1] - rect_ver[0]
                mod_dp_px = np.hypot(dp[0], dp[1])
                mod_dp_cm = mod_dp_px / self.prop_px_cm

                if mod_dp_cm < 60:  # muito pequeno pra ser o campo
                    continue

                # aplica offset e calcula vértices reais
                dd = self.offSetWindow
                rv = rect_ver + np.array([[coor_vetor[0] - dd, coor_vetor[1] - dd]] * 4, dtype=np.int32)

                # cria estrutura de vértices
                points = [Point2D(*pt) for pt in rect_ver]
                rect = Quad(P1=points[0], P2=points[1], P3=points[2], P4=points[3])

                # atualiza o objeto Field
                self.field.updatePos(rect, self.fieldWidth, self.fieldHeight)
                pts_src = np.array([p.getPos() for p in points])
                pts_dst = np.array([self.fieldP1v, self.fieldP2v, self.fieldP3v, self.fieldP4v])
                self.getHomographyMatrix(pts_src, pts_dst)
                self.field.setHomographyMatrix(self.homography_matrix, self.inv_homography_matrix)

                # debug visual
                if debug:
                    cv2.polylines(frame_origin, [rv], True, (0, 0, 255), 4)
                    for i, (x, y) in enumerate(rv):
                        cv2.circle(frame_origin, (x, y), 4, (0, 255, 0), -1)
                        cv2.putText(frame_origin, str(i), (x, y - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

                # sucesso — salva resultados
                result.update({
                    "success": True,
                    "modDpCm": mod_dp_cm,
                    "frameResult": field_reduce.copy(),
                    "rect_vertices": rv,
                    "homography": self.homography_matrix.copy(),
                    "inv_homography": self.inv_homography_matrix.copy(),
                })

                found_valid = True
                break  # achou campo, encerra loop

            if not found_valid:
                print("[VisionSystem] Nenhum campo válido detectado.")

            return result

        except Exception as e:
            print(f"[VisionSystem] Falha em detect_field: {e}")
            traceback.print_exc()
            return result

    def detect_ball(self, img: np.ndarray, colorBall: tuple[int, int, int], debug: bool = False) -> dict:
        """
        Detecta a bola na imagem reduzida com base na cor HSV fornecida.

        Parâmetros:
            img (np.ndarray): Imagem reduzida do campo (área onde a bola pode estar).
            colorBall (tuple): Cor HSV de referência da bola (H, S, V).
            debug (bool): Se True, desenha a bola e informações na imagem.

        Retorna:
            dict: {
                "success": bool,                  # True se a bola foi detectada
                "frameResult": np.ndarray,        # Imagem com a bola destacada (ou cópia original)
                "binaryMask": np.ndarray,         # Máscara binária usada na detecção
                "position_px": (float, float) | None,  # Posição (x, y) em pixels na imagem reduzida
                "position_cm": (float, float) | None,  # Posição (x, y) no espaço em cm
                "radius_px": float | None,        # Raio da bola em pixels
                "radius_cm": float | None,        # Raio da bola em cm
            }
        """
        result = {
            "success": False,
            "frameResult": img.copy() if img is not None else None,
            "binaryMask": None,
            "position_px": None,
            "position_cm": None,
            "radius_px": None,
            "radius_cm": None,
        }

        try:
            if img is None:
                print("[VisionSystem] Erro: imagem recebida é nula.")
                return result

            frame = img.copy()

            # Conversão para HSV e criação da máscara laranja
            img_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            h, s, v = colorBall

            hue_tol, sat_tol, val_tol = 6, 50, 50
            lower_bound = np.array([h - hue_tol, max(0, s - sat_tol), max(0, v - val_tol)])
            upper_bound = np.array([h + hue_tol, min(255, s + sat_tol), min(255, v + val_tol)])

            binary_mask = cv2.inRange(img_hsv, lower_bound, upper_bound)
            result["binaryMask"] = binary_mask.copy()

            # Filtragem morfológica (remoção de ruído)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)
            binary_mask = cv2.erode(binary_mask, kernel, iterations=1)

            # Contornos
            contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                if debug:
                    print("[VisionSystem] Nenhum contorno laranja encontrado.")
                return result

            # Seleciona o maior contorno (bola)
            ball_contour = max(contours, key=cv2.contourArea)
            (xb, yb), rb = cv2.minEnclosingCircle(ball_contour)

            # Rejeita falsos positivos (manchas pequenas)
            if cv2.contourArea(ball_contour) < 10:
                if debug:
                    print("[VisionSystem] Objeto muito pequeno para ser a bola.")
                return result

            # Conversões de coordenadas
            xv, yv = self.transformPoint(np.array([xb, yb]))
            xcm, ycm = self.getPointVirtual(np.array([xv, yv]))

            # Atualiza o objeto bola
            rb_cm = self.ballRadiusP  # raio padrão em cm
            time = self.timer.getElapsedTime()

            self.ball.setPosition(xcm, ycm, rb_cm, time)
            self.ball.setImgPosition(xb, yb, rb_cm)

            # Atualiza resultado
            result.update({
                "success": True,
                "position_px": (xb, yb),
                "position_cm": (xcm, ycm),
                "radius_px": rb,
                "radius_cm": rb_cm,
            })

            # Desenho de debug
            if debug:
                xb, yb, rb = int(xb), int(yb), int(rb / self.prop_px_cm)
                cv2.circle(frame, (xb, yb), rb + 2, (0, 0, 255), 2)
                cv2.putText(frame, "B", (xb, yb - rb - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

                xv, yv = int(xv), int(yv)
                cv2.circle(self.virtualImg, (xv, yv), 4, (0, 255, 255), -1)
                cv2.putText(self.virtualImg, "B", (xv - 5, yv - rb - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
                cv2.arrowedLine(self.virtualImg, (xv, yv),
                                (xv + int(self.ball.direction[0]), yv + int(self.ball.direction[1])),
                                (0, 255, 255), 2)

            result["frameResult"] = frame
            return result

        except Exception as e:
            print(f"[VisionSystem] Erro em detect_ball: {e}")
            traceback.print_exc()
            return result

    def detect_players(self, img: np.ndarray, debug: bool = False) -> dict:
        """
        Detecta todos os robôs (aliados e inimigos) na imagem reduzida do campo.

        Parâmetros:
            img (np.ndarray): imagem reduzida do campo.
            debug (bool): se True, desenha círculos e setas dos robôs detectados.

        Retorna:
            dict: {
                "success": bool,
                "frameResult": np.ndarray,
                "binaryPlayers": np.ndarray,
                "num_allies": int,
                "num_enemies": int,
                "ally_positions": list[tuple[float, float]],
                "enemy_positions": list[tuple[float, float]]
            }
        """
        result = {
            "success": False,
            "frameResult": img.copy() if img is not None else None,
            "binaryPlayers": None,
            "num_allies": 0,
            "num_enemies": 0,
            "ally_positions": [],
            "enemy_positions": [],
        }

        try:
            if img is None:
                print("[VisionSystem] Erro: imagem recebida é nula.")
                return result

            # Reinicia contadores e estados dos robôs
            self.playersCount = self.enemiesCount = self.alliesCount = 0
            for bot in self.enemyTeam:
                bot.setStatus(False)
            for bot in self.allyTeam:
                bot.setStatus(False)

            frame = img.copy()
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # --- 1. Máscara para objetos escuros (robôs) ---
            mask_objects = cv2.inRange(hsv, self.objectsDarkColor, self.objectsLightColor)

            # Remove a bola da máscara (se disponível)
            if hasattr(self, "binaryBall") and self.binaryBall is not None and self.binaryBall.size > 0:
                binary_ball = cv2.resize(self.binaryBall, (mask_objects.shape[1], mask_objects.shape[0]))
            else:
                binary_ball = np.zeros_like(mask_objects)

            binary_players = cv2.subtract(mask_objects, binary_ball)

            # --- 2. Filtragem morfológica ---
            kernel1 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            kernel2 = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
            binary_players = cv2.erode(binary_players, kernel1, iterations=1)
            binary_players = cv2.morphologyEx(binary_players, cv2.MORPH_CLOSE, kernel2)
            result["binaryPlayers"] = binary_players.copy()

            # --- 3. Detecta quadrados (robôs) ---
            binary_players, contours = self.detect_squares(binary_players)
            if not contours:
                if debug:
                    print("[VisionSystem] Nenhum contorno de robô encontrado.")
                return result

            # --- 4. Ajustes geométricos ---
            win_size = int(18 * self.prop_px_cm)
            self.playerRadius = (7.5 / 2) * np.sqrt(2) * self.prop_px_cm
            self.mainColorRadius = (7.5 / 4) * np.sqrt(5) * self.prop_px_cm
            self.secColorRadius = self.playerRadius / 2

            # --- 5. Limites de cores principais ---
            ally_lower, ally_upper = self.create_color_bounds(self.allyColor)
            enemy_lower, enemy_upper = self.create_color_bounds(self.enemyColor)

            # --- 6. Loop principal: processar cada robô ---
            for contour in contours:
                (xi, yi), ri = cv2.minEnclosingCircle(contour)
                if not (0.2 * self.playerRadius <= ri <= 2 * self.playerRadius):
                    continue

                # recorte local
                x1, y1 = max(0, int(xi - win_size / 2)), max(0, int(yi - win_size / 2))
                x2, y2 = min(frame.shape[1], int(xi + win_size / 2)), min(frame.shape[0], int(yi + win_size / 2))
                window = frame[y1:y2, x1:x2]

                # --- verifica se é inimigo ou aliado ---
                ally_contours = self.find_binary_contours(window, ally_lower, ally_upper)
                enemy_contours = self.find_binary_contours(window, enemy_lower, enemy_upper)

                # Coordenadas reais
                tm = self.timer.getElapsedTime()
                xv, yv = self.transformPoint(np.array([xi, yi]))
                xcm, ycm = self.getPointVirtual(np.array([xv, yv]))
                rcm = 5.30  # raio padrão em cm

                # === Inimigo ===
                if enemy_contours and self.enemiesCount < 3:
                    contour_enemy = max(enemy_contours, key=cv2.contourArea)
                    (_, _), rc = cv2.minEnclosingCircle(contour_enemy)
                    if rc >= 0.5 * self.mainColorRadius:
                        bot = self.enemyTeam[self.enemiesCount]
                        bot.setPosition(xcm, ycm, rcm, window, tm)
                        bot.updtPositionImg(xi, yi, ri)
                        bot.setStatus(True)
                        bot.setColor(colorT=self.enemyColor)
                        self.draw_player_circle(self.frameResult, bot)
                        self.draw_player_virtual(bot)

                        result["enemy_positions"].append((xcm, ycm))
                        self.enemiesCount += 1

                # === Aliado ===
                elif ally_contours and self.alliesCount < 3:
                    contour_ally = max(ally_contours, key=cv2.contourArea)
                    (_, _), rc = cv2.minEnclosingCircle(contour_ally)
                    if rc >= 0.3 * self.mainColorRadius:
                        bot = self.allyTeam[self.alliesCount]
                        bot.setPosition(xcm, ycm, rcm, window, tm)
                        bot.updtPositionImg(xi, yi, ri)
                        bot.setStatus(True)
                        bot.setColor(colorT=self.allyColor)
                        self.draw_player_circle(self.frameResult, bot)
                        self.draw_player_virtual(bot)

                        result["ally_positions"].append((xcm, ycm))
                        self.alliesCount += 1

                # --- Debug visual ---
                if debug:
                    cv2.circle(self.frameResult, (int(xi), int(yi)), int(ri) + 4, (0, 255, 0), 2)

            # Atualiza totais
            result.update({
                "success": self.alliesCount + self.enemiesCount > 0,
                "num_allies": self.alliesCount,
                "num_enemies": self.enemiesCount,
            })

            return result

        except Exception as e:
            print(f"[VisionSystem] Erro em detect_players: {e}")
            traceback.print_exc()
            return result

    #====================================| PIPELINES DE PROCESSAMENTO |==========================================
    


    
    
    #=======================================|FIM DOS MÉTODOS |=============================================