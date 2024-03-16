from modules import *

class settingsMenu(Frame):
    def __init__(self, App, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = App
        self.tree = Treeview(self, columns=('Valor',))
        self.tree.heading('#0',text="Variável")
        self.tree.heading('Valor', text='Valor')
        self.tree.column('Valor',stretch=False,minwidth=50, width=100)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.pack(fill=BOTH, expand=True)
        self.nodes={}
        # self.color_editables = ['Cor principal', 'J1 Cor 1', 'J1 Cor 2', 'J2 Cor 1', 'J2 Cor 2', 'J3 Cor 1', 'J3 Cor 2', 'Cor inimigos', 'Cor da bola']

    #Adicionando um nó
    def add_node(self, parent,id, name, value):
        if not self.tree:
            return
        node_id = self.tree.insert(parent,"end", text=name,values=(value,))
        self.nodes[node_id] = value
        return node_id

    def att_node_id(self,id, value):
        self.tree.set(id,'Valor',value)
        self.nodes[id] = value
        self.tree.item(id,tags=())

    def on_double_click  (self, event):
        editable_items = ['Câmera USB','Vídeo Path','Cor','Cor Principal T1', 'Cor Principal T2','T1_robo 1','T1_robo 2','T1_robo 3','T2_robo 1','T2_robo 2','T2_robo 3','Borda da janela','offSet da Erosão','Binarização Threshold','Dim. Matriz TOPHAT', 'Largura (menor)', 'Comprimento (maior)']
        #color_editables = ["Calibração das Cores"]
        color_editables = ['Cor principal', 'J1 Cor 1', 'J1 Cor 2', 'J2 Cor 1', 'J2 Cor 2', 'J3 Cor 1', 'J3 Cor 2', 'Cor inimigos', 'Cor da bola']
        item = self.tree.focus()
        if item:
            if self.tree.item(item,'text') in color_editables:
                #Caso isso aconteça, ele irá exibir um frame para modificar as cores e verificar o código
                # print("Calibrar a cor foi clicada")
                # self.tree.tag_configure('custom_color', background='lightblue')
                # self.tree.item(item, tags=('custom_color'))
                self.open_color_pick_window(item)

            elif self.tree.item(item, 'text') == 'Modo de Uso':
                self.open_mode_window(self.tree, item)

            elif self.tree.item(item, 'text') == 'Imagem Path':
                self.load_file(self.tree, item)

            elif self.tree.item(item, 'text') == 'Vídeo Path':
                self.load_file(self.tree, item)

            elif self.tree.item(item, 'text') == 'Debug':
                self.open_select_window(self.tree, item)
            
            elif self.tree.item(item, 'text') == 'CUDA':
                self.open_select_window(self.tree, item)
                
            # selecionando modo de conexão do computador
            elif self.tree.item(item, 'text') == 'Comunicação':
                self.open_window_connection(self.tree, item)

            elif self.tree.item(item, 'text') in editable_items:
                self.tree.item(item, tags=('edit',))
                entry = simpledialog.askstring("Editar variável", "Adicione o novo valor da variável")
                if entry is not None:
                    self.tree.set(item,'Valor',entry)
                    self.nodes[item] = entry
                self.tree.item(item,tags=())
            else:
                #Em caso negativo, ele não apenas irá retornar à configuração padrão
                print("Escolher a cor não foi encontrada")
                #self.app_edit.pack_forget()
                
                #Modifica à variável de estado para colocar os dados

    def load_file(self, tree, item):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.tree.set(item,'Valor', file_path)
            self.nodes[item] = file_path

    def open_mode_window(self, tree, item):
        self.item = item
        self.tree = tree

        new_window = Toplevel(self.tree)
        new_window.title("Seleção de modo")
        self.root = new_window

        try:
            if(self.app.system == 'Windows'):
                self.root.iconbitmap('src/data/icon.ico')
            elif(self.app.system =='Linux'):
                self.root.iconbitmap('src/data/icon.ico')
            else:
                self.root.iconbitmap('src/data/icon.ico')
        except:
            print("[APP]: Problemas em acessar o ícone")

        def update_value():
            mode_picked = pick_var.get()
            self.tree.set(item,'Valor',mode_picked)
            self.nodes[item] = mode_picked
            new_window.destroy()

        options = ['camera', 'imagem', 'video']
        texts = ['Câmera', 'Imagem', 'Vídeo']

        pick_var = StringVar()

        for i in range(3):
            radiobutton = ttk.Radiobutton(new_window, text=texts[i], variable=pick_var, value=options[i])
            radiobutton.pack(padx=10, pady=5)

        select_button = Button(new_window, text="Confirmar", command=update_value)
        select_button.pack(pady=10)

    #Janela se seleção true false
    def open_select_window(self, tree, item):
        self.item = item
        self.tree = tree

        new_window = Toplevel(self.tree)
        new_window.title("Seleção de modo")
        self.root = new_window

        try:
            if(self.app.system == 'Windows'):
                self.root.iconbitmap('src/data/icon.ico')
            elif(self.app.system =='Linux'):
                self.root.iconbitmap('src/data/icon.ico')
            else:
                self.root.iconbitmap('src/data/icon.ico')
        except:
            print("[APP]: Problemas em acessar o ícone")

        def update_value():
            mode_picked = pick_var.get()
            self.tree.set(item,'Valor',mode_picked)
            self.nodes[item] = mode_picked
            new_window.destroy()

        options = ['true', 'false']
        texts = ['Ativado', 'Desativado']

        pick_var = StringVar()

        for i in range(2):
            radiobutton = ttk.Radiobutton(new_window, text=texts[i], variable=pick_var, value=options[i])
            radiobutton.pack(padx=10, pady=5)

        select_button = Button(new_window, text="Confirmar", command=update_value)
        select_button.pack(pady=10)

        #Janela de seleção do modo de conexão do algorítmo
    
    
    #Selecionar tipo de conexão
    def open_window_connection(self,tree, item):
        #definindo a janela
        new_window = Toplevel(self.tree)
        new_window.title ("Seleção tipo de comunicação")
        self.root = new_window

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
        
        #frame principal
        frame = ttk.Frame(self.root)
        frame.pack(padx = 10, pady = 10)

        #label de seleção de comunicação
        label_comm = ttk.Label(frame, text="Selecione o tipo de comunicação:")
        label_comm.grid(row=0, column=0, padx=5, pady=5)

        # Combobox para seleção de comunicação
        combobox_comm = ttk.Combobox(frame, values=["MQTT", "SERIAL","Nenhuma"])
        combobox_comm.grid(row=0, column=1, padx=5, pady=5)

        # Label de seleção de porta serial
        label_serial = ttk.Label(frame, text="Selecione a porta serial:")
        label_serial.grid(row=1, column=0, padx=5, pady=5)
        label_serial.grid_remove()  # Inicialmente oculto

        # Combobox para seleção de porta serial
        combobox_serial = ttk.Combobox(frame)
        combobox_serial.grid(row=1, column=1, padx=5, pady=5)
        combobox_serial.grid_remove()  # Inicialmente oculto)

        #exibe as seriais conectadas
        def populate_serial_ports():
            serial_ports = [port.device for port in serial.tools.list_ports.comports()]
            combobox_serial["values"] = serial_ports
            combobox_serial["state"] = "readonly"  # Define o Combobox como somente leitura


        #mostra as opções de entrada serial
        def show_serial_options(event):
            selected_comm = combobox_comm.get()
            if selected_comm == "SERIAL":
                label_serial.grid()
                combobox_serial.grid()
                populate_serial_ports()

            else:
                label_serial.grid_remove()
                combobox_serial.grid_remove()

        #atualiza as portas seriais em tempo real
        def update_serial_ports():
            populate_serial_ports()
            # Chama esta função novamente após 1000 milissegundos (1 segundo)
            self.root.after(1000, update_serial_ports)
        
        #chama esse método para atualizar
        update_serial_ports()

        #destroi janela
        def destroy_window():
            self.root.destroy()

        #confirma seleção
        def on_confirm():
            selected_comm = combobox_comm.get()
            selected_port = combobox_serial.get() if selected_comm == "SERIAL" else None

            if selected_comm == "MQTT":
                self.tree.set(item, 'Valor', selected_comm)
                self.tree.set('I01D', 'Valor', "")
                self.nodes[item] = selected_comm
                self.nodes['I01D'] = ""
                destroy_window()
            elif selected_comm == "SERIAL":
                if selected_comm == "SERIAL" and not selected_port:
                    messagebox.showerror("Erro", "Selecione uma porta serial!")
                else:
                    self.tree.set(item, 'Valor', selected_comm)
                    self.tree.set('I01D', 'Valor', selected_port)
                    self.nodes[item] = selected_comm
                    self.nodes['I01D'] = selected_port
                    destroy_window()

            elif selected_comm == "Nenhuma":
                    self.tree.set(item, 'Valor', selected_comm)
                    self.tree.set('I01D', 'Valor', "")
                    self.nodes[item] = selected_comm
                    self.nodes['I01D'] = ""
                    destroy_window()
            else:
                    #Provavelmente foi um erro, então mantem o padrão
                    self.tree.set(item, 'Valor', "Nenhuma")
                    self.tree.set('I01D', 'Valor', "")
                    self.nodes[item] = "Nenhuma"
                    self.nodes['I01D'] = ""
                    destroy_window()



        #definindo callbacks
        combobox_comm.bind("<<ComboboxSelected>>", show_serial_options)

        # Botão de voltar
        button_back = ttk.Button(frame, text="Voltar", command=destroy_window)
        button_back.grid(row=2, column=0, padx=5, pady=5)

        # Botão de confirmar
        button_confirm = ttk.Button(frame, text="Confirmar", command=on_confirm)
        button_confirm.grid(row=2, column=1, padx=5, pady=5)
        
        
    #janela de seleção de cores
    def open_color_pick_window(self, item):
        self.mode = self.tree.item('I006','value')[0]
        self.imgPath = self.tree.item('I004','value')[0]
        self.camPath = self.tree.item('I003','value')[0]
        #print(self.mode)

        new_window = Toplevel(self.tree)
        new_window.title("Seleção de cores")
        self.root = new_window

        try:
            if(self.app.system == 'Windows'):
                self.root.iconbitmap('src/data/icon.ico')
            elif(self.app.system =='Linux'):
                self.root.iconbitmap('src/data/icon.ico')
            else:
                self.root.iconbitmap('src/data/icon.ico')
        except:
            print("[APP]: Problemas em acessar o ícone")

        self.root.resizable(False, False)#Não permitindo mudar
        
        #objeto de captura
        self.cap = None

        def close_window():
            if self.mode == "camera": self.cap.release()
            self.root.destroy()
            self.cap = None

        #adiciona um protocolo a new_window para desligar a câmera
        new_window.protocol("WM_DELETE_WINDOW", close_window)

        def update_color(val=None):
            h = hue_scale.get()
            s = saturation_scale.get()
            v = value_scale.get()

            hsv_color = np.array([h, s, v], dtype=np.uint8)
            bgr_color = cv2.cvtColor(np.uint8([[hsv_color]]), cv2.COLOR_HSV2BGR)
            rgb_color = rgb_to_hex(bgr_color[0, 0, :])

            color_display.configure(bg=rgb_color)

        def rgb_to_hex(rgb):
            return f'#{rgb[2]:02X}{rgb[1]:02X}{rgb[0]:02X}'
        
        def pick_color():
            hsv_color = get_color()
            #messagebox.showinfo(title="Color Picker", message=str(hsv_color))
            self.tree.set(item,'Valor',hsv_color)
            self.nodes[item] = hsv_color

            # bgr_color = cv2.cvtColor(np.uint8([[hsv_color]]), cv2.COLOR_HSV2BGR)
            # rgb_color = rgb_to_hex(bgr_color[0, 0, :])

            # self.tree.tag_configure('custom_color', background=rgb_color)
            # self.tree.item(item, tags=('custom_color'))

            close_window()

        def get_color():
            h = hue_scale.get()
            s = saturation_scale.get()
            v = value_scale.get()
            hsv_color = np.array([h, s, v], dtype=np.uint8)

            return hsv_color

        def string_to_int_array(array):
            values = array.strip("[]").split()
            int_array = list(map(int, values))

            return int_array
        
        close_button = Button(new_window, text="Voltar", command=close_window)
        close_button.pack(pady=10)

        show_button = Button(self.root, text="Selecionar cor", command=pick_color)
        show_button.pack()

        current_hsv = string_to_int_array(self.tree.item(item, 'value')[0])

        hue_initial = current_hsv[0]
        saturation_initial = current_hsv[1]
        value_initial = current_hsv[2]

        hue_label = Label(self.root, text="Matiz (H)")
        hue_label.pack()
        hue_scale = Scale(self.root, from_=0, to=179, orient="horizontal", command=update_color, length=300)
        hue_scale.set(hue_initial)  # Valor inicial
        hue_scale.pack()

        saturation_label = Label(self.root, text="Saturação (S)")
        saturation_label.pack()
        saturation_scale = Scale(self.root, from_=0, to=255, orient="horizontal", command=update_color, length=300)
        saturation_scale.set(saturation_initial)  # Valor inicial
        saturation_scale.pack()

        value_label = Label(self.root, text="Valor (V)")
        value_label.pack()
        value_scale = Scale(self.root, from_=0, to=255, orient="horizontal", command=update_color, length=300)
        value_scale.set(value_initial)  # Valor inicial
        value_scale.pack()

        # Criação da área de exibição da cor em tempo real
        color_display = Label(self.root, text="Cor Definida", width=10, height=2, bg="gray")
        color_display.pack()

        # Criação da área de exibição da imagem original (quadro da webcam)
        original_frame_label = Label(self.root, text="Imagem Original")
        original_frame_label.pack()

        # Criação da área de exibição da máscara da cor selecionada
        masked_frame_label = Label(self.root, text="Imagem Filtrada")
        masked_frame_label.pack()

        if self.tree.item(item, 'text') == 'Cor da bola':
            hue_tolerance = 6
        else:
            hue_tolerance = 10
        saturation_tolerance = 50
        value_tolerance = 50

        image_width = 300
        image_height = 150

        #Funções para ler imagem ou capturar vídeo
        # Função para ler imagem
        if self.mode == "imagem":
            def capture_image():
                frame = cv2.imread(self.imgPath)
                frame = cv2.resize(frame, (image_width, image_height))
                hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                # Criação da máscara da cor selecionada
                h = hue_scale.get()
                s = saturation_scale.get()
                v = value_scale.get()
                lower_bound = np.array([h - hue_tolerance, max(0, s - saturation_tolerance), max(0, v - value_tolerance)])
                upper_bound = np.array([h + hue_tolerance, min(255, s + saturation_tolerance), min(255, v + value_tolerance)])
                mask = cv2.inRange(hsv_frame, lower_bound, upper_bound)

                # Atualiza a máscara na tela
                masked_frame = cv2.bitwise_and(frame, frame, mask=mask)
                masked_frame_rgb = cv2.cvtColor(masked_frame, cv2.COLOR_BGR2RGB)
                masked_frame_label.img = ImageTk.PhotoImage(image=Image.fromarray(masked_frame_rgb))
                masked_frame_label.config(image=masked_frame_label.img)

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                original_frame_label.img = ImageTk.PhotoImage(image=Image.fromarray(frame_rgb))
                original_frame_label.config(image=original_frame_label.img)
                self.root.after(10, capture_image)
            self.root.after(10, capture_image)

        # Função para capturar vídeo da webcam
        if self.mode == "camera":
            # Inicializa a captura de vídeo da webcam
            try:
                self.cap = cv2.VideoCapture(int(self.camPath))  # 0 representa a primeira câmera disponível
            except:
                try:
                    self.cap = cv2.VideoCapture(int(0))
                except:
                    print("[APP]: Camera não encontrada")

            # Captura um quadro inicial para obter informações de tamanho
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.resize(frame, (image_width, image_height))
                hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            def capture_video():
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.resize(frame, (image_width, image_height))
                    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                    # Criação da máscara da cor selecionada
                    h = hue_scale.get()
                    s = saturation_scale.get()
                    v = value_scale.get()
                    lower_bound = np.array([h - hue_tolerance, max(0, s - saturation_tolerance), max(0, v - value_tolerance)])
                    upper_bound = np.array([h + hue_tolerance, min(255, s + saturation_tolerance), min(255, v + value_tolerance)])
                    mask = cv2.inRange(hsv_frame, lower_bound, upper_bound)

                    # Atualiza a máscara na tela
                    masked_frame = cv2.bitwise_and(frame, frame, mask=mask)
                    masked_frame_rgb = cv2.cvtColor(masked_frame, cv2.COLOR_BGR2RGB)
                    masked_frame_label.img = ImageTk.PhotoImage(image=Image.fromarray(masked_frame_rgb))
                    masked_frame_label.config(image=masked_frame_label.img)

                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    original_frame_label.img = ImageTk.PhotoImage(image=Image.fromarray(frame_rgb))
                    original_frame_label.config(image=original_frame_label.img)

                    self.root.after(10, capture_video)
            self.root.after(10, capture_video)
            #self.root.mainloop()

    #Adquirindo os dados com o get_tree_data, é uma função recursiva
    def get_tree_data(self, node_id=''):
        if node_id == '':
            children = self.tree.get_children()
        else:
            children = self.tree.get_children(node_id)

        data = {}
        for child in children:
            item_id = child
            name = self.tree.item(child, 'text')
            value = self.tree.item(child, 'values')
            data[item_id] = {"name": name, "value": value, "children": self.get_tree_data(child)}
        
        return data
    
    def save_to_json(self, filename):
        data = self.get_tree_data()
        with open(filename + '.json', "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False)

    # Método para carregar a TreeView a partir de um arquivo JSON
    def load_from_json(self, node):
        name = node.get('name')
        value = node.get('value')
        children = node.get('children')

        item_id = self.tree.insert('', 'end', text=name, values=value)

        # self.tree.tag_configure('custom_color', background='lightblue')
        # self.tree.item(item_id, tags=('custom_color'))

        if children:
            for child in children.values():
                self.load_from_json_recursive(item_id, child)
    
    def rgb_to_hex(rgb):
        return f'#{rgb[2]:02X}{rgb[1]:02X}{rgb[0]:02X}'
    
    #Carrega dados de um arquivo json
    def load_from_json_recursive(self, parent_id, node):
        name = node.get('name')
        value = node.get('value')
        children = node.get('children')

        item_id = self.tree.insert(parent_id, 'end', text=name, values=value)


        # if self.tree.item(item_id,'text') in self.color_editables:

        #     bgr_color = cv2.cvtColor(np.uint8([[value]]), cv2.COLOR_HSV2BGR)
        #     rgb_color = self.rgb_to_hex(bgr_color[0, 0, :])

        #     self.tree.tag_configure('custom_color', background=rgb_color)
        #     self.tree.item(item_id, tags=('custom_color'))
    
        # self.tree.tag_configure('custom_color', background='lightblue')
        # self.tree.item(item_id, tags=('custom color'))
        
        if children:
            for child in children.values():
                self.load_from_json_recursive(item_id, child)

    #Carrega configurações para um arquivo json
    def load_from_json_file(self, filename):
        with open(filename, 'r',encoding='utf-8') as file:
            data = json.load(file)

        root_node = data.get('I001')
        self.load_from_json(root_node)
