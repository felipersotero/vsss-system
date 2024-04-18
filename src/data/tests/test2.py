import tkinter as tk

class ColorSquare(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master, bg="white")
        self.square_size = 10
        self.status = "parado"
        self.square = tk.Canvas(self, width=self.square_size, height=self.square_size, bd=1, relief="solid", bg="white")
        self.square.pack(side=tk.LEFT, padx=5)
        self.text_var = tk.StringVar()
        self.text_var.set("Parado")
        self.text_label = tk.Label(self, textvariable=self.text_var, bg="white")
        self.text_label.pack(side=tk.LEFT)
        self.button = tk.Button(self, text="Iniciar", command=self.toggle_status)
        self.button.pack(side=tk.LEFT, padx=5)

    def toggle_status(self):
        if self.status == True:
            self.set_status("parado")
        else:
            self.set_status("executando")

    def set_status(self, status):
        self.status = status
        if status == True:
            self.square.config(bg="green")
            self.text_var.set("Em execução")
            self.button.config(text="Parar")
        elif status == False:
            self.square.config(bg="red")
            self.text_var.set("Parado")
            self.button.config(text="Iniciar")

# Exemplo de uso
root = tk.Tk()
square_frame = ColorSquare(root)
square_frame.pack()
root.mainloop()
