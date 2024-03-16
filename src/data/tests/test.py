import platform 
import pycuda.driver as pycuda
import ctypes

'''
@GNOMIO: Necessário baixar o pycuda.drive para fazer esse teste!
'''

def test_cuda():
    try:
        pycuda.init()
        device_count = pycuda.Device.count()
        if device_count > 0:
            print("CUDA está disponível neste sistema.")
            print("Número de dispositivos CUDA disponíveis:", device_count)
            for i in range(device_count):
                device = pycuda.Device(i)
                print("Dispositivo", i, ":", device.name())
        else:
            print("Nenhum dispositivo CUDA disponível.")
    except pycuda.RuntimeError:
        print("Erro ao inicializar o CUDA. Verifique sua configuração.")


def get_cuda_version():
    try:
        pycuda.init()
        context = pycuda.Device(0).make_context()
        version = context.get_api_version()
        context.detach()
        return version
    except pycuda.RuntimeError:
        return "CUDA não encontrado ou não está funcionando corretamente."

def get_screen_resolution():
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    return screen_width, screen_height

def test_resolution_window():
    # Obtém as dimensões da tela
    screen_width, screen_height = get_screen_resolution()
    print("Largura da tela:", screen_width)
    print("Altura da tela:", screen_height)


if __name__ == "__main__":
    test_resolution_window()