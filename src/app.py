from modules import *
from settingsMenu import settingsMenu
from viewer import MyViewer, WindowsViewer
from emulator import Emulator
from cards import *
from control import *
from communication import *
from objects import *
from windowControl import *

execution = False

class App:
    def __init__(self):
        root = Tk()
        self.root = root
        self.menu = None
        self.menuTop= None
        
        #verifica qual o sistema operacional
        self.system = platform.system()
        self.release = platform.release()
        self.version = platform.version()

        #variáveis de tamanho da tela do computador
        self.screen_height = None
        self.screen_width = None

        #tamanho da janela
        self.width = 1100
        self.height = 750

        self.configure_window() #self.window()

        self.create_main_frames() #self.frame_window()
        self.create_settings_frame() #self.frame_config()

        self.IdFrame = 2
        self.widgets_settings_frame()
        self.widgets_emulate_frame()
        self.widgets_images_frame()

        self.viewer  = MyViewer(self.tab1)
        self.debugField = MyViewer(self.tab2)
        self.debugObject = MyViewer(self.tab3)
        self.debugPlayers = MyViewer(self.tab4)
        self.debugTeam = MyViewer(self.tab5)
        self.result = MyViewer(self.tab6)

        self.cards = []
        for i in range(6):
            self.card = Card(self.players_infos, f"Jogador {i+1}", "white")
            self.cards.append(self.card)

        for i, card in enumerate(self.cards):
            card.frame.grid(row=i // 3, column=i % 3, padx=10, pady=10)

        #bloco de informações do emulador
        self.infosEmulator = CardInfos(self.infos_emulate,'Informações')
        
        #criando o objeto emulador
        self.emulator = Emulator(self)

        self.infosEmulator.setMaster(self.emulator)
        
        #já inicia carregando as informações antigas do emulador
        self.emulator.load_vars()

        #configurando um menu na interface
        self.configure_menu()

        #inicia looping principal
        root.mainloop()
    
    #configarando menu

    #configurando a janela do projeto
    def configure_window(self):
        #propriedades
        self.root.title("PINBOT - VSSS")
        self.root.configure(background="#dfe3ee")
        self.root.geometry("1100x750")
        self.root.resizable(False, False)

        #colocando ícone
        try:
            if(self.system == 'Windows'):
                self.root.iconbitmap('src/data/icon.ico')
            elif(self.system =='Linux'):
                self.root.iconbitmap('src/data/icon.ico')
            else:
                self.root.iconbitmap('src/data/icon.ico')
        except:
            print("[APP]: Problemas em acessar o ícone")
                # Calcula as dimensões da janela
            
        #posicionando a janela no centro
        self.center_window()
    
    def create_main_frames(self):
        self.settings_frame = Frame(self.root, bg="white")
        self.settings_frame.place(relx=0.01,rely=0.015, relwidth=0.29,relheight=0.97)
        
        self.images_frame = Frame(self.root,bg="white")
        self.images_frame.place(relx=0.31,rely=0.015, relwidth=0.68,relheight=0.68)
        
        self.vision_data_frame = Frame(self.root, bg="black")
        self.vision_data_frame.place(relx=0.31,rely=0.705, relwidth=0.68,relheight=0.28)
        
        #criando um frame do tipo grid
        self.players_infos = Frame(self.vision_data_frame, bg="white")
        self.players_infos.place(relx=0,rely=0, relwidth=0.76,relheight=1)
        
        #criando um frame para as informações
        self.infos_emulate = Frame(self.vision_data_frame, bg="white")
        self.infos_emulate.place(relx=0.76,rely=0, relwidth=1,relheight=1)

        
    def create_settings_frame(self):
        self.set_settings_frame=Frame(self.settings_frame, bg="white")
        self.set_settings_frame.place(relx=0,rely=0, relwidth=1,relheight=0.90)

        self.emulate_frame=Frame(self.settings_frame, bg="white")
        self.emulate_frame.place(relx=0,rely=0.90, relwidth=1,relheight=0.10)

    def widgets_settings_frame(self):
        self.menu = settingsMenu(self, self.set_settings_frame)
        self.menu.pack(fill=BOTH, expand=True)

        self.exec = execution

        if(self.exec):
            print('Configurações de Fábrica')
            self.build_tree_menu()
            self.exec = False
            try:
                self.menu.save_to_json('config')
            except:
                print('por algum motivo, não foi possível salvar o json')
        else:
            try:
                print('Carregando arquivo da memoria')
                self.menu.load_from_json_file('config.json')
                print("carregadas sucesso.")
            except:
                print("Não foi possível puxar o arquivo da memória. Será reiniciado o sistema")
                self.build_tree_menu()
                self.exec = True
                print('Configurações de Fábrica')
                self.menu.save_to_json('config')

        self.save_label = Label(self.set_settings_frame, text="Salvar as configurações")
        self.save_label.place(relx=0.1, rely=0.85, relwidth=0.8, relheight=0.05)
        self.save_label.config(fg="black",bg="white")
        self.save_button = Button(self.set_settings_frame, text='Salvar', command=self.save_config)
        self.save_button.place(relx=0.3, rely=0.90, relwidth=0.4, relheight=0.05)

    def widgets_emulate_frame(self):
        self.label_run_emulate = Label(self.emulate_frame,text="Estado da Emulação")
        self.label_run_emulate.pack(fill=BOTH, expand=1)

        self.btn_run = Button(self.emulate_frame, text="Executar", width=2,height=1,bg="darkgray", command=self.init_emulate)
        self.btn_run.pack(fill=BOTH, expand=1)

        self.btn_stop= Button(self.emulate_frame, text="Parar", width=2,height=1,bg="darkgray", command=self.stop_emulate)
        self.btn_stop.pack_forget()

    def widgets_images_frame(self):
        self.tabs = ttk.Notebook(self.images_frame)
        self.tab1 = Frame(self.tabs)
        self.tab2 = Frame(self.tabs)
        self.tab3 = Frame(self.tabs)
        self.tab4 = Frame(self.tabs)
        self.tab5 = Frame(self.tabs)
        self.tab6 = Frame(self.tabs)

        self.tab1.configure(background="black")
        self.tab2.configure(background="black")
        self.tab3.configure(background="black")
        self.tab4.configure(background="black")
        self.tab5.configure(background="black")
        self.tab6.configure(background="black")

        self.tabs.add(self.tab1, text="Imagem")
        self.tabs.add(self.tab2, text="Debug campo")
        self.tabs.add(self.tab3, text="Debug bola")
        self.tabs.add(self.tab4, text="Debug jogadores")
        self.tabs.add(self.tab5, text="Debug time")
        self.tabs.add(self.tab6, text="Resultado")

        self.tabs.place(relx=0, rely=0, relwidth=1, relheight=1)

    def build_tree_menu(self):

        SysVision = self.menu.add_node('','SysVisPinbot','Sistema de Visão', value='')

        EntryData=self.menu.add_node(SysVision,'EntryData','Entrada de dados', value='')
        self.menu.add_node(EntryData,'CamPth','Câmera USB', value='---')
        self.menu.add_node(EntryData,'ImagePath','Imagem Path', value='---')
        self.menu.add_node(EntryData,'VideoPath','Vídeo Path', value='---')
        self.menu.add_node(EntryData,'UseMode','Modo de Uso', value='Camera')

        AlgRec = self.menu.add_node(SysVision,'Algoritm','Calibração do algorítmo',value='')
        self.menu.add_node(AlgRec,'offsetW','Borda da janela', value='10')
        self.menu.add_node(AlgRec,'offSetErode','offSet da Erosão', value='3')
        self.menu.add_node(AlgRec,'Threshold','Binarização Threshold', value='245')
        self.menu.add_node(AlgRec,'DimMatrx','Dim. Matriz TOPHAT', value='25')
        self.menu.add_node(AlgRec,'DebugAlg','Debug do Algorítmo', value='False')     

        FieldSize=self.menu.add_node(SysVision,'fieldDimensions','Dimensões do campo (cm)', value='')
        self.menu.add_node(FieldSize,'fieldWidth','Largura (menor)', value='130')
        self.menu.add_node(FieldSize,'fieldHeight','Comprimento (maior)', value='150')

        CalColor=self.menu.add_node(SysVision,'ColorCalibration','Calibração das Cores', value='')
        self.menu.add_node(CalColor,'mainColor','Cor principal', value='[ 90 128 128]')
        self.menu.add_node(CalColor,'j1Color1','J1 Cor 1', value='[ 90 128 128]')
        self.menu.add_node(CalColor,'j1Color2','J1 Cor 2', value='[ 90 128 128]')
        self.menu.add_node(CalColor,'j2Color1','J2 Cor 1', value='[ 90 128 128]')
        self.menu.add_node(CalColor,'j2Color2','J2 Cor 2', value='[ 90 128 128]')
        self.menu.add_node(CalColor,'j3Color1','J3 Cor 1', value='[ 90 128 128]')
        self.menu.add_node(CalColor,'j3Color2','J3 Cor 2', value='[ 90 128 128]')
        self.menu.add_node(CalColor,'enemyColor','Cor inimigos', value='[ 90 128 128]')   
        self.menu.add_node(CalColor,'ballColor','Cor da bola', value='[9 93 220]')
        
        ConfigEmulator=self.menu.add_node(SysVision,'EmulatorConfig','Configurações do Emulador', value='')
        self.menu.add_node(ConfigEmulator,'Debug','Debug', value='False')
        self.menu.add_node(ConfigEmulator,'Comunicação','Comunicação', value='nenhuma')
        self.menu.add_node(ConfigEmulator,'Porta Serial','Porta Serial',value = ' ')
        self.menu.add_node(ConfigEmulator,'CUDA','CUDA', value='False')
        self.menu.add_node(ConfigEmulator,'ExectState','Estado de Execução', value='Parado')

    def save_config(self):
        self.data = self.menu.get_tree_data()
        with open('config.json', 'w',encoding="utf-8") as f:
            json.dump(self.data, f,ensure_ascii=False)
        print('[APP] config salvas com sucesso!')
        self.emulator.load_vars()

    def init_emulate(self):
        print("[APP] Emulação Iniciada")
        self.emulator.load_vars()
        self.emulator.show_variables()
        
        self.menu.save_to_json('config')

        self.emulator.init()
        self.menu.att_node_id('I01F','Em execução.')
        self.menu.save_to_json('config')

    def stop_emulate(self):
        self.emulator.stop()
        self.btn_stop.pack_forget()
        self.btn_run.pack(fill=BOTH, expand=1)
        
        self.menu.att_node_id('I01F','Parado')
        self.menu.save_to_json('config')

    #pegar as informações da tela
    def get_screen_resolution(self):
        #funcionando no windows
        if(self.system == 'Windows'):
            user32 = ctypes.windll.user32
            self.screen_width = user32.GetSystemMetrics(0)
            self.screen_height = user32.GetSystemMetrics(1)
        
        #funcionando no linux
        elif(self.system == 'Linux'):
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


    #centralizando a janela na tela
    def center_window(self):
        try:
            if(self.system =='Windows'):
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
    
    #configurando a mensagem de erro
    def show_error_message(self, message):
        messagebox.showerror("Erro", message)
    
    #configurando o menu
    def configure_menu(self):
        #criando o menu
        self.menuTop = Menu(self.root)
        self.root.config(menu=self.menuTop)

        #criando menu de informações
        self.infoMenu = Menu(self.menuTop, tearoff=0)
        self.menuTop.add_cascade(label='Informações',menu=self.infoMenu)
        self.infoMenu.add_command(label="Abrir informações", command=None)
        self.infoMenu.add_separator()

        #criando menus arquivo
        self.arqMenu = Menu(self.menuTop, tearoff=0)
        self.menuTop.add_cascade(label='Arquivos',menu=self.arqMenu)
        self.arqMenu.add_command(label="Abrir arquivo de backup", command=None)
        self.arqMenu.add_command(label="Salvar backup", command=None)
        self.arqMenu.add_command(label="Retornar às configurações de fábrica", command=None)
        self.arqMenu.add_separator()

        #criando menu de jogadores
        self.players= Menu(self.menuTop, tearoff=0)
        self.menuTop.add_cascade(label='Jogadores',menu=self.players)
        self.players.add_command(label="Abrir controle de jogadores",command = self.open_player_control)
        self.players.add_separator()

        #criando menu de ajuda
        self.helpMenu = Menu(self.menuTop, tearoff=0)
        self.menuTop.add_cascade(label='Ajuda',menu=self.helpMenu)
        self.helpMenu.add_command(label='Sequência de uso', command=None)
        self.helpMenu.add_separator()

    #funções do menu para utilizar
    

    #função de controle do jogador
    def open_player_control(self):
        #apenas abre se o jogador tiver escolhido modo câmera
        self.emulator.load_vars()

        #verifica então o modo
        if(self.emulator.Mode == MODE_USB_CAM ):
            print("Entrou com modo câmera e o emulador existe")
            self.popUp = ControlWindow(self.root, self, self.emulator)
        else:
            #abre uma janela de popup falando que precisa estar configurada a camera
            self.show_error_message("Necessário estar no modo câmera")
            

if __name__ == "__main__":
    app = App()