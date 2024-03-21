from modules import *
from viewer import MyViewer
from objects import *
from control import *
from communication import *
import serial.tools.list_ports

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
        self.app = App                  # aplicativo mestre
        self.emulador = Emulador        # emulador mestre
        self.viewer = None              # viewer para o carro
        
        #tamanho da tela
        self.width  = 800
        self.height = 700

        #frames
        self.frameViewer = None         #Frame de visualizar
        self.frameControl = None        #Frame de controle

        #Viewer que será utilizado
        self.viewer = MyViewer(self.frameViewer)

        #modo de execução da janela de controle


        #variáveis utilizadas pela janela de controle


        #configurando a janela
        self.config()               # Configurando frames
        self.initLabels()           # Configurando labels
    
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
        except:
            print("[APP]: Problemas em acessar o ícone")
                # Calcula as dimensões da janela
        
        #título da janela
        self.root.title("PINBOT - VSSS - Controle de Jogador")
        self.root.configure(background="#dfe3ee")
        self.root.geometry(f'{self.width}x{self.height}')
        self.root.resizable(False,False)

        #configurando frames labels necessários
        #frame de viewer do jogador
        try:
            if(self.app.system =='Windows'):
                hwnd = ctypes.windll.user32.FindWindowW(u"Shell_traywnd", None)
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                taskbar_height = rect.bottom - rect.top
            else:
                taskbar_height = 0 
        except:
            taskbar_height = 0

        self.get_screen_resolution()

        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        x = (self.screen_width // 2) - (self.width // 2)
        y = (self.screen_height // 2) - (self.height // 2) - (taskbar_height//2)

        # Impede que a janela seja redimensionada
        self.root.resizable(False, False)

        # Defina a geometria da janela
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

        #frame
        # Espaçamento entre os frames
        spacer1 = Frame(self.root, width=800, height=10, bg='white')
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
        spacer = Frame(self.root, width=800, height=10)
        spacer.pack()

        # Criando o segundo frame abaixo
        self.frameControl = Frame(self.root, width=800, height=280, bg="white")
        self.frameControl .pack_propagate(False)  # Evita que o frame ajuste seu tamanho automaticamente
        self.frameControl .pack()

        #frame filho do frameControl na esquerda
        self.choseFrame = Frame(self.frameControl, width = 240, height=280, bg = "white")
        self.choseFrame.pack_propagate(False)
        self.choseFrame.grid(row=0,column=0)

        #frame de controles
        self.cButtonsFrame = Frame(self.frameControl, width = 320, height=280, bg="white")
        self.cButtonsFrame.pack_propagate(False)
        self.cButtonsFrame.grid(row=0, column=1)

        #frame de análise
        self.analiseFrame = Frame(self.frameControl, width=240, height=280, bg="white")
        self.analiseFrame.pack_propagate(False)
        self.analiseFrame.grid(row=0, column=3)

    #Método para inicializar os labels
    def initLabels(self):
        #labels para o controle
        self.lChosePlayer=  Label(self.choseFrame, text="Escolher Jogados: ", fg="black", bg="white")
        self.lChosePlayer.grid(row=0,column=0, padx=5, pady =2, sticky="w")
        self.cBoxPlayer= ttk.Combobox(self.choseFrame, values=["Player 1", "Player 2", "Player 3"], state='readonly')
        self.cBoxPlayer.grid(row=0,column=1,padx=5, pady=2, sticky="w")

        #Label para escolher comunicação com o jogador
        self.labelCom = Label(self.choseFrame, text="Modo de comunicação: ", fg = "black", bg ="white")
        self.labelCom.grid(row=1,column=0, padx=5, pady =2, sticky="w")
        self.comBox = ttk.Combobox(self.choseFrame, values=["MQTT","SERIAL"],state="readonly")
        self.comBox.grid(row=1,column=1,padx=5,pady=2,sticky="w")
        self.comBox.bind("<<ComboboxSelected>>",self.show_serial_combobox)

        #label escondido para portas seriais
        self.labelComOptions = Label(self.choseFrame, text="Porta Serial:", fg="black", bg="white")
        self.labelComOptions.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.comBoxSerial = ttk.Combobox(self.choseFrame, state="readonly")
        self.comBoxSerial.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        #label de botões de processamento
        self.btnLabel = Label(self.choseFrame, bg="white")
        self.btnLabel.grid(row=3, column =0 , columnspan =2 , padx=5, pady=2, sticky="w")

        self.btn_save = Button(self.choseFrame, text="Salvar", command=self.save_choices)
        self.btn_save.grid(row=4, column=0, padx=(10,5), pady=5)
        self.btn_start = Button(self.choseFrame, text="Iniciar", command=self.start_processing)
        self.btn_start.grid(row=4, column=1, padx=(5,5),pady =5)

        #Label para escolher um ponto
        self.lChosePoint = Label(self.choseFrame, text="Escolher um ponto", fg="black", bg="white")
        self.lChosePoint.grid(row=5, column=0, padx=5, pady = 2 , sticky="w")
        self.btn_chose_point = Button(self.choseFrame, text="Escolher",command=self.choose_point)
        self.btn_chose_point.grid(row=5, column=1, padx=5, pady=2, sticky="w")

    #método para iniciar processamento e envio
    def init(self):
        i=2

    #método para enviar o comando para o carro executar
    def sendCommand(self):
        i = 3

    #exibir bombox da serial
    def show_serial_combobox(self, event):
        selected_comm = self.comBox.get()
        if selected_comm == "SERIAL":
            self.labelComOptions["state"] = NORMAL
            self.comBoxSerial["state"] = NORMAL
        else:
            self.labelComOptions["state"] = DISABLED
            self.comBoxSerial["state"] = DISABLED

    #salvar configurações
    def save_choices(self):
        print("Escolhas feitas")

    #começar processamento
    def start_processing(self):
        print("Começando processamento")

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
