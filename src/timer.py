# ==========================================================================================
# Classe Timer que será utilizada para contabilizar FPS e demais cálculos
#=========================================================================================
import time


'''
@GNOMIO: Classe responsável por realizar contagens em tempo real, contar intervalos, iniciar e parar.
'''
class Timer:
    def __init__(self):
        self.omg = 10

