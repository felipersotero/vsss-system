from objects import *
from modules import *
from app import *
from emulator import *
from communication import *
from detectorV2 import *



#Testando forma de capturar dados
capture = Capture(CaptureMode.CAM)

capture.setIdCam(0)
capture.setMode(CaptureMode.CAM)

#inicio o processo de captura
capture.initUSBProcess()
print("iniciou a execução")
time.sleep(20)

capture.stopUSBProcess()
print("finalizou a execução")

