import tkinter as tk
from modules import *

class Card:
    def __init__(self, master, title, color):
        self.master = master
        self.title = title
        self.color = color

        self.frame = Frame(master, bg="white")
        self.frame.grid(row=0, column=0)

        self.contentFrame = Frame(self.frame)
        self.contentFrame.grid(row=0, column=0)
        self.imageFrame = Frame(self.frame)
        self.imageFrame.grid(row=0, column=1)

        self.titleLabel = Label(self.contentFrame, text=title, font=("Helvetica", 11), bg="white")
        self.titleLabel.pack()
        self.idLabel = Label(self.contentFrame, text="", font=("Helvetica", 8), bg="white")
        self.idLabel.pack()
        self.positionLabel = Label(self.contentFrame, text="", font=("Helvetica", 8), bg="white")
        self.positionLabel.pack()

        self.canvas = Canvas(self.imageFrame, width=50, height=50)
        self.canvas.pack()

        self.image_path = "src/images/dark_screen.png"
        self.load_image()

    def load_image(self):
        try:
            image = tk.PhotoImage(file=self.image_path)
            self.canvas.create_image(40, 40, anchor=tk.CENTER, image=image)
            self.canvas.image = image
        except tk.TclError:
            print("Erro ao carregar a imagem.")

    def show_image(self, image):
        cv2Img = cv2.cvtColor(image, cv2.COLOR_BGR2RGBA)
        pilImage = Image.fromarray(cv2Img)
        
        # Obter as dimensões atuais da imagem
        width, height = pilImage.size
        
        # Definir o tamanho máximo desejado
        max_width = 50
        max_height = 50
        
        # Calcular a porcentagem de redução com base nas dimensões atuais
        percent_reduction = min(max_width / width, max_height / height)
        
        # Calcular o novo tamanho da imagem
        new_width = int(width * percent_reduction)
        new_height = int(height * percent_reduction)
        
        # Redimensionar a imagem
        #resized = pilImage.resize((new_width, new_height), Image.ANTIALIAS)
        resized = pilImage.resize((new_width, new_height), Image.LANCZOS)
        self.image = ImageTk.PhotoImage(image=resized)
        
        # Calcular as coordenadas para centralizar a imagem
        x = (max_width - new_width) // 2
        y = (max_height - new_height) // 2
    
        self.canvas.create_image(x,y, anchor=NW, image=self.image)

    def set_content(self, id, status, position, radius, image):
        x = str(position[0])
        y = str(position[1])
        r = radius

        if status:
            color = 'green'
        else:
            color = 'red'

        self.idLabel.config(text=f"{id} - {status}", bg=color)
        self.positionLabel.config(text=f"x = {x}, y = {y}\n r = {r}")

        if image is not None:
            self.show_image(image)


class CardInfos:
    def __init__(self, master, title):
        self.master = master
        self.title = title
        self.emulator = None
        
        #Informações que ele irá exibir
        #pegará as informações de tempo de frame, tempo de envio
        #e código de erro
        self.FPS = None
        self.frameTime = None
        self.sendTime = None
        self.timer = None
        self.errorEmulate = None
        self.Mode = None
        self.totalTime = None
        
        self.frame = Frame(self.master, bg="white")
        self.frame.grid(row=0, column=1, sticky="nsew")

        self.title_label = tk.Label(self.frame, text="DESEMPENHO", bg="white", font=("Arial", 12, "bold"))
        self.title_label.grid(row=0, column=0, columnspan=2, sticky="nsew")

        self.texts = {
            "FPS:": tk.StringVar(),                     # quadros por segundo
            "Vision. (ms):": tk.StringVar(),            # tempo para processar imagem
            "Proc. (ms):": tk.StringVar(),               # Tempo total para processar e imprimir
            "Envio (ms):": tk.StringVar(),              # tempo para enviar
            "Timer (s):": tk.StringVar(),               # timer de alta precisão do emulador
            "Error Code:": tk.StringVar(),              # código de erro
            "Modo:": tk.StringVar()                     # modo de emulação atual
        }

        for i, (label_text, var) in enumerate(self.texts.items()):
            label = tk.Label(self.frame, text=label_text, bg="white", font=("Arial", 8, "bold"))
            label.grid(row=i + 1, column=0, sticky="w")
            text = tk.Label(self.frame, textvariable=var, bg="white", font=("Arial", 8, "normal"))
            text.grid(row=i + 1, column=1, sticky="w")
            
        # Configurando a expansão do frame
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=1)
        
    #Atualiza informação
    def updateInfo(self, variable, value):
        #verifica se é um valor válido
        if isinstance(value, (int, float)):
            strValue = f"{value:.2f}"
        elif isinstance(value,(str)):
            strValue = value
        else:
            # Lidar com o caso em que value não é um número
            strValue = "N/A"

        if variable in self.texts:
            self.texts[variable].set(strValue)
        else:
            print("Variável não encontrada.")
        
    #Atualiza contínuamente as informações acessando o objeto emulador
    def update(self):
        self.updateInfo("FPS:", self.emulator.FPStime)
        self.updateInfo("Vision. (ms):",self.emulator.totalTime)
        self.updateInfo("Proc. (ms):",self.emulator.frameTime)
        self.updateInfo("Envio (ms):",self.emulator.sendTime)
        self.updateInfo("Timer (s):",self.emulator.realTime)
        self.updateInfo("Error Code:",self.emulator.errorCode)
        self.updateInfo("Modo:",self.conversionMode(self.emulator.Mode))
        
    #função para setar um mestre
    def setMaster(self, emulator):
        self.emulator = emulator   
        self.update()
    
    #converte o inteiro no modo de execução
    def conversionMode(self, n):
        id = int(n)
        str = ""
        
        if(id == 1):
            str = "Camera"
        elif (id == 2):
            str = "Imagem"
        elif (id == 3):
            str = "Video"
        else:
            str = "Default"
            
        return str
        
if __name__ == "__main__":
    print("Módulo sendo executado como funcao principal")
