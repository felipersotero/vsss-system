from imports import *
from ui.viewer import MyViewer
from modules.VisionSys.components.objects import *
from modules.control.control import *
from modules.communication.communication import *
import serial.tools.list_ports
from ui.cards import *
import numpy as np
#==========================/// Gerando classe de janela de controle de jogador /// ====================
#Essa janela funciona como um aplicativo que será utilizado para controlar
# o jogador de forma unica, para podermos verificar se ele está fazendo as
# ações escolhidas
class ControlWindow:
    def __init__(self, master, App, Emulador):
        #carregando mestre, aplicativo e mulador
        self.root = master
        self.newWindow = Toplevel(self.root)
        self.root = self.newWindow
        
        #pegando valores
        self.app = App                      # aplicativo mestre
        self.treeMenu = self.app.menu       # puxa a tree view
        self.emulador = Emulador            # emulador mestre
        self.viewer = None                  # viewer para o carro
        
        #modo
        self.mode = 'manual'                # Modo padrão

        #frames
        self.frameViewer = None             #Frame de visualizar
        self.frameControl = None            #Frame de controle

        #Viewer que será utilizado
        self.viewer = MyViewer(self.frameViewer)

        #modo de execução da janela de controle
        self.Mode = ModeControlW.DEFAULT                    # Vai estar ou em POINTER, ou MANUAL

        #variáveis utilizadas pela janela de controle
        self.SerialPorts = None                             # Portas seriais descobretas
        self.SerialPort = None                              # Porta serial escolhida
        self.comMode = None                                 # Modo de comunicação
        self.controlMode =  tk.StringVar(value="manual")    # Modo de configuração

        #variável de controle
        self._isRun = False                                 # Simulação iniciou
        self.command = None                                 # comando atual que será enviado

        #thread para processamento
        self.queueIn = queue.Queue()                        # fila para enviar dados para a thread
        self.queueOut = queue.Queue()                       # fila para receber dados da thread

        #configurando a janela
        self.config()                                       # Configurando frames
        self.initLabels()                                   # Configurando labels
        
        self.show_serial_combobox(None)                     # simulando evento
        self.control_mode_changed(None)                     

        self.loadMemory()                                   # Carregando  configurações da memória

        #self.centerWindow()                                 # tentanto centralizar a janela

        #atualizando os cards
        self.cardsInfos.setMaster(self.emulador)

    #configurando a janela
    def config(self):
        #adicionando ícone
        try:
            if(self.app.system == 'Windows'):
                self.root.iconbitmap('src/data/icon.ico')
            elif(self.app.system =='Linux'):
                self.root.iconbitmap('src/data/icon.ico')
            else:
                self.root.iconbitmap('src/data/icon.ico')
        except ValueError as e:
            print("[APP]: Problemas em acessar o ícone", e)
                # Calcula as dimensões da janela
        
        #título da janela
        self.root.title("PINBOT - VSSS - Controle de Jogador")
        self.root.configure(background="#dfe3ee")
        self.root.geometry()

        #configurando frames labels necessários
        #frame de viewer do jogador
        try:
            if(self.app.system =='Windows'):
                hwnd = ctypes.windll.user32.FindWindowW(u"Shell_traywnd", None)
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                self.taskbar_height = rect.bottom - rect.top
            else:
                self.taskbar_height = 0 
        except:
            self.taskbar_height = 0

        #frame
        # Espaçamento entre os frames
        spacer1 = Frame(self.root, height=10, bg='#dfe3ee')
        spacer1.pack_propagate(False)  # Evita que o frame ajuste seu tamanho automaticamente
        spacer1.pack()

        # Criando o primeiro frame acima
        self.frameViewer = Frame(self.root, width=600, height=400, bg="black")
        self.frameViewer.pack_propagate(False)  # Evita que o frame ajuste seu tamanho automaticamente
        self.frameViewer.pack()

        # Centralizando o primeiro frame
        self.frameViewer.grid_propagate(False)
        self.frameViewer.grid_rowconfigure(0, weight=1)
        self.frameViewer.grid_columnconfigure(0, weight=1)

        # Espaçamento entre os frames
        spacer = Frame(self.root, height=10, bg="#dfe3ee")
        spacer.pack()


        # Criando o segundo frame abaixo
        self.frameControl = Frame(self.root, bg="white")
        self.frameControl.pack_propagate(False)  # Evita que o frame ajuste seu tamanho automaticamente
        self.frameControl.pack()

        #frame filho do frameControl na esquerda
        self.choseFrame = Frame(self.frameControl, bg = "white")
        self.choseFrame.grid(row=0,column=0)

        #frame de controles (controle manual)
        self.cButtonsFrame = Frame(self.frameControl, bg="white")
        
        #frame de ajuste de constantes (controle automático)
        self.cConstFrame = Frame(self.frameControl, bg="white")
        
        #frame de análise
        self.analiseFrame = Frame(self.frameControl, bg="white")
        self.analiseFrame.grid(row=0, column=3)

    #Método para inicializar os labels
    def initLabels(self):
        #labels para o controle
        self.lChosePlayer=  Label(self.choseFrame, text="Escolher Jogados: ", fg="black", bg="white")
        self.lChosePlayer.grid(row=0,column=0, padx=10, pady =2, sticky="w")
        self.cBoxPlayer= ttk.Combobox(self.choseFrame, values=["Goleiro", "Atacante 1", "Atacante 2"], state='readonly')
        self.cBoxPlayer.grid(row=0,column=1,padx=10, pady=2, sticky="w")
        
        #Label para escolher comunicação com o jogador
        self.labelCom = Label(self.choseFrame, text="Modo de comunicação: ", fg = "black", bg ="white")

        self.labelCom.grid(row=1,column=0, padx=10, pady =2, sticky="w")
        self.comBox = ttk.Combobox(self.choseFrame, values=["MQTT","SERIAL"],state="readonly")
        self.comBox.grid(row=1,column=1,padx=10,pady=2,sticky="w")
        self.comBox.bind("<<ComboboxSelected>>",self.show_serial_combobox)

        #label escondido para portas seriais
        self.labelComOptions = Label(self.choseFrame, text="Porta Serial:", fg="black", bg="white")
        self.labelComOptions.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.comBoxSerial = ttk.Combobox(self.choseFrame, state="readonly")
        self.comBoxSerial.grid(row=2, column=1, padx=10, pady=5, sticky="w")


        self.btn_save = Button(self.choseFrame, text="Salvar configurações", command=self.save_choices)
        self.btn_save.grid(row=7, column=0, padx=(10,5), pady=5)
        self.btn_start = Button(self.choseFrame, text="Iniciar processamento", command=self.start_processing)
        self.btn_start.grid(row=7, column=1, padx=(10,5),pady =5)

        self.state = StateSquare(self.choseFrame, self._isRun, self.btn_start)
        self.state.grid(row=10, column=1, padx=5, pady=5, sticky="w")

        #Label para escolher um ponto
        self.lChosePoint = Label(self.choseFrame, text="Escolher um ponto", fg="black", bg="white")
        self.lChosePoint.grid(row=3, column=0, padx=10, pady = 2 , sticky="w")
        self.btn_chose_point = Button(self.choseFrame, text="Escolher Ponto",command=self.choose_point)
        self.btn_chose_point.grid(row=3, column=1, padx=10, pady=2, sticky="w")

        #radio button
        # Crie os radiobuttons
        self.manualRadio = tk.Radiobutton(self.choseFrame, text="Manual", variable=self.controlMode, value="manual", bg="white")
        self.autoRadio = tk.Radiobutton(self.choseFrame, text="Automático", variable=self.controlMode, value="automatic", bg="white")
        
        ## Desative o segundo radiobutton
        self.autoRadio.configure(state='disabled')

        # Posicione os radiobuttons
        self.manualRadio.grid(row=4, column=0, columnspan=2, padx=10, pady=2, sticky="w")
        self.autoRadio.grid(row=4, column=1, columnspan=2, padx=10, pady=2, sticky="w")

        # Adicione uma função de callback para lidar com a mudança no estado do radiobutton
        self.controlMode.trace_add("write", self.control_mode_changed)

        # Tratando label Central
        self.cTitle = Frame(self.cButtonsFrame, bg="white")
        self.cTitle.pack()

        self.lblTitle = Label(self.cTitle, text="CONTROLE MANUAL",bg="white",font=("TkDefaultFont", 10, "bold"))
        self.lblTitle.pack()

        self.cBModule = Frame(self.cButtonsFrame, bg="white")
        self.cBModule.pack()

        self.lblSpeed = Label(self.cBModule, text="Velocidade:", bg="white")
        self.lblSpeed.grid(row=0, column=0, padx=1, pady=1)

        self.scaleSpeed = Scale(self.cBModule, from_=0, to=1023, orient=HORIZONTAL)
        self.scaleSpeed.grid(row=1, column=0, padx=1, pady=1)

        self.lblAngle = Label(self.cBModule, text="Ângulo:", bg="white")
        self.lblAngle.grid(row=2, column=0, padx=1, pady=1)

        self.scaleAngle = Scale(self.cBModule, from_=-180, to=180, orient=HORIZONTAL)
        self.scaleAngle.grid(row=3, column=0, padx=2, pady=2)

        self.btnSend = Button(self.cBModule, text="Send", command=self.send_angle)
        self.btnSend.grid(row=3, column=1, padx=2, pady=2)

        self.cBVelocity = Frame(self.cButtonsFrame, bg="white")
        self.cBVelocity.pack(padx=3, pady=3)

        # Defina as direções
        self.directions = ["NW", "N", "NE", "W", "Stop", "E", "SW", "S", "SE"]

        # Criar um dicionário vazio para armazenar os botões
        self.btns_dict = {}

        # Iterar sobre as direções e criar botões para cada uma delas
        for i,direction in enumerate(self.directions):
            #calcula a linha e coluna para esse botão
            row = i //3  
            col = i % 3
            # Crie o botão
            button = Button(self.cBVelocity, text=direction, width=5, height=2, command=lambda dir=direction: self.choseDirection(dir))
            button.grid(row=row, column=col, padx=2, pady=2)
            
            # Adicione o botão ao dicionário, usando a direção como chave
            self.btns_dict[direction] = button


        #Tratando label de informações
        self.cardsInfos = CardInfos(self.analiseFrame,'Informações')
        self.cardsInfos.setMaster(self.emulador)

        #adicionando labels de controle automático:
        self.fTitleAuto = Frame(self.cConstFrame, bg="white")
        self.fTitleAuto.pack(padx=5, pady=(2,10))
        self.cTitleConst = Label(self.fTitleAuto, text = "CONTROLE AUTOMÁTICO", bg="white",font=("TkDefaultFont", 10, "bold"))
        self.cTitleConst.pack()

        #constante 1
        self.frameCConst = Frame(self.cConstFrame, bg="white")
        self.fScale1 = Frame(self.frameCConst, bg="white")
        self.fScale1.pack(padx=10, pady =10)
        self.lbScale1 = Label(self.fScale1, text = "K(ρ)", bg="white")
        self.lbScale1.grid(row=0, column=0, padx=5, pady =5)
        self.scaleKp = Scale(self.fScale1, from_=0, to=140, orient=HORIZONTAL)
        self.scaleKp.grid(row=0, column=1,padx=5, pady =5)

        #constante 2
        self.fScale2 = Frame(self.frameCConst, bg="white")
        self.fScale2.pack(padx=10, pady =10)
        self.lbScale2 = Label(self.fScale2, text = "K(α)", bg="white")
        self.lbScale2.grid(row=0, column=0, padx=5, pady =5)
        self.scaleKa = Scale(self.fScale2, from_=0, to=140, orient=HORIZONTAL)
        self.scaleKa.grid(row=0, column=1,padx=5, pady =5)

        #constante 3
        self.fScale3 = Frame(self.frameCConst, bg="white")
        self.fScale3.pack(padx=10, pady =10)
        self.lbScale3 = Label(self.fScale3, text = "K(β)", bg="white")
        self.lbScale3.grid(row=0, column=0, padx=5, pady =5)
        self.scaleKb = Scale(self.fScale3, from_=0, to=140, orient=HORIZONTAL)
        self.scaleKb.grid(row=0, column=1, padx=5, pady =5)

        #publicando
        self.frameCConst.pack(anchor=CENTER)

        #botão de publicar configuração de constante
        self.btnCFrame = Frame(self.cConstFrame)
        self.btnCSend = Button(self.btnCFrame, text="Configurar constantes", command=self.send_consts)
        self.btnCSend.pack()
        self.btnCFrame.pack(padx=10,pady=10)

        #publicando os frames
        self.cButtonsFrame.grid(padx=10, pady=10,row=0, column=1)
        self.cConstFrame.grid(padx=10, pady=10,row=0, column=2)

        self.root.resizable("false", "false")
        
    #método para centralizar  a janela
    def centerWindow(self):
        
        #Centralizando janela
        self.get_screen_resolution()

        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        self.width = self.root.winfo_width()
        self.height = self.root.winfo_height()
        
        x = (self.screen_width // 2) - (self.width // 2)
        y = (self.screen_height // 2) - (self.height // 2) - (self.taskbar_height//2)

        # Defina a geometria da janela
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
            
        # Impede que a janela seja redimensionada
        self.root.resizable(False, False)

    #método para puxar os dados do usuário já presentes e colocar-los na janela
    def loadMemory(self):
        #puxa dados do emulador
        self.emulador.load_vars()
        self.SerialPort = self.emulador.serialPort
        self.comMode = self.emulador.comMode
        
        
        #atribui ao seus respectivos lugares e trata os dados
        if(self.comMode == "mqtt"):
            self.comBox.current(0)
        elif(self.comMode == "serial"):
            self.comBox.current(1)

        #atualiza contínuamente da memória
        try:
            self.cardsInfos.updateFuncs()
        except:
            messagebox.showerror("Erro", "Não foi possível acessar a memória!")

    #publicando constantes
    def send_consts(self):
        kp = self.scaleKp.get()
        ka = self.scaleKa.get()
        kb = self.scaleKb.get()
        print("constantes (ka,kb, kp):", ka, kb, kp)

    #angulo para enviar?
    def send_angle(self):
        self.angle = self.scaleAngle.get()
        print("Sending angle:", self.angle)
    
    #exibir bombox da serial
    def show_serial_combobox(self, event):
        selected_comm = self.comBox.get()
        if selected_comm == "SERIAL":
            self.labelComOptions["state"] = NORMAL
            self.comBoxSerial["state"] = NORMAL
        else:
            self.labelComOptions["state"] = DISABLED
            self.comBoxSerial["state"] = DISABLED


    #definindo como pegar os valores das seriais
    def populate_serial_ports(self):
        self.serial_ports  = [ port.device for port in serial.tools.list_ports.comports()]

        self.comBoxSerial["values"] = self.serial_ports


    #salvar configurações
    def save_choices(self):
        #pega valores dos labels e envia para o emulador
        print("Escolhas feitas")

    #começar processamento
    def start_processing(self):
        player = self.cBoxPlayer.get()
        if(player is None or player ==''):
            messagebox.showwarning("Problema no processamento", "Necessário selecionar o jogador")
        else:
            self.state.toggle_status()
            self._isRun = self.state.status
            if(self._isRun):
                #inicio a thread de processamento
                pass
            else:
                #paro a threa de processamento
                pass


    #função de callback dos botões de direção
    def choseDirection(self, name):
        #["NW", "N", "NE", "W", "Stop", "E", "SW", "S", "SE"]
        #puxando valor de velocidade
        velocity = self.scaleSpeed.get()
        dir = name 
        player = self.cBoxPlayer.get()

        self.makeCommand(1,velocity =velocity, direction = dir, player = player)

    #função de callback do botão de ângulo
    def choseAngle(self):
        pass

    #função para construir um comando e o enviar
    def makeCommand(self, mode =1,velocity = 0, direction =0 , player = None, angle =0):
        #puxando velocidade e direção
        vel = velocity
        dir = direction
        player = player

        #no referencial do robô -> encontrar we e wd



        #gerando string
        if(mode == 1): # modo de controle por botão
            command = ""
            #criando o comando
            if dir == 'NW': 
                w1 = None
                w2 = None
                pass
            elif dir == 'N':
                pass
            elif dir == 'NE':
                pass
            elif dir == 'W':
                pass
            elif dir == 'Stop':
                pass
            elif dir =='E':
                pass
            elif dir == 'SW':
                pass
            elif dir == 'S':
                pass
            elif dir == 'SE':
                pass
            else:
                pass
            
            
            self.command = command
            #enviando para a fila o comando
        else:          

            # girar um angulo qualquer
            command = ""
            self.command = command
    


    #método para escolher um ponto na teal
    def choose_point(self):
        print("Escolhendo um ponto na tela")

    #definindo destruidor da janela
    def destroy(self):
        self.root.destroy()

    #pegar as informações da tela
    def get_screen_resolution(self):
        #funcionando no windows
        if(self.app.system == 'Windows'):
            user32 = ctypes.windll.user32
            self.screen_width = user32.GetSystemMetrics(0)
            self.screen_height = user32.GetSystemMetrics(1)
        
        #funcionando no linux
        elif(self.app.system == 'Linux'):
            # Executar o comando xrandr e obter a saída
            output = subprocess.check_output(['xrandr']).decode('utf-8')

            # Expressão regular para encontrar as dimensões da tela
            pattern = r'\b(\d+)x(\d+)\+\d+\+\d+\b'

            # Procurar as dimensões da tela na saída do xrandr
            match = re.search(pattern, output)

            # Se for encontrada uma correspondência, extrair as dimensões
            if match:
                self.screen_width, self.screen_height = map(int, match.groups())
                print("Largura:", self.screen_width)
                print("Altura:", self.screen_height)
        else:
             print("Não foi possível encontrar as dimensões da tela.")

    # Defina a função de callback
    def control_mode_changed(self, *args):
        self.mode = self.controlMode.get()
        if self.mode == "manual":
            self.Mode = ModeControlW.MANUAL
            #Variaveis do modo manual
            for direction in self.directions:
                button = self.btns_dict[direction]
                button.config(state=NORMAL)

            self.btnSend['state'] = NORMAL
            self.scaleSpeed['state'] = NORMAL
            self.scaleAngle['state'] = NORMAL

            #variáveis do modo automático
            self.scaleKa['state'] = DISABLED
            self.scaleKb['state'] = DISABLED
            self.scaleKp['state'] = DISABLED
            self.btnCSend ['state'] = DISABLED
            self.btn_chose_point['state'] = DISABLED

            #muda o background dos estados, para mostrar o ativo
            self.cButtonsFrame.configure(borderwidth=1,relief="sunken")
            self.cConstFrame.configure(borderwidth=0,relief="solid")

        elif self.mode == "automatic":
            self.Mode = ModeControlW.POINTER
            #variáveis do modo manual
            for direction in self.directions:
                button = self.btns_dict[direction]
                button.config(state=DISABLED)


            self.btnSend['state'] = DISABLED
            self.scaleSpeed['state'] = DISABLED
            self.scaleAngle['state'] = DISABLED

            #variáveis do modo automático
            self.scaleKa['state'] = NORMAL
            self.scaleKb['state'] = NORMAL
            self.scaleKp['state'] = NORMAL
            self.btnCSend ['state'] = NORMAL
            self.btn_chose_point['state'] = NORMAL

            #Muda o background dos estados para indicar o ativo
            self.cButtonsFrame.configure(borderwidth=0,relief="sunken")
            self.cConstFrame.configure(borderwidth=1,relief="sunken")

        else:
            self.Mode= ModeControlW.MANUAL
            #variáveis do modo manual
            for direction in self.directions:
                button = self.btns_dict[direction]
                button.config(state=DISABLED)



            self.btnSend['state'] = DISABLED
            self.scaleSpeed['state'] = DISABLED
            self.scaleAngle['state'] = DISABLED

            #variáveis do modo automático
            self.scaleKa['state'] = DISABLED
            self.scaleKb['state'] = DISABLED
            self.scaleKp['state'] = DISABLED
            self.btnCSend ['state'] = DISABLED
            self.btn_chose_point['state'] = DISABLED
            
            #Muda o background dos estados para indicar o ativo
            self.cButtonsFrame.configure(borderwidth=0,relief="sunken")
            self.cConstFrame.configure(borderwidth=0,relief="sunken")
    
        #Definindo funções dos botões com lógica de chamada

    #definindo o processamento, ou seja como a thread irá realizar o processamento, o importante é que ela apenas execute em looping no manual.
    def callBack(self):
        if (self.mode == "Manual"):
            pass
        else:
            pass

