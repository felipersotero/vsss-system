from modules.VisionSys.components.objects import *
from imports import *
from app import *
from modules.emulator.emulator import *
from modules.communication.communication import *
from modules.VisionSys.detectorV2 import *



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

