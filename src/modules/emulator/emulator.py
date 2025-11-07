'''
    @GNOMIO: O algorítmo de detecção terá agora uma nova lógica de programação, no qual ele é conti-
    tuído de uma classe 'detector' responsável por realizar.
    Os cálculos serão acelerados utilizando a GPU. Para isso utiliza a bibliteca OpenCV com 
    base na plataforma cuda, e usa também a cupy para realizar cálculos da biblioteca
    numpy na GPU do computador.

    Necessário configurar CMAKE e etc para utilizar essa interface.
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
        self._init_viewers()
        self._init_control_system()
        self._init_timers(App)
        self._init_system_info(App)
        self._init_gpu_info()
        self._init_camera_settings()
        self._init_communication()
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

        self.communication = None  # será instanciada depois
        self.hasCuda = False
        self.CudaDevice = None
        self.CudaDeviceVersion = None
        self.CUDAselected = False

        self.processing_lock = threading.Lock()

    # ==============================================================
    #  3. Filas, buffers e coleções
    # ==============================================================
    def _init_collections(self):
        """Configura filas e coleções auxiliares usadas no sistema."""
        import queue
        from collections import deque

        self.commands_queue = queue.Queue(maxsize=1)
        self.sent_data_queue = queue.Queue(maxsize=1)
        self.received_data_queue = queue.Queue(maxsize=1)

        self.maxDeque = 1
        self.capture_deque = deque(maxlen=self.maxDeque)

        # Entidades controladas
        self.field = None
        self.ball = None
        self.allies = [None, None, None]
        self.enemies = [None, None, None]

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
        self.frameTime = None
        self.sendTime = None
        self.FPStime = None
        self.realTime = None
        self.totalTime = None

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
        self.communication: Communication = None

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
        self.CUDAselected = self.hasCudaDevice() if self.CUDAService == 'true' else False

        # -------------------------
        # 🔹 Comunicação (via classe Communication)
        # -------------------------
        com_mode = self.comMode.lower()

        if com_mode == 'mqtt':
            broker = self.settingsTree.tree.item('I021', 'value')[0] if 'I021' in self.settingsTree.tree.get_children('') else 'localhost'
            port_str = self.settingsTree.tree.item('I022', 'value')[0] if 'I022' in self.settingsTree.tree.get_children('') else '1883'
            port = int(port_str) if port_str.isdigit() else 1883

            self.communication = Communication(use_mqtt=True, broker_address=broker, port=port)
            print(f"[EMULADOR] Comunicação configurada via MQTT → {broker}:{port}")

        elif com_mode == 'serial':
            port = self.serialPort or '/dev/ttyUSB0'
            self.communication = Communication(use_mqtt=False, serial_port=port)
            print(f"[EMULADOR] Comunicação configurada via Serial → {port}")

        else:
            # Nenhum modo de comunicação selecionado
            print('[EMULADOR] Comunicação desativada (nenhuma selecionada).')
            self.communication = None

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

    # Método para enviar os comandos via comunicação
    def send_data(self, queue):
        while True:
            try:
                if not self.communication or not hasattr(self.communication, 'send_data'):
                    raise RuntimeError("Comunicação não inicializada")
                    
                item = queue.get()
                result = self.communication.send_data(
                    client=self.clientMQTT,
                    topic="vsss-ifal-pin/robots",
                    message=item
                )
                queue.task_done()
            except Exception as e:
                print(f"Erro no envio: {e}")
            time.sleep(0.015)

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
        self.captureThread = CameraCaptureThread(
            main=self,
            settingMenu=self.settingsTree,
            capture_instance=self.capture,
            deque=self.capture_deque
        )
        self.captureThread.start()
        self.startThreadsLoop()

        # Se houver comunicação configurada, inicia a thread de envio
        if self.communication:
            threading.Thread(
                target=self.send_data, args=(self.commands_queue,), daemon=True
            ).start()

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

        if self.communication:
            self.communication.reset()

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

    #Método para Parar a Emulação.
    def stop(self):
        """Interrompe completamente a execução do emulador e libera todos os recursos."""
        print('[EMULADOR] Execução interrompida.')

        # -----------------------------
        # 🔹 1. Parar captura e threads
        # -----------------------------
        self._stop_capture_thread()
        self._reset_capture()

        # -----------------------------
        # 🔹 2. Encerrar comunicação ativa
        # -----------------------------
        self._close_communication()

        # -----------------------------
        # 🔹 3. Atualizar interface e viewers
        # -----------------------------
        self._reset_ui_by_mode()
        self.viewer.default_mode()
        self.debugFieldViewer.default_mode()
        self.infoCards.update()

        # -----------------------------
        # 🔹 4. Parar e zerar o timer
        # -----------------------------
        self.Timer.stop()
        self.Timer.reset()

        # -----------------------------
        # 🔹 5. Resetar modo geral
        # -----------------------------
        self.Mode = MODE_DEFAULT
        self.cameraIsRunning = False

    # Métodos auxiliares do stop
    def _stop_capture_thread(self):
        """Para a thread de captura de forma segura."""
        if hasattr(self, "captureThread") and self.captureThread:
            try:
                self.captureThread.stop()
                print("[EMULADOR] Thread de captura parada com sucesso.")
            except Exception as e:
                print(f"[EMULADOR] Thread de captura forçada a terminar: {e}")
            finally:
                self.captureThread = None

    def _reset_capture(self):
        """Libera a câmera e limpa a fila de imagens."""
        if hasattr(self, "capture") and self.capture:
            try:
                self.capture.reset()
                print("[EMULADOR] Câmera liberada.")
            except Exception as e:
                print(f"[EMULADOR] Falha ao liberar câmera: {e}")

        # Limpa deque de imagens para evitar frames antigos
        self.capture_deque.clear()

    
    def _close_communication(self):
        """Fecha qualquer tipo de comunicação ativa (MQTT/Serial) via classe Communication."""
        if hasattr(self, "communication") and self.communication:
            try:
                print("[EMULADOR] Encerrando comunicação...")
                self.communication.reset()
                print("[EMULADOR] Comunicação encerrada com sucesso.")
            except Exception as e:
                print(f"[EMULADOR] Erro ao encerrar comunicação: {e}")
        else:
            print("[EMULADOR] Nenhuma comunicação ativa para encerrar.")

    def _reset_ui_by_mode(self):
        """Atualiza botões e estado visual conforme o modo atual."""
        print(f"[EMULADOR] Resetando UI para o modo: {self.Mode}")

        self.btn_stop.pack_forget()
        self.btn_run.pack(fill=BOTH, expand=1)
        self.cameraIsRunning = False



    # ============================ | Métodos de processamento | ==================
    #Funções que executam os processos (execução por USB, por imagem ou )
    def processUSB(self):
          #print("[VS]: Novo processo de USB sendo utilizado")
        #Id de captura
        print("[PROC. THREAD]: INICIANDO TAREFA.")
        while self.cameraIsRunning:
            if len(self.capture_deque) == 0:  # Espera até que haja pelo menos um elemento no deque
                time.sleep(0.02)  # Espera por 0.1 segundos antes de verificar 
                continue
            
            self.frame = self.capture_deque[-1].copy()
            print(f"[PROC. THREAD]: Frame capturado. Dimensões: {self.frame.shape}")
            #puxando o tempo inicial do processamento, ou seja esse aqui, ou seja, o tempo
            # que a imagem foi pega e enviada
            dt = self.Timer.getElapsedTime()

            # padronizando tipo de informação da fila
            data_structure = {'frame': self.frame, 'debug': self.debug_view, 'time': dt}

            #enviando dados na fila
            while not self.sent_data_queue.empty():
                try:
                    self.sent_data_queue.get_nowait()
                except queue.Empty:
                    break

            try:
                self.sent_data_queue.put_nowait(data_structure)
                print("[PROC. THREAD]: Dados enviados para a fila.")
            except queue.Full:
                print("[PROC. THREAD]: Fila de dados cheia, não foi possível enviar.")

            self.vs.drawAllRobots()
            time.sleep(self.delay/1000)
        

    #================================================================================
    #=========== // Gerando tarefa para processar as imagens que chegam
    #definindo nova função para processar imagens
    def call_detection_system(self, input_queue, output_queue):
        """Thread unificada para processar imagens"""
        print("[DETECT.THREAD]: INICIANDO TAREFA.")
        
        while self.cameraIsRunning:
            try:
                if not input_queue.empty():
                    with self.processing_lock:
                        St1 = self.Timer.getElapsedTime()  # início
                        received_data = input_queue.get(timeout=0.1)
                        
                        # Processamento
                        result = self.vs.processImg(received_data.get('frame'), received_data.get('debug', False))
                        
                        # Resultado
                        output_data = {
                            'result': result,
                            'objects': self.vs.virtualImg,
                            'objects': self.vs.getObjects(),
                            'time': St1  # Adicionar tempo inicial
                        }

                        # Calcula FPS e tempo de frame
                        St2 = self.Timer.getElapsedTime()  # fim
                        self.frameTime = (St2 - St1)
                        self.FPStime = int(1000.0 / self.frameTime if self.frameTime != 0 else 0)
                        
                        output_queue.put(output_data)
                        print("[DETECT.THREAD]: Dados processados e enviados para a fila.")

            except queue.Empty:
                time.sleep(self.delay/1000)
            except Exception as e:
                print(f"Erro geral: {e}")
                traceback.print_exc()
                
            print("[DETECT.THREAD]: Tarefa finalizada. Câmera desligada.")

    #========== // Gerando tarefa para exibir os resultados, quando há
    def getResults(self):
        """Pegar resultados processados e atualizar a GUI."""
        if not self.cameraIsRunning:
            print('[RESULT. THREAD]: Thread finalizada.')
            return

        try:
            data = self.received_data_queue.get_nowait()
            
            # Processa dados recebidos
            objects = data.get('objects', {})
            self.result = data.get('result', None)
            self.virtualRImg = data.get('virtual', None)
            
            # Atualiza objetos
            try:
                self.field = objects.get(ID_Objects.FIELD, self.field)
                self.ball = objects.get(ID_Objects.BALL, self.ball)
                self.allies = objects.get(ID_Objects.ALLIES, self.allies)
                self.enemies = objects.get(ID_Objects.ENEMIES, self.enemies)
            except Exception as e:
                print(f"[RESULT.THREAD] Erro ao atualizar objetos: {e}")

            # Atualiza UI com informações de timing
            self.infoCards.updateInfo("FPS:", self.FPStime)
            self.infoCards.updateInfo("Vision. (ms):", self.totalTime)
            self.infoCards.updateInfo("Proc. (ms):", self.frameTime)
            self.infoCards.updateInfo("Timer (s):", self.realTime)
            
            # Atualiza viewers
            if self.frame is not None:
                self.viewer.show(self.frame)
                
            if self.DEBUGA:
                self.updateDebugViewers()

            self.vs.drawAllRobots()
            
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[RESULT.THREAD] Erro: {e}")
            traceback.print_exc()
        finally:
            # Re-schedule next update
            self.viewer.window.after(self.delay, self.getResults)

    # ========= // Definindo método que dá start nessas duas threads
    def startThreadsLoop(self):
        '''
            Método responsável por iniciar as threads de processamento
        '''
        #dando start na thread de processamento
        # Thread responsável
        self.processUSBThread = threading.Thread(target=self.processUSB)
        self.processUSBThread.daemon = True
        self.processUSBThread.start()

        #tempo para ajeitar tudo
        time.sleep(0.010)

        #dando start na thread de detecção
        #possível perda de desempenho para ser analisado
        self.procVideoThread = threading.Thread(target=self.call_detection_system, args=(self.sent_data_queue, self.received_data_queue))
        self.procVideoThread.daemon = True
        self.procVideoThread.start()

        #tempo para ajeitar tudo
        time.sleep(0.010)
        
        try:
            self.viewer.window.after(self.delay, self.getResults)
        except Exception:
            print("[RESULT. THREAD]: Iniciando tarefa em thread (fallback)")
            self.getResultsThread = threading.Thread(target=self.getResults)
            self.getResultsThread.daemon = True
            self.getResultsThread.start()
            time.sleep(0.010)
    
    # ========= // Método para parar as threads
    def stopThreadsLoop(self):
        """Encerra todas as threads de processamento de forma segura"""
        self.cameraIsRunning = False  # Sinaliza para threads pararem
        time.sleep(0.1)  # Permite que threads vejam a mudança
        
        threads_to_stop = [
            self.processUSBThread,
            self.procVideoThread,
            self.getResultsThread
        ]
        
        for thread in threads_to_stop:
            if thread and thread.is_alive():
                try:
                    thread.join(timeout=1.0)
                    if thread.is_alive():
                        print(f"Thread {thread.name} não encerrou no timeout")
                except Exception as e:
                    print(f"Erro ao encerrar thread: {e}")


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
        #segundos
        
        self.realTime = self.Timer.getElapsedTime() / 1000

        self.FPStime = int(1000/self.totalTime)

        #atualizo informações na interface
        self.infoCards.update()
    
    

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
