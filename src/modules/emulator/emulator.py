'''
    @GNOMIO: Motor principal do sistema VSSS. Gerencia o pipeline de processamento,
    coordena threads de visão e comunicação, e mantém o estado global do sistema.

    Versão: v3.0.1
    Última modificação: 14/02/2024
    Autor: Saulo (update)

    Patch Notes v3.0.1:
    - Implementado novo sistema de threads com melhor desempenho
    - Separação de processamento em visão e comunicação
    - Melhor gerenciamento de recursos
    - Sistema de filas otimizado para UI e comunicação
    - Novo sistema de debug com menor overhead
    - Correções na estabilidade do processamento
'''
#=============================================================
from modules.VisionSys.detectorV2 import VisionSystem
from imports import *
from ui.settingsMenu import *
from ui.viewer import MyViewer, WindowsViewer
from ui.cards import *

from modules.VisionSys.components.objects import *
from modules.control.control import Control
from modules.communication.communication import *
from modules.communication.ui.interface import *

# Protocolo PFOX
from modules.communication.protocol.protocolHeader import *

import threading
import queue
import time
from collections import deque
import ast

import traceback

#=============================================================
class Emulator:
    '''
        Emulador é o nome dado à Engine que controla o sistema de captura, controle, comunicação e visão computacional.
    '''
    def __init__(self, App):
        print("[EMULATOR] Construindo instância do emulador...")
        self._init_app_references(App)
        self._init_state_variables()
        self._init_collections()
        self._init_parallel_processing()
        self._init_viewers()
        self._init_control_system()
        self._init_timers(App)
        self._init_system_info(App)
        self._init_gpu_info()
        self._init_camera_settings()
        self._init_capture_and_vision()

        print("[EMULATOR] Inicialização concluída com sucesso.")

    # ==============================================================
    #  1. Referências principais da aplicação (UI, botões, viewers)
    # ==============================================================
    def _init_app_references(self, App):
        """Carrega referências vindas da aplicação principal."""
        self.settingsTree = App.menu
        self.viewer = App.viewer
        self.debugFieldViewer = App.debugField
        self.debugObjectsViewer = App.debugObject
        self.debugPlayersViewer = App.debugPlayers
        self.debugTeamViewer = App.debugTeam
        self.resultViewer = App.result
        self.virtualResult = App.virtualVision

        self.cards = App.cards
        self.infoCards = App.infosEmulator

        self.IdCap = App.IdFrame
        self.btn_run = App.btn_run
        self.btn_stop = App.btn_stop

        # Salvando instância da aplicação original
        self.app = App

    # ==============================================================
    #  2. Variáveis de estado e controle
    # ==============================================================
    def _init_state_variables(self):
        """Inicializa variáveis de controle e estado interno do emulador."""
        self.Mode = MODE_DEFAULT
        self.cameraIsRunning = False
        self.DEBUGA = False

        self.thread = None
        self.delay = 8  # ms

        self.clientMQTT = None
        self.clientSerial = None
        self.commands = None

        self.captureThread = None
        self.frame = None
        self.errorCode = 0

        # Classe de controle da comunicação
        self.comm = None

        # Janela de comunicação
        self.comm_debug_window = None
        self.should_open_comm_window = False

        self.hasCuda = False
        self.CudaDevice = None
        self.CudaDeviceVersion = None
        self.CUDAselected = False

        # Tempo de comunicação
        self.comm_send_interval = 0.02 #150 FPS

    # ==============================================================
    #  2.1 Processamento paralelo
    #= =============================================================
    def _init_parallel_processing(self):
        """Configura variáveis para controle de processamento paralelo."""
        # Fila original mantida para compatibilidade, mas não será mais usada diretamente
        self.output_queue = queue.Queue(maxsize=1)

        # Filas separadas — independentes para UI e comunicação
        self.ui_queue = queue.Queue(maxsize=1)
        self.comm_queue = queue.Queue(maxsize=1)
        self.control_queue = queue.Queue(maxsize=1)

        # Threads
        self.vision_thread = None
        self.comm_thread = None


    # ==============================================================
    # Processamento paralelo: thread de visão e loop da UI, comunicação e controle
    # ==============================================================
    # Thread de captura e processamento das imagens
    def visionThread(self):
        """Thread separada que faz captura e processamento de visão."""
        print("[VISION THREAD] Iniciada.")
        while self.cameraIsRunning:
            loop_start = time.time()

            try:
                # --- Captura ---
                frame = self.capture.getImage() #A câmera tem um FPS de 30, então fica travado a 30 FPS o sistema.
                if frame is None:
                    # Meu FPS é limitado pela velocidade de aquisição de dados da câmera.
                    time.sleep(0.002)
                    continue

                # --- Processamento de visão ---
                t_proc_start = time.time()
                result = self.vs.processImg(frame, self.DEBUGA)
                objects = self.vs.getObjects()
                virtual = self.vs.virtualImg
                t_proc_end = time.time()

                # --- Atualiza tempos ---
                self.frameTime = (t_proc_end - t_proc_start) * 1000.0  # processamento
                self.totalTime = (time.time() - loop_start) * 1000.0   # visão total
                self.realTime = self.Timer.getElapsedTime()/1000.0           # desde init
                #print("[EMULADOR]: Tempo total em segundos ", self.realTime)
          
                self.fill_deques_time()

                # --- Atualiza objetos detectados ---
                self.field = objects.get(ID_Objects.FIELD, self.field)
                self.ball = objects.get(ID_Objects.BALL, self.ball)
                self.allies = objects.get(ID_Objects.ALLIES, self.allies)
                self.enemies = objects.get(ID_Objects.ENEMIES, self.enemies)

                # --- Prepara pacote para a UI ---
                data = {
                    'frame': frame,
                    'result': result,
                    'virtual': virtual,
                    'field': self.field,
                    'ball': self.ball,
                    'allies': self.allies,
                    'enemies': self.enemies,
                    'vision_time': self.totalTime,
                    'proc_time': self.frameTime,
                    'real_time': self.realTime,
                    'fps': self.FPStime,
                    'timestamp': self.realTime
                }

                # --- Envia para fila da UI ---
                if self.ui_queue.full():
                    try:
                        self.ui_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.ui_queue.put_nowait(data)

                # --- Envia para fila da comunicação ---
                if self.comm_queue.full():
                    try:
                        self.comm_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.comm_queue.put_nowait(data)

            except Exception as e:
                print("[VISION THREAD] Erro:", e)
                traceback.print_exc()
                time.sleep(0.003)
                continue

        print("[VISION THREAD] Finalizada.")

    # Apenas para atualizar a UI
    def updateUI(self):
        """Atualiza a interface com base nas informações da thread de visão."""
        if not self.cameraIsRunning:
            print("[UPDATE UI] Encerrado.")
            self.Timer.stop()
            return

        try:
            data = self.ui_queue.get_nowait()
            frame = data['frame']
            result = data['result']
            virtual = data['virtual']
            self.field = data['field']
            self.ball = data['ball']
            self.allies = data['allies']
            self.enemies = data['enemies']
            self.totalTime = data['vision_time']
            self.frameTime = data['proc_time']
            self.realTime = data['real_time']
            self.FPStime = data['fps']

            # --- Exibição segura (Tkinter thread principal) ---
            if frame is not None:
                self.viewer.show(frame)
            if result is not None:
                self.resultViewer.show(result)
            virtual = data.get('virtual', None)
            if virtual is not None:
                self.virtualResult.show(virtual)


            # Atualiza debug
            if self.DEBUGA:
                try:
                    imgs = self.vs.getDebugImages()
                    if imgs and len(imgs) > 0 and imgs[0] is not None:
                        self.debugFieldViewer.show(imgs[0])
                except Exception:
                    pass

            # --- Atualiza UI (info cards e controle) ---
            avg_proc = self.avg(self.deque_proc)
            self.FPStime = int(1000/avg_proc) if avg_proc > 0 else 0

            self.infoCards.updateInfo("FPS:", self.FPStime)
            self.infoCards.updateInfo("Vision. (ms):", f"{avg_proc:.2f}")
            self.infoCards.updateInfo("Proc. (ms):", f"{self.avg(self.deque_proc):.2f}")
            self.infoCards.updateInfo("Envio (ms):", f"{self.avg(self.deque_send):.2f}")

            self.infoCards.updateInfo("Timer (s):", f"{self.realTime / 1000:.2f}")
            self.infoCards.updateInfo("Error Code:", self.errorCode)
            self.infoCards.update()

            self.control.updateObjectsValues(self.field, self.ball, self.allies, self.enemies)

        except queue.Empty:
            pass

        # Loop contínuo (~60 FPS)
        self.viewer.window.after(16, self.updateUI)

    def communicationThread(self):
        """
        Thread principal de comunicação bidirecional.
        Envia comandos pendentes e processa respostas recebidas
        somente quando a comunicação está ativa.
        """

        send_interval = getattr(self, "comm_send_interval", 0.02)

        while self.cameraIsRunning:
            
            t1 = self.Timer.getElapsedTime()
            # ------------------------------------------
            # 0) Verificar se comunicação existe e está ativa
            # ------------------------------------------
            if not self.comm or not self.comm.is_connected():
                # Comunicação OFF → não tenta enviar nem receber
                time.sleep(0.1)
                continue

            # ------------------------------------------
            # 1) ENVIO DE COMANDOS
            # ------------------------------------------
            try:
                while not self.commands_queue.empty():
                    cmd = self.commands_queue.get_nowait()
                    self.comm.send_data("espfox/cmd", cmd)

                
                # Teste de envio de um comando qualquer.
                cmd = self.PFOXcontroler.create_packet(Address.ESPMAIN, MsgType.HEARTBEAT,[]).to_bytes()
                self.comm.send_data("TEST", cmd)

            except Exception as e:
                print(f"[Emulator] Erro ao enviar: {e}")

            # ------------------------------------------
            # 2) RECEPÇÃO DE PACOTES
            # ------------------------------------------
            try:
                responses = self.comm.get_responses()
                for resp in responses:
                    if self.DEBUGA: print(f"[Emulator RX] {resp}")

                    # repassar p/ módulo de controle se existir
                    if hasattr(self, "control_module") and self.control_module:
                        try:
                            self.control_module.update(resp)
                        except Exception as e2:
                            print(f"[ControlModule] Erro no update: {e2}")

            except Exception as e:
                print(f"[Emulator] Erro ao processar RX: {e}")

            # ------------------------------------------
            # 3) INTERVALO DO LOOP
            # ------------------------------------------

            time.sleep(send_interval)
            t2 = self.Timer.getElapsedTime()
            dif = (t2-t1)

            self.deque_send.append(dif) #COntabilizando tempo de envio.



    # ==============================================================
    #  3. Filas, buffers e coleções
    # ==============================================================
    def _init_collections(self):
        """Configura filas e coleções auxiliares usadas no sistema."""
        self.commands_queue = queue.Queue(maxsize=1)
        self.sent_data_queue = queue.Queue(maxsize=10)
        self.received_data_queue = queue.Queue(maxsize=10)

        self.maxDeque = 4
        self.capture_deque = deque(maxlen=self.maxDeque)

        self.avg_window = 40 #quantidade de samples para média 

        # Criando deques para salvar os tempos
        self.deque_vision = deque(maxlen=self.avg_window)
        self.deque_proc = deque(maxlen=self.avg_window)
        self.deque_send = deque(maxlen=self.avg_window)
        self.deque_fps  = deque(maxlen=self.avg_window)


        # Entidades controladas
        self.field = None
        self.ball = None
        self.allies = [None, None, None]
        self.enemies = [None, None, None]

    def avg(self, dq):
        if len(dq) == 0:
            return 0
        return sum(dq)/len(dq)
    
    # ==============================================================
    #  4. Inicialização dos viewers
    # ==============================================================
    def _init_viewers(self):
        """Configura os elementos visuais do aplicativo (viewers e painéis)."""
        for viewer in [
            self.viewer,
            self.debugFieldViewer,
            self.debugObjectsViewer,
            self.debugPlayersViewer,
            self.debugTeamViewer,
            self.resultViewer,
            self.virtualResult,
        ]:
            if hasattr(viewer, "config"):
                viewer.config()

    # ==============================================================
    #  5. Controle e configuração lógica
    # ==============================================================
    def _init_control_system(self):
        """Inicializa o sistema de controle e define conteúdo dos robôs."""
        self.setContentRobots()
        self.control = Control(self)

    # ==============================================================
    #  6. Timer de alta precisão
    # ==============================================================
    def _init_timers(self, App):
        """Cria o temporizador de alta precisão."""
        self.Timer = HighPrecisionTimer(self)
        self.frameTime = 0.0
        self.sendTime = 0.0
        self.FPStime = 0.0
        self.realTime = 0.0
        self.totalTime = 0.0

    def fill_deques_time(self):
        self.deque_vision.append(self.totalTime)
        self.deque_proc.append(self.frameTime)
        self.deque_send.append(self.sendTime)

    def erase_deques_times(self):
        self.deque_vision.clear()
        self.deque_proc.clear()
        self.deque_send.clear()


    # ==============================================================
    #  7. Informações do sistema operacional
    # ==============================================================
    def _init_system_info(self, App):
        """Armazena informações do sistema operacional."""
        self.OP = App.system
        self.OPrelease = App.release
        self.OPversion = App.version

    # ==============================================================
    #  8. GPU e CUDA
    # ==============================================================
    def _init_gpu_info(self):
        """Inicializa as variáveis relacionadas à GPU e CUDA."""
        self.hasCuda = False
        self.CudaDevice = None
        self.CudaDeviceVersion = None
        self.CUDAselected = False

    # ==============================================================
    #  9. Configurações da câmera
    # ==============================================================
    def _init_camera_settings(self):
        """Define parâmetros padrão da câmera."""
        self.FocusValue = 0
        self.FocusMode: FocusMode = FocusMode.AUTO

    # ==============================================================
    #  10. Comunicação e captura
    # ==============================================================
    def _init_communication(self):
        """Inicializa o objeto de comunicação."""
                # -------------------------
        # 🔹 Comunicação (via classe Communication)
        # -------------------------
        com_mode = self.comMode.lower()

        if com_mode == 'mqtt':
            broker = self.settingsTree.tree.item('I021', 'value')[0] if 'I021' in self.settingsTree.tree.get_children('') else 'localhost'
            port_str = self.settingsTree.tree.item('I022', 'value')[0] if 'I022' in self.settingsTree.tree.get_children('') else '1883'
            port = int(port_str) if port_str.isdigit() else 1883

            self.comm = Communication(use_mqtt=True, broker_address=broker, port=port)
            print(f"[EMULADOR] Comunicação configurada via MQTT → {broker}:{port}")

        elif com_mode == 'serial':
            port = self.serialPort or '/dev/ttyUSB0'
            self.comm = Communication(use_mqtt=False, serial_port=port)
            print(f"[EMULADOR] Comunicação configurada via Serial → {port}")

        else:
            # Nenhum modo de comunicação selecionado
            print('[EMULADOR] Comunicação desativada (nenhuma selecionada).')
            self.comm = None

        self.should_open_comm_window = (
            self.Mode == MODE_USB_CAM and 
            com_mode in ['mqtt', 'serial'] and
            self.comm is not None
        )
        
        if self.should_open_comm_window:
            print(f"[EMULADOR] Janela de comunicação será aberta - Modo: {com_mode}")
            
        self.PFOXcontroler = PFOXController() #API para gerar pacotes no protocolo PFOX 

        
        # Inicializo a thread de comunicação
        self.comm_thread = threading.Thread(target=self.communicationThread, daemon=True)
        self.comm_thread.start()

        # 🔹 ABRE JANELA DE COMUNICAÇÃO (se necessário)
        if self.should_open_comm_window:
            # Agenda a abertura para depois da UI estar estável
            self.viewer.window.after(500, self._open_communication_window)

    def _init_capture_and_vision(self):
        """Cria a instância de captura e o sistema de visão."""
        self.capture = Capture(CaptureMode.DEFAULT, False)
        self.EConfig = EConfig()
        self.vs = VisionSystem(capture=self.capture, UseCuda=False, GPUType=None)

    #===================================================================
    def load_vars(self):
        """Carrega variáveis de configuração do emulador e ajusta o comportamento do sistema."""
        tree = self.settingsTree.tree
        get = lambda key: tree.item(key, 'value')[0]

        # -------------------------
        # 🔹 Entradas gerais
        # -------------------------
        self.CamUSB = int(get('I003'))
        self.ImgPath = get('I004')
        self.VideoPath = get('I005')
        self.UseMode = self.format_var(get('I006'))

        # -------------------------
        # 🔹 Parâmetros de processamento de imagem
        # -------------------------
        self.OffSetBord = int(get('I008'))
        self.OffSetErode = int(get('I009'))
        self.BINThresh = int(get('I00A'))
        self.MatrixTop = int(get('I00B'))
        self.FocusMode = self.format_var(get('I00C'))

        focus_str = get('I00D')
        self.FocusValue = float(focus_str) if focus_str else 0.0

        # -------------------------
        # 🔹 Campo
        # -------------------------
        self.fieldWidth = int(get('I00F'))
        self.fieldHeight = int(get('I010'))

        # -------------------------
        # 🔹 Cores
        # -------------------------
        color_keys = {
            "mainColor": 'I012',
            "player1Color1": 'I013',
            "player1Color2": 'I014',
            "player2Color1": 'I015',
            "player2Color2": 'I016',
            "player3Color1": 'I017',
            "player3Color2": 'I018',
            "enemiesMainColor": 'I019',
            "ballColor": 'I01A',
        }

        for attr, key in color_keys.items():
            setattr(self, attr, self.format_var(get(key)))

        # -------------------------
        # 🔹 Modo e execução
        # -------------------------
        self.debug_view = self.format_var(get('I01C'))
        self.comMode = self.format_var(get('I01D'))  # "mqtt" ou "serial" ou "nenhuma"
        self.serialPort = get('I01E')
        self.CUDAService = self.format_var(get('I01F'))
        self.EXECMode = self.format_var(get('I020'))

        # -------------------------
        # 🔹 Modo de debug
        # -------------------------
        debug_flag = str(self.debug_view).lower()
        self.DEBUGA = debug_flag == 'true'
        self.debug_view = self.DEBUGA

        # -------------------------
        # 🔹 Modo de uso (câmera, imagem, vídeo)
        # -------------------------
        mode_map = {
            'camera': MODE_USB_CAM,
            'imagem': MODE_IMAGE,
            'video': MODE_VIDEO_CAM,
        }
        self.Mode = mode_map.get(self.UseMode, MODE_DEFAULT)
        if self.Mode == MODE_DEFAULT:
            print('[EMULADOR] Valor inválido para modo de uso.')
            self.stop()

        # -------------------------
        # 🔹 CUDA
        # -------------------------
        self.CUDAselected = "Don't have cuda"

        # 🔹 Comunicação (via classe Communication)
        # -------------------------
        com_mode = self.comMode.lower()


        # -------------------------
        # 🔹 Foco da câmera
        # -------------------------
        focus_map = {
            'automatico': FocusMode.AUTO,
            'manual': FocusMode.MANUAL,
        }
        self._focusMode = focus_map.get(self.FocusMode, FocusMode.AUTO)

        # -------------------------
        # 🔹 Atualização do card
        # -------------------------
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

    # Método para inicializar o processo utilizar o sistema de visão os resultados
    def init(self):
        print("[EMULADOR] Configurando variáveis...")

        # -----------------------------
        # 🔹 Inicialização base
        # -----------------------------
        self.Timer.run()
        self.viewer.config()
        self.debugFieldViewer.config()
        self.infoCards.updateFuncs()

        def str_to_int_array(s: str) -> np.ndarray:
            return np.array(list(map(int, s.strip("[]").split())))

        # Dimensões e cores
        self.fieldDimensions = np.array([self.fieldWidth, self.fieldHeight])
        self.teamMainColor = str_to_int_array(self.mainColor)
        self.enemiesMainColor = str_to_int_array(self.enemiesMainColor)

        self.player1Colors = np.array([str_to_int_array(self.player1Color1), str_to_int_array(self.player1Color2)])
        self.player2Colors = np.array([str_to_int_array(self.player2Color1), str_to_int_array(self.player2Color2)])
        self.player3Colors = np.array([str_to_int_array(self.player3Color1), str_to_int_array(self.player3Color2)])
        self.playersAllColors = np.array([self.player1Colors, self.player2Colors, self.player3Colors])

        self.ballColor = str_to_int_array(self.ballColor)

        # -----------------------------
        # 🔹 Criar e aplicar configuração do emulador
        # -----------------------------
        #Reseto as configurações do sistema de visão
        self.vs._resetVs()

        #Recarrego as novas
        self.EConfig = EConfig(
            offSetWindow=self.OffSetBord,
            offSetErode=self.OffSetErode,
            dimMatrix=self.MatrixTop,
            Trashhold=self.BINThresh,
            FieldWidth=self.fieldWidth,
            FieldHeight=self.fieldHeight,
            ballColor=self.ballColor,
            allyColor=self.teamMainColor,
            enemyColor=self.enemiesMainColor,
            goalAllyColor1=self.player1Colors[0],
            goalAllyColor2=self.player1Colors[1],
            atk1AllyColor1=self.player2Colors[0],
            atk1AllyColor2=self.player2Colors[1],
            atk2AllyColor1=self.player3Colors[0],
            atk2AllyColor2=self.player3Colors[1],
            emulatorMode=self.Mode,
            timer=self.Timer
        )
        self.vs.setConfigEmulator(self.EConfig)

        # -----------------------------
        # 🔹 Inicialização conforme o modo
        # -----------------------------
        if self.Mode == MODE_USB_CAM:
            self._init_usb_mode()


        elif self.Mode == MODE_IMAGE:
            self._init_image_mode()

        elif self.Mode == MODE_VIDEO_CAM:
            self._init_video_mode()

        else:
            print('[EMULADOR] Entrada inválida.')
            self._reset_ui_and_stop()

    #==== Métodos auxiliares da inicialização ====
    def _init_usb_mode(self):
        print('[EMULADOR] Modo: Câmera USB')

        # Configura botões da UI
        self.btn_run.pack_forget()
        self.btn_stop.pack(fill=BOTH, expand=1)

        # Reset da captura
        self.capture.reset()
        self.capture.setMode(CaptureMode.CAM)

        # Tenta abrir a câmera
        if not self.capture.setIdCam(self.CamUSB):
            print("[EMULADOR] Falha ao abrir a câmera USB.")
            self._handle_camera_error()
            return

        # Configura foco da câmera
        self._configure_focus()

        # Marca câmera como ativa
        self.cameraIsRunning = True
        print("[CAPTURA] Iniciando thread da câmera...")

        # Inicia thread de captura e processamento
        print("[EMULADOR] Iniciando modo paralelo de captura e processamento...")

        self.cameraIsRunning = True
        self.Timer.run()

        # Inicia thread de visão (processamento pesado)
        self.vision_thread = threading.Thread(target=self.visionThread, daemon=True)
        self.vision_thread.start()

        self._init_communication()
        
        # Inicia loop da UI (Tkinter)
        self.viewer.window.after(0, self.updateUI)
    


    def _configure_focus(self):
        """Define o modo de foco de acordo com a configuração."""
        if not self.settingsTree._hasControlFocus:
            print("[EMULADOR] Árvore não detectou controle de foco. Aplicando padrão.")
            self._focusMode = FocusMode.AUTO

        if self._focusMode == FocusMode.AUTO:
            if not self.capture.setModeFocus(FocusMode.AUTO):
                print("[EMULADOR] Câmera não suporta foco automático.")
        else:
            if not self.capture.setModeFocus(FocusMode.MANUAL):
                print("[EMULADOR] Câmera não suporta foco manual.")
            else:
                self.capture.setFocusManual(self.FocusValue)
                print(f"[EMULADOR] Foco manual ajustado para {self.FocusValue}")

    def _open_communication_window(self):
        """Abre a janela de comunicação debug de forma assíncrona."""
        try:
            # ✅ CORREÇÃO: usar self.comm em vez de self.communication
            if (self.comm_debug_window is None and 
                self.comm is not None and  # ← CORRIGIDO
                self.cameraIsRunning):
                
                # Cria a janela de comunicação
                self.comm_debug_window = CommunicationDebugWindow(
                    self.app.root,  # Master é a janela principal
                    comm=self.comm,  # ← CORRIGIDO
                    on_close_ref_clear=self._on_comm_window_close
                )
                
                print("[EMULADOR] Janela de comunicação aberta com sucesso")
                
        except Exception as e:
            print(f"[EMULADOR] Erro ao abrir janela de comunicação: {e}")
            import traceback
            traceback.print_exc()

    def _on_comm_window_close(self, window_ref):
        """Callback quando a janela de comunicação é fechada."""
        self.comm_debug_window = None
        print("[EMULADOR] Janela de comunicação fechada")


    def _init_image_mode(self):
        print('[EMULADOR] Modo: Imagem estática')
        self.cameraIsRunning = False
        self.capture.reset()
        self.capture.setMode(CaptureMode.IMG)
        self.btn_stop.pack_forget()
        self.btn_run.pack(fill=BOTH, expand=1)
        self.processImageNew()

    def _init_video_mode(self):
        print('[EMULADOR] Modo: Vídeo')
        self.btn_run.pack_forget()
        self.btn_stop.pack(fill=BOTH, expand=1)
        self.capture.reset()
        self.capture.setMode(CaptureMode.VIDEO)
        self.cameraIsRunning = False
        self.delay = 14
        self.processVideo()

    def _handle_camera_error(self):
        """Trata erro de inicialização da câmera."""
        messagebox.showerror(
            "Erro de captura", 
            "O equipamento não tem permissão ou o índice de câmera é inválido."
        )
        if self.capture:
            self.capture.reset()

        if self.comm:
            self.comm.reset()

        self.cameraIsRunning = False
        self._reset_ui_and_stop()

    def _reset_ui_and_stop(self):
        """Reseta a interface e interrompe a execução."""
        self.btn_stop.pack_forget()
        self.btn_run.pack(fill=BOTH, expand=1)
        self.Mode = MODE_DEFAULT
        self.viewer.default_mode()
        self.debugFieldViewer.default_mode()
        self.infoCards.update()
        self.Timer.stop()
        self.Timer.reset()
        self.stop()

    def stop(self):
        """
        Interrompe toda a execução do emulador, incluindo:
        - Loop da UI (updateUI)
        - Thread de visão (visionThread)
        - Captura de câmera
        - Temporizador (Timer)
        """
        print("[EMULATOR] Encerrando execução...")

        # --- Fecha janela de comunicação ---
        if self.comm_debug_window is not None:
            try:
                self.comm_debug_window.destroy()
            except Exception as e:
                print(f"[EMULATOR] Erro ao fechar janela de comunicação: {e}")
            finally:
                self.comm_debug_window = None

        # --- sinaliza parada global ---
        self.cameraIsRunning = False

        # --- encerra thread de visão, se ativa ---
        if hasattr(self, "vision_thread") and self.vision_thread and self.vision_thread.is_alive():
            print("[EMULATOR] Aguardando thread de visão encerrar...")
            self.vision_thread.join(timeout=1.0)

        # --- encerra thread de comunicação ---
        if hasattr(self, "comm_thread") and self.comm_thread and self.comm_thread.is_alive():
            print("[EMULATOR] Aguardando thread de comunicação encerrar...")
            self.comm_thread.join(timeout=1.0)

        # --- para captura de câmera ---
        try:
            if hasattr(self, "capture") and self.capture is not None:
                self.capture.reset()
        except Exception as e:
            print("[EMULATOR] Erro ao resetar captura:", e)

        # --- para o temporizador ---
        try:
            self.Timer.stop()
            self.Timer.reset()
        except Exception as e:
            print("[EMULATOR] Erro ao parar Timer:", e)

        # --- limpa a fila de saída (evita referências antigas) ---
        try:
            if hasattr(self, "output_queue") and not self.output_queue.empty():
                while not self.output_queue.empty():
                    self.output_queue.get_nowait()
        except Exception:
            pass

        # --- zera tempos e status ---
        self.totalTime = 0.0
        self.frameTime = 0.0
        self.sendTime = 0.0
        self.realTime = 0.0
        self.FPStime = 0
        self.errorCode = 0

        self.erase_deques_times()

        print("[EMULATOR] Execução finalizada com sucesso.")


    # Métodos auxiliares do stop
    def _stop_capture_thread(self):
        """Para a thread de captura de forma segura."""
        if hasattr(self, "captureThread") and self.captureThread:
            try:
                self.captureThread.stop()
                print("[EMULATOR] Thread de captura parada com sucesso.")
            except Exception as e:
                print(f"[EMULATOR] Thread de captura forçada a terminar: {e}")
            finally:
                self.captureThread = None

    def _reset_capture(self):
        """Libera a câmera e limpa a fila de imagens."""
        if hasattr(self, "capture") and self.capture:
            try:
                self.capture.reset()
                print("[EMULATOR] Câmera liberada.")
            except Exception as e:
                print(f"[EMULATOR] Falha ao liberar câmera: {e}")

        # Limpa deque de imagens para evitar frames antigos
        self.capture_deque.clear()

    
    def _close_communication(self):
        """Fecha qualquer tipo de comunicação ativa (MQTT/Serial) via classe Communication."""
        # ✅ CORREÇÃO: usar self.comm em vez de self.communication
        if hasattr(self, "comm") and self.comm:
            try:
                print("[EMULATOR] Encerrando comunicação...")
                self.comm.reset()
                print("[EMULATOR] Comunicação encerrada com sucesso.")
            except Exception as e:
                print(f"[EMULATOR] Erro ao encerrar comunicação: {e}")
        else:
            print("[EMULATOR] Nenhuma comunicação ativa para encerrar.")
            
    def _reset_ui_by_mode(self):
        """Atualiza botões e estado visual conforme o modo atual."""
        print(f"[EMULADOR] Resetando UI para o modo: {self.Mode}")

        self.btn_stop.pack_forget()
        self.btn_run.pack(fill=BOTH, expand=1)
        self.cameraIsRunning = False



    # ============================ | Métodos de processamento | ==================
    # ========== // Trabalhar com um loop apenas // ==============

    #================================================================================
    #processando uma imagem utilizando o novo sistema de visão
    def processImageNew(self):
        print("[EMULADOR] Processando imagem: ",self.ImgPath)
        St1i = self.Timer.getElapsedTime()
        self.capture.setImagePath(self.ImgPath)
        self.frame = self.capture.getImage()
        self.debugFrame = self.frame.copy()

        #Método de RUN para imagem
        result = self.vs.processImg(self.debugFrame, debug=self.DEBUGA)

        #retornando valores
        St2i = self.Timer.getElapsedTime()

        #Exibindo dados em tela
        self.viewer.show(self.frame)

        #imagens de debug
        if(self.DEBUGA == True):
            binary_treat, binaryBall, binaryPlayers, binaryTeam = self.vs.getDebugImages()
            self.debugFieldViewer.show(binary_treat)
            self.debugObjectsViewer.show(binaryBall)
            self.debugPlayersViewer.show(binaryPlayers)
            self.debugTeamViewer.show(binaryTeam)
        else:
            self.debugFieldViewer.clear()
            self.debugObjectsViewer.clear()
            self.debugPlayersViewer.clear()
            self.debugTeamViewer.clear()
            
        #imagens de resultado
        self.resultViewer.show(result)
        self.virtualResult.show(self.vs.virtualImg)
        
        # puxando informações do sistema de visão
        self.allies     = self.vs.allyTeam
        self.enemies    = self.vs.enemyTeam

        #Adicionando conteúdos
        self.setContentRobots()

        #resetando configurações já que é modo imagem
        self.vs._resetVs()

        self.totalTime = (St2i - St1i)                       #tempo em mili 
        self.frameTime = self.totalTime
        #segundos
        
        self.realTime = self.Timer.getElapsedTime() / 1000

        self.FPStime = int(1000/self.totalTime)

        #atualizo informações na interface
        self.fill_deques_time()
        self.infoCards.update()
        self.erase_deques_times()
    
    

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
                self.cards[i].set_content("#0", False, ["0.0", "0.0"], "0.0", None)
                
        for i in range(3):
            if self.enemies[i] is not None:
                self.cards[i+3].set_content(self.enemies[i].id, self.enemies[i].detected, self.enemies[i].position, self.enemies[i].radius, self.enemies[i].image)
            else:
                self.cards[i+3].set_content("#0", False, ["0.0", "0.0"], "0.0", None)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
