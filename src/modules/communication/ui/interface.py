import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import threading
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any, Tuple, List
import queue
import logging

# Importando módulo de comunicação
from modules.communication.communication import Communication

# Logger básico da aplicação
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("espfox.debug")

# =================================================================
# CommunicationDebugWindow (Singleton)
# =================================================================
class CommunicationDebugWindow(tk.Toplevel):
    """
    Janela de Monitor / Debug para o módulo de comunicação ESPFox.
    Integrada com a classe Communication do communication.py.
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
        width: int = 800,
        height: int = 500,
    ):
        if hasattr(self, "_initialized") and self._initialized:
            return

        super().__init__(master)
        self._initialized = True

        self.on_close_ref_clear = on_close_ref_clear
        self.comm = comm

        # Configuração da janela
        self.title("ESPFox — Monitor de Comunicação")
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)

        # Estilos e cores
        self._setup_styles()

        # Estado interno
        self._running = False
        self._stop_loop = False
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._update_interval_ms = 60

        # Construção da interface
        self._create_layout()

        # Configura listener de logs na comunicação
        self.comm.add_log_listener(self._enqueue_log)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _show_comm_config_info(self):
        """Exibe informações sobre a configuração da comunicação."""
        try:
            # Obtém estatísticas para determinar o modo
            comm_type = "Desconhecido"
            connection_status = "Desconectado"
            
            if hasattr(self.comm, 'is_connected') and self.comm.is_connected():
                connection_status = "Conectado"

            if hasattr(self.comm, 'use_mqtt') and self.comm.use_mqtt:
                # Para MQTT, obtém informações do broker
                if hasattr(self.comm, 'broker_address') and hasattr(self.comm, 'port'):
                    broker = self.comm.broker_address
                    port = self.comm.port
                    comm_type = f"MQTT → {broker}:{port}"
                else:
                    comm_type = "MQTT → Configuração não disponível"
            else:
                # Para Serial
                if hasattr(self.comm, 'serial_port'):
                    port = self.comm.serial_port
                    comm_type = f"Serial → {port}"
                else:
                    comm_type = "Serial → Configuração não disponível"

            
            # Atualiza a label do modo com informações detalhadas
            self.lbl_mode.config(text=f"Modo: {comm_type}")
            
            # Log apenas na primeira vez ou quando mudar
            if not hasattr(self, '_last_comm_info') or self._last_comm_info != (comm_type, connection_status):
                self.print_message(f"Comunicação configurada: {comm_type} - Estado: {connection_status}")
                self._last_comm_info = (comm_type, connection_status)
                
        except Exception as e:
            self.print_message(f"Erro ao obter informações da comunicação: {e}")
        
    def _setup_styles(self) -> None:
        """Configura estilos visuais exclusivos para esta janela de debug."""
        style = ttk.Style(self)

        # ESCOPANDO OS ESTILOS PRA ESTA JANELA
        # (isso evita interferir na janela principal)
        style.theme_use(style.theme_use())

        # Botões
        style.configure("Debug.TButton",
                        font=("Segoe UI", 9))

        # Títulos e labels
        style.configure("DebugHeader.TLabelframe.Label",
                        font=("Segoe UI", 10, "bold"))
        style.configure("DebugTitle.TLabel",
                        font=("Segoe UI", 9, "bold"))
        style.configure("DebugStatus.TLabel",
                        font=("Segoe UI", 9))
        style.configure("DebugStats.TLabel",
                        font=("Segoe UI", 9))

        # Status dos robôs
        style.configure("RobotOK.TLabel", foreground="green")
        style.configure("RobotFAIL.TLabel", foreground="red")
        style.configure("RobotUnknown.TLabel", foreground="gray")

        # Botões Custom.TButton usados no layout
        style.configure("Custom.TButton",
                        font=("Segoe UI", 9))



    def _create_layout(self) -> None:
        """Cria layout da interface."""
        pad = 12
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=pad, pady=pad)

        # grid principal
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # LOG (LEFT)
        log_frame = ttk.Labelframe(main, text="Log de Comunicação", style="Header.TLabelframe")
        log_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.log_box = ScrolledText(
            log_frame, width=70, height=25, state="disabled", 
            font=("Consolas", 9), wrap=tk.WORD
        )
        self.log_box.pack(fill="both", expand=True, padx=6, pady=6)

        # Estatísticas e status (RIGHT)
        status_frame = ttk.Labelframe(main, text="Estatísticas e Status", style="Header.TLabelframe")
        status_frame.grid(row=0, column=1, sticky="nsew")

        # Container de estatísticas
        stats_container = ttk.Frame(status_frame)
        stats_container.pack(fill="x", padx=10, pady=10)

        ttk.Label(stats_container, text="Comunicação", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        
        self.lbl_mode = ttk.Label(stats_container, text="Modo: ---", style="Status.TLabel")
        self.lbl_mode.pack(anchor="w", pady=2)
        
        self.lbl_tx = ttk.Label(stats_container, text="Pacotes enviados: 0", style="Status.TLabel")
        self.lbl_tx.pack(anchor="w", pady=2)
        
        self.lbl_rx = ttk.Label(stats_container, text="Pacotes confirmados: 0", style="Status.TLabel")
        self.lbl_rx.pack(anchor="w", pady=2)
        
        self.lbl_success_rate = ttk.Label(stats_container, text="Taxa de sucesso: 0.0%", style="Stats.TLabel")
        self.lbl_success_rate.pack(anchor="w", pady=2)
        
        self.lbl_errors = ttk.Label(stats_container, text="Erros: 0", style="Status.TLabel")
        self.lbl_errors.pack(anchor="w", pady=2)
        
        self.lbl_last_lat = ttk.Label(stats_container, text="Última latência: --- ms", style="Status.TLabel")
        self.lbl_last_lat.pack(anchor="w", pady=2)
        
        self.lbl_avg_lat = ttk.Label(stats_container, text="Latência média: --- ms", style="Status.TLabel")
        self.lbl_avg_lat.pack(anchor="w", pady=2)
        
        self.lbl_uptime = ttk.Label(stats_container, text="Uptime: 0s", style="Status.TLabel")
        self.lbl_uptime.pack(anchor="w", pady=2)

        ttk.Separator(status_frame, orient="horizontal").pack(fill="x", pady=10, padx=10)

        # Status dos robôs
        robots_container = ttk.Frame(status_frame)
        robots_container.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(robots_container, text="Status dos Robôs:", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        
        self.robot_labels: Dict[int, ttk.Label] = {}
        for r in range(1, 4):
            frame = ttk.Frame(robots_container)
            frame.pack(fill="x", pady=3)
            
            ttk.Label(frame, text=f"Robô {r}:", width=8, style="Status.TLabel").pack(side="left")
            lbl = ttk.Label(frame, text="---", style="RobotUnknown.TLabel")
            lbl.pack(side="left", fill="x", expand=True)
            self.robot_labels[r] = lbl

        # Bottom: control buttons + entry
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=pad, pady=(0, pad))

        # 🔹 ADICIONAR: Botões de controle de comunicação
        comm_controls = ttk.Frame(bottom)
        comm_controls.pack(side="top", fill="x", pady=(0, 5))

        self.btn_comm_start = ttk.Button(
            comm_controls, text="▶ Iniciar Comunicação", 
            command=self._start_communication, style="Custom.TButton"
        )
        self.btn_comm_start.pack(side="left", padx=2)

        self.btn_comm_stop = ttk.Button(
            comm_controls, text="⏹ Parar Comunicação", 
            command=self._stop_communication, style="Custom.TButton"
        )
        self.btn_comm_stop.pack(side="left", padx=2)

        self.btn_comm_reset = ttk.Button(
            comm_controls, text="🔄 Reiniciar", 
            command=self._reset_communication, style="Custom.TButton"
        )
        self.btn_comm_reset.pack(side="left", padx=2)

        # Botões de controle (mantidos do código original)
        controls = ttk.Frame(bottom)
        controls.pack(side="left", fill="x", expand=True)

        self.btn_start = ttk.Button(
            controls, text="▶ Iniciar Monitoramento", 
            command=self.start, style="Custom.TButton"
        )
        self.btn_start.pack(side="left", padx=2)

        self.btn_stop = ttk.Button(
            controls, text="⏹ Parar Monitoramento", 
            command=self.stop, style="Custom.TButton", state="disabled"
        )
        self.btn_stop.pack(side="left", padx=2)

        self.btn_test = ttk.Button(
            controls, text="⚡ Testar Comunicação", 
            command=self._on_run_test, style="Custom.TButton"
        )
        self.btn_test.pack(side="left", padx=2)

        self.btn_clear = ttk.Button(
            controls, text="🗑 Limpar Log", 
            command=self.clear_log, style="Custom.TButton"
        )
        self.btn_clear.pack(side="left", padx=2)

        # Entrada de comando (mantida do código original)
        entry_frame = ttk.Frame(bottom)
        entry_frame.pack(side="right", fill="x", expand=True)

        ttk.Label(entry_frame, text="Comando:", style="Status.TLabel").pack(side="left", padx=(0, 6))

        self.entry_send = ttk.Entry(entry_frame, width=25, font=('Arial', 9))
        self.entry_send.pack(side="left", fill="x", expand=True, padx=2)
        self.entry_send.bind("<Return>", lambda e: self._on_send_debug())

        ttk.Button(entry_frame, text="Enviar", 
                command=self._on_send_debug, style="Custom.TButton").pack(side="left", padx=2)

        # Label de resultado de teste (mantida do código original)
        self.test_result_var = tk.StringVar(value="")
        ttk.Label(bottom, textvariable=self.test_result_var, style="Status.TLabel").pack(side="right", padx=10)

    # ===================== CONTROLE PRINCIPAL =====================
    def start(self) -> None:
        """Inicia o monitoramento."""
        if self._running:
            return
            
        self._running = True
        self._stop_loop = False
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="enabled")
        
        try:
            self.comm.start_monitoring()
        except Exception as e:
            logger.warning("Erro ao iniciar monitoramento: %s", e)
            
        self._schedule_update()
        self.print_message("Sistema de monitoramento iniciado")

    # ===================== CONTROLE DE COMUNICAÇÃO =====================
    def _start_communication(self):
        """Inicia/reconecta a comunicação."""
        try:
            self.print_message("Iniciando comunicação...")
            self.comm._setup_connection()  # Reconecta
            
            # Aguarda um pouco e atualiza informações
            self.after(1000, self._show_comm_config_info)
            
        except Exception as e:
            self.print_message(f"Erro ao iniciar comunicação: {e}")

    def _stop_communication(self):
        """Para a comunicação."""
        try:
            self.print_message("Parando comunicação...")
            self.comm.close()
            
            # Para o monitoramento também se estiver rodando
            if self._running:
                self.stop()
                
            self._show_comm_config_info()
            self.print_message("Comunicação parada")
            
        except Exception as e:
            self.print_message(f"Erro ao parar comunicação: {e}")

    def _reset_communication(self):
        """Reinicia a comunicação."""
        try:
            self.print_message("Reiniciando comunicação...")
            self.comm.reset_connection()
            
            # Aguarda e atualiza informações
            self.after(1500, self._show_comm_config_info)
            
        except Exception as e:
            self.print_message(f"Erro ao reiniciar comunicação: {e}")
            
    def stop(self) -> None:
        """Para o monitoramento."""
        if not self._running:
            return
            
        self._running = False
        self._stop_loop = True
        self.btn_start.config(state="enabled")
        self.btn_stop.config(state="disabled")
        
        try:
            self.comm.stop_monitoring()
        except Exception as e:
            logger.warning("Erro ao parar monitoramento: %s", e)
            
        self.print_message("Sistema de monitoramento parado")

    def _schedule_update(self) -> None:
        """Agenda próxima atualização."""
        if self._running and not self._stop_loop:
            self._update_from_comm()
            self.after(self._update_interval_ms, self._schedule_update)

    # ===================== ATUALIZAÇÕES DA INTERFACE =====================
    def _update_from_comm(self) -> None:
        """Atualiza interface com dados da comunicação."""
        # Atualiza logs
        self._flush_log_queue()
        
        # Atualiza informações da comunicação (incluindo status de conexão)
        self._show_comm_config_info()

        # Atualiza estatísticas
        try:
            stats = self.comm.get_stats()
            self._apply_stats(stats)
        except Exception as e:
            logger.debug("Erro ao obter estatísticas: %s", e)

        # Atualiza status dos robôs
        try:
            robot_status = self.comm.get_robot_status()
            self._apply_robot_status(robot_status)
        except Exception as e:
            logger.debug("Erro ao obter status dos robôs: %s", e)
        
        # 🔹 ADICIONAR: Atualiza informações da comunicação periodicamente
        self._show_comm_config_info()

    def _enqueue_log(self, message: str) -> None:
        """Recebe logs da comunicação (callback)."""
        self._log_queue.put(message)

    def _flush_log_queue(self) -> None:
        """Processa fila de logs."""
        if self._log_queue.empty():
            return
            
        self.log_box.config(state="normal")
        while not self._log_queue.empty():
            try:
                msg = self._log_queue.get_nowait()
                self.log_box.insert("end", msg + "\n")
            except queue.Empty:
                break
        self.log_box.config(state="disabled")
        self.log_box.yview("end")

    def _apply_stats(self, stats: Dict[str, Any]) -> None:
        """Aplica estatísticas na interface."""
        # 🔹 REMOVER: Não atualizar lbl_mode aqui para evitar conflito
        # O lbl_mode será atualizado apenas por _show_comm_config_info
        
        tx = stats.get("tx", 0)
        rx_ok = stats.get("rx_ok", 0)  # Este é o número de envios bem-sucedidos, não recebidos
        success_rate = stats.get("success_rate", 0.0)
        errors = stats.get("total_errors", 0)
        avg_lat = stats.get("avg_latency")
        last_lat = stats.get("last_latency")
        uptime = stats.get("uptime", 0)

        self.lbl_tx.config(text=f"Pacotes enviados: {tx}")
        self.lbl_rx.config(text=f"Envios bem-sucedidos: {rx_ok}")  # Corrigindo o label
        self.lbl_success_rate.config(text=f"Taxa de sucesso: {success_rate:.1f}%")
        self.lbl_errors.config(text=f"Erros: {errors}")
        self.lbl_uptime.config(text=f"Uptime: {uptime:.0f}s")

        if last_lat is None:
            self.lbl_last_lat.config(text="Última latência: --- ms")
        else:
            self.lbl_last_lat.config(text=f"Última latência: {last_lat:.1f} ms")

        if avg_lat is None:
            self.lbl_avg_lat.config(text="Latência média: --- ms")
        else:
            self.lbl_avg_lat.config(text=f"Latência média: {avg_lat:.1f} ms")
            
    def _apply_robot_status(self, status: Dict[int, str]) -> None:
        """Aplica status dos robôs na interface."""
        for robot_id, lbl in self.robot_labels.items():
            state = status.get(robot_id, "---")

            if state == "OK":
                style = "RobotOK.TLabel"
            elif state == "FAIL":
                style = "RobotFAIL.TLabel"
                self._flash_alert()
            else:
                style = "RobotUnknown.TLabel"

            lbl.config(text=state, style=style)

    def _flash_alert(self) -> None:
        """Alerta visual sutil para falhas."""
        orig = self.title()
        if "⚠" not in orig:
            self.title("⚠ " + orig)
            self.after(2000, lambda: self.title(orig))

    # ===================== MÉTODOS PÚBLICOS =====================
    def print_message(self, message: str) -> None:
        """Imprime mensagem no log (thread-safe)."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted = f"[{timestamp}] {message}"
        self._enqueue_log(formatted)

    def clear_log(self) -> None:
        """Limpa o conteúdo do log."""
        self.log_box.config(state="normal")
        self.log_box.delete(1.0, "end")
        self.log_box.config(state="disabled")
        self.print_message("Log limpo")

    # ===================== COMANDOS MANUAIS =====================
    def _on_send_debug(self) -> None:
        """Envia comando manual."""
        text = self.entry_send.get().strip()
        if not text:
            return
            
        try:
            # Envia como bytes (compatível com interface original)
            data = text.encode("utf-8")
            self.comm.send(data)
            self.entry_send.delete(0, "end")
        except Exception as e:
            self.print_message(f"Erro ao enviar comando: {e}")

    def _on_run_test(self) -> None:
        """Executa teste de comunicação."""
        self.test_result_var.set("Testando...")
        self.print_message("Iniciando teste de comunicação...")
        threading.Thread(target=self._run_test_thread, daemon=True).start()

    def _run_test_thread(self) -> None:
        """Thread para execução do teste."""
        try:
            sent, ok = self.comm.run_test()
            result_text = f"Resultado: {ok}/{sent} OK"
            self.test_result_var.set(result_text)
            self.print_message(f"Teste concluído: {ok}/{sent} pacotes bem-sucedidos")
        except Exception as e:
            self.test_result_var.set("Erro no teste")
            self.print_message(f"Erro durante teste: {e}")

    # ===================== ENCERRAMENTO =====================
    def _on_close(self) -> None:
        """Fecha a janela de forma segura."""
        self.stop()
        
        if callable(self.on_close_ref_clear):
            try:
                self.on_close_ref_clear(None)
            except Exception:
                pass

        CommunicationDebugWindow._instance = None
        self.destroy()

# =================================================================
if __name__ == "__main__":
    print("Módulo executado como princial")