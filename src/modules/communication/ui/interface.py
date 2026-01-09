import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import threading
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any, Tuple, List
import queue
import logging

from modules.communication.protocol.protocolHeader import MsgType, Address

# =================================================================
# CommunicationDebugWindow (Singleton)
# =================================================================
class CommunicationDebugWindow(tk.Toplevel):
    """
    Janela de Monitor / Debug para o módulo de comunicação ESPFox.
    Otimizada para lidar com fluxo de logs híbrido (Texto/Binário).
    """

    _instance: Optional["CommunicationDebugWindow"] = None

    def __new__(cls, *args, **kwargs):
        # garante apenas uma instância
        if cls._instance is None or not getattr(cls._instance, "winfo_exists", lambda: False)():
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        master: tk.Misc,
        comm: Any,
        on_close_ref_clear: Optional[Callable[[Optional["CommunicationDebugWindow"]], None]] = None,
        *,
        width: int = 1000, # Ligeiramente mais largo para caber logs HEX
        height: int = 700,
    ):
        if hasattr(self, "_initialized") and self._initialized:
            return

        super().__init__(master)
        self.iconbitmap("src/data/icon.ico")
        self._initialized = True

        self.on_close_ref_clear = on_close_ref_clear
        self.comm = comm

        # Configuração da janela
        self.title("ESPFox — Monitor de Comunicação (PFOX)")
        self.geometry(f"{width}x{height}")
        # self.resizable(False, False) # Permitir redimensionar é melhor para debug

        # Estilos e cores
        self._setup_styles()

        # Estado interno
        self._running = False
        self._stop_loop = False
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._update_interval_ms = 60
        self._max_log_lines = 1000 # OTIMIZAÇÃO: Limite de linhas para não travar GUI

        # Construção da interface
        self._create_layout()

        # Configura listener de logs na comunicação
        # Verifica se o método existe para evitar crash se comm for mock
        if hasattr(self.comm, 'add_log_listener'):
            self.comm.add_log_listener(self._enqueue_log)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Inicia atualização automática da UI
        self.start()

    def _show_comm_config_info(self):
        """Exibe informações sobre a configuração da comunicação."""
        try:
            comm_type = "Desconhecido"
            connection_status = "Desconectado"
            
            # Verificação segura de conexão
            if hasattr(self.comm, 'is_connected') and self.comm.is_connected():
                connection_status = "Conectado"
                style_status = "RobotOK.TLabel" # Reutilizando estilo verde
            else:
                connection_status = "Desconectado"
                style_status = "RobotFAIL.TLabel" # Reutilizando estilo vermelho

            if hasattr(self.comm, 'use_mqtt'):
                if self.comm.use_mqtt:
                    broker = getattr(self.comm, 'broker_address', '?')
                    port = getattr(self.comm, 'port', '?')
                    comm_type = f"MQTT [{broker}:{port}]"
                else:
                    port = getattr(self.comm, 'serial_port', '?')
                    comm_type = f"Serial [{port}]"
            
            # Atualiza labels
            self.lbl_mode.config(text=f"Modo: {comm_type}")
            self.lbl_status_con.config(text=f"Estado: {connection_status}", style=style_status)
                
        except Exception as e:
            self.print_message(f"Erro GUI config: {e}")
        
    def _setup_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use(style.theme_use())

        # Botões
        style.configure("Debug.TButton", font=("Segoe UI", 9))
        style.configure("Custom.TButton", font=("Segoe UI", 9))

        # Títulos e labels
        style.configure("Header.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Title.TLabel", font=("Segoe UI", 9, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 9))
        style.configure("Stats.TLabel", font=("Segoe UI", 9))

        # Status Coloridos
        style.configure("RobotOK.TLabel", foreground="green", font=("Segoe UI", 9, "bold"))
        style.configure("RobotFAIL.TLabel", foreground="red", font=("Segoe UI", 9, "bold"))
        style.configure("RobotUnknown.TLabel", foreground="gray", font=("Segoe UI", 9))

    def _create_layout(self) -> None:
        pad = 10
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=pad, pady=pad)

        # Grid: Coluna 0 (Logs) maior que Coluna 1 (Stats)
        main.columnconfigure(0, weight=4)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # === ESQUERDA: LOG ===
        log_frame = ttk.Labelframe(main, text="Log de Eventos", style="Header.TLabelframe")
        log_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.log_box = ScrolledText(
            log_frame, width=60, height=20, state="disabled", 
            font=("Consolas", 9), wrap=tk.CHAR # Wrap CHAR é melhor para hex dumps
        )
        self.log_box.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Tags de coloração para o log
        self.log_box.tag_config("TX", foreground="blue")
        self.log_box.tag_config("RX", foreground="green")
        self.log_box.tag_config("ERR", foreground="red")
        self.log_box.tag_config("SYS", foreground="gray")

        # === DIREITA: STATS & CONTROLES ===
        right_panel = ttk.Frame(main)
        right_panel.grid(row=0, column=1, sticky="nsew")

        # 1. Painel de Conexão
        conn_frame = ttk.Labelframe(right_panel, text="Conexão", style="Header.TLabelframe")
        conn_frame.pack(fill="x", pady=(0, 10))
        
        self.lbl_mode = ttk.Label(conn_frame, text="Modo: ---", style="Status.TLabel")
        self.lbl_mode.pack(anchor="w", padx=5, pady=2)
        
        self.lbl_status_con = ttk.Label(conn_frame, text="Estado: ---", style="Status.TLabel")
        self.lbl_status_con.pack(anchor="w", padx=5, pady=2)

        btn_conn_frame = ttk.Frame(conn_frame)
        btn_conn_frame.pack(fill="x", padx=5, pady=5)
        
        # Botão Conectar
        self.btn_connect = ttk.Button(btn_conn_frame, text="🔗 Conectar", 
                                       command=self._connect, style="Custom.TButton")
        self.btn_connect.pack(fill="x", pady=2)
        
        # Botão Disconectar
        self.btn_disconnect = ttk.Button(btn_conn_frame, text="🔌 Disconectar", 
                                       command=self._disconnect, style="Custom.TButton")
        self.btn_disconnect.pack(fill="x", pady=2)

        # Botão Iniciar
        self.btn_iniciar = ttk.Button(btn_conn_frame, text="▶ Iniciar", 
                                       command=self._iniciar, style="Custom.TButton")
        self.btn_iniciar.pack(fill="x", pady=2)

        # Botão Pausar
        self.btn_pausar = ttk.Button(btn_conn_frame, text="⏸ Pausar", 
                                       command=self._pausar, style="Custom.TButton")
        self.btn_pausar.pack(fill="x", pady=2)

        # 2. Estatísticas
        stats_frame = ttk.Labelframe(right_panel, text="Estatísticas PFOX", style="Header.TLabelframe")
        stats_frame.pack(fill="x", pady=(0, 10))
        
        container_stats = ttk.Frame(stats_frame)
        container_stats.pack(fill="x", padx=5, pady=5)

        self.lbl_tx = ttk.Label(container_stats, text="TX Total: 0", style="Status.TLabel")
        self.lbl_tx.pack(anchor="w")
        
        self.lbl_rx = ttk.Label(container_stats, text="RX Total: 0", style="Status.TLabel")
        self.lbl_rx.pack(anchor="w")
        
        self.lbl_success_rate = ttk.Label(container_stats, text="Sucesso: 0.0%", style="Stats.TLabel")
        self.lbl_success_rate.pack(anchor="w")
        
        self.lbl_errors = ttk.Label(container_stats, text="Erros: 0", style="Status.TLabel")
        self.lbl_errors.pack(anchor="w")
        
        ttk.Separator(container_stats, orient="horizontal").pack(fill="x", pady=5)
        
        self.lbl_last_lat = ttk.Label(container_stats, text="Latência: --- ms", style="Status.TLabel")
        self.lbl_last_lat.pack(anchor="w")
        
        self.lbl_uptime = ttk.Label(container_stats, text="Uptime: 0s", style="Status.TLabel")
        self.lbl_uptime.pack(anchor="w")

        # 3. Status Robôs
        robots_frame = ttk.Labelframe(right_panel, text="Status Robôs", style="Header.TLabelframe")
        robots_frame.pack(fill="x", pady=(0, 10))
        
        self.robot_labels = {}
        for r in range(1, 4):
            f = ttk.Frame(robots_frame)
            f.pack(fill="x", padx=5, pady=2)
            ttk.Label(f, text=f"Robô {r}:", width=8, style="Status.TLabel").pack(side="left")
            lbl = ttk.Label(f, text="---", style="RobotUnknown.TLabel")
            lbl.pack(side="right", fill="x", expand=True)
            self.robot_labels[r] = lbl

        # 4. Ferramentas
        tools_frame = ttk.Labelframe(right_panel, text="Ferramentas", style="Header.TLabelframe")
        tools_frame.pack(fill="x", expand=True, anchor="n")
        
        self.btn_test = ttk.Button(tools_frame, text="⚡ Teste Rápido", 
                                 command=self._on_run_test, style="Custom.TButton")
        self.btn_test.pack(fill="x", padx=5, pady=2)
        
        self.btn_clear = ttk.Button(tools_frame, text="🗑 Limpar Log", 
                                  command=self.clear_log, style="Custom.TButton")
        self.btn_clear.pack(fill="x", padx=5, pady=2)
        
        self.test_result_var = tk.StringVar()
        ttk.Label(tools_frame, textvariable=self.test_result_var, style="Status.TLabel", foreground="blue").pack(pady=2)

        # === BARRA INFERIOR: COMANDO MANUAL ===
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=pad, pady=(0, pad))

        # Tipo de mensagem
        ttk.Label(bottom, text="Tipo:", style="Status.TLabel").grid(row=0, column=0, sticky="w", padx=5)
        self.msg_type_var = tk.StringVar()
        self.msg_type_combo = ttk.Combobox(bottom, textvariable=self.msg_type_var, state="readonly", width=15)
        self.msg_type_combo['values'] = [t.name for t in MsgType]
        self.msg_type_combo.current(0)  # Default to first
        self.msg_type_combo.grid(row=0, column=1, padx=5)
        self.msg_type_combo.bind("<<ComboboxSelected>>", self._on_msg_type_change)

        # Para quem
        ttk.Label(bottom, text="Para:", style="Status.TLabel").grid(row=0, column=2, sticky="w", padx=5)
        self.address_var = tk.StringVar()
        self.address_combo = ttk.Combobox(bottom, textvariable=self.address_var, state="readonly", width=10)
        self.address_combo['values'] = [a.name for a in Address]
        self.address_combo.current(0)
        self.address_combo.grid(row=0, column=3, padx=5)

        # O que fazer
        ttk.Label(bottom, text="Ação:", style="Status.TLabel").grid(row=0, column=4, sticky="w", padx=5)
        self.action_var = tk.StringVar()
        self.action_combo = ttk.Combobox(bottom, textvariable=self.action_var, state="readonly", width=15)
        self.action_combo.grid(row=0, column=5, padx=5)

        # Checkbox Controle Dinâmico
        self.dynamic_control_var = tk.BooleanVar()
        self.dynamic_control_check = ttk.Checkbutton(bottom, text="Controle Dinâmico", variable=self.dynamic_control_var, command=self._on_dynamic_control_toggle)
        self.dynamic_control_check.grid(row=0, column=6, padx=5)

        # Botão Enviar
        ttk.Button(bottom, text="Enviar", command=self._on_send_command).grid(row=0, column=7, padx=5)

        # Inicializar ações
        self._on_msg_type_change()
    # ===================== LÓGICA DE CONTROLE =====================
    def start(self) -> None:
        """Inicia loop de atualização da UI."""
        if self._running: return
        self._running = True
        self._stop_loop = False
        
        # Garante que o monitoramento do backend também esteja rodando
        if hasattr(self.comm, 'start_monitoring'):
            self.comm.start_monitoring()
            
        self._schedule_update()

    def stop(self) -> None:
        """Para atualizações."""
        self._running = False
        self._stop_loop = True

    def _schedule_update(self) -> None:
        if self._running and not self._stop_loop:
            self._update_from_comm()
            self.after(self._update_interval_ms, self._schedule_update)

    def _update_from_comm(self) -> None:
        # 1. Processa Logs
        self._flush_log_queue()
        
        # 2. Atualiza Config e Status de Conexão
        self._show_comm_config_info()

        # 3. Atualiza Estatísticas
        try:
            stats = self.comm.get_stats()
            
            self.lbl_tx.config(text=f"TX Total: {stats.get('tx', 0)}")
            self.lbl_rx.config(text=f"RX Total: {stats.get('rx_ok', 0)}") # 'rx_ok' vem do novo communication.py
            self.lbl_success_rate.config(text=f"Sucesso: {stats.get('success_rate', 0):.1f}%")
            self.lbl_errors.config(text=f"Erros: {stats.get('total_errors', 0)}")
            self.lbl_uptime.config(text=f"Uptime: {stats.get('uptime', 0):.0f}s")
            
            lat = stats.get('last_latency')
            lat_str = f"{lat:.1f} ms" if lat else "---"
            self.lbl_last_lat.config(text=f"Latência: {lat_str}")
            
        except Exception:
            pass

        # 4. Atualiza Robôs
        try:
            robot_status = self.comm.get_robot_status()
            for rid, lbl in self.robot_labels.items():
                st = robot_status.get(rid, "FAIL") # Default FAIL se não houver dados
                
                style = "RobotUnknown.TLabel"
                if st == "OK": style = "RobotOK.TLabel"
                elif st == "FAIL": style = "RobotFAIL.TLabel"
                
                lbl.config(text=st, style=style)
        except Exception:
            pass

    # ===================== LOGGING OTIMIZADO =====================
    def _enqueue_log(self, message: str) -> None:
        self._log_queue.put(message)

    def _flush_log_queue(self) -> None:
        if self._log_queue.empty(): return
        
        self.log_box.config(state="normal")
        
        # OTIMIZAÇÃO: Inserir em lotes para não congelar se vierem 1000 logs de vez
        count = 0
        while not self._log_queue.empty() and count < 50:
            msg = self._log_queue.get_nowait()
            
            # Detecção de Tags para colorir
            tag = "SYS"
            if "TX" in msg: tag = "TX"
            elif "RX" in msg: tag = "RX"
            elif "Erro" in msg or "FAIL" in msg: tag = "ERR"
            
            self.log_box.insert("end", msg + "\n", tag)
            count += 1
            
        # OTIMIZAÇÃO: Limpa logs antigos para economizar memória
        num_lines = int(self.log_box.index('end-1c').split('.')[0])
        if num_lines > self._max_log_lines:
            self.log_box.delete(1.0, float(num_lines - self._max_log_lines))
            
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    # ===================== AÇÕES =====================
# ===================== CONTROLE DE COMUNICAÇÃO =====================
    def _connect(self):
        """Estabelece a conexão sem iniciar o envio."""
        try:
            if hasattr(self.comm, 'connect'):
                self.comm.connect()
                self.print_message("Conexão estabelecida.")
            else:
                self.print_message("Método connect() não encontrado no backend.")
        except Exception as e:
            self.print_message(f"Erro ao conectar: {e}")

    def _disconnect(self):
        """Desconecta a instância de conexão atual."""
        try:
            if hasattr(self.comm, 'close'):
                self.comm.close()
                self.print_message("Desconectado.")
            else:
                self.print_message("Método close() não encontrado no backend.")
        except Exception as e:
            self.print_message(f"Erro ao desconectar: {e}")

    def _iniciar(self):
        """Inicia o ciclo de envio de informações."""
        try:
            if hasattr(self.comm, 'start'):
                self.comm.start()
                self.comm.set_sending_enabled(True)
                self.print_message("Envio de informações iniciado.")
            else:
                self.print_message("Método start() não encontrado no backend.")
        except Exception as e:
            self.print_message(f"Erro ao iniciar envio: {e}")

    def _pausar(self):
        """Pausa o ciclo de envio de informações."""
        try:
            if hasattr(self.comm, 'set_sending_enabled'):
                self.comm.set_sending_enabled(False)
                self.print_message("Envio de informações pausado.")
            else:
                self.print_message("Método set_sending_enabled() não encontrado no backend.")
        except Exception as e:
            self.print_message(f"Erro ao pausar envio: {e}")

    def _on_send_debug(self):
        text = self.entry_send.get().strip()
        if not text: return
        
        # Envia como texto utf-8. O communication.py lida com a conversão se necessário.
        self.comm.send(text)
        self.entry_send.delete(0, "end")

    def _on_run_test(self):
        # 1. VERIFICA CONEXÃO ANTES DE INICIAR O TESTE
        if not hasattr(self.comm, 'is_connected') or not self.comm.is_connected():
            self.print_message("⚠️ ERRO: O teste de comunicação requer uma conexão SERIAL ou MQTT ativa.")
            return

        self.test_result_var.set("Rodando...")
        # 2. Inicia o teste em uma thread separada
        threading.Thread(target=self._run_test_thread, daemon=True).start()

    def _run_test_thread(self):
        try:
            # Assumindo que self.comm.run_test() envia pacotes PFOX e espera respostas
            s, k = self.comm.run_test()
            self.test_result_var.set(f"Fim: {k}/{s} OK")
        except Exception as e:
            self.test_result_var.set("Erro Teste")
            self.print_message(f"❌ Erro durante a execução do teste: {e}")

    def print_message(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self._enqueue_log(f"[{ts}] {msg}")

    def _on_msg_type_change(self, event=None):
        msg_type = MsgType[self.msg_type_var.get()]
        if msg_type == MsgType.CMD_SET_SPEED:
            self.action_combo['values'] = ["Frente", "Trás", "Esquerda", "Direita"]
            self.action_combo.current(0)
            self.dynamic_control_check.grid()  # Show
        elif msg_type == MsgType.CMD_FLOW_CTRL:
            self.action_combo['values'] = ["STOP", "RUN", "PAUSE"]
            self.action_combo.current(0)
            self.dynamic_control_check.grid_remove()  # Hide
        elif msg_type == MsgType.HEARTBEAT:
            self.action_combo['values'] = ["Enviar"]
            self.action_combo.current(0)
            self.dynamic_control_check.grid_remove()
        elif msg_type == MsgType.ACK:
            self.action_combo['values'] = ["Enviar"]
            self.action_combo.current(0)
            self.dynamic_control_check.grid_remove()
        else:
            self.action_combo['values'] = ["Enviar"]
            self.action_combo.current(0)
            self.dynamic_control_check.grid_remove()

    def _on_send_command(self):
        msg_type = MsgType[self.msg_type_var.get()]
        address = Address[self.address_var.get()]
        action = self.action_var.get()

        try:
            if msg_type == MsgType.CMD_SET_SPEED:
                if action == "Frente":
                    self.comm.send_robot_velocity(address, 200, 200, 200, 200)
                elif action == "Trás":
                    self.comm.send_robot_velocity(address, -200, -200, -200, -200)
                elif action == "Esquerda":
                    self.comm.send_robot_velocity(address, -100, -100, 100, 100)
                elif action == "Direita":
                    self.comm.send_robot_velocity(address, 100, 100, -100, -100)
            elif msg_type == MsgType.CMD_FLOW_CTRL:
                if action == "STOP":
                    self.comm.send_flow_control(address, 0x20)
                elif action == "RUN":
                    self.comm.send_flow_control(address, 0x10)
                elif action == "PAUSE":
                    self.comm.send_flow_control(address, 0x30)
            elif msg_type == MsgType.HEARTBEAT:
                self.comm.send_heartbeat(address)
            elif msg_type == MsgType.ACK:
                # Assuming send_ack method exists
                if hasattr(self.comm, 'pfox_controller'):
                    pkt = self.comm.pfox_controller.send_ack(address)
                    self.comm.send(pkt.to_bytes())
            else:
                self.print_message("Tipo de mensagem não suportado para envio.")
        except Exception as e:
            self.print_message(f"Erro ao enviar comando: {e}")

    def _on_dynamic_control_toggle(self):
        if self.dynamic_control_var.get():
            self.focus_set()  # Ensure window has focus
            self.bind('<KeyPress-w>', lambda e: self._send_dynamic('Frente'))
            self.bind('<KeyPress-s>', lambda e: self._send_dynamic('Trás'))
            self.bind('<KeyPress-a>', lambda e: self._send_dynamic('Esquerda'))
            self.bind('<KeyPress-d>', lambda e: self._send_dynamic('Direita'))
            self.print_message("Controle dinâmico ativado. Use W/A/S/D.")
        else:
            self.unbind('<KeyPress-w>')
            self.unbind('<KeyPress-s>')
            self.unbind('<KeyPress-a>')
            self.unbind('<KeyPress-d>')
            self.print_message("Controle dinâmico desativado.")

    def _send_dynamic(self, action):
        address = Address[self.address_var.get()]
        if action == "Frente":
            self.comm.send_robot_velocity(address, 200, 200, 200, 200)
        elif action == "Trás":
            self.comm.send_robot_velocity(address, -200, -200, -200, -200)
        elif action == "Esquerda":
            self.comm.send_robot_velocity(address, -100, -100, 100, 100)
        elif action == "Direita":
            self.comm.send_robot_velocity(address, 100, 100, -100, -100)

    def clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete(1.0, "end")
        self.log_box.config(state="disabled")

    def _on_close(self):
        self.stop()
        if callable(self.on_close_ref_clear):
            self.on_close_ref_clear(None)
        CommunicationDebugWindow._instance = None
        self.destroy()

if __name__ == "__main__":
    print("Execute via main.py")