import platform 
import pycuda.driver as pycuda

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

if __name__ == "__main__":
    cuda_version = get_cuda_version()
    print("Versão do CUDA:", cuda_version)