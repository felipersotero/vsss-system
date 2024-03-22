from tkinter import *
from tkinter import ttk

class ControlWindow:
    def __init__(self, master):
        self.root = master
        self.root.title("Controle Manual")
        
        self.frameControl = Frame(self.root, bg="white")
        self.frameControl.pack(padx=10, pady=10)

        self.cTitle = Frame(self.frameControl, bg="white")
        self.cTitle.pack(padx=10, pady=10)

        self.lblTitle = Label(self.cTitle, text="Controle Manual", bg="white")
        self.lblTitle.pack()

        self.cBModule = Frame(self.frameControl, bg="white")
        self.cBModule.pack(padx=10, pady=10)

        self.lblSpeed = Label(self.cBModule, text="Velocidade:", bg="white")
        self.lblSpeed.grid(row=0, column=0, padx=5, pady=5)

        self.scaleSpeed = Scale(self.cBModule, from_=0, to=1023, orient=HORIZONTAL)
        self.scaleSpeed.grid(row=1, column=0, padx=5, pady=5)

        self.lblAngle = Label(self.cBModule, text="Ângulo:", bg="white")
        self.lblAngle.grid(row=2, column=0, padx=5, pady=5)

        self.scaleAngle = Scale(self.cBModule, from_=-180, to=180, orient=HORIZONTAL)
        self.scaleAngle.grid(row=3, column=0, padx=5, pady=5)

        self.btnSend = Button(self.cBModule, text="Send", command=self.send_angle)
        self.btnSend.grid(row=3, column=1, padx=5, pady=5)

        self.cBVelocity = Frame(self.frameControl, bg="white")
        self.cBVelocity.pack(padx=10, pady=10)

        directions = ["NW", "N", "NE", "W", "Stop", "E", "SW", "S", "SE"]
        row_indices = [0, 0, 0, 1, 1, 1, 2, 2, 2]
        col_indices = [0, 1, 2, 0, 1, 2, 0, 1, 2]

        for direction, row, col in zip(directions, row_indices, col_indices):
            btn = Button(self.cBVelocity, text=direction, width=5, height=2)  # Definindo o tamanho dos botões
            btn.grid(row=row, column=col, padx=5, pady=5)

    def send_angle(self):
        angle = self.scaleAngle.get()
        print("Sending angle:", angle)

if __name__ == "__main__":
    root = Tk()
    app = ControlWindow(root)
    root.mainloop()
