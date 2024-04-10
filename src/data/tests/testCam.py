import wmi

def listar_cameras():
    try:
        # Conecta ao serviço Windows Management Instrumentation (WMI)
        c = wmi.WMI()

        # Consulta os dispositivos de vídeo
        cameras = c.Win32_PnPEntity(Description="USB Video Device")

        print("Câmeras disponíveis:")
        for i, camera in enumerate(cameras):
            print(f"Câmera {i + 1}: {camera.Name}")

    except Exception as e:
        print(f"Erro ao listar as câmeras: {e}")

if __name__ == "__main__":
    listar_cameras()
