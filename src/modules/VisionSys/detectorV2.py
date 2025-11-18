# ==========================================================================================
# MÓDULO DE FUNÇÕES PARA ALGORÍTMO DE DETECÇÃO VSS (version v3.0.40)
#==========================================================================================
'''
    @GNOMIO: Sismtea de detecção de objetos VSS (Vision System Soccer) versão 2.2.40    
    
    Versão: v3.0.40
    Última modificação: 16/11/2025
    Autor: Saulo (update)

    Patch Notes v3.1.105:
    - Implementado novo sistema de threads com melhor desempenho
    - Separação de processamento em visão e comunicação
    - Melhor gerenciamento de recursos
    - Sistema de filas otimizado para UI e comunicação
    - Novo sistema de debug com menor overhead
    - Correções na estabilidade do processamento
    - Implementação de uma estrutura para armazenar as cores em tempo real
'''
#importando bibliotecas necessárias para o código
import cv2
from matplotlib.font_manager import X11FontDirectories
import numpy as np
from timer import *
import threading
import queue
import imports

from modules.VisionSys.components.objects import *
from modules.VisionSys.components.viewcapture import *
from modules.VisionSys.components.field import *
from modules.VisionSys.components.ball import *
from modules.VisionSys.components.robot import *

import traceback
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# ====================== DEFINIÇÕES DAS CLASSES DE OBJETO DO SISTEMA ==================
#======================|| Sistema de detecção POO||======================================#
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
        self.min_diag = (7.5 / 4) * np.sqrt(2) * self.prop_px_cm
        
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

        #Variável importante para ditar quanto tempo até a próxima atualização de dados
        self.newProcTime        = 10
        
        # Variável da identificação de cores
        self.colorTree = ColorTree()
        
        #Extrai os dados do objeto de configuração 
        self.toMineData()

        #construir o campo
        self.buildField()
    
    # Implementação da lógica de processamento para várias coisas
    # Esse é o PROC MAIOR
    def proc(self, img, debug: bool, isT: bool = False):
        """
        Pipeline principal de processamento da imagem de visão.
        Executa a detecção do campo, bola e jogadores, e gera a visualização final.

        Parâmetros:
            img (np.ndarray): imagem de entrada.
            debug (bool): habilita visualização e marcações de depuração.
            isT (bool): flag opcional usada em detecção de jogadores.
        """
        # Reseta estado de execução temporário
        self.resetExecutionState()
        
        # marca tempo de início do processamento maior (se não inicializado)
        if not hasattr(self, 'lastMajorTime') or self.lastMajorTime == 0:
            self.lastMajorTime = self.timer.getElapsedTime()

        self.currentTime = self.timer.getElapsedTime()
        # tempo em segundos desde último processamento maior
        self._firstTimeExec = (self.currentTime - self.lastMajorTime) / 1000.0
        self.debug = debug

        # Zera a imagem virtual
        self.virtualImg = self.virtual.copy()

        # Validação de imagem
        if img is None:
            self.drawAllRobots()
            return img

        # Reseta status dos robôs
        for bot in self.enemyTeam:
            bot.setStatus(False)
        for bot in self.allyTeam:
            bot.setStatus(False)

        imgP = img.copy()

        # Detecta o campo
        wbCmField = self.detect_field(imgP, debug)


        # Corrige erro de redução de campo
        if self.fieldReduce is None or self.fieldReduce.shape[1] < 100:
            print("[SystemVision][PROC]: FieldReduce é None ou muito pequeno, usando frame original.")
            self.fieldReduce = self.frameOrigin

        # === Detecta bola ===
        self._safe_call(self.detect_ball, self.fieldReduce, self.ballColor, debug, name="BALL")

        # === Detecta jogadores ===
        self._safe_call(self.detect_players, self.fieldReduce, debug, isT=isT, name="PLAYERS")

        # Só continua se o campo for válido e com tamanho consistente
        if wbCmField == -1 or abs(wbCmField - self.fieldWidth) > 30:
            self.drawAllRobots()
            return img
            
        # === Renderização de depuração ===
        if debug:
            self._draw_field_debug()

        # Desenha robôs na imagem final
        self.drawAllRobots()

        # atualiza lastMajorTime ao final do processamento "maior" (importante para decidir próximo tipo de processamento)
        try:
            self.lastMajorTime = self.timer.getElapsedTime()
        except Exception:
            # fallback seguro
            self.lastMajorTime = self.currentTime

        return self.frameResult

    # Funções auxiliares
    def _safe_call(self, func, *args, name="", **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"[VS][SAFE_CALL] Erro ao executar {name}: {e}")
            traceback.print_exc()
            return None

    def _draw_field_debug(self):
        """Desenha os pontos e linhas do campo no modo debug."""
        self.field.drawPointsField()

        points = [
            self.fieldP1v, self.fieldP2v, self.fieldP3v, self.fieldP4v,
            self.fieldCenterv,
            self.PA1v, self.PA2v, self.PA3v,
            self.PE1v, self.PE2v, self.PE3v,
            self.GA1v, self.GA2v, self.GA3v, self.GA4v,
            self.GAI1v, self.GAI2v, self.GAI3v, self.GAI4v,
            self.GE1v, self.GE2v, self.GE3v, self.GE4v,
            self.GEI1v, self.GEI2v, self.GEI3v, self.GEI4v,
            self.fieldP12v, self.fieldP34v
        ]

        for p in points:
            cv2.circle(self.virtualImg, p, 2, (0, 0, 255), -1)

        # Ponto de referência (O')
        cv2.circle(self.virtualImg, (self.xnv, self.ynv), 3, (0, 255, 255), -1)


    def resetExecutionState(self):
        """
        Reseta apenas variáveis temporárias entre execuções do processamento.
        Preserva dados dos robôs, bola, campo e configurações permanentes.
        
        Deve ser chamado APÓS cada proc() completo para limpar estado interno.
        """
        # ==================== IMAGENS TEMPORÁRIAS ====================
        self.frameOrigin = None
        self.fieldReduce = None
        self.frameResult = None
        self.imgReduce = None
        self.ballImg = None
        
        # ==================== IMAGENS BINÁRIAS ====================
        self.binaryObjects = None
        self.binaryPlayers = None
        self.binaryTeam = None
        self.binaryBall = None
        self.binReduceField = None
        self.binField = None
        self.binaryAllTeam = None
        
        # ==================== BUFFERS DE PROCESSAMENTO ====================
        self.playersWindows = [None, None, None, None, None, None]
        self.alliesWindows = [None, None, None]
        self.enimiesWindows = [None, None, None]
        
        # ==================== CONTADORES TEMPORÁRIOS ====================
        self.playersCount = 0
        self.alliesCount = 0
        self.enemiesCount = 0
        
        # ==================== ESTADO DE DETECÇÃO ATUAL ====================
        # Reset apenas dos flags de detecção do frame atual
        # (não afeta histórico de posições)
        for bot in self.allyTeam:
            bot.detected = False  # Apenas o status de detecção atual
            bot.possessionBall = False  # Posse de bola é temporária
            
        for bot in self.enemyTeam:
            bot.detected = False
            bot.possessionBall = False
            
        if hasattr(self.ball, 'detected'):
            self.ball.detected = False
        
        # ==================== VARIÁVEIS DE TEMPO DO FRAME ====================
        # Não resetar: self.lastMajorTime, self.currentTime, self.dT
        # (são necessárias para controle temporal entre execuções)
        
        # ==================== RESET DA IMAGEM VIRTUAL ====================
        if hasattr(self, 'virtual'):
            self.virtualImg = self.virtual.copy()
        
        # ==================== LIMPEZA DE THREADS FINALIZADAS ====================
        # Limpa threads que já terminaram, mantém executor ativo
        self._threads = [t for t in self._threads if t.is_alive()]
        
        # Reseta a árvore de cores
        self.colorTree.reset_tree()

    #função para prever posição dos jogadores e encontrar onde estão
    # Esse é um PROC MENOR (Que usa um filtro para detecção)
    def filtred_detection(self, img, tms):
        """
        Detecção leve de robôs usando predição do Kalman para definir ROI.
        A imagem original é recortada na janela prevista pelo Kalman, 
        reduzindo o custo computacional.
        
        Parâmetros:
            img : np.ndarray
                Frame completo da câmera.
            tms : float
                Tempo atual do frame (segundos ou milissegundos dependendo do sistema).
        """

        # --- 1) Pega as coordenadas do viewCapture configurado---
        x_w, y_w, w_w, h_w = self.viewCapture.cooVetor

        # Evita índices inválidos
        if img is None:
            return

        # --- 2) Ajusta limites da janela para não ultrapassar a imagem ---
        h_img, w_img = img.shape[:2]
        x_w = max(0, min(int(x_w), w_img - 1))
        y_w = max(0, min(int(y_w), h_img - 1))
        w_w = max(1, min(int(w_w), w_img - x_w))
        h_w = max(1, min(int(h_w), h_img - y_w))

        # --- 3) Recorta a imagem para processamento na ROI ---
        self.fieldReduce = img[y_w:y_w+h_w, x_w:x_w+w_w].copy()
        self.frameResult = self.fieldReduce.copy()

        # --- 4) Aqui você aplicaria a detecção leve ---
        # Exemplo de pseudocódigo:
        # for robot in self.robots:
        #     xi, yi, ri = detect_robot_in_roi(self.fieldReduce, robot)
        #     if xi is not None:
        #         # Ajusta para coordenadas da imagem completa
        #         robot.setPosition(x=xi + x_w, y=yi + y_w, r=ri, image=self.fieldReduce, time=tms)
        #     else:
        #         # Fallback: mantém posição predita pelo Kalman
        #         robot.position = robot.position_filtered

        # --- 5) Desenha todos os robôs no frameResult ---
        self.drawAllRobots()



    #lógica completa de processamento do sistema de visão
    def processImg(self, img, debug: bool):
        """
        Executa o pipeline principal de visão, alternando entre:
        - Processamento completo (detecção e atualização)
        - Predição leve (usando o filtro de Kalman)
        
        O filtro de Kalman é preservado entre frames no modo de vídeo
        e reinicializado apenas no modo imagem (emulação).
        """
        self.debug = debug
        self.frameOrigin = img
        self.currentTime = self.timer.getElapsedTime()

        # --- Caso especial: modo imagem (emulação única) ---
        if self.emulatorMode == MODE_IMAGE:
            # Reseta contadores
            self._count = 0
            self.lastMajorTime = 0

            # Reseta robôs e bola completamente (inclusive Kalman)
            for bot in (*self.allyTeam, *self.enemyTeam):
                bot.reset()  # reset total
            if hasattr(self, "ball"):
                self.ball.reset()

            # Processa a imagem estática e retorna
            self.proc(img, debug)
            
            return self.frameResult

        # --- Caso normal: processamento contínuo (vídeo) ---

        # Tempo desde o último processamento completo (em segundos)
        elapsed = (
            (self.currentTime - getattr(self, "lastMajorTime", 0)) / 1000.0
            if hasattr(self, "lastMajorTime") else float("inf")
        )

        # --- Caso 1 - Atualização períodica com processamento pesado ---
        if elapsed < self.newProcTime:
            self._count += 1

            # Nas 3 primeiras execuções após inicialização, forçar processamento completo
            if self._count <= 10: #Fase 1 - Alimentar o filtro de Kalman
                self.proc(img, debug)

                # Reset apenas dos estados físicos (não do Kalman)
                for bot in (*self.allyTeam, *self.enemyTeam):
                    bot.resetState()
                if hasattr(self, "ball"):
                    self.ball.resetState()

            else: #Fase 2 - Utilizar as predições do filtro
                '''
                    Após ele ser alimentado com N medições e atualização sigo o
                    seguinte processo:

                    1) Uso o Kalman como Guia de ROI
                        * Se a detecção estiver dentro do ROI, atualizo kalman e o robô
                        * Se a detecção não estiver dentro do ROI, utilizo o valor de kalman
                    
                    Isso garante uma detecção contínua do robô
                '''
                #self.predictObjects(img, tms=self.currentTime)
                self.proc(img, debug)

        # --- Caso 2: processamento completo periódico ---
        else:
            self._count = 0
            self.lastMajorTime = self.currentTime

            if hasattr(self, "virtual"):
                self.virtualImg = self.virtual.copy()

            # Processamento completo da visão
            self.proc(img, debug)

            # Após um proc, reseta apenas o estado físico (direção, velocidade)
            for bot in (*self.allyTeam, *self.enemyTeam):
                bot.resetState()
            if hasattr(self, "ball"):
                self.ball.resetState()

        # --- Atualiza delta temporal do frame ---
        tmf = self.timer.getElapsedTime()
        self.dT = tmf - self.currentTime

        return getattr(self, "frameResult", img)




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

        #Setando
        self.setTreeColorDefault()
        # Atribuindo cores a arvore da decisão

    #definir novas configurações
    def setConfigEmulator(self, config:EConfig):
        '''
            Essa função seta uma nova configuração para o sistema de visão pelo emulador
        '''
        self.config = config
        self.toMineData()

    def setTreeColorDefault(self):
        ''' Setando configurações padrões da árvore'''
        self.colorTree.add_robot(ID_Team.TEAM_ALLY, self.allyColor, ID_Robots.ROBOT_ALLY_GOAL, self.goalAllyColor1, self.goalAllyColor2 )
        self.colorTree.add_robot(ID_Team.TEAM_ALLY, self.allyColor, ID_Robots.ROBOT_ALLY_1, self.atk1AllyColor1, self.atk1AllyColor2 )
        self.colorTree.add_robot(ID_Team.TEAM_ALLY, self.allyColor, ID_Robots.ROBOT_ALLY_2, self.atk2AllyColor1, self.atk2AllyColor2 )


    #método para retornar o processamento
    def getViewCapture(self):
        '''
            Retorna a janela de interesse do sistema de visão
        '''
        return self.viewCapture
    
    #definindo modo para resetar configurações
    def _resetVs(self):
        """Reset COMPLETO do sistema de visão"""
        
        # 1. Recria objetos principais
        self.createObjs()
        
        # 2. Reset de TODAS as variáveis de estado
        self._countProcess = 0
        self._count = 0
        self._firstTimeExec = 0
        self.lastMajorTime = 0
        self.currentTime = 0
        self.dT = 0
        
        # 3. Reset de transformações
        self.homography_matrix = None
        self.inv_homography_matrix = None
        self.prop_px_cm = 1
        self.min_diag = (7.5 / 4) * np.sqrt(2) * self.prop_px_cm
        
        # 4. Reset de configurações de GPU/CPU
        self.GPUimg = None
        self.CPUimg = None
        self.emulatorMode = MODE_IMAGE
        
        # 5. Reset de imagens e buffers
        self.frameOrigin = None
        self.ballImg = None
        self.fieldReduce = None
        self.frameResult = None
        # ... resto do reset original
        
        
        # 7. Reconstroi o campo
        self.buildField()

        # 8. Recaptura cores
        self.setTreeColorDefault()

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
    #puxando imagem
    def load_image(self, imgPath):
        '''
            Função que carrega imagem na CPU por meio de um caminho (imgPath). Sem usar a GPU
        '''
        self.imgOrigim = cv2.imread(imgPath) 
    
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
    def trait_noise(self, binImg, it=1):
        """
        Reduz ruídos em imagens binarizadas.

        Parâmetros:
            binImg (np.ndarray): imagem binarizada (grayscale ou binária 0/255).
            it (int): número de iterações de erosão/dilatação (default = 1).

        Retorna:
            np.ndarray: imagem binarizada com menos ruído.
        """
        try:
            # Garante tipo binário
            if binImg.dtype != np.uint8:
                binImg = cv2.convertScaleAbs(binImg)

            # Estrutura cruzada pequena remove ruídos pontuais sem deformar objetos
            kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))

            # Erosão seguida de dilatação = abertura morfológica (remove ruídos brancos)
            binImgProc = cv2.morphologyEx(binImg, cv2.MORPH_OPEN, kernel, iterations=it)

            # (Opcional) fechamento remove buracos pequenos dentro dos objetos
            binImgProc = cv2.morphologyEx(binImgProc, cv2.MORPH_CLOSE, kernel, iterations=max(1, it - 1))

            return binImgProc

        except Exception as e:
            print(f"[SystemVision][TRAIT_NOISE]: Erro ao tratar ruído — {e}")
            return binImg

    
    #recuperando objeto de maior área
    def get_object(self,img):
        '''
            Retorna o maior contorno encontrado ou None se não houver contornos.
        '''
        contours, _ = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        return max(contours, key=cv2.contourArea)
    
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
    
    def highlight_img(self, img, dim=25):
        """
        Realça objetos brilhantes em uma imagem em tons de cinza.

        Parâmetros:
            img (np.ndarray): imagem de entrada em escala de cinza.
            dim (int): tamanho do elemento estruturante para o rea00lce (default = 25).

        Retorna:
            np.ndarray: imagem realçada.
        """
        try:
            # Garante que a imagem esteja em escala de cinza
            if len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Cria elemento estruturante elíptico (suave)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dim, dim))

            # Top-hat: realça áreas mais brilhantes que o entorno
            img_tophat = cv2.morphologyEx(img, cv2.MORPH_TOPHAT, kernel)

            # Opcional: uma segunda passada pode suavizar ainda mais o ruído
            img_tophat = cv2.morphologyEx(img_tophat, cv2.MORPH_TOPHAT, kernel)

            # Ajuste de contraste (equivalente a multiplicar brilho)
            img_highlight = cv2.convertScaleAbs(img_tophat, alpha=4.0, beta=0)

            return img_highlight

        except Exception as e:
            print(f"[SystemVision][HIGHLIGHT_IMG]: Erro ao realçar imagem — {e}")
            return img

    #função para reduzir a imagem original
    def reduce_window(self, img, coorVetor, d=10):
        """
        Reduz a imagem para uma subjanela baseada nas coordenadas (x, y, w, h)
        aplicando uma leve transformação de perspectiva.

        Parâmetros:
            img (np.ndarray): imagem original.
            coorVetor (list | tuple): [x, y, w, h] delimitando a janela.
            d (int): margem adicional em pixels (default = 10).

        Retorna:
            np.ndarray: imagem reduzida (ou original, em caso de erro).
        """
        try:
            x, y, w, h = map(int, coorVetor)

            if w <= 0 or h <= 0:
                print("[SystemVision][REDUCE_WINDOW]: Dimensões inválidas de recorte.")
                return img

            # Limita margem para evitar índices negativos
            d = max(0, min(d, x, y))

            # Define pontos da área de interesse (com margem)
            firstPoints = np.float32([
                [x - d, y - d],
                [x + w + d, y - d],
                [x - d, y + h + d],
                [x + w + d, y + h + d]
            ])

            # Pontos destino (retângulo final)
            lastPoints = np.float32([
                [0, 0],
                [w, 0],
                [0, h],
                [w, h]
            ])

            # Calcula matriz de transformação perspectiva
            matrizPerspectiva = cv2.getPerspectiveTransform(firstPoints, lastPoints)

            # Garante que dimensões sejam inteiras e válidas
            w, h = int(max(1, w)), int(max(1, h))

            # Aplica a transformação de perspectiva
            img_Reduce = cv2.warpPerspective(img, matrizPerspectiva, (w, h))

            return img_Reduce

        except Exception as e:
            print(f"[SystemVision][REDUCE_WINDOW]: Erro ao reduzir janela — {e}")
            return img

        
    #função responsável para reduzir a imagem para os contornos do campo
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
        # Encontrar contornos
        contours, _ = cv2.findContours(BinImg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            print("[SystemVision]/[REDUCE_FIELD]: Nenhum contorno encontrado.")
            return BinImg, Img, [0, 0, 0, 0]

        try:
            # Maior contorno (presumido como o campo)
            objT = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(objT)
            cooVetor = [x, y, w, h]

            # Margem de segurança (impede valores negativos)
            d = max(0, min(d, x, y))

            # Recorte com margem
            y1, y2 = max(0, y - d), min(BinImg.shape[0], y + h + d)
            x1, x2 = max(0, x - d), min(BinImg.shape[1], x + w + d)

            bin_Reduce = BinImg[y1:y2, x1:x2]
            img_Reduce = Img[y1:y2, x1:x2]

            # Define o retângulo de visão atual
            pi = np.float32([[x1, y1], [x2, y1], [x1, y2], [x2, y2]])
            rect = Quad(
                Point2D(pi[0, 0], pi[0, 1]),
                Point2D(pi[1, 0], pi[1, 1]),
                Point2D(pi[3, 0], pi[3, 1]),
                Point2D(pi[2, 0], pi[2, 1])
            )

            # Atualiza o campo de visão
            self.viewCapture.setViewCapture(rect, cooVetor)

            # Atualiza proporção pixel/cm
            threshold = 50
            if w > threshold and h > threshold:
                pixelWidth = min(w, h)
                self.convert_measures(fieldWidth, pixelWidth)

        except Exception as e:
            print(f"[SystemVision][REDUCE_FIELD]: Erro ao reduzir o campo: {e}")
            bin_Reduce, img_Reduce, cooVetor = BinImg, Img, [0, 0, 0, 0]
            self.prop_px_cm = 1

        return bin_Reduce, img_Reduce, cooVetor

    #função para converter medidas
    def convert_measures(self, w_cm, w_px):
        '''
            Ajusto a constante de proporcionaldiade de px para cm. 
            Representada pela variável: prop_px_cm
        '''
        #atualizando proporções para realizar os devidos cálculos
        self.prop_px_cm = w_px / w_cm
        self.min_diag = (7.5 / 4) * np.sqrt(2) * self.prop_px_cm

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

    def draw_player_virtual(self, robot:Robot):
        '''
            Desenha um círculo no jogador + seta indicando direção (no debug)
        '''
        xi = int(robot.position[0])
        yi = int(robot.position[1])
        ri = int(robot.radius)

        # converter para dimensões da imagem
        xi, yi = self.getImageIndice(np.array([xi, yi]))

        # Seleção de cor e rótulo
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
            color = (0, 0, 255)
            if robot.id == ID_Robots.ROBOT_ENEMY_GOAL:
                id = "G"
            elif robot.id == ID_Robots.ROBOT_ENEMY_1:
                id = "A1"
            elif robot.id == ID_Robots.ROBOT_ENEMY_2:
                id = "A2"
        else:
            team = "N/A"
            id = "N/A"
            color = (0, 255, 0)

        # Desenha o ponto central do robô
        cv2.circle(self.virtualImg, (xi, yi), 4, color, -1)
        text = f"{team}{id}"

        # px/cm = 3  => 6 cm = 18 px
        arrow_len_px = int(6 * 3)

        dir_vec = robot.direction  # já normalizada

        x_end = int(xi + dir_vec[0] * arrow_len_px)
        y_end = int(yi - dir_vec[1] * arrow_len_px)  # Y invertido na imagem

        # Corpo da seta
        cv2.arrowedLine(
                self.virtualImg,
                (xi, yi),
                (x_end, y_end),
                color,
                2,
                tipLength=0.3
            )
        
        # Sem debug → só o círculo e o texto padrão
        cv2.circle(self.virtualImg, (xi, yi), int(3 * robot.radius), color, 1)
        cv2.putText(
                self.virtualImg,
                text,
                (int(xi - 8), int(yi - 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                color,
                1
            )


    def isSquare(self, contorno):
        """
        Verifica se o contorno é aproximadamente quadrado
        usando medidas geométricas simples (mais rápido).
        """
        area = cv2.contourArea(contorno)
        if area < 10:  # ignora ruídos muito pequenos
            return False

        x, y, w, h = cv2.boundingRect(contorno)
        aspect = w / float(h)
        extent = area / (w * h)

        # Quadrados têm aspecto ~1 e extent próximo de 1
        return 0.7 <= aspect <= 1.3 and extent > 0.8


    def upSaturation(self, img, boost: int = 50):
        """
        Aumenta a saturação de uma imagem BGR.
        
        Parâmetros:
            img (np.ndarray): imagem em formato BGR.
            boost (int): valor a adicionar à saturação (padrão: +50).
        
        Retorna:
            np.ndarray: imagem com saturação aumentada.
        """
        # Converte para HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Aumenta o canal de saturação (S) de forma vetorizada
        hsv[..., 1] = np.clip(hsv[..., 1].astype(np.int16) + boost, 0, 255).astype(np.uint8)

        # Converte de volta para BGR
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    
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
    
    def detect_ally_robot(self, window, colorP, colorS):
        """
        Verifica se há um robô aliado dentro de uma janela, com base em duas cores (primária e secundária).

        Retorna:
            bool: True se ambas as cores forem detectadas, False caso contrário.

        Parâmetros:
            window (np.ndarray): imagem em que será feita a busca.
            colorP (list[int]): cor primária em HSV (ex: [H, S, V]).
            colorS (list[int]): cor secundária em HSV (ex: [H, S, V]).
        """
        try:
            # Cria limites HSV das duas cores
            p_lower, p_upper = self.create_color_bounds(colorP)
            s_lower, s_upper = self.create_color_bounds(colorS)

            # Obtém contornos das duas cores na janela
            contoursP = self.find_binary_contours(window, p_lower, p_upper)
            contoursS = self.find_binary_contours(window, s_lower, s_upper)

            # Define o raio mínimo esperado (pré-calculado para evitar recomputação)
            min_radius = max(2, 0.08 * self.secColorRadius)

            # Verifica se existem contornos com tamanho significativo
            primaryFound = any(cv2.minEnclosingCircle(c)[1] >= min_radius for c in contoursP)
            secondaryFound = any(cv2.minEnclosingCircle(c)[1] >= min_radius for c in contoursS)

            return primaryFound and secondaryFound

        except Exception as e:
            print(f"[detect_ally_robot] Erro ao processar imagem: {e}")
            return False

    def find_binary_contours(self, image, lower_bound, upper_bound):
        '''
        Encontra contornos na imagem capturada filtrando com HSV
        '''
        lower = np.array(lower_bound)
        upper = np.array(upper_bound)

        if image is None:
            print("[VisionSystem]: Em find_binary_contours() a Imagem é None")
            return [], None

        if image.shape[1] < 30:
            print("[VisionSystem]: Em find_binary_contours() a janela é muito pequena, provável que nem exista")
            return [], None
        
        imageHSV = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        binaryImage = cv2.inRange(imageHSV, lower, upper)
        
        structuringElement = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        binaryImage = cv2.morphologyEx(binaryImage, cv2.MORPH_CLOSE, structuringElement)
        binaryImage = cv2.erode(binaryImage, structuringElement, iterations=1)

        contours, _ = cv2.findContours(binaryImage, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        return contours
    
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

    
    #=============| Definindo funções módulares | ===========================
    def detect_field(self, img ,debug):
        '''
            Função responsável por detectar o campo na imagem e gerar um ViewRect com as coordenadas
            do campo que foi reduzido. Salvando o objeto em Field.

            Os argumentos da função são configurações vindas do emulador.
        '''
        # usa variável local para offSetErode — evitar alterar o atributo da classe entre frames
        local_offSetErode = self.offSetErode
        h = img.shape[0]
        w = img.shape[1]
        debug = debug

        self.pixelWidth = min(w,h)

        #conversão da imagem para pixels
        self.convert_measures(self.fieldWidth, self.pixelWidth)

        #flag para o laço while 
        flagStop = False 

        #looping principal
        while local_offSetErode< 20 and not flagStop:
            try:
                #imagem original
                self.frameOrigin = img.copy()

                if img is None:
                    print("[VisionSystem]: A imagem é nula!!")
                #tomando imagem em tons de cinza
                gray = self.gray_scale(self.frameOrigin)

                #aplica filtro de mediana para diminuir ruídos
                blur = self.median_blur(gray, 3)

                #realça objetos brilhantes, que nesse caso é o campo
                imgProc = self.highlight_img(blur, self.dimMatrix)

                #binarizando a imagem num limiar
                binary = self.binarize_up(imgProc, self.Thrashhold)

                #tratando ruídos da imagem binarizada
                self.binaryObjects = self.trait_noise(binary, self.offSetErode)

                #reduzindo imagem e gerando ViewRect
                self.binReduceField, self.fieldReduce, coorVetor = self.reduce_field(self.binaryObjects, self.frameOrigin, self.fieldWidth, self.offSetWindow)

                if self.fieldReduce is None:
                    print("[VisionSystem]: Passou do reduce field, mas o campo aqui não reduziu")
                    print("[VisionSystem]: Coorvetor", coorVetor)

                    self.binReduceField, self.fieldReduce = self.binaryObjects, self.frameOrigin
                
                #encontra extremos do paralelogramo
                contours, _ = cv2.findContours(self.binReduceField, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

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
                            
                            #Organizando da forma que o algorítmo entende
                            rectVer = self.sort_points(rectVer)
                            
                            #Verifica o tamanho do campo
                            dp = rectVer[1]-rectVer[0]
                            modDpPx = np.sqrt(dp[0]**2+dp[1]**2)

                            self.modDpCm = modDpPx/self.prop_px_cm

                            if self.modDpCm >= 60: #só salva um campo maior que 60 cm

                                #rv é a janela com um "offset" de valor dd na imagem original.
                                P1i=Point2D(rectVer[0, 0], rectVer[0, 1])
                                P2i=Point2D(rectVer[1, 0], rectVer[1, 1])
                                P3i=Point2D(rectVer[2, 0], rectVer[2, 1])
                                P4i=Point2D(rectVer[3, 0], rectVer[3, 1])

                                rect = Quad(P1=P1i, P2=P2i, P3=P3i, P4=P4i)

                                
                                #salvando extremos do objeto campo informando os extremos e o tamanho do campo
                                self.field.updatePos(rect, self.fieldWidth, self.fieldHeight)
                                
                                ptsSource =np.array([P1i.getPos(),P2i.getPos(),P3i.getPos(),P4i.getPos()])
                                ptsFinal  =np.array([self.fieldP1v,self.fieldP2v,self.fieldP3v,self.fieldP4v])
                                
                                #Adquirindo as matrizes de equivalência
                                self.getHomographyMatrix(ptsSrc=ptsSource, ptsFinal=ptsFinal)

                                #setando matrizes de homography para o campo conhecer
                                self.field.setHomographyMatrix(mHomography=self.homography_matrix, invHomo=self.inv_homography_matrix)

                        except Exception as e:
                            flagStop = False
                            print("[VisionSystem]: Não conseguiu desenhar na imagem: \n",e)
                            self.fieldReduce = img.copy()
                            self.frameResult = self.fieldReduce.copy()
                            traceback.print_exc()
                
                
                flagStop = True 
                self.frameResult = self.fieldReduce.copy()
                # sucesso: resetar o offSetErode persistente para comportamento inicial
                self.offSetErode = 0
                return self.modDpCm

            except Exception as e:
                flagStop = False
                self.offSetErode += 1
                print("[VisionSystem]: Foi necessário subir um pouco o offset, devido ao erro:\n",e)
                
                # Captura a stack trace do erro
                traceback.print_exc()

                #retornaria as variáveis, mas ele vai atualizar as variáveis internas
                self.fieldReduce = self.frameOrigin.copy()
                #copio o campo reduzido para frameResult
                self.frameResult = self.fieldReduce.copy()

                return -1



    #Detectar a imagem da bola na imagem
    def detect_ball(self, img, colorBall, debug:bool):
        '''
            Função responsável por detectar a bola na imagem

            Necessário informar a imagem que irá ser processada para encontrar a bola. A cor da bola e se irá querer exibir ela na imagem, que tem que ser informada em HSV
        '''
        #copiando imagem inicial
        self.ballImg = self.fieldReduce.copy()
        if self.fieldReduce is None:
            print("FIELDREDUCE É NONE")

        #Cor laranja da bola 
        h = colorBall[0]
        s = colorBall[1]
        v = colorBall[2]

        hue_tolerance = 6
        saturation_tolerance = 50
        value_tolerance = 50

        ball_lower_bound = np.array([h - hue_tolerance, max(0, s - saturation_tolerance), max(0, v - value_tolerance)])
        ball_upper_bound = np.array([h + hue_tolerance, min(255, s + saturation_tolerance), min(255, v + value_tolerance)])

        imgHSV = cv2.cvtColor(self.ballImg, cv2.COLOR_BGR2HSV)

        self.binaryBall = cv2.inRange(imgHSV, ball_lower_bound, ball_upper_bound)

        #Operações de erosão e fechamento
        structuringElement = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)) #(8,8)
        self.binaryBall = cv2.morphologyEx(self.binaryBall, cv2.MORPH_CLOSE, structuringElement)
        self.binaryBall = cv2.erode(self.binaryBall, structuringElement, iterations=1 )
        
        #Encontrando contornos da bola
        contours, _ = cv2.findContours(self.binaryBall, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            ballContour = max(contours, key=cv2.contourArea)
            (xb, yb), rb = cv2.minEnclosingCircle(ballContour)

            #passando o ponto para o espaço virtual
            xv, yv = self.transformPoint(np.array([xb,yb]))

            #valor do objeto dentro do sistema de coordenadas O'
            xcm, ycm = self.getPointVirtual(np.array([xv,yv]))
            
            #Tempo que se passou
            time = self.timer.getElapsedTime()

            rb = self.ballRadiusP   #cm -> valor padrão

            #atualizando posição do objeto bola
            self.ball.setPosition(xcm, ycm, rb, time)
            self.ball.setImgPosition(xb,yb,rb)

            rb = int(rb/self.prop_px_cm)
            xb = int(xb)
            yb = int(yb)

            # Circulando bola
            cv2.circle(self.frameResult, (xb, yb), (rb + 2), (0, 0, 255), 2)
            cv2.putText(self.frameResult, "B", (int(xb),int(yb-rb-10)), cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,255), 1)
            
            #parte plotando na imagem virtual
            xv = int(xv)
            yv = int(yv)
            
            #desenhando na imagem virtual
            cv2.circle(self.virtualImg, (xv, yv), 4, (0, 255,255), -1)
            cv2.putText(self.virtualImg, "B", (int(xv-5),int(yv-rb-10)), cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,255,255), 1)
            cv2.arrowedLine(self.virtualImg, (xv, yv), ((xv + int(self.ball.direction[0])), (yv + int(self.ball.direction[1]))), (0, 255, 255), 2)


    def detect_players(self, img, dbg=False, isT=False):
        """
        Detecta robôs na imagem com distinção por dominância de cor
        (comparando proporção de área entre cor de aliado e inimigo).
        Em modo debug, gera máscaras binárias de aliados e de todos os robôs.
        """
        debug = dbg
        # Reset de contadores e status
        self.playersCount = self.enemiesCount = self.alliesCount = 0
        for bot in (*self.enemyTeam, *self.allyTeam):
            bot.setStatus(False)

        # Garante a forma da máscara da bola
        if getattr(self, "binaryBall", None) is None or self.binaryBall.size == 0:
            self.binaryBall = np.zeros(img.shape[:2], dtype=np.uint8)
        elif self.binaryBall.shape != img.shape[:2]:
            self.binaryBall = cv2.resize(self.binaryBall, (img.shape[1], img.shape[0]))

        # Conversão e máscaras
        imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        Objects = cv2.inRange(imgHSV, self.objectsDarkColor, self.objectsLightColor)
        self.binaryPlayers = cv2.subtract(Objects, self.binaryBall)

        # Filtragem morfológica
        ellipse5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        rect11 = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
        self.binaryPlayers = cv2.erode(self.binaryPlayers, ellipse5, iterations=1)
        self.binaryPlayers = cv2.morphologyEx(self.binaryPlayers, cv2.MORPH_CLOSE, rect11)

        # Limites de cor
        self.ally_lower_bound, self.ally_upper_bound = self.create_color_bounds(self.allyColor)
        self.enemy_lower_bound, self.enemy_upper_bound = self.create_color_bounds(self.enemyColor)

        # Reconhecimento de objetos
        self.binaryPlayers, players = self.detect_squares(self.binaryPlayers)

        # Pré-cálculos
        winSize = int(18 * self.prop_px_cm)
        playerRadius = (7.5 / 2) * np.sqrt(2) * self.prop_px_cm
        mainColorRadius = (7.5 / 4) * np.sqrt(5) * self.prop_px_cm

        # Flags de controle
        AgoalFlag = Aatk1Flag = Aatk2Flag = False

        # Inicializa máscaras de debug se necessário
        if debug:
            binaryAllies = np.zeros(img.shape[:2], dtype=np.uint8)
            binaryAllTeam = np.zeros(img.shape[:2], dtype=np.uint8)

            print("\n===============================")
            print(f"🔍 [DEBUG] Detectando robôs na imagem...")
            print(f"▪ Total de possíveis jogadores detectados: {len(players)}")
            print("===============================")

        for i, currentPlayer in enumerate(players):
            # Coordenada do centro do robô na imagem reduzida, já detectada.
            (xi, yi), ri = cv2.minEnclosingCircle(currentPlayer)

            if debug:
                print(f"\n[🧩 Player {i+1}] Posição estimada: ({xi:.1f}, {yi:.1f}) | Raio: {ri:.2f}")
                cv2.circle(self.frameResult, (int(xi), int(yi)), int(ri) + 5, (0, 255, 0), 2)       
            if not (0.2 * playerRadius < ri < 2 * playerRadius and self.playersCount < 6):
                if debug:
                    print("  ⚠️ Ignorado (fora do range esperado ou excedeu limite).")
                continue


            # recorta área de interesse
            half_win = winSize // 2
            x1, y1 = max(0, int(xi - half_win)), max(0, int(yi - half_win))
            x2, y2 = min(img.shape[1], int(xi + half_win)), min(img.shape[0], int(yi + half_win))
            windowActual = img[y1:y2, x1:x2]

            # converte a região para HSV
            hsv = cv2.cvtColor(windowActual, cv2.COLOR_BGR2HSV)

            # Máscaras de cor
            mask_ally = cv2.inRange(hsv, self.ally_lower_bound, self.ally_upper_bound)
            mask_enemy = cv2.inRange(hsv, self.enemy_lower_bound, self.enemy_upper_bound)

            # Áreas detectadas
            ally_area = cv2.countNonZero(mask_ally)
            enemy_area = cv2.countNonZero(mask_enemy)
            total_area = max(ally_area + enemy_area, 1)

            # Proporções relativas
            ally_ratio = ally_area / total_area
            enemy_ratio = enemy_area / total_area

            if debug:
                print(f"  ▪ Proporção aliado: {ally_ratio:.2f} | inimigo: {enemy_ratio:.2f}")

            # Decide dominância
            if ally_ratio > 0.55:
                team_type = "ally"
            elif enemy_ratio > 0.55:
                team_type = "enemy"
            else:
                team_type = "uncertain"

            #Tempo coletado para salvar os robôs
            tm = self.timer.getElapsedTime()/1000.0 #Tempo que foi detectado em segundos

            xcm, ycm = self.getPointVirtual(self.transformPoint(np.array([xi, yi])))
            rcm = 5.30

            # --- INIMIGOS ---
            if team_type == "enemy" and self.enemiesCount < 3:
                contour = max(cv2.findContours(mask_enemy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0],
                            key=cv2.contourArea, default=None)
                if contour is not None:
                    (x_m, y_m), rc = cv2.minEnclosingCircle(contour)

                    # Transformar as coordenadas da janela para as coordenadas reais (somando o extremo novamente)
                    x_m = x_m+x1
                    y_m = y_m+y1

                    if debug:
                        print(f"  🔴 Inimigo detectado | Raio cor: {rc:.2f}")
                    if rc >= 0.6 * mainColorRadius:
                        #Direção do robô nas coordenadas da imagem, apenas transformando corretamente
                        # como as coordenadas da imagem tem y negativo como padrão, inverte o sinal dele
                        direction = np.array([xi,-yi]) - np.array([x_m,-y_m]) 

                        #Normalizando
                        modDir = np.linalg.norm(direction)
                        if modDir > 1e-6:
                            direction = direction/modDir

                        # Adquirindo as cores principais do robô
                        C_p, C_s, _ = self.get_centers_colors(xi,yi, x_m, y_m)

                        # Cor principal do inimigo
                        Color_p = self.get_hsv_mean(imgHSV, C_p[0],C_p[1])

                        # Cor secundária do inimigo
                        Color_s = self.get_hsv_mean(imgHSV, C_s[0],C_s[1])

                        # Pegar quais são essas cores 
                        bot = self.enemyTeam[self.enemiesCount]
                        bot.setPosition(x=xcm, y=ycm, r=rcm, image=windowActual, time=tm)
                        bot.updtPositionImg(xi=xi, yi=yi, ri=ri)
                        bot.setStatus(True)
                        bot.setDirection(direction)
                        bot.setColor(colorT=self.enemyColor, colorP=Color_p, colorS=Color_s)
                        self.draw_player_circle(self.frameResult, bot)
                        self.draw_player_virtual(bot)
                        self.enemiesCount += 1
                        
                        if debug:
                            print(f"  ✅ Inimigo #{self.enemiesCount} confirmado.")
                            # ponto da cor dominante (x_m, y_m)
                            cv2.circle(self.frameResult, (int(x_m), int(y_m)), 3, (255, 128, 255), -1) # laranja

                           # --- C_p ---
                            cx, cy = int(C_p[0]), int(C_p[1])
                            bgr_p = self.hsv2bgr(Color_p)

                            cv2.circle(self.frameResult, (cx, cy), 4, (0, 0, 0), -1)   # borda preta
                            cv2.circle(self.frameResult, (cx, cy), 3, bgr_p, -1)       # dentro colorido

                            # --- C_s ---
                            cx2, cy2 = int(C_s[0]), int(C_s[1])
                            bgr_s = self.hsv2bgr(Color_s)

                            cv2.circle(self.frameResult, (cx2, cy2), 4, (0, 0, 0), -1)  # borda preta
                            cv2.circle(self.frameResult, (cx2, cy2), 3, bgr_s, -1)      # dentro colorido


            # --- ALIADOS ---
            elif team_type == "ally" and self.alliesCount < 3:
                contour = max(cv2.findContours(mask_ally, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0],
                            key=cv2.contourArea, default=None)
                if contour is not None:
                    (x_m, y_m), rc = cv2.minEnclosingCircle(contour)
                    
                    # Transformar as coordenadas da janela para as coordenadas reais (somando o extremo novamente)
                    x_m = x_m+x1
                    y_m = y_m+y1

                    if debug:
                        print(f"  🔵 Possível aliado detectado | Raio cor: {rc:.2f}")

                    if rc >= 0.5 * mainColorRadius:
                        tim = self.timer.getElapsedTime()
                        ally_checks = [
                            (not AgoalFlag, self.goalAllyColor1, self.goalAllyColor2, ID_Robots.ROBOT_ALLY_GOAL, "Goleiro"),
                            (not Aatk1Flag, self.atk1AllyColor1, self.atk1AllyColor2, ID_Robots.ROBOT_ALLY_1, "Atacante 1"),
                            (not Aatk2Flag, self.atk2AllyColor1, self.atk2AllyColor2, ID_Robots.ROBOT_ALLY_2, "Atacante 2"),
                        ]

                        for flag, c1, c2, bot_id, name in ally_checks:
                            if flag and self.detect_ally_robot(windowActual, c1, c2):
                                #Direção do robô nas coordenadas da imagem, apenas transformando corretamente
                                # como as coordenadas da imagem tem y negativo como padrão, inverte o sinal dele
                                direction = np.array([xi,-yi]) - np.array([x_m,-y_m]) 

                                #Normalizando
                                modDir = np.linalg.norm(direction)
                                if modDir > 1e-6:
                                    direction = direction/modDir

                                bot = self.allyTeam[bot_id]
                                bot.setPosition(xcm, ycm, rcm, windowActual, time=tim)
                                bot.updtPositionImg(xi, yi, ri)
                                bot.setStatus(True)
                                bot.setDirection(direction)
                                bot.setColor(colorT=self.allyColor, colorP=c1, colorS=c2)
                                self.draw_player_circle(self.frameResult, bot)
                                self.draw_player_virtual(bot)
                                if bot_id == ID_Robots.ROBOT_ALLY_GOAL:
                                    if debug:
                                        print(f"  ✅ Goleiro Aliado Detectado")

                                    AgoalFlag = True
                                elif bot_id == ID_Robots.ROBOT_ALLY_1:
                                    if debug:
                                        print(f"  ✅ Atacante 1 Aliado Detectado")

                                    Aatk1Flag = True
                                else:
                                    if debug:
                                        print(f"  ✅ Atacante 2 Aliado Detectado")

                                    Aatk2Flag = True

                                if debug:

                                    # ponto da cor dominante (x_m, y_m)
                                    cv2.circle(self.frameResult, (int(x_m), int(y_m)), 4, (255, 128, 255), -1) # laranja


                                break

                        self.alliesCount = min(self.alliesCount + 1, 3)

                        # Adiciona aos binários em debug
                        if debug:
                            cv2.drawContours(binaryAllies, [currentPlayer], -1, 255, -1)
                            cv2.drawContours(binaryAllTeam, [currentPlayer], -1, 255, -1)

            self.playersCount += 1

        if debug:
            self.binaryAllies = binaryAllies
            self.binaryAllTeam = binaryAllTeam
            print("\n===============================")
            print(f"🏁 [DEBUG] Resumo da detecção:")
            print(f"    ▪ Total: {self.playersCount}")
            print(f"    ▪ Aliados: {self.alliesCount}")
            print(f"    ▪ Inimigos: {self.enemiesCount}")
            print("===============================")

        self._countProcess += 1

    #desenhar robôs na imagem
    def drawAllRobots(self):
        '''
            Desenhando todos os robôs na imagem final
        '''
        for bot in self.allyTeam:
            if bot.getStatus():
                self.draw_player_circle(self.frameResult, bot)
                self.draw_player_virtual(bot)

        for bot in self.enemyTeam:
            if bot.getStatus():
                self.draw_player_circle(self.frameResult, bot)
                self.draw_player_virtual(bot)


#==========================| MÉTODOS DE PREVISÃO DO KALMAN | ================================================
    #prevendo posição da bola
    def predictBall(self, timestamp:int):
        '''
            Função para prever posição da bola com base na imagem
            processo de encontrar a bola
        '''

        pass 
    # função para para puxar informações de predição
    def predictRobot(self, team:ID_Team, robot_id:ID_Robots, timestamp:int):
        '''
            prevê posições dos robôs informando i time dele e o identificador do robô
        '''
        pass 

# ==========================| Utilidades para métodos estruturados | =============================================
    # Método novo para procurar se existe um robô na janela
    def get_centers_colors(self, xci, yci, xmci, ymci, tol=45):
        '''
            Retorna os centros das cores primária e secundária.
            (xci, yci) são os centros do objeot (coordenadas da imagem)
            (xmci, ymci) são os centros da cor principal (coordenadas da image)
            tol = tolerancia da aquisição
        '''
        
        dx = xci - xmci
        dy = yci - ymci
        norm = (dx*dx + dy*dy)**0.5
        if norm < 1e-6:
            return (xci, yci), (xci, yci), (0.0, 0.0)

        dirx = dx / norm
        diry = dy / norm

        # Constantes pré-computadas
        L_m = 2.651650429449553
        L_s = 5.303300858899106

        tol_ang = 1 + (tol + 20) / 100.0
        tol_lin = 1 + tol / 100.0

        theta = np.arctan2(L_m, L_s) * tol_ang
        k = (L_m*L_m + L_s*L_s)**0.5 * tol_lin

        cos_t = np.cos(theta)
        sin_t = np.sin(theta)

        # Rotação manual
        r1x = k * (dirx*cos_t + diry*sin_t)
        r1y = k * (-dirx*sin_t + diry*cos_t)

        r2x = k * (dirx*cos_t - diry*sin_t)
        r2y = k * (dirx*sin_t + diry*cos_t)

        return (xci + r1x, yci + r1y), (xci + r2x, yci + r2y), (dirx, diry)

    def get_hsv_mean(self, img_hsv, x, y, kernel=2):
        """
        Retorna a média HSV de uma região quadrada (ex: 3x3) centrada em (x, y).
        kernel=1 → janela 3x3
        kernel=2 → janela 5x5
        """
        h, w = img_hsv.shape[:2]
        x, y = int(x), int(y)
        
        # limites seguros (cortando nas bordas)
        x1, x2 = max(0, x - kernel), min(w, x + kernel + 1)
        y1, y2 = max(0, y - kernel), min(h, y + kernel + 1)
        
        region = img_hsv[y1:y2, x1:x2]
        if region.size == 0:
            return np.array([0, 0, 0], dtype=np.float32)

        mean_hsv = region.mean(axis=(0, 1))

        return mean_hsv
    
    def hsv2bgr(self, color_hsv):
        '''
            Converte HSV para BGR
        '''
        hsv_pixel = np.uint8([[color_hsv]])   # shape (1,1,3)
        bgr_pixel = cv2.cvtColor(hsv_pixel, cv2.COLOR_HSV2BGR)
        return tuple(int(c) for c in bgr_pixel[0,0])

    def color_in_range(self, hsv_values, lower, upper):
        """
        Verifica se uma ou várias cores HSV estão dentro da faixa especificada.
        Suporta faixas que cruzam o limite do Hue (ex: vermelho 170–10).

        Parâmetros:
            hsv_values : np.ndarray
                Cor única [H, S, V] ou matriz Nx3 com várias cores HSV.
            lower : iterable
                Limite inferior [H, S, V].
            upper : iterable
                Limite superior [H, S, V].

        Retorna:
            np.ndarray (bool) se hsv_values for Nx3, ou bool se for [3]
        """
        hsv_values = np.atleast_2d(hsv_values).astype(np.uint16)
        lower = np.array(lower, dtype=np.uint16)
        upper = np.array(upper, dtype=np.uint16)

        # --- caso em que faixa cruza o 0° do Hue (ex: 170–10)
        if lower[0] > upper[0]:
            mask_hue = ((hsv_values[:, 0] >= lower[0]) | (hsv_values[:, 0] <= upper[0]))
        else:
            mask_hue = ((hsv_values[:, 0] >= lower[0]) & (hsv_values[:, 0] <= upper[0]))

        # --- máscaras para S e V (sempre diretas)
        mask_sat = ((hsv_values[:, 1] >= lower[1]) & (hsv_values[:, 1] <= upper[1]))
        mask_val = ((hsv_values[:, 2] >= lower[2]) & (hsv_values[:, 2] <= upper[2]))

        # Combina tudo
        mask = mask_hue & mask_sat & mask_val

        # Retorna booleano simples se foi entrada única
        return mask[0] if hsv_values.shape[0] == 1 else mask

    def is_color_match(self, measured_hsv, target_hsv):
        lower, upper = self.create_color_bounds(target_hsv)
        return self.color_in_range(measured_hsv, lower, upper)

    # ================= Método simplificado de processamento ==========
    def search_obj(self, wnd, object:ID_Objects, bot:ID_Robots):
        '''
            Método compatível de checar uma janela compatível com o 
            filtro de Kalman. Ou seja, a partir dele ele realiza o processamento
            apenas na janela.

            Necessário apenas enviar a janela 
        '''
        if object == ID_Objects.ALLIES:
            if bot == ID_Robots.ROBOT_ALLY_GOAL:
                pass
            elif bot == ID_Robots.ROBOT_ALLY_1:
                pass
            elif bot == ID_Robots.ROBOT_ALLY_2:
                pass
        elif object == ID_Objects.ENEMIES:
            if bot == ID_Robots.ROBOT_ENEMY_GOAL:
                pass
            elif bot == ID_Robots.ROBOT_ENEMY_1:
                pass
            elif bot == ID_Robots.ROBOT_ENEMY_2:
                pass
        elif object == ID_Objects.BALL:
            pass

    def search_bots(self, wnd, debug=False) -> bool:
        '''
        Função responsável por verificar se há um robô aliado ou inimigo dentro de uma janela, com base na cor do time.
        Ela retorna TRUE quando a cor é detectada e retorna FALSE quando nenhuma cor é detectada.

        Variáveis:
        - player: contorno referente ao robô processado
        - wnd: janela da região de interesse
        - flags: flags (AgoalFlag, Aatk1Flag, Aatk2Flag)
        '''
        pass 

    def search_ball(self, wnd, debug=False) -> bool:
        '''
        Função responsável por procurar pela bola na janela indicada
        '''
        pass 
    
    # =================== Delete | Liberação de recursos =================

# Testar função principal e nova lógica
if __name__ =='__main__':
    print("Utilizada em função de main")