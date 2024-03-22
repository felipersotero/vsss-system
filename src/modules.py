from tkinter import *
from tkinter import ttk
from tkinter.ttk import Treeview, Scrollbar, Entry, Style
from tkinter import simpledialog, messagebox, filedialog
import cv2
from PIL import Image, ImageTk, ImageGrab
import json
import base64
import unidecode
import threading
import numpy as np
import math
import serial
import ctypes 
import subprocess
import serial.tools.list_ports
import re

#Bibliotecas 
from detector import *


#suporte a GPU
from cv2 import cuda
import platform 
import pycuda.driver as pycuda
import numba