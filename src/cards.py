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

        self.titleLabel = Label(self.contentFrame, text=title, font=("Helvetica", 14), bg=color)
        self.titleLabel.pack()
        self.idLabel = Label(self.contentFrame, text="", font=("Helvetica", 10), bg="white")
        self.idLabel.pack()
        self.positionLabel = Label(self.contentFrame, text="", font=("Helvetica", 10), bg="white")
        self.positionLabel.pack()

        self.canvas = Canvas(self.imageFrame, width=80, height=80)
        self.canvas.pack()

        self.image_path = "src/images/dark_screen.png"
        #self.load_image()

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
        max_width = 80
        max_height = 80
        
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

if __name__ == "__main__":
    print("Módulo sendo executado como funcao principal")
