# ==========================================================================================
# MÓDULO DE FUNÇÕES PARA ALGORÍTMO DE DETECÇÃO VSS (version v3.2)
#==========================================================================================
'''
    @GNOMIO: Sismtea de detecção de objetos VSS (Vision System Soccer) versão 2.2.40    
    
    Versão: v3.2.2
    Última modificação: 22/11/2025
    Autor: Saulo (update)

    Patch Notes v3.2.2:
    - Foi atualizado a função de detecção que utiliza filtro de Kalman
    - Novo gerenciamento de cores dos jogadores

    Obs: Ainda está numa versão BETA, necessário testes para verificar se está
    corretamente funcionando!!!

'''
#importando bibliotecas necessárias para o código
import cv2
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
from modules.VisionSys.components.combination import *

import traceback

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

        self.bmk = Benchmark()

        # ===============================================================================
        # WATCHDOG CONFIG
        self.MAX_MISSED_FRAMES_BALL = 10  # ~0.3s a 30fps
        self.MAX_MISSED_FRAMES_ROBOT = 15 # Robôs tem mais inércia, toleramos mais
        
        # ESTADO
        self.missed_frames_ball = 0
        self.ball_kalman_reset_flag = False # Começa resetado
        
        # Para robôs, usamos um dicionário {robot_id: missed_count}
        # Inicializa com 0 para todos os seus robôs (ex: 3 aliados, 3 inimigos)
        self.missed_frames_robots = {} 
        self.robot_kalman_reset_flags = {}
        #+====================================================================================

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
        self.fieldWidth             =  150                    # largura do campo
        self.fieldHeight            = 130                     # altura do campo
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

        self.newSendTime = 0.02

        #Tamanho padrão da bola
        self.ballRadiusP = 2.135 #cm

        #tamanho do campo para utilizar
        self.modDpCm     = 0        
        self.fieldDetectedFlag = False 

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
        self.fieldDetectionFailCount  = 0
        self.maxFieldFailures = 10

        self.playersWindows     = [None, None, None, None, None, None]

        self.alliesWindows      = [None, None, None]
        self.enimiesWindows     = [None, None, None]

        #lista de threads a serem utilizadas pelo objeto
        self._threads           = []

        #Variável importante para ditar quanto tempo até a próxima atualização de dados
        self.newProcTime        = 10000
        
        # Variável da identificação de cores
        self.colorTree = TreeColors()

        # Objetos utilizados para estrutura do código.
        self.struct_ellipse5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
        self.struct_rect11   = cv2.getStructuringElement(cv2.MORPH_RECT,   (11,11))

        
        #Extrai os dados do objeto de configuração 
        self.toMineData()

        # CACHE
        # [OTIMIZAÇÃO] Cache de estruturas para detect_field
        # Evita recriar matrizes a cada frame
        self.kernel_blur = (5, 5) 
        self.kernel_morph = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)) 
        
        self.ptsSource_buffer = np.zeros((4, 2), dtype=np.float32)
        # Cache para evitar alocação de numpy arrays no loop
        self.ptsSource_cache = np.zeros((4, 2), dtype=np.float32)
        self.ptsFinal_cache = np.array([
                self.fieldP1v, self.fieldP2v,
                self.fieldP3v, self.fieldP4v
            ], dtype=np.float32)
    
        #construir o campo
        self.buildField()
    
    # Implementação da lógica de processamento para várias coisas
    def proc(self, img, currentTime, debug: bool, isT: bool = False, force_field_detect: bool = True):
            """
            Executa a detecção do campo (sob demanda) e robôs.
            Arg:
                force_field_detect: Se True, força a execução pesada do detect_field.
                                    Se False, tenta reutilizar o ROI anterior (cooVetor).
            """
            # ===========================
            # RESET ESTADO E TEMPOS
            # ===========================
            self.resetExecutionState()
            
            if not hasattr(self, 'lastMajorTime') or self.lastMajorTime == 0:
                self.lastMajorTime = self.timer.getElapsedTime()
            self._firstTimeExec = (currentTime - self.lastMajorTime) / 1000.0
            self.debug = debug

            if img is None:
                return img

            # =========================================================
            # 1. DETECÇÃO DE CAMPO (OBRIGATÓRIA A CADA FRAME)
            # =========================================================

            # Decide se roda a detecção pesada ou usa o cache
            # Só usamos o cache se: NÃO forçado E o campo já foi detectado antes E temos o vetor salvo
            use_cache = (not force_field_detect) and self.fieldDetectedFlag and (self.viewCapture.cooVetor is not None)

            wbCmField = 0 

            if use_cache:
                try:
                    # OTIMIZAÇÃO: Recorta a imagem baseada no último ROI válido
                    # O cooVetor geralmente é [x, y, w, h] ou [j, i, w, h]
                    x, y, w, h = self.viewCapture.cooVetor
                    
                    # Validação de limites para evitar crash do numpy
                    if x < 0 or y < 0 or (x+w) > img.shape[1] or (y+h) > img.shape[0]:
                        raise ValueError("ROI fora dos limites da imagem")

                    # Gera o fieldReduce manualmente (Processamento < 0.1ms)
                    self.fieldReduce = img[y : y + h, x : x + w]
                    wbCmField = w # Assume a largura do recorte
                    
                except Exception as e:
                    if debug: print(f"[VS][PROC] Falha ao usar cache do campo: {e}. Forçando detecção.")
                    use_cache = False # Falha no cache, força detecção abaixo

            # Se não pode usar cache (ou falhou), roda a pesada detect_field (~10ms)
            if not use_cache:
                self.bmk.tic()
                wbCmField = self.detect_field(img, debug)
                self.bmk.toc("Campo")

            # Validação simples do campo (Crítico para garantir que o recorte ou detecção funcionou)
            campo_valido = (
                wbCmField != -1
                and self.fieldReduce is not None
                and self.fieldReduce.shape[0] > 10 
                and self.fieldReduce.shape[1] > 10
            )
            self.fieldDetectedFlag = campo_valido

            if not campo_valido:
                try: self.lastMajorTime = self.timer.getElapsedTime()
                except: self.lastMajorTime = currentTime
                return img
                
            # =========================================================
            # 2. OTIMIZAÇÃO CRÍTICA: CACHE DE HSV
            # =========================================================
            self.hsv_fieldReduce = cv2.cvtColor(self.fieldReduce, cv2.COLOR_BGR2HSV)

            # =========================================================
            # 3. DETECÇÃO DE OBJETOS (Usando o Cache)
            # =========================================================
            self.bmk.tic()
            self._safe_call(self.detect_ball, self.fieldReduce, currentTime, debug, 
                            name="BALL", hsv_img=self.hsv_fieldReduce)
            self.bmk.toc("Bola")

            self.bmk.tic()
            self._safe_call(self.detect_players, self.fieldReduce, currentTime, debug, isT=isT, 
                            name="PLAYERS", hsv_img=self.hsv_fieldReduce)
            self.bmk.toc("Players")

            # ===========================
            # 3) RENDERIZAÇÃO / VISUALIZAÇÃO (O GARGALO REAL)
            # ===========================
            # AQUI está o segredo da performance. Só gastamos CPU desenhando se alguém for ver.
            if debug:
                # Agora sim criamos a cópia para desenhar em cima
                if hasattr(self, 'virtual'):
                    self.virtualImg = self.virtual.copy()

                self.bmk.tic()
                self._draw_field_debug()
                self.bmk.toc("Draw Field Debug")

                self.colorTree.print_store()
                
                # Essa função é a mais pesada visualmente (loops de desenho)
                self.bmk.tic()
                self.drawAllRobots()
                self.bmk.toc("Draw Robots")
            # ===========================
            # ATUALIZA TEMPO FINAL
            # ===========================
            try:
                self.lastMajorTime = self.timer.getElapsedTime()
            except Exception:
                self.lastMajorTime = currentTime

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
        self.fieldDetectionFailCount  = 0
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
        self.colorTree.clear()
        self.setTreeColorDefault()

    def _detect_field_once(self, img, debug):
        '''
            Método auxiliar para detectar o campo uma vez e retornar se foi válido.
        '''
        wb = self.detect_field(img, debug)

        campo_valido = (
            wb != -1 and
            abs(wb - self.fieldWidth) < 20 and
            self.fieldReduce is not None
        )

        self.fieldDetectedFlag = campo_valido
        return campo_valido


    def processImg(self, img, debug: bool):
        """
        Orquestrador: Gerencia a troca entre Detecção (Proc) e Rastreamento (Filtered).
        """
        self.debug = debug
        self.frameOrigin = img
        if img is None: return img
        if self.timer is None: self.timer = HighPrecisionTimer()
        self.currentTime = self.timer.getElapsedTime()

        # =========================================================
        # MODO IMAGEM (PROCESSAMENTO ÚNICO)
        # =========================================================
        if self.emulatorMode == MODE_IMAGE:
            self._count = 0
            self.lastMajorTime = 0
            self.proc(img, self.currentTime, debug)
            return self.frameResult
        
        # =========================================================
        # MODO VÍDEO (PROCESSAMENTO CONTÍNUO)
        # =========================================================
        # 1) Campo ainda NÃO detectado → Detecta aqui e avisa o proc para NÃO detectar de novo
        if not self.fieldDetectedFlag:
            wb = self.detect_field(img, debug)
            # ... validação ...
            campo_valido = (wb != -1 and self.fieldReduce is not None) # Simplificado para leitura
            self.fieldDetectedFlag = campo_valido
            self._count = 0
            self.lastMajorTime = self.currentTime

            if not campo_valido: return img

            # OTIMIZAÇÃO AQUI: Passamos False porque ACABAMOS de detectar acima
            self.proc(img, self.currentTime, debug, force_field_detect=False)
            return getattr(self, "frameResult", img)
        
        # 2) Verifica tempo para recalibração periódica
        elapsed = self.currentTime - self.lastMajorTime
        should_recalibrate = elapsed >= self.newProcTime

        if should_recalibrate:
            wb = self.detect_field(img, debug)
            campo_valido = (wb != -1 and self.fieldReduce is not None)
            self.fieldDetectedFlag = campo_valido
            self.lastMajorTime = self.currentTime
            self._count = 0

            if campo_valido:
                # OTIMIZAÇÃO AQUI: Passamos False, pois detect_field já rodou acima
                self.proc(img, self.currentTime, debug, force_field_detect=False)
                return getattr(self, "frameResult", img)
            else:
                return img
        
        # 3) Warm-up do Kalman (frames iniciais)
        WARMUP_FRAMES = 120
        if self._count < WARMUP_FRAMES:
            self._count += 1

            self.proc(img, self.currentTime, debug, force_field_detect=False)
            return getattr(self, "frameResult", img)
        
        #4) Rastreamento rápido (Filtered Detection)
        try:
            self.filtered_detection(img, self.currentTime, debug)
        except Exception as e:
            if debug: print(f"[VisionSystem] Erro no Tracking: {e}. Reiniciando detecção.")
            
            # 1. Marca que perdemos a garantia de onde está o campo
            self.fieldDetectedFlag = False
            self._count = 0

            # 2. Chama a proc() forçando a redetecção completa para recuperar o sistema
            # Como o padrão já é True, chamar self.proc(img, ...) funciona, 
            # mas explicitar ajuda na leitura:
            self.proc(img, self.currentTime, debug, force_field_detect=True)


        # Cálculo de dT para física/predição
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

        # Limites de cor
        self.ally_lower_bound, self.ally_upper_bound = self.create_color_bounds(self.allyColor)
        self.enemy_lower_bound, self.enemy_upper_bound = self.create_color_bounds(self.enemyColor)

        #Cor laranja da bola 
        h = self.ballColor[0]
        s = self.ballColor[1]
        v = self.ballColor[2]

        hue_tolerance = 6
        saturation_tolerance = 50
        value_tolerance = 50

        self.ball_lower_bound = np.array([h - hue_tolerance, max(0, s - saturation_tolerance), max(0, v - value_tolerance)])
        self.ball_upper_bound = np.array([h + hue_tolerance, min(255, s + saturation_tolerance), min(255, v + value_tolerance)])

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
        '''Setando configurações padrões da árvore de cores'''
        # Time Aliado
        self.colorTree.add_robot(
            ID_Team.TEAM_ALLY,      # time
            ID_Robots.ROBOT_ALLY_GOAL,  # ID do robô
            self.allyColor,         # cor principal do time
            self.goalAllyColor1,    # cor primária do robô
            self.goalAllyColor2     # cor secundária do robô
        )
        
        self.colorTree.add_robot(
            ID_Team.TEAM_ALLY,
            ID_Robots.ROBOT_ALLY_1,
            self.allyColor, 
            self.atk1AllyColor1,
            self.atk1AllyColor2
        )
        
        self.colorTree.add_robot(
            ID_Team.TEAM_ALLY,
            ID_Robots.ROBOT_ALLY_2, 
            self.allyColor, 
            self.atk2AllyColor1,
            self.atk2AllyColor2
        )
        
        # Time Inimigo (exemplo - se necessário)
        # self.colorTree.add_robot(
        #     ID_Team.TEAM_ENEMY,
        #     self.enemyColor,
        #     ID_Robots.ROBOT_ENEMY_GOAL,
        #     self.goalEnemyColor1,
        #     self.goalEnemyColor2
        # )
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
            Esse método pega as coordenadas virtuais em O' e passa retorna para os indices da imagem real.
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
            kernel = self.kernel_morph

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
        Reduz a imagem para a região do maior contorno (campo).
        """

        # Buscar contornos externos
        contours, _ = cv2.findContours(BinImg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            print("[SystemVision]/[REDUCE_FIELD]: Nenhum contorno encontrado.")
            return BinImg, Img, [0, 0, 0, 0]

        try:
            # Selecionar contornos úteis (descartar ruidos pequenos)
            contours = [c for c in contours if cv2.contourArea(c) > 200]  
            if not contours:
                print("[REDUCE_FIELD]: Contornos muito pequenos.")
                return BinImg, Img, [0, 0, 0, 0]

            # Maior contorno
            objT = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(objT)
            cooVetor = [x, y, w, h]

            # Margem segura
            d = max(0, d)

            # Limite dos eixos
            maxH, maxW = BinImg.shape[:2]

            y1 = max(0, y - d)
            y2 = min(maxH, y + h + d)
            x1 = max(0, x - d)
            x2 = min(maxW, x + w + d)

            # Recortes
            bin_Reduce = BinImg[y1:y2, x1:x2]
            img_Reduce = Img[y1:y2, x1:x2]

            # Retângulo do View Capture (ordem consistente)
            pi = np.float32([
                [x1, y1],  # TL
                [x2, y1],  # TR
                [x2, y2],  # BR
                [x1, y2]   # BL
            ])

            rect = Quad(
                Point2D(pi[0, 0], pi[0, 1]),   # TL
                Point2D(pi[1, 0], pi[1, 1]),   # TR
                Point2D(pi[2, 0], pi[2, 1]),   # BR
                Point2D(pi[3, 0], pi[3, 1])    # BL
            )

            # Atualiza viewport
            self.viewCapture.setViewCapture(rect, cooVetor)

        except Exception as e:
            print(f"[SystemVision][REDUCE_FIELD]: Erro ao reduzir o campo: {e}")
            return BinImg, Img, [0, 0, 0, 0]

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

    # =========== | CALIBRAÇÃO DA CÂMERA | ===========================

    """
    @GNõMIO 2025: Aqui seria interessante, mas seria um bonûs. Pois, só com a homografica
    já garanto resultados suficientemente satisfatórios.
    """
    #=============| Definindo funções módulares | ===========================
    
    def _check_field_reset(self):
        """
        Verifica se houve muitas falhas consecutivas na detecção do campo
        e executa um reset completo se necessário.
        """
        if self.fieldDetectionFailCount >= self.maxFieldFailures:
            print(f"[VisionSystem] RESET: {self.fieldDetectionFailCount} falhas consecutivas na detecção do campo")
            
            # Reset completo de todos os objetos
            for bot in (*self.allyTeam, *self.enemyTeam):
                bot.reset()  # Reset completo (incluindo Kalman)
                
            if hasattr(self, "ball"):
                self.ball.reset()
                
            # Reset de transformações e configurações
            self.homography_matrix = None
            self.inv_homography_matrix = None
            self.fieldDetectedFlag = False
            
            # Reset do contador (opcional - ou manter para evitar reset contínuo)
            self.fieldDetectionFailCount = 0  # Reset para evitar múltiplos resets
            
            if self.debug:
                print("[FIELD_RESET] Sistema resetado devido a falhas persistentes na detecção do campo")
                

    def detect_field(self, img, debug):
        """
        Detecta o campo com no máximo DUAS tentativas.
        Retorna o tamanho do campo detectado em centímetros ou -1 se falhar.
        """

        if img is None:
            print("[VisionSystem]: A imagem é nula!!")
            self.fieldDetectionFailCount += 1
            self._check_field_reset()
            return -1

        h, w = img.shape[:2]
        self.pixelWidth = min(w, h)

        # Vamos tentar apenas com esses dois offsets:
        tentativa_offsets = [self.offSetErode, self.offSetErode + 1]

        campo_detectado = False
        resultado_dp_cm = -1

        for local_offset in tentativa_offsets:
            try:
                # imagem base desta tentativa
                self.frameOrigin = img.copy()

                # pipeline de processamento
                gray = self.gray_scale(self.frameOrigin)
                blur = self.median_blur(gray, 3)
                imgProc = self.highlight_img(blur, self.dimMatrix)
                binary = self.binarize_up(imgProc, self.Thrashhold)

                self.binaryObjects = self.trait_noise(binary, local_offset)

                self.binReduceField, self.fieldReduce, coorVetor = self.reduce_field(
                    self.binaryObjects,
                    self.frameOrigin,
                    self.fieldWidth,
                    self.offSetWindow
                )

                if self.fieldReduce is None:
                    self.fieldReduce = self.frameOrigin.copy()

                contours, _ = cv2.findContours(
                    self.binReduceField,
                    cv2.RETR_EXTERNAL,
                    cv2.CHAIN_APPROX_SIMPLE
                )

                encontrou_retangulo = False

                for contour in contours:
                    epsilon = 0.02 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)

                    if len(approx) != 4:
                        continue

                    rectVer = np.array([a[0] for a in approx], dtype=np.int32)
                    rectVer = self.sort_points(rectVer)

                    top = np.linalg.norm(rectVer[1] - rectVer[0])
                    bottom = np.linalg.norm(rectVer[2] - rectVer[3])
                    left = np.linalg.norm(rectVer[3] - rectVer[0])
                    right = np.linalg.norm(rectVer[2] - rectVer[1])

                    width_px = (top + bottom) / 2
                    height_px = (left + right) / 2

                    self.convert_measures(self.fieldWidth, width_px)
                    modDpCm = width_px / self.prop_px_cm

                    if modDpCm < 60:
                        continue

                    P1, P2, P3, P4 = [Point2D(v[0], v[1]) for v in rectVer]
                    rect = Quad(P1=P1, P2=P2, P3=P3, P4=P4)

                    self.field.updatePos(rect, self.fieldWidth, self.fieldHeight)

                    ptsSource = np.array([P1.getPos(), P2.getPos(), P3.getPos(), P4.getPos()])
                    ptsFinal = np.array([
                        self.fieldP1v, self.fieldP2v,
                        self.fieldP3v, self.fieldP4v
                    ])

                    self.getHomographyMatrix(ptsSrc=ptsSource, ptsFinal=ptsFinal)

                    self.field.setHomographyMatrix(
                        mHomography=self.homography_matrix,
                        invHomo=self.inv_homography_matrix
                    )

                    encontrou_retangulo = True
                    campo_detectado = True
                    resultado_dp_cm = modDpCm

                    # Resetar contador de falhas
                    self.fieldDetectionFailCount = 0
                    break

                # Se achou retângulo, não tenta mais
                if encontrou_retangulo:
                    self.offSetErode = 0
                    break

            except Exception as e:
                print("[VisionSystem]: Erro durante detecção:", e)
                traceback.print_exc()
                continue  # vai para segunda tentativa

        # FIM DAS DUAS TENTATIVAS

        if not campo_detectado:
            self.fieldDetectionFailCount += 1
            if debug:
                print(f"[FIELD_DETECTION] Falha #{self.fieldDetectionFailCount}")
        else:
            self.fieldDetectionFailCount = 0

        self._check_field_reset()

        self.frameResult = (self.fieldReduce.copy()
                            if self.fieldReduce is not None
                            else img.copy())

        # ---------------------------------------------------------
        
        return resultado_dp_cm if campo_detectado else -1

    #Detectar a imagem da bola na imagem
    def detect_ball(self, img, timestamp, dbg=False, isT=False, hsv_img=None):
        '''
            Função responsável por detectar a bola na imagem

            Necessário informar a imagem que irá ser processada para encontrar a bola. A cor da bola e se irá querer exibir ela na imagem, que tem que ser informada em HSV
        '''
        # 1. Usa o HSV Global
        if hsv_img is not None:
            imgHSV = hsv_img
        else:
            imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        

        self.ballImg = self.fieldReduce.copy()
        if self.fieldReduce is None:
            print("FIELDREDUCE É NONE")


        self.binaryBall = cv2.inRange(imgHSV, self.ball_lower_bound, self.ball_upper_bound)

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
            time = timestamp

            rb = self.ballRadiusP   #cm -> valor padrão

            #atualizando posição do objeto bola
            self.ball.setPosition(xcm, ycm, rb, time)
            self.ball.setImgPosition(xb,yb,rb)
            self.ball.status = True 

            rb = int(rb/self.prop_px_cm)
            xb = int(xb)
            yb = int(yb)

            # Circulando bola
            if self.debug:
                cv2.circle(self.frameResult, (xb, yb), (rb + 2), (0, 0, 255), 2)
                cv2.putText(self.frameResult, "B", (xb,yb-rb-10), cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,255), 1)
                
            #parte plotando na imagem virtual
            xv = int(xv)
            yv = int(yv)
            
            #desenhando na imagem virtual
            cv2.circle(self.virtualImg, (xv, yv), 4, (0, 255,255), -1)
            cv2.putText(self.virtualImg, "B", (int(xv-5),int(yv-rb-10)), cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,255,255), 1)
            cv2.arrowedLine(self.virtualImg, (xv, yv), ((xv + int(self.ball.direction[0])), (yv + int(self.ball.direction[1]))), (0, 255, 255), 2)
        else:
            self.ball.status = False

    def detect_players(self, img, timestamp, dbg=False, isT=False, hsv_img=None):
        """
        Detecta robôs na imagem com distinção por dominância de cor
        (comparando proporção de área entre cor de aliado e inimigo).
        Em modo debug, gera máscaras binárias de aliados e de todos os robôs.
        """
        # 1. Usa o HSV Global
        if hsv_img is not None:
            imgHSV = hsv_img
        else:
            imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        debug = dbg
        # Reset de contadores e status
        self.playersCount = self.enemiesCount = self.alliesCount = 0
        enemies_count = 0
        for bot in (*self.enemyTeam, *self.allyTeam):
            bot.setStatus(False)

        self.binaryPlayers = cv2.inRange(imgHSV, self.objectsDarkColor, self.objectsLightColor)
       
        # 2. Remoção cirúrgica da bola na máscara de objetos
        if self.ball.status:
            # Coordenadas inteiras da bola na imagem reduzida
            xb, yb = int(self.ball.xb), int(self.ball.yb)
            
            # Define o raio da janela (ex: r=5 para uma janela 10x10)
            r = 5 
            
            # Obtém as dimensões para evitar erro de índice fora da imagem
            h, w = self.binaryPlayers.shape[:2]
            
            # Calcula os limites com clamp (garante que fiquem dentro da imagem)
            y1, y2 = max(0, yb - r), min(h, yb + r)
            x1, x2 = max(0, xb - r), min(w, xb + r)
            
            # OPERAÇÃO DIRETA: Zera os pixels onde a bola está
            self.binaryPlayers[y1:y2, x1:x2] = 0


        # Filtragem morfológica
        ellipse5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        rect11 = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
        self.binaryPlayers = cv2.erode(self.binaryPlayers, ellipse5, iterations=1)
        self.binaryPlayers = cv2.morphologyEx(self.binaryPlayers, cv2.MORPH_CLOSE, rect11)

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
            hsv = imgHSV[y1:y2, x1:x2]

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

                        #Adicionando o robô à estrutura de arvore
                        self.colorTree.add_robot(
                            ID_Team.TEAM_ENEMY,
                            enemies_count,
                            self.enemyColor, 
                            Color_p,
                            Color_s
                        )

                        # Pegar quais são essas cores 
                        bot = self.enemyTeam[self.enemiesCount]
                        bot.setPosition(xcm, ycm, direction, windowActual, time=timestamp)
                        bot.updtPositionImg(xi, yi, ri)
                        bot.setStatus(True)
                        bot.setRadius(rcm)
                        bot.setColor(colorT=self.allyColor, colorP=Color_p, colorS=Color_s)
                        self.draw_player_virtual(bot)
                        self.enemiesCount += 1
                        enemies_count +=1

                        if debug:
                            self.draw_player_circle(self.frameResult, bot)

                            print(f"  ✅ Inimigo #{self.enemiesCount} confirmado.")
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
                                bot.setPosition(xcm, ycm, direction, windowActual, time=timestamp)
                                bot.updtPositionImg(xi, yi, ri)
                                bot.setStatus(True)
                                bot.setRadius(rcm)
                                bot.setColor(colorT=self.allyColor, colorP=c1, colorS=c2)
                                if self.debug: self.draw_player_circle(self.frameResult, bot)
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
    def get_ROI_img(self, ROI_obj, img_shape, min_size=12, max_ratio=0.5):
        """
        Converte ROI do espaço virtual (cm) para coordenadas da imagem em pixels.
        Garante limites mínimos e máximos.
        """
        x_cm, y_cm, w_cm, h_cm = ROI_obj

        # Canto superior esquerdo e inferior direito
        top_left_real = self.getImageRealIndice((x_cm, y_cm))
        bottom_right_real = self.getImageRealIndice((x_cm + w_cm, y_cm + h_cm))

        tl_x, tl_y = int(top_left_real[0]), int(top_left_real[1])
        br_x, br_y = int(bottom_right_real[0]), int(bottom_right_real[1])

        # Ajuste dentro da imagem
        H, W = img_shape[:2]
        tl_x = max(0, min(tl_x, W-1))
        tl_y = max(0, min(tl_y, H-1))
        br_x = max(0, min(br_x, W))
        br_y = max(0, min(br_y, H))

        # Dimensões
        w_img = max(abs(br_x - tl_x), min_size)
        h_img = max(abs(br_y - tl_y), min_size)

        # Limite máximo relativo à imagem
        max_w = int(W * max_ratio)
        max_h = int(H * max_ratio)
        w_img = min(w_img, max_w)
        h_img = min(h_img, max_h)

        return (tl_x, tl_y, w_img, h_img)

    def predictBall(self, img_shape, timestamp):
            """
            Retorna (imagem_crop, (x, y, w, h)).
            """
            h_img, w_img = img_shape[:2]

            # 1. Obter ROI virtual (cm) do Kalman
            roi_virtual_cm = self._safe_call(
                self.ball.get_roi,
                img_shape,
                t_now=timestamp,
                name="ball.get_roi"
            )

            fallback_rect = (0, 0, int(w_img*0.5), int(h_img*0.5))

            if roi_virtual_cm is None:
                # Se falhar, tenta pegar o centro da imagem
                return None, fallback_rect

            # 2. Converter para Pixels (Tupla x,y,w,h)
            # Atenção: Mudei o nome da variável para roi_rect para não confundir
            roi_rect = self._safe_call(
                self.get_ROI_img,
                roi_virtual_cm,
                img_shape=img_shape,
                name="get_ROI_img (bola)"
            )

            if roi_rect is None:
                return None, fallback_rect

            # 3. Recortar a imagem (Igual ao predictRobot)
            x, y, w, h = roi_rect
            # Verifica se as coordenadas estão dentro do fieldReduce
            # O get_ROI_img já deve garantir, mas o slice do numpy é seguro
            crop_img = self.fieldReduce[y:y+h, x:x+w]

            if crop_img.size == 0:
                return None, roi_rect

            return crop_img, roi_rect

    def predictRobot(self, img_shape, team: ID_Team, robot_id: ID_Robots, timestamp):
            """
            Retorna a imagem do ROI e a tupla (x, y, w, h) global.
            """
            h_img, w_img = img_shape[:2]
            
            # 1. Recupera o objeto Robô
            try:
                Tm = self.allyTeam if team == ID_Team.TEAM_ALLY else self.enemyTeam
                bot = Tm[robot_id]
            except IndexError:
                # Fallback: centro da imagem
                fallback_rect = (0, 0, int(w_img*0.5), int(h_img*0.5))
                return None, fallback_rect

            # 2. Pega ROI Virtual (cm) do Kalman
            roi_virtual_cm = self._safe_call(
                bot.get_roi,
                image_shape=img_shape,
                t_now=timestamp,
                name=f"robot[{robot_id}].get_roi"
            )

            if roi_virtual_cm is None:
                fallback_rect = (0, 0, int(w_img*0.5), int(h_img*0.5))
                return None, fallback_rect

            # 3. Converte para Pixels e ajusta limites
            roi_rect = self._safe_call(
                self.get_ROI_img,
                roi_virtual_cm,
                img_shape=img_shape,
                name=f"get_ROI_img(robot[{robot_id}])"
            )

            if roi_rect is None:
                fallback_rect = (0, 0, int(w_img*0.5), int(h_img*0.5))
                return None, fallback_rect

            # 4. Extrai a imagem (Recorte)
            x, y, w, h = roi_rect
            roi_img = self.fieldReduce[y:y+h, x:x+w] # Assumindo que usa fieldReduce ou image passada

            return roi_img, roi_rect


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
    def search_bots(self, img, timestamp, debug=False) -> list:
            if img is None:
                return []

            shape = img.shape[:2]
            H, W = shape
            
            # Atualiza a imagem HSV GLOBAL para usos de fallback/amostragem de cor
            self.imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            detected_list = []

            # Lista de alvos: (ObjetoRobo, EnumTime)
            targets = []
            for b in self.allyTeam:
                targets.append((b, ID_Team.TEAM_ALLY))
            for b in self.enemyTeam:
                targets.append((b, ID_Team.TEAM_ENEMY))

            for bot, team_enum in targets:
                # 1. PREDIÇÃO: Pega imagem cortada e retângulo
                roi_img, roi_rect = self.predictRobot([H, W], team_enum, bot.id, timestamp)

                # Se não retornou imagem válida (ex: fora do campo), pula
                if roi_img is None or roi_img.size == 0:
                    continue

                # 2. DETECÇÃO: Passa a imagem cortada
                # Nota: 'img' global não é passada, passamos 'roi_img'
                result = self._detect_bot_in_roi(roi_img, roi_rect, bot, debug)

                if result:
                    detected_list.extend(result)
                    
                    # Debug Visual: Desenhar o retângulo onde o robô foi buscado
                    if debug:
                        xr, yr, wr, hr = roi_rect
                        cv2.rectangle(self.frameResult, (xr, yr), (xr+wr, yr+hr), (0, 255, 0), 1)

            return detected_list


    def _detect_bot_in_roi(self, roi_img, roi_rect, target_bot, debug=False) -> list:
            """
            Processa o ROI para achar candidatos e recorta uma janela menor (bot_win)
            para análise de cor e direção, retornando-a nos resultados.
            """
            # 0. Validações básicas
            if roi_img is None or roi_img.size == 0:
                return []

            # Desempacota offsets globais (x0, y0 é o canto sup. esq. do ROI no campo)
            x0, y0, w0, h0 = roi_rect
            results = []

            # --------------------------------------------------------
            # 1. Pré-processamento no ROI (igual ao antigo search_bot, mas no ROI)
            # --------------------------------------------------------
            roi_hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
            obj_mask = cv2.inRange(roi_hsv, self.objectsDarkColor, self.objectsLightColor)

            # Remover Bola e Jogadores (Subtração das máscaras globais recortadas)
            if self.binaryBall is not None:
                ball_roi = self.binaryBall[y0:y0+h0, x0:x0+w0] # Slice global
                if ball_roi.shape == obj_mask.shape:
                    obj_mask = cv2.subtract(obj_mask, ball_roi)

            if self.binaryPlayers is not None:
                p_roi = self.binaryPlayers[y0:y0+h0, x0:x0+w0] # Slice global
                if p_roi.shape == obj_mask.shape:
                    obj_mask = cv2.subtract(obj_mask, p_roi)

            # Morfologia
            mask = cv2.erode(obj_mask, self.struct_ellipse5, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.struct_rect11)

            # Detecção de contornos (Candidatos)
            _, candidates = self.detect_squares(mask)
            if not candidates:
                return []

            # Parâmetros de tamanho (Convertidos de cm para px)
            winSize = int(18 * self.prop_px_cm)
            half_win = winSize // 2
            playerRadius = (7.5 / 2) * np.sqrt(2) * self.prop_px_cm
            mainColorRadius = (7.5 / 4) * np.sqrt(5) * self.prop_px_cm

            # --------------------------------------------------------
            # 2. Loop pelos Candidatos
            # --------------------------------------------------------
            for cnt in candidates:
                # Centro e Raio LOCAL (relativo ao roi_img)
                (xi_local, yi_local), ri = cv2.minEnclosingCircle(cnt)

                # Cálculo das coordenadas GLOBAIS
                xi_global = int(xi_local + x0)
                yi_global = int(yi_local + y0)

                # Filtro de Tamanho (igual ao original)
                if not (0.2 * playerRadius < ri < 2 * playerRadius):
                    # if debug: print("Ignorado por tamanho")
                    continue

                # --------------------------------------------------------
                # 3. Recorte do bot_win (Janela do Robô)
                # --------------------------------------------------------
                # No código antigo, você cortava da imagem 'img' global usando xi_global.
                # Aqui, cortamos de 'roi_img' usando 'xi_local'.
                
                # Limites dentro do roi_img
                x1_local = max(0, int(xi_local - half_win))
                y1_local = max(0, int(yi_local - half_win))
                x2_local = min(w0, int(xi_local + half_win))
                y2_local = min(h0, int(yi_local + half_win))

                # A 'bot_win' é o recorte específico do robô
                bot_win = roi_img[y1_local:y2_local, x1_local:x2_local]
                
                if bot_win.size == 0: continue

                # HSV dessa pequena janela
                hsv_win = cv2.cvtColor(bot_win, cv2.COLOR_BGR2HSV)

                # --------------------------------------------------------
                # 4. Análise de Cores (Time) dentro de bot_win
                # --------------------------------------------------------
                mask_ally = cv2.inRange(hsv_win, self.ally_lower_bound, self.ally_upper_bound)
                mask_enemy = cv2.inRange(hsv_win, self.enemy_lower_bound, self.enemy_upper_bound)

                ally_area = cv2.countNonZero(mask_ally)
                enemy_area = cv2.countNonZero(mask_enemy)
                total_area = max(ally_area + enemy_area, 1)

                detected_team = None
                curr_mask = None
                curr_main_color = None

                if (ally_area / total_area) > 0.55:
                    detected_team = ID_Team.TEAM_ALLY
                    curr_mask = mask_ally
                    curr_main_color = self.allyColor
                elif (enemy_area / total_area) > 0.55:
                    detected_team = ID_Team.TEAM_ENEMY
                    curr_mask = mask_enemy
                    curr_main_color = self.enemyColor
                else:
                    continue # Time indefinido

                # --------------------------------------------------------
                # 5. Determinar Direção (Centro da Cor)
                # --------------------------------------------------------
                sub_cnts, _ = cv2.findContours(curr_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                contour_color = max(sub_cnts, key=cv2.contourArea, default=None)
                if contour_color is None:
                    continue

                (xm_win, ym_win), rc = cv2.minEnclosingCircle(contour_color)

                # Coordenadas GLOBAIS da mancha de cor
                # xm_win é relativo a bot_win -> somar x1_local -> relativo a roi_img -> somar x0 -> Global
                xm_global = xm_win + x1_local + x0
                ym_global = ym_win + y1_local + y0

                if rc < 0.6 * mainColorRadius:
                    continue

                # Cálculo da Direção: (Centro Robô - Centro Cor)
                # Igual ao seu código original: direction = np.array([xi_global, -yi_global]) - np.array([x_m, -y_m])
                dx = xi_global - xm_global
                dy = -(yi_global - ym_global) # Inverte Y conforme seu padrão

                direction = np.array([dx, dy], dtype=float)
                norm = np.linalg.norm(direction)
                if norm > 1e-6:
                    direction /= norm
                else:
                    direction = np.array([1.0, 0.0])

                theta = float(np.arctan2(direction[1], direction[0]))

                # --------------------------------------------------------
                # 6. Identificação do ID
                # --------------------------------------------------------
                # Extrair cores nos pontos geométricos globais
                C_p, C_s, _ = self.get_centers_colors(xi_global, yi_global, xm_global, ym_global)
                
                # Usa imgHSV global (self.imgHSV deve estar atualizado no filtered_detection)
                primary = self.get_hsv_mean(self.imgHSV, C_p[0], C_p[1])
                secondary = self.get_hsv_mean(self.imgHSV, C_s[0], C_s[1])

                identified_id = None

                # a) Verifica match com o alvo
                if detected_team == target_bot.team:
                    if self.matches_robot(target_bot, primary, secondary):
                        identified_id = target_bot.id

                # b) Verifica match com outros (Arvore de cores)
                if identified_id is None:
                    match = self.colorTree.find_by_colors(curr_main_color, primary, secondary)
                    if match:
                        cand_id = match["robot_id"]
                        # Valida se existe no time
                        team_list = self.allyTeam if detected_team == ID_Team.TEAM_ALLY else self.enemyTeam
                        if any(b.id == cand_id for b in team_list):
                            identified_id = cand_id

                # --------------------------------------------------------
                # 7. Compilação dos Resultados
                # --------------------------------------------------------
                if identified_id is not None:
                    # Conversão px -> cm
                    xv, yv = self.transformPoint(np.array([xi_global, yi_global]))
                    xcm, ycm = self.getPointVirtual(np.array([xv, yv]))

                    result_data = {
                        "id": identified_id,
                        "team": detected_team,
                        "x": xcm,
                        "y": ycm,
                        "theta": theta,
                        "direction": direction,
                        "img_x": xi_global,
                        "img_y": yi_global,
                        "img_r": ri,
                        "xi_image": int(xm_global), # Centro da cor (debug)
                        "yi_image": int(ym_global),
                        "bot_win": bot_win, # <--- AQUI ESTÁ A WINDOW RETORNADA
                        "contour_global": None 
                    }

                    # Prepara contorno global para desenhar na máscara global depois
                    c_global = cnt.copy()
                    c_global[:, 0, 0] += x0
                    c_global[:, 0, 1] += y0
                    result_data["contour_global"] = c_global

                    # Atualiza máscara global (opcional, igual ao original)
                    if self.binaryPlayers is not None:
                        cv2.drawContours(self.binaryPlayers, [c_global], -1, 255, -1)
                    
                    results.append(result_data)

            return results

    #=================================================================================

    def get_bot_by_id(self, team:ID_Team, bot_id:ID_Robots) -> Robot:
        '''
            retorna o robô por meio do identificador e do time.
        '''
        if team == ID_Team.TEAM_ALLY:
            return self.allyTeam[bot_id]
        else:
            return self.enemyTeam[bot_id]
            
    def search_bot(self, img, roi, team: ID_Team, bot_id: ID_Robots, timestamp, debug=False):
        """
        Procura um robô específico na ROI, mas atualiza também outros robôs do mesmo time
        se forem detectados.
        """
        bot = self.get_bot_by_id(team, bot_id)
        if bot is None:
            if debug:
                print(f"[search_bot] Bot {team, bot_id} não existe na lista")
            return False

        x0, y0, w0, h0 = roi
        # --------------------------------------------------------
        # Valida ROI
        # --------------------------------------------------------
        if w0 <= 0 or h0 <= 0 or x0 < 0 or y0 < 0 or x0+w0 > img.shape[1] or y0+h0 > img.shape[0]:
            if debug:
                print(f"[search_bot] ROI inválida: {roi}")
            return False

        # --------------------------------------------------------
        # Preparar janela e máscara de objetos
        # --------------------------------------------------------
        # Recorte direto da ROI
        window = img[y0:y0+h0, x0:x0+w0]
        windowHSV = cv2.cvtColor(window, cv2.COLOR_BGR2HSV)
        obj_window = cv2.inRange(windowHSV, self.objectsDarkColor, self.objectsLightColor)

        if self.binaryBall is not None:
            obj_window = cv2.subtract(obj_window, self.binaryBall[y0:y0+h0, x0:x0+w0])
        if self.binaryPlayers is not None:
            obj_window = cv2.subtract(obj_window, self.binaryPlayers[y0:y0+h0, x0:x0+w0])

        # --------------------------------------------------------
        # Morfologia e detecção de candidatos
        # --------------------------------------------------------
        ellipse5 = self.struct_ellipse5
        rect11   = self.struct_rect11
        binaryPlayer = cv2.erode(obj_window, ellipse5, iterations=1)
        binaryPlayer = cv2.morphologyEx(binaryPlayer, cv2.MORPH_CLOSE, rect11)
        _, candidates = self.detect_squares(binaryPlayer)

        if not candidates:
            if debug:
                print(f"[search_bot] Nenhum candidato detectado na ROI")
            return False

        winSize = int(18 * self.prop_px_cm)
        half_win = winSize // 2
        playerRadius = (7.5 / 2) * np.sqrt(2) * self.prop_px_cm
        mainColorRadius = (7.5 / 4) * np.sqrt(5) * self.prop_px_cm
        found = False

        # --------------------------------------------------------
        # Processamento dos candidatos
        # --------------------------------------------------------
        for contour in candidates:
            (xi, yi), ri = cv2.minEnclosingCircle(contour)
            xi_global = xi + x0
            yi_global = yi + y0

            if not (0.2 * playerRadius < ri < 2 * playerRadius and self.playersCount < 6):
                if debug:
                    print("  ⚠️ Ignorado (fora do range esperado ou excedeu limite).")
                continue

            x1 = max(0, int(xi_global - half_win))
            y1 = max(0, int(yi_global - half_win))
            x2 = min(self.fieldReduce.shape[1], int(xi_global + half_win))
            y2 = min(self.fieldReduce.shape[0], int(yi_global + half_win))

            # Janela menor ainda para processamento do robô
            bot_win = img[y1:y2, x1:x2]
            hsv_win = cv2.cvtColor(bot_win, cv2.COLOR_BGR2HSV)

            # Máscaras de cor
            mask_ally = cv2.inRange(hsv_win, self.ally_lower_bound, self.ally_upper_bound)
            mask_enemy = cv2.inRange(hsv_win, self.enemy_lower_bound, self.enemy_upper_bound)

            ally_area = cv2.countNonZero(mask_ally)
            enemy_area = cv2.countNonZero(mask_enemy)
            total_area = max(ally_area + enemy_area, 1)

            #Proporção das áreas
            ally_ratio = ally_area / total_area
            enemy_ratio = enemy_area / total_area

            if ally_ratio > 0.55:
                team_type = "ally"
                mainColor = self.allyColor
                teamBots = self.allyTeam
            elif enemy_ratio > 0.55:
                team_type = "enemy"
                mainColor = self.enemyColor
                teamBots = self.enemyTeam
            else:
                continue 

            #Coordenadas absolutas:
            xcm, ycm = self.getPointVirtual(self.transformPoint(np.array([xi, yi])))

            # ----------------------------------------------------
            # Determinar coordenadas globais do centro da cor principal
            # ----------------------------------------------------
            contour_color = max(cv2.findContours(mask_enemy if team_type=="enemy" else mask_ally,
                                                cv2.RETR_EXTERNAL,
                                                cv2.CHAIN_APPROX_SIMPLE)[0],
                                key=cv2.contourArea, default=None)
            if contour_color is None:
                continue

            (x_m, y_m), rc = cv2.minEnclosingCircle(contour_color)
            # Corrigindo para coordenadas gerais
            # o indice está numa janela dentro de outra janela
            # então a coordenada real é somando o extremo roi do roi
            x_m += x1
            y_m += y1

            if rc < 0.6 * mainColorRadius: #raio da cor maior tem que ser considerável
                continue

            direction = np.array([xi_global, -yi_global]) - np.array([x_m, -y_m])
            norm = np.linalg.norm(direction)
            if norm > 1e-6:
                direction /= norm

            # ----------------------------------------------------
            # Extrair cores e tentar identificar robô
            # ----------------------------------------------------
            C_p, C_s, _ = self.get_centers_colors(xi_global, yi_global, x_m, y_m)
            primary = self.get_hsv_mean(self.imgHSV, C_p[0], C_p[1])
            secondary = self.get_hsv_mean(self.imgHSV, C_s[0], C_s[1])

            # Tenta o robô específico
            if self.matches_robot(bot, primary, secondary):
                # O robô corresponde, então só atualiza a posição.
                bot.updatePosition(x=xcm, y=ycm, direction=direction, image=bot_win, time=timestamp)
                bot.updtPositionImg(xi_global, yi_global, ri)
                bot.setStatus(True)
                self.draw_player_circle(self.frameResult, bot)
                self.draw_player_virtual(bot)
                found = True
                if debug:
                    print(f"✅ Detectado Robô {team.name} {bot_id.name} (específico) na ROI {roi}")

            else:
                # Verifico se ele corresponde a algum robô do mesmo time
                match = self.colorTree.find_by_colors(mainColor, primary, secondary)
                if match is None:
                    continue 

                bot_id = match['robot_id']
                other_bot = teamBots[bot_id]
                other_bot.updatePosition(x=xcm, y=ycm, direction=direction, image=bot_win, time=timestamp)
                other_bot.updtPositionImg(xi_global, yi_global, ri)
                other_bot.setStatus(True)
                self.draw_player_circle(self.frameResult, other_bot)
                self.draw_player_virtual(other_bot)
                if debug:
                    print(f"✅ Detectado Robô {team.name} {bot_id.name} (específico) na ROI {roi}")


            # Atualiza binário global
            cont_global = contour.copy()
            cont_global[:, 0, 0] += x0
            cont_global[:, 0, 1] += y0
            if self.binaryPlayers is not None:
                cv2.drawContours(self.binaryPlayers, [cont_global], -1, 255, -1)
            if team_type == "ally" and self.binaryAllTeam is not None:
                cv2.drawContours(self.binaryAllTeam, [cont_global], -1, 255, -1)

        return found
    
    def matches_robot(self, bot: Robot, primary, secondary) -> bool:
        """
        Verifica se a combinação de cores detectada corresponde ao robô esperado.
        """
        team = bot.team
        robot_id = bot.id
        main_color = bot.colorTeam

        match = self.colorTree.find_by_colors(main_color, primary, secondary)
        if match is None:
            return False

        return match['robot_id'] == robot_id and match['team'] == team


    #=================================================================================
    def search_ball(self, roi_img, roi_rect, timestamp, debug=False, name=""):
            """
            Busca a bola dentro do recorte (roi_img).
            Retorna coordenadas globais somando o offset (roi_rect).
            """
            # Se a imagem do recorte for inválida
            if roi_img is None or roi_img.size == 0:
                return {'found': False}

            # Desempacota o offset global
            x0, y0, w0, h0 = roi_rect
            
            # 1. Processamento na imagem recortada (rápido)
            # Não precisa recriar wnd, roi_img JÁ É a janela
            hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, self.ball_lower_bound, self.ball_upper_bound)

            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.struct_ellipse5)
            mask = cv2.erode(mask, self.struct_ellipse5, iterations=1)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                return {'found': False}

            # 2. Encontrar o centro local
            c = max(contours, key=cv2.contourArea)
            (xb_local, yb_local), r_ball_px = cv2.minEnclosingCircle(c)

            # 3. Converter para Global (Fundamental!)
            xb = int(xb_local + x0)
            yb = int(yb_local + y0)

            # Debug Visual Global
            if self.binaryBall is not None:
                cv2.circle(self.binaryBall, (xb, yb), int(r_ball_px * 1.3), 255, -1)
            
            if debug:
                # Aqui desenhamos na imagem global (frameResult) usando as coords globais
                cv2.circle(self.frameResult, (xb, yb), int(r_ball_px) + 2, (0, 0, 255), 2)
                # Opcional: desenhar o retângulo de busca
                cv2.rectangle(self.frameResult, (x0, y0), (x0+w0, y0+h0), (0, 255, 255), 1)

            # 4. Transformação para Mundo Virtual
            xv, yv = self.transformPoint(np.array([xb, yb]))
            xcm, ycm = self.getPointVirtual(np.array([xv, yv]))

            return {
                'found': True, 
                'x': xcm, 
                'y': ycm,
                'img_x': xb, 
                'img_y': yb, 
                'img_r': r_ball_px,
                'radius': self.ballRadiusP # Ou usar r_ball_px convertido
            }

    def _predict_bot_fallback(self, bot, timestamp, mark_detected=False):
        """
        Atualiza o objeto bot usando a predição do Kalman sem alterar o filtro.
        - bot: instância de Robot
        - timestamp: tempo atual (mesmo que passou para predict_with_cov)
        - mark_detected: se True marca bot.detected = True (útil se quiser desenhar)
        """
        try:
            st_pred, P_pred = bot.predict_with_cov(timestamp)  # (6x1), (6x6)
            x_pred = float(st_pred[0, 0])
            y_pred = float(st_pred[1, 0])
            theta_pred = float(st_pred[2, 0])

            # Use a API do Robot para atualizar sem tocar no Kalman
            # signature: setPositionNoKalman(x, y, theta, timestamp, image=None)
            bot.setPositionNoKalman(x_pred, y_pred, theta_pred, timestamp, image=None)

            # status: por padrão fallback não é "detectado" (mas escolha sua política)
            bot.detected = bool(mark_detected)

            # update bbox/view já feito por setPositionNoKalman
            # opcional: atualizar imagem virtual (ponto) para debug
            if hasattr(self, "virtualImg"):
                xi, yi = self.getImageIndice((x_pred, y_pred))
                bot.updtPositionImg(int(xi), int(yi), int(bot.radius * 3))  # ri visual aproximado

            return True
        except Exception as e:
            print(f"[VS][_predict_bot_fallback] erro ao aplicar fallback para bot {getattr(bot,'id', '?')}: {e}")
            return False


    def _predict_ball_fallback(self, timestamp, mark_detected=False):
        """
        Predição fallback para a bola usando o Kalman da bola.
        Usa ball.predict/predict_with_cov e atualiza com setPositionNoKalman da Ball.
        """
        try:
            # ball tem predict_with_cov? seu Ball tem predict(timestamp) (retorna x,y,theta)
            # se tiver predict_with_cov, prefira-o para obter P_pred; aqui usamos predict_with_cov se existir
            if hasattr(self.ball, "predict_with_cov"):
                st_pred, P_pred = self.ball.predict_with_cov(timestamp)
                x_pred = float(st_pred[0, 0])
                y_pred = float(st_pred[1, 0])
                theta_pred = float(st_pred[2, 0])
            else:
                x_pred, y_pred, theta_pred = self.ball.predict(timestamp)

            # converter predição virtual para CM já está no estado do filtro (x,y são cm)
            # usar API da bola que você definiu: setPositionNoKalman(x, y, r, timestamp=0.0, theta=None)
            rb = getattr(self, "ballRadiusP", self.ball.radius)
            self.ball.setPositionNoKalman(x_pred, y_pred, rb, timestamp, theta=theta_pred)

            self.ball.detected = bool(mark_detected)

            # debug: atualizar pos em imagem real
            if hasattr(self, "virtualImg"):
                xi, yi = self.getImageIndice((x_pred, y_pred))
                try:
                    self.ball.setImgPosition(int(xi), int(yi), int(rb / self.prop_px_cm))
                except Exception:
                    pass

            return True
        except Exception as e:
            print(f"[VS][_predict_ball_fallback] erro: {e}")
            return False
        
    def _handle_robot_loss(self, bot, team, timestamp):
            """Gerencia falha de detecção: Predição Suave ou Reset."""
            key = (bot.id, team)
            curr_missed = self.missed_frames_robots.get(key, 0) + 1
            self.missed_frames_robots[key] = curr_missed

            if curr_missed <= self.MAX_MISSED_FRAMES_ROBOT:
                # Fallback: Predição do EKF (mantém movimento suave)
                # bot.predict(t) retorna (x, y, theta) preditos pelo modelo
                pred_x, pred_y, pred_theta = bot.predict(timestamp)
                
                # Atualiza visualmente sem tocar no estado do filtro
                bot.setPositionNoKalman(pred_x, pred_y, pred_theta, timestamp)
                bot.setStatus(True) # Mantém visualmente ativo
            else:
                # Perda Real: Desliga e marca para reset
                bot.setStatus(False)
                self.robot_kalman_reset_flags[key] = True


    def filtered_detection(self, img, currentTime, debug=False):
            """
            Pipeline otimizado:
            1. Validações e Recorte do Campo.
            2. Predição e Atualização da Bola.
            3. Predição e Atualização dos Robôs (Delegando lógica interna para a classe Robot).
            """

            # ==========================================================
            # 0) Validações e Sanity Checks
            # ==========================================================
            if img is None or not self.fieldDetectedFlag:
                return self.proc(img, currentTime, debug)
            
            if not hasattr(self.viewCapture, "cooVetor") or self.viewCapture.cooVetor is None:
                return self.proc(img, currentTime, debug)

            # Extrai coordenadas e valida tamanho mínimo (Sanity Check)
            try:
                x_w, y_w, w_w, h_w = map(int, self.viewCapture.cooVetor)
            except ValueError:
                return self.proc(img, currentTime, debug)

            if self.prop_px_cm > 0:
                w_r = w_w / self.prop_px_cm
                h_r = h_w / self.prop_px_cm
                if w_r < 100 or h_r < 100: 
                    if debug: print(f"[filtered_detection] Campo muito pequeno. Resetando.")
                    return self.proc(img, currentTime, debug)

            # ==========================================================
            # 1) Extração do FieldReduce
            # ==========================================================
            H0, W0 = img.shape[:2]
            x_w = max(0, min(x_w, W0 - 1))
            y_w = max(0, min(y_w, H0 - 1))
            w_w = max(1, min(w_w, W0 - x_w))
            h_w = max(1, min(h_w, H0 - y_w))

            self.fieldReduce = img[y_w:y_w + h_w, x_w:x_w + w_w].copy()
            H, W = self.fieldReduce.shape[:2]

            self.frameResult = self.fieldReduce.copy()
            
            if hasattr(self, "virtual") and self.virtual is not None:
                self.virtualImg = self.virtual.copy()

            self.imgHSV = cv2.cvtColor(self.fieldReduce, cv2.COLOR_BGR2HSV)

            # ==========================================================
            # 2) DETECÇÃO DA BOLA
            # ==========================================================
            roi_ball_img, roi_ball_rect = self.predictBall((H, W), currentTime)
            
            ball_found = False
            self.bmk.tic()
            if roi_ball_img is not None:
                ball_data = self._safe_call(
                    self.search_ball, roi_img=roi_ball_img, roi_rect=roi_ball_rect,
                    timestamp=currentTime, debug=debug, name="search_ball"
                ) or {}
                ball_found = ball_data.get("found", False)
            self.bmk.toc("Bola")
            
            if ball_found:
                xb, yb = int(ball_data["img_x"]), int(ball_data["img_y"])
                r_px = int(ball_data.get("img_r", 4))
                xcm, ycm = float(ball_data["x"]), float(ball_data["y"])

                # Bola geralmente não tem updatePosition complexo igual Robô,
                # mas mantemos a consistência se houver update:
                try:
                    self.ball.update(xcm, ycm, currentTime)
                except:
                    self.ball.setPosition(xcm, ycm, self.ballRadiusP, currentTime)

                self.ball.setImgPosition(xb, yb, r_px)
                self.ball.detected = True
                self.missed_frames_ball = 0

                if self.binaryBall is not None:
                    cv2.circle(self.binaryBall, (xb, yb), int(r_px * 1.3), 255, -1)
                if debug:
                    cv2.circle(self.frameResult, (xb, yb), r_px+1, (0,0,255), 2)
            else:
                self.missed_frames_ball = getattr(self, "missed_frames_ball", 0) + 1
                if self.missed_frames_ball > self.MAX_MISSED_FRAMES_BALL:
                    self.ball.detected = False
                    self.ball_kalman_reset_flag = True

            # ==========================================================
            # 3) DETECÇÃO DOS ROBÔS
            # ==========================================================
            self.bmk.tic()
            robots_found = self._safe_call(
                self.search_bots,
                img=self.fieldReduce, # search_bots recorta internamente via predictRobot
                timestamp=currentTime,
                debug=debug
            ) or []
            self.bmk.toc("Players")

            updated_keys = set()

            for r in robots_found:
                try:
                    rid = r["id"]
                    team = r["team"]
                    key = (rid, team)
                    
                    if key in updated_keys: continue
                    updated_keys.add(key)

                    bot = self.get_bot_by_id(team, rid)
                    if bot is None: continue

                    # Extração dos dados
                    mx, my = float(r["x"]), float(r["y"])
                    direction = r["direction"] # Vetor np.array([dx, -dy])
                    theta = float(r["theta"])  # Apenas para debug visual, pois updatePosition recalcula
                    
                    # Dados visuais
                    x_img, y_img = int(r["img_x"]), int(r["img_y"])
                    r_img = int(r.get("img_r", 8))
                    
                    # A IMAGEM DO ROBÔ (WINDOW)
                    # search_bots deve retornar isso na chave "bot_win"
                    bot_window = r.get("bot_win", None) 

                    # --- Lógica de Reset (Watchdog) ---
                    missed = int(self.missed_frames_robots.get(key, 0))
                    
                    # Se perdeu por muito tempo, resetamos o robô.
                    # Isso fará o próximo updatePosition reinicializar o Kalman.
                    if missed > self.MAX_MISSED_FRAMES_ROBOT or self.robot_kalman_reset_flags.get(key, False):
                        bot.reset() 
                        self.robot_kalman_reset_flags[key] = False

                    # --- ATUALIZAÇÃO CENTRALIZADA NO ROBÔ ---
                    # O robô cuida do Kalman, direção, bbox e guarda a imagem
                    bot.updatePosition(mx, my, direction, bot_window, currentTime)
                    
                    # Atualização extra de propriedades visuais (Bounding Box global)
                    bot.updtPositionImg(x_img, y_img, r_img)
                    bot.detected = True
                    
                    self.missed_frames_robots[key] = 0

                    # Desenho de Debug
                    if debug:
                        color = (255, 0, 0) if team == ID_Team.TEAM_ALLY else (0, 0, 255)
                        end_pt = (int(x_img + 15*np.cos(theta)), int(y_img - 15*np.sin(theta)))
                        cv2.arrowedLine(self.frameResult, (x_img, y_img), end_pt, color, 1)
                        cv2.putText(self.frameResult, str(rid), (x_img-5, y_img-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

                except Exception as e:
                    if debug:
                        print(f"[filtered_detection][ERROR robot {key}]: {e}")
                        traceback.print_exc()

            # ==========================================================
            # 4) Watchdog (Robôs perdidos)
            # ==========================================================
            for bot, team in [(b, ID_Team.TEAM_ALLY) for b in self.allyTeam] + \
                            [(b, ID_Team.TEAM_ENEMY) for b in self.enemyTeam]:
                key = (bot.id, team)
                if key not in updated_keys:
                    self._safe_call(self._handle_robot_loss, bot, team, currentTime)

            return self.frameResult
    
    # Adicione este método dentro da classe VisionSystem
    def _get_shape(self, img):
        """Retorna (altura, largura) independente se é CPU (numpy) ou GPU (UMat)."""
        if isinstance(img, cv2.UMat):
            return img.get().shape[:2]
        return img.shape[:2]
    #=================================================================================
# Testar função principal e nova lógica
if __name__ =='__main__':
    print("Utilizada em função de main")