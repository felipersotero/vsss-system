from modules import *
from settingsMenu import *
from viewer import MyViewer, WindowsViewer
from cards import Card

from control import *
from communication import *

import threading
import queue
import time

import ast

MODE_DEFAULT:int = 1
MODE_USB_CAM: int= 2
MODE_VIDEO_CAM:int = 3
MODE_IMAGE:int = 4

class Emulator:
    def __init__(self, settingsMenu: settingsMenu, viewer: MyViewer, debugFieldViewer: MyViewer, debugObjectsViewer: MyViewer, debugPlayersViewer: MyViewer, debugTeamViewer: MyViewer, playersWindows: WindowsViewer, resultViewer: MyViewer, cards: Card, IdCap: int, btn_run: Button, btn_stop: Button):
        print("Emulador foi construído")

        self.settingsTree = settingsMenu
        self.viewer = viewer
        self.debugFieldViewer = debugFieldViewer
        self.debugObjectsViewer = debugObjectsViewer
        self.debugPlayersViewer = debugPlayersViewer
        self.debugTeamViewer = debugTeamViewer
        self.playersWindows = playersWindows
        self.resultViewer = resultViewer

        self.cards = cards

        self.IdCap = IdCap
        self.btn_run = btn_run
        self.btn_stop = btn_stop
        
        #Variáveis de controle
        self.Mode = MODE_DEFAULT
        self.cameraIsRunning = False

        self.DEBUGA = False
        self.thread = None
        self.capture = None
        self.delay = 14 #ms

        self.clientMQTT = None
        self.commands = None
        self.my_queue = queue.Queue()

        self.viewer.config()
        self.debugFieldViewer.config()
        self.debugObjectsViewer.config()
        self.debugPlayersViewer.config()
        self.debugTeamViewer.config()
        self.playersWindows.config()
        self.resultViewer.config()

        # Objetos

        self.ball = None
        self.allies = [None, None, None]
        self.enemies = [None, None, None]

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

        self.DEBUG = self.settingsTree.tree.item('I01B','value')[0]
        self.EXECMode = self.settingsTree.tree.item('I01C','value')[0]
        

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
        self.DEBUG = self.format_var(self.DEBUG)
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
        
        DEBUG: {self.DEBUG}
        EXECMode: {self.EXECMode}
        """.encode('utf-8')

        print(msg.decode('utf-8', errors='replace'))

    def worker_function(self, queue):
        while True:
            item = queue.get()
            # print(f"Trabalhando com {item}")
            send_data(self, self.clientMQTT, item)
            queue.task_done()
            
            time.sleep(2)
            
    #Método para o emulador exibir as imagens
    def init(self):
        print("[EMULADOR] Configurando variaveis")
        self.viewer.config()
        self.debugFieldViewer.config()
        # self.clientMQTT = conect_to_broker()
        
        #Inicializa o viewer
        if(self.Mode== MODE_USB_CAM): #Modo camera
            print('[EMULADOR] Emulador em modo de processamento de imagem da Camera USB')
            #Configurando Viewer para modo de exibição de câmera            
            #Entrada do vídeo
            self.capture = cv2.VideoCapture(self.CamUSB)
            self.btn_run.pack_forget() # torna o botão "run" invisível
            self.btn_stop.pack(fill=BOTH, expand=1) # torna o botão "stop" visível
            self.cameraIsRunning = True #Camera Não pausada
            self.delay = 14 #14ms
            # self.firstExecution = True

            self.processUSB()

            #Trabalhando com filas e threads
            worker_thread = threading.Thread(target=self.worker_function, args=(self.my_queue,), daemon=True)
            worker_thread.start()
            
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
            self.cameraIsRunning = False
            self.btn_stop.pack_forget() # torna o botão "run" invisível
            self.btn_run.pack(fill=BOTH, expand=1) # torna o botão "stop" visível
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
            self.Mode = MODE_DEFAULT
            self.btn_stop.pack_forget() # torna o botão "run" invisível
            self.btn_run.pack(fill=BOTH, expand=1) # torna o botão "stop" visível
        
        #Configurando para base novamente
        self.Mode = MODE_DEFAULT
        self.viewer.default_mode()
        self.debugFieldViewer.default_mode()

    def call_detection_system(self):

        def string_to_int_array(array):
            values = array.strip("[]").split()
            int_array = list(map(int, values))

            return int_array
        
        fieldDimensions = np.array([self.fieldWidth, self.fieldHeight])
        teamMainColor = string_to_int_array(self.mainColor)
        player1Colors = np.array([string_to_int_array(self.player1Color1), string_to_int_array(self.player1Color2)])
        player2Colors = np.array([string_to_int_array(self.player2Color1), string_to_int_array(self.player2Color2)])
        player3Colors = np.array([string_to_int_array(self.player3Color1), string_to_int_array(self.player3Color2)])
        playersAllColors = np.array([player1Colors, player2Colors, player3Colors])
        enemiesMainColor = string_to_int_array(self.enemiesMainColor)
        ballColor = string_to_int_array(self.ballColor)

        #Chamando funções de detecção de campo, bola e jogadores
        binary_treat, frame, rect_vertices, frame_reduce, prop_px_cm = detect_field(self.frame, self.DEBUGA, fieldDimensions, self.OffSetBord,self.OffSetErode, self.MatrixTop, self.BINThresh)
        ballImg, ball_object, binaryBall = detect_ball(frame_reduce, ballColor, self.ball, prop_px_cm, True)
        imgDebug, binaryPlayers, binaryTeam, amountOfPlayers, amountOfAlslies, amountOfEnemies, playersWindows, alliesWindows, enimiesWindows, allies_list, enemies_list, robots = detect_players(frame_reduce, ballImg, binaryBall, binary_treat, teamMainColor, enemiesMainColor, playersAllColors, prop_px_cm, ball_object, self.allies, self.enemies, True)

        self.ball = ball_object
        self.allies = allies_list
        self.enemies = enemies_list

        #Exibindo dados em tela
        self.viewer.show(frame)
        self.debugFieldViewer.show(binary_treat)
        self.debugObjectsViewer.show(binaryBall)
        self.debugPlayersViewer.show(binaryPlayers)
        self.debugTeamViewer.show(binaryTeam)
        self.resultViewer.show(imgDebug)

        playersWindowsSeparated = alliesWindows[:3] + enimiesWindows[:3]
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
        
    #Funções que executam os processos (execução por USB, por imagem ou )
    def processUSB(self):
        ret, self.frame = self.capture.read()

        if self.cameraIsRunning and ret:
            self.call_detection_system()
            self.commands = recieve_data(self, self.ball, self.allies, self. enemies, self.clientMQTT)

            self.my_queue.queue.clear()
            self.my_queue.put(self.commands)

        self.viewer.window.after(self.delay, self.processUSB)

    def processImage(self):
        print("[EMULADOR] Processando imagem: ",self.ImgPath)

        self.frame = load_image(self.ImgPath)

        self.call_detection_system()
