import numpy as np
#Definição de um ponto 2D no sistema
class Point2D:
    ''' Classe para representar um ponto de 2 dimensões'''
    def __init__(self, px,py):
        self.px = px        #Coordenada x 
        self.py = py        #Coordenada y

        #ponto no formato array do numpy
        self.pos = np.array([px,py])

    #retornando posição central
    def getPos(self):
        '''
        Retorna posição do ponto (x,y)
        '''
        return self.pos 
    
    #Definindo operações com Point2D
    #definindo a soma (x,y)+(a,b) = (x+a, y+b)
    def __add__(self, other):
        if isinstance(other, Point2D):
            return Point2D(self.px +other.px, self.py+other.py)
        elif isinstance(other, tuple):
            return Point2D(self.px +other[0], self.py+other[1])
        else:
            raise TypeError("Operação inválida")
        
    #definindo a subtração de dois pontos (x,y)-(a,b) = (x-a,y-b)
    def __sub__(self, other):
        if isinstance(other, Point2D):
            return Point2D(self.px -other.px, self.py-other.py)
        elif isinstance(other, tuple):
            return Point2D(self.px -other[0], self.py-other[1])
        else:
            raise TypeError("Operação inválida")
        
    #definindo multiplicação entre esses dois pontos 2D
    def __mul__(self, other):
        #Multiplicação por escalar (x,y)*k = (kx,ky)
        if isinstance(other, (int, float)):
            # Se 'other' for um escalar, realizar multiplicação por escalar
            return Point2D(self.px * other, self.py * other)
        
        #multiplicação por uma instância (x,y) * (a,b) = (x*a,y*b) => Necessário criar uma lógica
        elif isinstance(other, Point2D): 
            # Se 'other' for um vetor, realizar produto escalar
            return Point2D(self.px * other.px, self.py * other.py)
        else:
            # Caso contrário, lançar uma exceção ou retornar None
            raise TypeError("Operação de multiplicação não suportada para o tipo de objeto passado.")
    
    # Define o comportamento do operador de string
    def __str__(self):
        return f"Point2D({self.px}, {self.py})"
    
    #define a operação de equalidade
    def __eq__(self, other):
        #Multiplicação por escalar (x,y)*k = (kx,ky)
        if isinstance(other, Point2D):
            if self.px == other.px and self.py == other.py:
                return True 
            else:
                return False 
        elif isinstance(other, tuple):
            try: 
                if self.px == other[0] and self.py == other[0]:
                    return True 
                else:
                    return False
            except:
                return False 
        else:
            # Caso contrário, lançar uma exceção ou retornar None
            raise TypeError("Não é possível tomar a igualdade entre dois valores diferentes")
    
    #define o tamanho do objeto
    def __len__(self):
        return 2 
    
    #define como pegar um valor desse método
    def __getitem__(self, index):
        ''' Retorna o valor correspondente ao índice'''
        if index == 0:
            return self.px
        elif index == 1:
            return self.py
        else:
            raise IndexError("Índice fora do intervalo para Point2D")
    
A = Point2D(2,1)

B = Point2D(2,3)

print("a",A)

print("b",B)
print("a+b =",A+B)

print("a-b = ",A-B)

print("a*b =",A*B)

print("5A+4B =",(A*5+B*4))

print("primeiro elemento de A:", A[0])

print("A = B? ", A==B) 