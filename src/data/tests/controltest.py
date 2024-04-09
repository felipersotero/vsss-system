from tkinter import *
import cv2

def listar_webcams():
    # Lista os dispositivos de vídeo
    dispositivos = []
    for i in range(10):  # Número arbitrário de dispositivos
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            dispositivos.append(f"Webcam {i}")
            cap.release()

    # Mostra os dispositivos em uma janela
    root = Tk()
    root.title("Webcams Disponíveis")
    for i, dispositivo in enumerate(dispositivos):
        label = Label(root, text=dispositivo)
        label.pack()

    root.mainloop()

if __name__ == "__main__":
    listar_webcams()
