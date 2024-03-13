from modules import *
from settingsMenu import *
from viewer import MyViewer, WindowsViewer
from cards import Card
from objects import *
from control import Control
from communication import *

import threading
import queue
import time

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
        self.playersWindows = App.playersWindows
        self.resultViewer = App.result

        self.cards = App.cards

        self.IdCap = App.IdFrame
        self.btn_run = App.btn_run
        self.btn_stop = App.btn_stop
        
        #Variáveis de controle
        self.Mode = MODE_DEFAULT
        self.cameraIsRunning = False

        self.DEBUGA = False
        self.thread = None
        self.capture = None
        self.delay = 14 #14 ms

        self.clientMQTT = None
        self.commands = None

        self.commands_queue = queue.Queue()
        self.sent_data_queue = queue.Queue()
        self.received_data_queue = queue.Queue()

        self.viewer.config()
        self.debugFieldViewer.config()
        self.debugObjectsViewer.config()
        self.debugPlayersViewer.config()
        self.debugTeamViewer.config()
        self.playersWindows.config()
        self.resultViewer.config()

        # Objetos

        self.field = None
        self.ball = None
        self.allies = [None, None, None]
        self.enemies = [None, None, None]

        self.control = Control(self)

        #Temporizador
        self.timer_running = False
        self.start_time = 0
    
    def load_vars(self):
        self.CamUSB = int(self.settingsTree.tree.item('I003','value')[0])
        self.ImgPath = self.settingsTree.tree.item('I004','value')[0]
        self.VideoPath = self.settingsTree.tree.item('I005','value')[0]
        self.UseMode = self.settingsTree.tree.item('I006','value')[0]

        self.OffSetBord = int(self.settingsTree.tree.item('I008','value')[0])
        self.OffSetErode = int(self.settingsTree.tree.item('I009','value')[0])
        self.BINThresh = int(self.settingsTree.tree.item('I00A','value')[0])
        self.MatrixTop = int(self.settingsTree.tree.item('I00B','value')[0])
        self.DEBUGalg = self.settingsTree.tree.item('I00C','value')[0]

        self.fieldWidth = int(self.settingsTree.tree.item('I00E','value')[0])
        self.fieldHeight = int(self.settingsTree.tree.item('I00F','value')[0])

        self.mainColor = self.settingsTree.tree.item('I011','value')[0]
        self.player1Color1 = self.settingsTree.tree.item('I012','value')[0]
        self.player1Color2 = self.settingsTree.tree.item('I013','value')[0]
        self.player2Color1 = self.settingsTree.tree.item('I014','value')[0]
        self.player2Color2 = self.settingsTree.tree.item('I015','value')[0]
        self.player3Color1 = self.settingsTree.tree.item('I016','value')[0]
        self.player3Color2 = self.settingsTree.tree.item('I017','value')[0]
        self.enemiesMainColor = self.settingsTree.tree.item('I018','value')[0]
        self.ballColor = self.settingsTree.tree.item('I019','value')[0]

        self.debug_view = self.settingsTree.tree.item('I01B','value')[0]
        self.mqttConection = self.settingsTree.tree.item('I01C','value')[0]
        self.EXECMode = self.settingsTree.tree.item('I01D','value')[0]


        self.UseMode = self.format_var(self.UseMode)

        self.mainColor = self.format_var(self.mainColor)
        self.player1Color1 = self.format_var(self.player1Color1)
        self.player1Color2 = self.format_var(self.player1Color2)
        self.player2Color1 = self.format_var(self.player2Color1)
        self.player2Color2 = self.format_var(self.player2Color2)
        self.player3Color1 = self.format_var(self.player3Color1)
        self.player3Color2 = self.format_var(self.player3Color2)
        self.enemiesMainColor = self.format_var(self.enemiesMainColor)
        self.ballColor = self.format_var(self.ballColor)

        self.EXECMode = self.format_var(self.EXECMode)
        self.debug_view = self.format_var(self.debug_view)
        self.mqttConection = self.format_var(self.mqttConection)
        self.DEBUGalg = self.format_var(self.DEBUGalg)
        
        if(self.DEBUGalg == 'true'):
            self.DEBUGA = True
        elif(self.DEBUGalg == 'false'):
            self.DEBUGA = False
        else:
            self.DEBUGA = False
        

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

    def format_var(self, var):
        var = unidecode.unidecode(var)
        var = var.lower()
        return var

    def show_variables(self):
        msg=f"""
        [EMULADOR]
        ====Emulador===
        CamUSB: {self.CamUSB}
        ImgPath: {self.ImgPath}
        VideoPath: {self.VideoPath}
        UseMode: {self.UseMode}
        
        OffSetBord: {self.OffSetBord}
        OffSetErode: {self.OffSetErode}
        BINThresh: {self.BINThresh}
        MatrixTop: {self.MatrixTop}
        DEBUGalg: {self.DEBUGalg}
        
        fieldWidth: {self.fieldWidth}
        fieldHeight: {self.fieldHeight}

        mainColor: {self.mainColor}
        player1Color1: {self.player1Color1}
        player1Color2: {self.player1Color2}
        player2Color1: {self.player2Color1}
        player2Color2: {self.player2Color2}
        player3Color1: {self.player3Color1}
        player3Color2: {self.player3Color2}
        enemiesMainColor: {self.enemiesMainColor}
        ballColor: {self.ballColor}
        
        debug_view: {self.debug_view}
        EXECMode: {self.EXECMode}
        """.encode('utf-8')

        print(msg.decode('utf-8', errors='replace'))

    def send_mqtt_data(self, queue):
        while True:
            item = queue.get()
            result = publish_data(self.clientMQTT, "vsss-ifal-pin/robots", item)

            # print(f"Mensagem publicada! Resultado: {result}.")

            print(item)
            queue.task_done()
            time.sleep(0.015)
            
    #Método para o emulador exibir as imagens
    def init(self):
        print("[EMULADOR] Configurando variaveis")
        self.viewer.config()
        self.debugFieldViewer.config()
        
        if (self.mqttConection == 'true'): self.clientMQTT = connect_to_broker("broker.hivemq.com", 1883)
       
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

        #Inicializa o viewer
        if(self.Mode== MODE_USB_CAM): #Modo camera
            print('[EMULADOR] Emulador em modo de processamento de imagem da Camera USB')
            #Configurando Viewer para modo de exibição de câmera   
            if (self.mqttConection == 'true'): self.clientMQTT = connect_to_broker("broker.hivemq.com", 1883)        
            #Entrada do vídeo
            self.btn_run.pack_forget() # torna o botão "run" invisível
            self.btn_stop.pack(fill=BOTH, expand=1) # torna o botão "stop" visível

            self.capture = cv2.VideoCapture(self.CamUSB)
            self.cameraIsRunning = True #Camera Não pausada
            self.delay = 14 #14ms
            # self.firstExecution = True
            self.processUSB()

            #Trabalhando com filas e threads
            if (self.mqttConection == 'true'):
                communication_thread = threading.Thread(target=self.send_mqtt_data, args=(self.commands_queue,), daemon=True)
                communication_thread.start()
 
        elif(self.Mode ==  MODE_IMAGE): #Modo Imagem
            print('[EMULADOR] Emulador em modo de processamento de Imagem')
            #Configurar viewer para modo de exibição imagem
            #Entrada do vídeo
            self.cameraIsRunning = False
            self.btn_stop.pack_forget() # torna o botão "run" invisível
            self.btn_run.pack(fill=BOTH, expand=1) # torna o botão "stop" visível
            self.processImage()
            
        elif(self.Mode == MODE_VIDEO_CAM):
            print('[EMULADOR] Emulador em modo de processamento de Video')
            #configurar viewer para modo de exibição de vídeo
            self.btn_run.pack_forget() # torna o botão "run" invisível
            self.btn_stop.pack(fill=BOTH, expand=1) # torna o botão "stop" visível
            
            video_path = '/home/felipersotero/Documentos/Codigos/interface-vsss/src/videos/jogadores-movimento.mp4'
            self.capture = cv2.VideoCapture(self.VideoPath)
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
        if(self.capture): self.capture.release() #Libera a câmera

        if (self.clientMQTT):
            self.clientMQTT.loop_stop()
            self.clientMQTT.disconnect()
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

    def start_timer(self):
        if not self.timer_running:
            self.start_time = time.time()
            self.timer_running = True
            
    def stop_timer(self):
        if self.timer_running:
            elapsed_time = time.time() - self.start_time
            self.timer_running = False
            print(f"Tempo decorrido: {elapsed_time*1000} milisegundos")
    
    def call_detection_system(self, input_queue, output_queue):

        #self.start_timer()
        received_data = input_queue.get()

        frame, debug, fieldDimensions, OffSetBord, OffSetErode, MatrixTop, BINThresh, ballColor, ball, teamMainColor, enemiesMainColor, playersAllColors, allies, enemies, OffSetBord = received_data

        #Chamando funções de detecção de campo, bola e jogadores
        binary_treat, frame, rect_vertices, frame_reduce, prop_px_cm = detect_field(frame, debug, fieldDimensions, OffSetBord, OffSetErode, MatrixTop, BINThresh)
        ballImg, ball_object, binaryBall = detect_ball(frame_reduce, ballColor, ball, prop_px_cm, debug)
        imgDebug, binaryPlayers, binaryTeam, amountOfPlayers, amountOfAlslies, amountOfEnemies, playersWindows, alliesWindows, enemiesWindows, allies_list, enemies_list, robots = detect_players(frame_reduce, ballImg, binaryBall, binary_treat, teamMainColor, enemiesMainColor, playersAllColors, prop_px_cm, ball_object, allies, enemies, OffSetBord, rect_vertices, debug)

        sending_data = (ball_object, allies_list, enemies_list, frame, binary_treat, binaryBall, binaryPlayers, binaryTeam, imgDebug, alliesWindows, enemiesWindows)
        output_queue.queue.clear()
        output_queue.put(sending_data)
        
        #self.stop_timer()

    #Funções que executam os processos (execução por USB, por imagem ou )
    def processUSB(self):
        ret, self.frame = self.capture.read()

        field_data_structure = (self.frame, self.debug_view, self.fieldDimensions, self.OffSetBord, self.OffSetErode, self.MatrixTop, self.BINThresh)
        ball_data_structure = (self.ballColor, self.ball)
        players_data_structure = (self.teamMainColor, self.enemiesMainColor, self.playersAllColors, self.allies, self.enemies, self.OffSetBord)
        
        data_structure = field_data_structure + ball_data_structure + players_data_structure

        # print(data_structure)

        if self.cameraIsRunning and ret:
            
            # Chamando a função para detecção e enviando os parâmetros necessários
            self.sent_data_queue.queue.clear()
            self.sent_data_queue.put(data_structure)

            video_processor_thread = threading.Thread(target=self.call_detection_system, args=(self.sent_data_queue, self.received_data_queue))
            video_processor_thread.daemon = True
            video_processor_thread.start()

            # Salvando dados recebidos
            received_data = self.received_data_queue.get()
            ball_object, allies_list, enemies_list, frame, binary_treat, binaryBall, binaryPlayers, binaryTeam, imgDebug, alliesWindows, enemiesWindows = received_data

            self.ball = ball_object
            self.allies = allies_list
            self.enemies = enemies_list

            # Enviando dados para o processamento
            self.control.updateObjectsValues(self.field, self.ball, self.allies, self.enemies)
            self.commands = self.control.processControl()
            self.commands_queue.queue.clear()
            self.commands_queue.put(self.commands)

            #Exibindo dados em tela
            self.viewer.show(frame)
            self.debugFieldViewer.show(binary_treat)
            self.debugObjectsViewer.show(binaryBall)
            self.debugPlayersViewer.show(binaryPlayers)
            self.debugTeamViewer.show(binaryTeam)
            self.resultViewer.show(imgDebug)

            playersWindowsSeparated = alliesWindows[:3] + enemiesWindows[:3]
            self.playersWindows.show(playersWindowsSeparated)

            #Exibindo dados nos cards
            for i in range(3):
                if self.allies[i] is not None:
                    self.cards[i].set_content(self.allies[i].id, self.allies[i].detected, self.allies[i].position, self.allies[i].radius, self.allies[i].image)
                else:
                    self.cards[i].set_content("#", " ", [" ", " "], " ", None)
            for i in range(3):
                if self.enemies[i] is not None:
                    self.cards[i+3].set_content(self.enemies[i].id, self.enemies[i].detected, self.enemies[i].position, self.enemies[i].radius, self.enemies[i].image)
                else:
                    self.cards[i+3].set_content("#", " ", [" ", " "], " ", None)
                    
            # self.call_detection_system()


        self.viewer.window.after(self.delay, self.processUSB)

    def processImage(self):
        print("[EMULADOR] Processando imagem: ",self.ImgPath)

        self.frame = load_image(self.ImgPath)
        
        field_data_structure = (self.frame, self.debug_view, self.fieldDimensions, self.OffSetBord, self.OffSetErode, self.MatrixTop, self.BINThresh)
        ball_data_structure = (self.ballColor, self.ball)
        players_data_structure = (self.teamMainColor, self.enemiesMainColor, self.playersAllColors, self.allies, self.enemies, self.OffSetBord)

        data_structure = field_data_structure + ball_data_structure + players_data_structure

        # Chamando a função para detecção e enviando os parâmetros necessários
        self.sent_data_queue.queue.clear()
        self.sent_data_queue.put(data_structure)

        video_processor_thread = threading.Thread(target=self.call_detection_system, args=(self.sent_data_queue, self.received_data_queue))
        video_processor_thread.daemon = True
        video_processor_thread.start()

        # Salvando dados recebidos
        received_data = self.received_data_queue.get()
        ball_object, allies_list, enemies_list, frame, binary_treat, binaryBall, binaryPlayers, binaryTeam, imgDebug, alliesWindows, enemiesWindows = received_data

        self.ball = ball_object
        self.allies = allies_list
        self.enemies = enemies_list

        # Enviando dados para o processamento
        # self.commands = recieve_data(self, self.ball, self.allies, self. enemies, self.clientMQTT)
        # self.commands_queue.queue.clear()
        # self.commands_queue.put(self.commands)

        #Exibindo dados em tela
        self.viewer.show(frame)
        self.debugFieldViewer.show(binary_treat)
        self.debugObjectsViewer.show(binaryBall)
        self.debugPlayersViewer.show(binaryPlayers)
        self.debugTeamViewer.show(binaryTeam)
        self.resultViewer.show(imgDebug)

        playersWindowsSeparated = alliesWindows[:3] + enemiesWindows[:3]
        self.playersWindows.show(playersWindowsSeparated)

        #Exibindo dados nos cards
        for i in range(3):
            if self.allies[i] is not None:
                self.cards[i].set_content(self.allies[i].id, self.allies[i].detected, self.allies[i].position, self.allies[i].radius, self.allies[i].image)
            else:
                self.cards[i].set_content("#", " ", [" ", " "], " ", None)
        for i in range(3):
            if self.enemies[i] is not None:
                self.cards[i+3].set_content(self.enemies[i].id, self.enemies[i].detected, self.enemies[i].position, self.enemies[i].radius, self.enemies[i].image)
            else:
                self.cards[i+3].set_content("#", " ", [" ", " "], " ", None)

        # self.call_detection_system()

    def processVideo(self):
        print(self.VideoPath)
        print("[EMULADOR] Processando vídeo")

        ret, self.frame = self.capture.read()

        if ret:
            self.call_detection_system(self.sent_data_queue, self.received_data_queue)

        self.viewer.window.after(self.delay, self.processVideo)