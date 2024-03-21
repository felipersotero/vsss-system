import tkinter as tk
from tkinter import ttk

def main():
    # Funções de exemplo para os botões
    def save_choices():
        print("Salvando escolhas...")
    
    def start_processing():
        print("Iniciando processamento...")

    # Função para alternar a visibilidade do Combobox da porta serial
    def show_serial_combobox(event):
        selected_comm = combo_comm_mode.get()
        if selected_comm == "SERIAL":
            label_serial_port.grid(row=2, column=0, padx=10, pady=5, sticky="w")
            combo_serial_port.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        else:
            label_serial_port.grid_remove()
            combo_serial_port.grid_remove()

    # Função para escolher um ponto na tela
    def choose_point():
        print("Escolhendo ponto...")

    # Criando a janela
    root = tk.Tk()
    root.title("Janela com Frames")
    root.geometry("1000x700")

    # Criando o primeiro frame acima
    frame_top = tk.Frame(root, width=600, height=350, bg="black")
    frame_top.pack_propagate(False)  # Evita que o frame ajuste seu tamanho automaticamente
    frame_top.pack()

    # Espaçamento entre os frames
    spacer = tk.Frame(root, width=800, height=50)
    spacer.pack()

    # Criando o segundo frame abaixo
    frame_bottom = tk.Frame(root, width=800, height=200, bg="blue")
    frame_bottom.pack_propagate(False)  # Evita que o frame ajuste seu tamanho automaticamente
    frame_bottom.pack()

    # Criando frames internos no frame_bottom (colunas)
    frame_left = tk.Frame(frame_bottom, width=240, height=200, bg="red")
    frame_left.pack_propagate(False)
    frame_left.grid(row=0, column=0)

    frame_center = tk.Frame(frame_bottom, width=320, height=200, bg="yellow")
    frame_center.pack_propagate(False)
    frame_center.grid(row=0, column=1)

    frame_right = tk.Frame(frame_bottom, width=240, height=200, bg="green")
    frame_right.pack_propagate(False)
    frame_right.grid(row=0, column=2)

    # Labels para o frame esquerdo (30%)
    label_choose_player = tk.Label(frame_left, text="1 - Escolher jogador:", fg="white", bg="red")
    label_choose_player.grid(row=0, column=0, padx=10, pady=5, sticky="w")
    combo_players = ttk.Combobox(frame_left, values=["Jogador 1", "Jogador 2", "Jogador 3", "Jogador 4", "Jogador 5", "Jogador 6"], state='readonly')
    combo_players.grid(row=0, column=1, padx=10, pady=5, sticky="w")

    label_comm_mode = tk.Label(frame_left, text="2 - Modo de comunicação:", fg="white", bg="red")
    label_comm_mode.grid(row=1, column=0, padx=10, pady=5, sticky="w")
    combo_comm_mode = ttk.Combobox(frame_left, values=["MQTT", "SERIAL"], state='readonly')
    combo_comm_mode.grid(row=1, column=1, padx=10, pady=5, sticky="w")
    combo_comm_mode.bind("<<ComboboxSelected>>", show_serial_combobox)

    # Label e Combobox para porta serial (será visível apenas quando SERIAL for selecionado)
    label_serial_port = tk.Label(frame_left, text="Porta serial:", fg="white", bg="red")
    combo_serial_port = ttk.Combobox(frame_left, state='readonly')

    label_btn_grid = tk.Label(frame_left, text="3 - Opções de processamento:", fg="white", bg="red")
    label_btn_grid.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")
    btn_save = tk.Button(frame_left, text="Salvar escolhas", command=save_choices)
    btn_save.grid(row=4, column=0, padx=(10, 5), pady=5)
    btn_start = tk.Button(frame_left, text="Iniciar processamento", command=start_processing)
    btn_start.grid(row=4, column=1, padx=(5, 10), pady=5)

    label_choose_point = tk.Label(frame_left, text="4 - Escolher um ponto na tela:", fg="white", bg="red")
    label_choose_point.grid(row=5, column=0, padx=10, pady=5, sticky="w")
    btn_choose_point = tk.Button(frame_left, text="Escolher", command=choose_point)
    btn_choose_point.grid(row=5, column=1, padx=10, pady=5, sticky="w")

    root.mainloop()

if __name__ == "__main__":
    main()
