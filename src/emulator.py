from detectorV2 import VisionSystem
from modules import *
from settingsMenu import *
from viewer import MyViewer, WindowsViewer
from cards import *
from objects import *
from control import Control
from communication import *

import threading
import queue
import time
from collections import deque
import ast

class Emulator:
    def __init__(self,App):
        print("Emulador foi construído")

        self.settingsTree = App.menu
        self.viewer = App.viewer
        self.debugFieldViewer = App.debugField
        self.debugObjectsViewer = App.debugObject
        self.debugPlayersViewer = App.debugPlayers
        self.debugTeamViewer = App.debugTeam
        self.resultViewer = App.result

        #informações para exibir
        self.cards = App.cards
        self.infoCards = App.infosEmulator
        
        #campos iterativos
        self.IdCap = App.IdFrame
        self.btn_run = App.btn_run
        self.btn_stop = App.btn_stop
        
        #Variáveis de controle
        self.Mode = MODE_DEFAULT
        self.cameraIsRunning = False

        self.DEBUGA = False
        self.thread = None
        self.capture = Capture(CaptureMode.DEFAULT,False)
        self.delay = 14 #14 ms

        self.clientMQTT = None
        self.clientSerial = None
        self.commands = None

        #filas
        self.commands_queue = queue.Queue()
        self.sent_data_queue = queue.Queue()
        self.received_data_queue = queue.Queue()
                
        #deque de no máximo 10 imagens
        self.maxDeque = 4
        self.capture_deque = deque(maxlen=self.maxDeque)

        self.viewer.config()
        self.debugFieldViewer.config()
        self.debugObjectsViewer.config()
        self.debugPlayersViewer.config()
        self.debugTeamViewer.config()
        self.resultViewer.config()

        # Objetos
        self.field = None
        self.ball = None
        self.allies = [None, None, None]
        self.enemies = [None, None, None]

        #Setando conteúdo
        self.setContentRobots()

        #objeto de controle
        self.control = Control(self)

        #Criando temporizador de alta precisão
        self.Timer = HighPrecisionTimer(self)
        
        #informações que serão uteis para computar
        self.frameTime = None           # tempo de um frame em ms
        self.sendTime = None            # tempo de envio de dados em ms
        self.FPStime = None             # FPS do processo em quadros / segundo
        self.realTime = None            # tempo contado pelo timer
        self.errorCode = 0              # código de erro do emulador
        self.totalTime = None           # tempo total para processar um quadro
        
        #imformações uteis do processamento do emulador
        self.OP = App.system            # Sistema operacional
        self.OPrelease = App.release    # release
        self.OPversion = App.version    # versão

        self.hasCuda = False             # verifica a versão do cuda
        self.CudaDevice = None           # Qual o serviço cuda
        self.CudaDeviceVersion = None    # Quantos serviços cuda há
        self.communication = False       # verifica se está ok a comunicação
        self.CUDAselected = False        # variável para indicar que foi selecionado o cuda

        #variáveis da câmera
        self.FocusValue = 0                         # Variável com o valor do foco da câmera
        self.FocusMode: FocusMode =FocusMode.AUTO


        #Variável relativa ao tipo de conexão escolhida pelo usuário
        self.comSelected = None         # Será uma string {nenhuma, MQTT ou Serial}
        self.hasConection = False       # verifica se foi selecionada alguma conexão
        self.serialPort = None          # Porta serial escolhida, caso esteja em modo serial
        self.hasMqtt    = False         # caso MQTT seja escolhido, essa variável será true
        self.hasSerial  = False         # caso Serial seja escolhido, essa  variável será true
        
        #variável de travar threads numa variável compartilhada
        self.captureThread = None


        #imagem padrão do emulador vindo da caputar
        self.frame = None   
        
        #criando um objeto que será responsável por guardar as informações do emulador
        self.EConfig = EConfig()

        #verificando se funciona
        self.vs = VisionSystem(capture=self.capture, UseCuda=False, GPUType=None)

    def load_vars(self):
        self.CamUSB = int(self.settingsTree.tree.item('I003','value')[0])
        self.ImgPath = self.settingsTree.tree.item('I004','value')[0]
        self.VideoPath = self.settingsTree.tree.item('I005','value')[0]
        self.UseMode = self.settingsTree.tree.item('I006','value')[0]

        self.OffSetBord = int(self.settingsTree.tree.item('I008','value')[0])
        self.OffSetErode = int(self.settingsTree.tree.item('I009','value')[0])
        self.BINThresh = int(self.settingsTree.tree.item('I00A','value')[0])
        self.MatrixTop = int(self.settingsTree.tree.item('I00B','value')[0])
        self.FocusMode = self.settingsTree.tree.item('I00C','value')[0]
        focus_value_str = self.settingsTree.tree.item('I00D','value')[0]
        if focus_value_str:
            self.FocusValue = float(focus_value_str)
        else:
            self.FocusValue = 0

        #dimensão do campo
        self.fieldWidth = int(self.settingsTree.tree.item('I00F','value')[0])
        self.fieldHeight = int(self.settingsTree.tree.item('I010','value')[0])

        #cores
        self.mainColor = self.settingsTree.tree.item('I012','value')[0]
        self.player1Color1 = self.settingsTree.tree.item('I013','value')[0]
        self.player1Color2 = self.settingsTree.tree.item('I014','value')[0]
        self.player2Color1 = self.settingsTree.tree.item('I015','value')[0]
        self.player2Color2 = self.settingsTree.tree.item('I016','value')[0]
        self.player3Color1 = self.settingsTree.tree.item('I017','value')[0]
        self.player3Color2 = self.settingsTree.tree.item('I018','value')[0]
        self.enemiesMainColor = self.settingsTree.tree.item('I019','value')[0]
        self.ballColor = self.settingsTree.tree.item('I01A','value')[0]

        #variáveis que influenciam no desenvolvimento 
        self.debug_view = self.settingsTree.tree.item('I01C','value')[0]
        self.comMode = self.settingsTree.tree.item('I01D','value')[0]
        self.serialPort = self.settingsTree.tree.item('I01E','value')[0]
        self.CUDAservice = self.settingsTree.tree.item('I01F','value')[0]
        self.EXECMode = self.settingsTree.tree.item('I020','value')[0]

        #modo de uso do emulador
        self.UseMode = self.format_var(self.UseMode)

        #cores
        self.mainColor = self.format_var(self.mainColor)
        self.player1Color1 = self.format_var(self.player1Color1)
        self.player1Color2 = self.format_var(self.player1Color2)
        self.player2Color1 = self.format_var(self.player2Color1)
        self.player2Color2 = self.format_var(self.player2Color2)
        self.player3Color1 = self.format_var(self.player3Color1)
        self.player3Color2 = self.format_var(self.player3Color2)
        self.enemiesMainColor = self.format_var(self.enemiesMainColor)
        self.ballColor = self.format_var(self.ballColor)

        #variáveis que influenciam no modo de emulação
        self.EXECMode = self.format_var(self.EXECMode)
        self.debug_view = self.format_var(self.debug_view)
        self.comMode = self.format_var(self.comMode)
        self.CUDAService = self.format_var(self.CUDAservice)
        
        #variável de controle de foco da câmera
        self.FocusMode = self.format_var(self.FocusMode)

        #verifica se foi solicitado DEBUG do código
        if(self.debug_view == 'true'):
            self.DEBUGA = True
            self.debug_view = True
        elif(self.debug_view == 'false'):
            self.DEBUGA = False
            self.debug_view = False
        else:
            self.DEBUGA = False
            self.debug_view = False
        
        #verifica se qual modo de execução foi solicitado
        if(self.UseMode== 'camera'):
            self.Mode = MODE_USB_CAM
        elif(self.UseMode == 'imagem'):
            self.Mode = MODE_IMAGE 
        elif(self.UseMode == 'video'):
            self.Mode = MODE_VIDEO_CAM       
        else:
            print('[EMULADOR] Valor inválido')
            self.Mode = MODE_DEFAULT
            self.stop() #Para o emulador.


        #Verifica se foi solicitado suporte ao cuda
        if(self.CUDAService == 'true'):
            #verifica se tem suporte ao CUDA
            self.CUDAselected = self.hasCudaDevice()
        else:
            self.CUDAselected = False        # Cuda não foi selecionado
            self.hasCudaDevice()             # Atualizo informações do cuda
        
        #Trata qual foi o tipo de conexão escolhida pelo usuário


        if(self.comMode == 'mqtt'):
            #seleciona o modo mqtt
            self.hasConection = True
            self.hasMqtt = True
            self.hasSerial = False
        elif(self.comMode == 'serial'):
            #seleciona o modo serial
            self.hasConection = True
            self.hasSerial = True
            self.hasMqtt = False
        elif(self.comMode == 'nenhuma'):
            #nenhuma foi selecionada, então vira falso]
            self.hasConection = False
            self.hasSerial = False
            self.hasMqtt = False
        else:
            #provavelmente foi um erro e nenhuma será selecionada
            print("Não tem comunicação selecionada")
            self.hasConection = False
            self.hasSerial = False
            self.hasMqtt = False

        #tratar os valores de captura para aplicar as variações que eu quero
        if self.FocusMode == 'automatico':
            self._focusMode = FocusMode.AUTO
        elif self.FocusMode == 'manual':
            self._focusMode = FocusMode.MANUAL
        else: 
            self._focusMode = FocusMode.AUTO


        #Atualizo o card
        self.infoCards.updateFuncs()

   
    def format_var(self, var):
        var = unidecode.unidecode(var)
        var = var.lower()
        return var

    def show_variables(self):
        msg=f"""
        [EMULADOR]
        ====Emulador===
        CamUSB          : {self.CamUSB}
        ImgPath         : {self.ImgPath}
        VideoPath       : {self.VideoPath}
        UseMode         : {self.UseMode}
        
        OffSetBord      : {self.OffSetBord}
        OffSetErode     : {self.OffSetErode}
        BINThresh       : {self.BINThresh}
        MatrixTop       : {self.MatrixTop}
        
        fieldWidth      : {self.fieldWidth}
        fieldHeight     : {self.fieldHeight}

        ally Color      : {self.mainColor}
        Goleiro CorP    : {self.player1Color1}
        Goleiro CorS    : {self.player1Color2}
        Atk1    CorP    : {self.player2Color1}
        Atk1    CorS    : {self.player2Color2}
        Atk2    CorP    : {self.player3Color1}
        Atk2    CorS    : {self.player3Color2}
        Enemies Color   : {self.enemiesMainColor}
        ballColor       : {self.ballColor}
        
        debug_view      : {self.debug_view}
        EXECMode        : {self.EXECMode}
        """.encode('utf-8')

        print(msg.decode('utf-8', errors='replace'))

    def send_data(self, queue):
        while True:
            #Inicia contagem de tempo
            St1 = self.Timer.getElapsedTime()
            item = queue.get()

            if(self.hasMqtt):
                result = publish_mqtt_data(self.clientMQTT, "vsss-ifal-pin/robots", item)            
            elif(self.hasSerial):
                send_serial_data(self.clientSerial, item)

            queue.task_done()
            time.sleep(0.015)
            
            #Tempo de envio da mensagem em ms
            St2 = self.Timer.getElapsedTime()
            self.sendTime = (St2-St1)
            self.infoCards.update()

    #Método para o emulador exibir as imagens
    def init(self):
        print("[EMULADOR] Configurando variaveis")

        #inicializando timer de alta precisão
        self.Timer.run()

        #Inicio das configurações necessárias
        self.viewer.config()
        self.debugFieldViewer.config()

        self.infoCards.updateFuncs()

        def string_to_int_array(array):
            values = array.strip("[]").split()
            int_array = list(map(int, values))

            return int_array

        self.fieldDimensions = np.array([self.fieldWidth, self.fieldHeight])
        self.teamMainColor = string_to_int_array(self.mainColor)
        self.enemiesMainColor = string_to_int_array(self.enemiesMainColor)

        self.player1Colors = np.array([string_to_int_array(self.player1Color1), string_to_int_array(self.player1Color2)])
        self.player2Colors = np.array([string_to_int_array(self.player2Color1), string_to_int_array(self.player2Color2)])
        self.player3Colors = np.array([string_to_int_array(self.player3Color1), string_to_int_array(self.player3Color2)])
        self.playersAllColors = np.array([self.player1Colors, self.player2Colors, self.player3Colors])

        self.ballColor = string_to_int_array(self.ballColor)


        #Gero o EConfig para realizar o processamento
        self.EConfig = EConfig(
            offSetWindow    =   self.OffSetBord,
            offSetErode     =   self.OffSetErode,
            dimMatrix       =   self.MatrixTop,
            Trashhold       =   self.BINThresh,
            FieldWidth      =   self.fieldWidth ,
            FieldHeight     =   self.fieldHeight,
            ballColor       =   self.ballColor,
            allyColor       =   self.teamMainColor,
            enemyColor      =   self.enemiesMainColor,
            goalAllyColor1  =   np.array(string_to_int_array(self.player1Color1)),
            goalAllyColor2  =   np.array(string_to_int_array(self.player1Color2)),
            atk1AllyColor1  =   np.array(string_to_int_array(self.player2Color1)),
            atk1AllyColor2  =   np.array(string_to_int_array(self.player2Color2)),
            atk2AllyColor1  =   np.array(string_to_int_array(self.player3Color1)),
            atk2AllyColor2  =   np.array(string_to_int_array(self.player3Color2)),
            emulatorMode    =   self.Mode 
        )

        self.vs.setConfigEmulator(self.EConfig)
        #Inicializa o viewer
        if(self.Mode== MODE_USB_CAM): #Modo camera
            print('[EMULADOR] Emulador em modo de processamento de imagem da Camera USB')
            # Inicialização da comunicação (Serial, MQTT ou nenhuma)
            if (self.hasMqtt == True): 
                print("[EMULADOR] Comunicação MQTT inicializada")

                self.clientMQTT = connect_to_broker("broker.hivemq.com", 1883)

                if (self.clientMQTT != None): 
                    self.hasConection = True 
                    self.hasMqtt = True
                else: 
                    self.hasConection = False
                    self.hasMqtt = False

            elif (self.hasSerial == True):
                print("[EMULADOR] Comunicação Serial inicializada")
                print(self.serialPort)
                self.clientSerial = connect_to_serial(self.serialPort)

                if (self.clientSerial != None): 
                    self.hasConection = True 
                    self.hasSerial = True
                else: 
                    self.hasConection = False
                    self.hasSerial = False

            #Entrada do vídeo
            self.btn_run.pack_forget() # torna o botão "run" invisível
            self.btn_stop.pack(fill=BOTH, expand=1) # torna o botão "stop" visível

            self.capture.reset()
            self.capture.setMode(CaptureMode.CAM)
            
            if self.capture.setIdCam(self.CamUSB):
                #verifica se tem suporte a controle de foco
                if self.settingsTree._hasControlFocus:
                    if self._focusMode == FocusMode.AUTO:
                        self.capture.setModeFocus(self._focusMode)
                    else: #foco manual
                        self._focusMode = FocusMode.MANUAL
                        self.capture.setModeFocus(self._focusMode)
                        self.capture.setFocusManual(self.FocusValue)
                else: #a árvore de variáveis não verificou se tem controle de foco
                    if self._focusMode == FocusMode.AUTO:
                        #Verifico se tem suporte
                        if not self.capture.setModeFocus(FocusMode.AUTO):
                            print("[EMULADOR]: Câmera não suporta controle de foco")
                            #atualizo a arvore 
                            self.settingsTree.att_node_id('I00C','AUTOMATICO')
                            self.settingsTree.att_node_id('I00D','')
                            self.settingsTree.save_to_json('config')

                            #executa sem setar o modo
                        else:
                            self.settingsTree.att_node_id('I00C','AUTOMATICO')
                            self.settingsTree.att_node_id('I00D','')
                            self.settingsTree.save_to_json('config')

                            #executa sem setar o modo
                    else: #foco manual
                        self._focusMode = FocusMode.MANUAL
                        if not self.capture.setModeFocus(FocusMode.MANUAL):
                            self._focusMode = FocusMode.MANUAL
                            print("[EMULADOR]: Câmera não suporta controle de foco")
                            #atualizo a arvore
                            self.settingsTree.att_node_id('I00C','AUTOMATICO')
                            self.settingsTree.att_node_id('I00D','')
                            self.settingsTree.save_to_json('config')

                            #executa sem setar o modo
                        else:
                            self.capture.setFocusManual(self.FocusValue)
                            print("[EMULADOR]: Foco manual com valor setado de ", self.FocusValue)
                            #atualizo a arvore
                            self.settingsTree.att_node_id('I00C','MANUAL')
                            self.settingsTree.att_node_id('I00D',self.FocusValue)
                            self.settingsTree.save_to_json('config')
                
                
                #seta a flag de que a câmera está funcionando
                self.cameraIsRunning = True 
                
                print("[CAPTURA]: Iniciou-se a thread novamente!")
                self.captureThread= CameraCaptureThread(main=self, settingMenu=self.settingsTree, capture_instance=self.capture, deque=self.capture_deque)
                self.captureThread.start()  

                # self.firstExecution = True
                self.processUSB()

                # Chamando thread para processamento de vídeo
                self.showInformation()

                #Trabalhando com filas e threads
                if (self.hasConection == True):
                    self.communication_thread = threading.Thread(target=self.send_data, args=(self.commands_queue,), daemon=True)
                    self.communication_thread.start()
            else:
                messagebox.showerror("Erro ao criar o objeto de captura", "O equipamento não tem permissão para funcionar, ou não existe câmera com esse index.")
                
                #libera recursos
                #print(self.capture_deque)
                if(self.capture): 
                    self.capture.reset() #Libera a câmera
                    #self.capture_deque = deque(maxlen=self.maxDeque)

                if (self.clientMQTT != None):
                    self.clientMQTT.loop_stop()
                    self.clientMQTT.disconnect()
                    self.hasConection = False
                    self.hasMqtt = False
                
                if(self.clientSerial != None):
                    print(self.clientSerial)
                    close_serial(self.clientSerial)
                    self.hasConection = False
                    self.hasSerial = False

                self.cameraIsRunning = False 
                self.btn_stop.pack_forget()
                self.btn_run.pack(fill = BOTH, expand =1 )

                self.Mode = MODE_DEFAULT
                self.viewer.default_mode()
                self.debugFieldViewer.default_mode()

                self.infoCards.update()

                self.Timer.stop()
                self.Timer.reset()

                self.stop()
                
        elif(self.Mode ==  MODE_IMAGE): #Modo Imagem
            print('[EMULADOR] Emulador em modo de processamento de Imagem')
            #Configurar viewer para modo de exibição imagem
            #Entrada do vídeo
            self.cameraIsRunning = False
            self.capture.reset()
            self.capture.setMode(CaptureMode.IMG)  

            #inicia thread de captura

            self.btn_stop.pack_forget() # torna o botão "run" invisível
            self.btn_run.pack(fill=BOTH, expand=1) # torna o botão "stop" visível
            #self.processImage()
            self.processImageNew()
        elif(self.Mode == MODE_VIDEO_CAM):
            print('[EMULADOR] Emulador em modo de processamento de Video')
            
            
            #configurar viewer para modo de exibição de vídeo
            self.btn_run.pack_forget() # torna o botão "run" invisível
            
            self.btn_stop.pack(fill=BOTH, expand=1) # torna o botão "stop" visível
            
            #video_path = '/home/felipersotero/Documentos/Codigos/interface-vsss/src/videos/jogadores-movimento.mp4'
            #self.capture = cv2.VideoCapture(self.VideoPath)
            self.capture.reset()
            self.capture.setMode(CaptureMode.VIDEO)
            self.cameraIsRunning = False
            self.delay = 14 #14ms
            self.processVideo()
            
        else:
            self.Mode == MODE_DEFAULT
            print('[EMULADOR] Entrada inválida')
            self.btn_stop.pack_forget() # torna o botão "run" invisível
            self.btn_run.pack(fill=BOTH, expand=1) # torna o botão "stop" visível
            self.stop() #Para o emulador.

 
    #Método para Parar a Emulação.
    def stop(self):
        print('[EMULADOR] Emulador teve sua execução parada.')

        #parando a thread de captura
        try:
            self.captureThread.stop()
        except:
            print('[EMULADOR]: thread foi forçada a terminar.')
        #print(self.capture_deque)
        if(self.capture): 
            self.capture.reset() #Libera a câmera
            #self.capture_deque = deque(maxlen=self.maxDeque)

        if (self.clientMQTT != None):
            self.clientMQTT.loop_stop()
            self.clientMQTT.disconnect()
            self.hasConection = False
            self.hasMqtt = False
        
        if(self.clientSerial != None):
            print(self.clientSerial)
            close_serial(self.clientSerial)
            self.hasConection = False
            self.hasSerial = False

        #Atualiza cards
        self.infoCards.updateFuncs()

        #Inicializa o viewer
        if(self.Mode== MODE_USB_CAM): #Modo camera
            #Configurando Viewer para modo de exibição de câmera
            #Entrada do vídeo
            self.cameraIsRunning = False #Camera Não pausada
            self.btn_stop.pack_forget() # torna o botão "run" invisível
            self.btn_run.pack(fill=BOTH, expand=1) # torna o botão "stop" 
            
        elif(self.Mode ==  MODE_IMAGE): #Modo Imagem
            #Configurar viewer para modo de exibição imagem
            
            self.cameraIsRunning = False #Camera Não pausada
            self.btn_stop.pack_forget() # torna o botão "run" invisível
            self.btn_run.pack(fill=BOTH, expand=1) # torna o botão "stop" visível
            
        elif(self.Mode == MODE_VIDEO_CAM):
            #configurar viewer para modo de exibição de vídeo
            self.cameraIsRunning = False #Camera Não pausad
            self.btn_stop.pack_forget() # torna o botão "run" invisível
            self.btn_run.pack(fill=BOTH, expand=1) # torna o botão "stop" visível
            
        else:
            print("################### MODE DEFAULT ############################")
            self.Mode = MODE_DEFAULT
            self.btn_stop.pack_forget() # torna o botão "run" invisível
            self.btn_run.pack(fill=BOTH, expand=1) # torna o botão "stop" visível
        
        #Configurando para base novamente
        self.Mode = MODE_DEFAULT
        self.viewer.default_mode()
        self.debugFieldViewer.default_mode()

        #atualizo informações na interface
        self.infoCards.update()

        #parando o timer e resetando sua contagem
        self.Timer.stop()
        self.Timer.reset()




    
    def call_detection_system(self, input_queue, output_queue):
        #inicio da contagem de tempo
        St1 = self.Timer.getElapsedTime()

        received_data = input_queue.get()

        frame, debug, fieldDimensions, OffSetBord, OffSetErode, MatrixTop, BINThresh, ballColor, ball, teamMainColor, enemiesMainColor, playersAllColors, allies, enemies, OffSetBord = received_data

        try:
            #Chamando funções de detecção de campo, bola e jogadores
            binary_treat, frame, rect_vertices, frame_reduce, prop_px_cm = detect_field(frame, debug, fieldDimensions, OffSetBord, OffSetErode, MatrixTop, BINThresh)
            ballImg, ball_object, binaryBall = detect_ball(frame_reduce, ballColor, ball, prop_px_cm, debug)
            imgDebug, binaryPlayers, binaryTeam, amountOfPlayers, amountOfAlslies, amountOfEnemies, playersWindows, alliesWindows, enemiesWindows, allies_list, enemies_list, robots = detect_players(frame_reduce, ballImg, binaryBall, binary_treat, teamMainColor, enemiesMainColor, playersAllColors, prop_px_cm, ball_object, allies, enemies, OffSetBord, rect_vertices, debug)


            sending_data = (ball_object, allies_list, enemies_list, frame, binary_treat, binaryBall, binaryPlayers, binaryTeam, imgDebug, alliesWindows, enemiesWindows)
            output_queue.queue.clear()
            output_queue.put(sending_data)
        
        except:
            print("[DETECTION]: Ocorreu um erro em processar. Provavel que foi imagem None")
        #finalizo contagem completa dos frames
        St2 = self.Timer.getElapsedTime()

        self.frameTime = (St2 - St1)               #tempo em  milisegundos
        self.FPStime = int(1000.0 / self.frameTime) if self.frameTime != 0 else 0 
        self.realTime = self.Timer.getElapsedTime() /1000
        #atualizo informações na interface
        self.infoCards.update()
    

    #Funções que executam os processos (execução por USB, por imagem ou )
    def processUSB(self):
        #carrega informações de focus

        #Id de captura
        while len(self.capture_deque) == 0:  # Espera até que haja pelo menos um elemento no deque
            time.sleep(0.1)  # Espera por 0.1 segundos antes de verificar novamente

        self.frame = self.capture_deque[-1]
        
        field_data_structure = (self.frame, self.debug_view, self.fieldDimensions, self.OffSetBord, self.OffSetErode, self.MatrixTop, self.BINThresh)
        ball_data_structure = (self.ballColor, self.ball)
        players_data_structure = (self.teamMainColor, self.enemiesMainColor, self.playersAllColors, self.allies, self.enemies, self.OffSetBord)
        
        data_structure = field_data_structure + ball_data_structure + players_data_structure

        #Pegando time atual do processamento
        Stp1 = self.Timer.getElapsedTime()

        if self.cameraIsRunning:
        
            # Chamando a função para detecção e enviando os parâmetros necessários
            self.sent_data_queue.queue.clear()
            self.sent_data_queue.put(data_structure)

            self.video_processor_thread = threading.Thread(target=self.call_detection_system, args=(self.sent_data_queue, self.received_data_queue))
            self.video_processor_thread.daemon = True
            self.video_processor_thread.start()

            # Salvando dados recebidos
            received_data = self.received_data_queue.get()
            self.ball, self.allies, self.enemies, self.frame, self.binary_treat, self.binaryBall, self.binaryPlayers, self.binaryTeam, self.imgDebug, self.alliesWindows, self.enemiesWindows = received_data


            # Enviando dados para o processamento
            self.control.updateObjectsValues(self.field, self.ball, self.allies, self.enemies)
            self.commands = self.control.processControl()
            self.commands_queue.queue.clear()
            self.commands_queue.put(self.commands)
                    
        #Finaliza contagem de tempo de processamento
        Stp2 = self.Timer.getElapsedTime()

        self.totalTime = (Stp2-Stp1)  
        self.realTime = self.Timer.getElapsedTime()/1000.0        #tempo em segundos                              #tempo atual que se passou                                            #Em ms
        self.FPStime = (1000/self.totalTime) if (self.totalTime != 0) else 0      

        if self.cameraIsRunning:
            #Aqui tem um tempo de delay fixo entre as execuções da função
            self.viewer.window.after(self.delay, self.processUSB)

    #processando a imagem utilizando o antigo sistema de visão
    def processImage(self):
        print("[EMULADOR] Processando imagem: ",self.ImgPath)
        St1i = self.Timer.getElapsedTime()
        self.capture.setImagePath(self.ImgPath)
        self.frame = self.capture.getImage()
        
        field_data_structure = (self.frame, self.debug_view, self.fieldDimensions, self.OffSetBord, self.OffSetErode, self.MatrixTop, self.BINThresh)
        ball_data_structure = (self.ballColor, self.ball)
        players_data_structure = (self.teamMainColor, self.enemiesMainColor, self.playersAllColors, self.allies, self.enemies, self.OffSetBord)

        data_structure = field_data_structure + ball_data_structure + players_data_structure

        # Chamando a função para detecção e enviando os parâmetros necessários
        self.sent_data_queue.queue.clear()
        self.sent_data_queue.put(data_structure)

        self.video_processor_thread = threading.Thread(target=self.call_detection_system, args=(self.sent_data_queue, self.received_data_queue))
        self.video_processor_thread.daemon = True
        self.video_processor_thread.start()

        # Salvando dados recebidos
        received_data = self.received_data_queue.get()
        ball_object, allies_list, enemies_list, frame, binary_treat, binaryBall, binaryPlayers, binaryTeam, imgDebug, alliesWindows, enemiesWindows = received_data

        self.ball = ball_object
        self.allies = allies_list
        self.enemies = enemies_list
        St2i = self.Timer.getElapsedTime()

        binaryPlayers = detect_squares(binaryPlayers)
        #Exibindo dados em tela
        self.viewer.show(frame)
        if(self.DEBUGA == True):
            print("tá funcionando em debug")
            self.debugFieldViewer.show(binary_treat)
            self.debugObjectsViewer.show(binaryBall)
            self.debugPlayersViewer.show(binaryPlayers)
            self.debugTeamViewer.show(binaryTeam)
        self.resultViewer.show(imgDebug)

        #Adicionando conteúdos
        self.setContentRobots()

      # self.call_detection_system()
        self.totalTime = (St2i - St1i)                       #tempo em mili 
        #segundos
        
        self.realTime = self.Timer.getElapsedTime() / 1000

        #atualizo informações na interface
        self.infoCards.update()

    #processando uma imagem utilizando o novo sistema de visão
    def processImageNew(self):
        print("[EMULADOR] Processando imagem: ",self.ImgPath)
        St1i = self.Timer.getElapsedTime()
        self.capture.setImagePath(self.ImgPath)
        self.frame = self.capture.getImage()

        #Método de RUN para imagem
        result = self.vs.proc(self.frame, debug=self.DEBUGA)

        #retornando valores
        St2i = self.Timer.getElapsedTime()

        #Exibindo dados em tela
        self.viewer.show(self.frame)

        if(self.DEBUGA == True):
            binary_treat, binaryBall, binaryPlayers, binaryTeam = self.vs.getDebugImages()
            self.debugFieldViewer.show(binary_treat)
            self.debugObjectsViewer.show(binaryBall)
            self.debugPlayersViewer.show(binaryPlayers)
            self.debugTeamViewer.show(binaryTeam)
        self.resultViewer.show(result)

        # puxando informações do sistema de visão
        self.allies     = self.vs.allyTeam
        self.enemies    = self.vs.enemyTeam

        #Adicionando conteúdos
        self.setContentRobots()

        #resetando configurações já que é modo imagem
        self.vs._resetVs()

        self.totalTime = (St2i - St1i)                       #tempo em mili 
        #segundos
        
        self.realTime = self.Timer.getElapsedTime() / 1000

        self.FPStime = int(1000/self.totalTime)

        #atualizo informações na interface
        self.infoCards.update()
    
    
    #Método para exibir informações
    def showInformation(self):
        if self.cameraIsRunning:
            #Atualizo informações do cards sobre funcionalidade
            self.infoCards.updateFuncs()
            self.viewer.show(self.frame)
            if(self.DEBUGA == True):
                self.debugFieldViewer.show(self.binary_treat)
                self.debugObjectsViewer.show(self.binaryBall)
                self.debugPlayersViewer.show(self.binaryPlayers)
                self.debugTeamViewer.show(self.binaryTeam)
            self.resultViewer.show(self.imgDebug)

            #Adicionando conteúdos
            self.setContentRobots()

            self.viewer.window.after(20, self.showInformation)
        else:
            print('Não está no modo câmera')
    #Método para processar o vídeo
    def processVideo(self):
        print(self.VideoPath)
        print("[EMULADOR] Processando vídeo")

        self.capture.setMode(CaptureMode.DEFAULT)
        self.frame = self.capture.getImage()

        #if ret:
        #    self.call_detection_system(self.sent_data_queue, self.received_data_queue)

        #self.viewer.window.after(self.delay, self.processVideo)

        #atualizo informações na interface
        self.infoCards.update()

    #Adicionar conteúdo dos robÔs
    def setContentRobots(self):
        for i in range(3):
            if self.allies[i] is not None:
                self.cards[i].set_content(self.allies[i].id, self.allies[i].detected, self.allies[i].position, self.allies[i].radius, self.allies[i].image)
            else:
                self.cards[i].set_content("#0", False, ["0.0000", "0.0000"], "0.0000", None)
                
        for i in range(3):
            if self.enemies[i] is not None:
                self.cards[i+3].set_content(self.enemies[i].id, self.enemies[i].detected, self.enemies[i].position, self.enemies[i].radius, self.enemies[i].image)
            else:
                self.cards[i+3].set_content("#0", False, ["0.0000", "0.0000"], "0.0000", None)

    #Nova forma de adicionar conteúdo dos robôs
    def setContentRobotsNew(self):
        pass 


    # Verifica se tem um serviço cuda no computador
    def hasCudaDevice(self):
        try:
            pycuda.init()
            device_count = pycuda.Device.count()
            if device_count > 0:
                self.hasCuda = True
                context = pycuda.Device(0).make_context()
                self.CudaDeviceVersion = context.get_api_version
                context.detach()
                self.CudaDevice= pycuda.Device(0).name()
                
                #Atualizo o card
                self.infoCards.updateFuncs()
                return True
            else:
                self.hasCuda = False
                self.CudaDeviceVersion = None
                self.CudaDevice= None

                #Atualizo o card
                self.infoCards.updateFuncs()
                return False
        except pycuda.RuntimeError:
                self.hasCuda = False
                self.CudaDeviceVersion = None
                self.CudaDevice= None
                #Atualizo o card
                self.infoCards.updateFuncs()
                return False