import tkinter as tk
from tkinter import ttk
import serial.tools.list_ports

class TempWindow:
    def __init__(self, parent):
        self.parent = parent
        self.parent.title("Selecionar tipo de comunicação")

        # Frame principal
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(padx=10, pady=10)

        # Label de seleção de comunicação
        self.label_comm = ttk.Label(self.frame, text="Selecione o tipo de comunicação:")
        self.label_comm.grid(row=0, column=0, padx=5, pady=5)

        # Combobox para seleção de comunicação
        self.combobox_comm = ttk.Combobox(self.frame, values=["MQTT", "SERIAL","Nenhuma"])
        self.combobox_comm.grid(row=0, column=1, padx=5, pady=5)
        self.combobox_comm.bind("<<ComboboxSelected>>", self.show_serial_options)

        # Label de seleção de porta serial
        self.label_serial = ttk.Label(self.frame, text="Selecione a porta serial:")
        self.label_serial.grid(row=1, column=0, padx=5, pady=5)
        self.label_serial.grid_remove()  # Inicialmente oculto

        # Combobox para seleção de porta serial
        self.combobox_serial = ttk.Combobox(self.frame)
        self.combobox_serial.grid(row=1, column=1, padx=5, pady=5)
        self.combobox_serial.grid_remove()  # Inicialmente oculto

        # Botão de voltar
        self.button_back = ttk.Button(self.frame, text="Voltar", command=self.destroy_window)
        self.button_back.grid(row=2, column=0, padx=5, pady=5)

        # Botão de confirmar
        self.button_confirm = ttk.Button(self.frame, text="Confirmar", command=self.on_confirm)
        self.button_confirm.grid(row=2, column=1, padx=5, pady=5)

    def show_serial_options(self, event):
        selected_comm = self.combobox_comm.get()
        if selected_comm == "SERIAL":
            self.label_serial.grid()
            self.combobox_serial.grid()
            self.populate_serial_ports()
        else:
            self.label_serial.grid_remove()
            self.combobox_serial.grid_remove()

    def populate_serial_ports(self):
        serial_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.combobox_serial["values"] = serial_ports

    def destroy_window(self):
        self.parent.destroy()

    def on_confirm(self):
        selected_comm = self.combobox_comm.get()
        selected_port = self.combobox_serial.get() if selected_comm == "SERIAL" else None
        print("Comunicação selecionada:", selected_comm)
        print("Porta serial selecionada:", selected_port)
        # Adicione aqui a lógica que deseja executar ao confirmar a seleção

def main():
    root = tk.Tk()
    temp_window = TempWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
