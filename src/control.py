"""# FUNÇÕES DE MEDIDAS ====================

## Calcular distância entre dois pontos
## Encontrar jogador mais próximo de certo ponto

# FUNÇÕES ELEMENTARES ====================
# (essas funções talvez devam ir para o arquivo de comunicação)

## Andar
## Girar
## Parar

# FUNÇÕES BÁSICAS ====================

## Deslocamento entre dois pontos
## Seguir bola
## Desvio de objetos

# POSICIONAMENTO ESPECÍFICO ====================

## Tiro livre
## Pênalti
## Tiro de meta
## Bola livre"""

from modules import *
from communication import *


class Control:
    def __init__(self, Emulator):
        self.field = Emulator.field
        self.ball = Emulator.ball
        self.allies = Emulator.allies
        self.enemies = Emulator.enemies

        self.ball_coordinates = None
        self.allies_coordinates = [None, None, None]
        self.allies_status = [None, None, None]
        self.allies_direction = [None, None, None]

        self.enemies_coordinates = [None, None, None]

        self.possibleRecognition = [False, False, False]

    def updateObjectsValues(self, field, ball, allies, enemies):
        self.field = field
        self.ball = ball
        self.allies = allies
        self.enemies = enemies

    def getCoordinates(self):

        # Coordenadas da bola
        if self.ball is not None:
            self.ball_coordinates = np.array([self.ball.position[0], self.ball.position[1]])

        # Coordenadas do aliados
        for i in range(3):
            if self.allies[i] is not None:
                self.allies_coordinates[i] = np.array([self.allies[i].position[0], self.allies[i].position[1]])
                self.allies_direction[i] = np.array([self.allies[i].direction[0], self.allies[i].direction[1]])
                self.possibleRecognition[i] = True

        # Coordenadas dos inimigos
        # Pivots do campo        
        
    def angleBetweenObjects(self, target_coordinates, source_coordinates, source_direction):

        v1 = source_direction
        v2 = np.array([target_coordinates[0]-source_coordinates[0], target_coordinates[1]-source_coordinates[1]])

        dot_product = np.dot(v1, v2)
        magnitude1 = np.linalg.norm(v1)
        magnitude2 = np.linalg.norm(v2)

        cosine_theta = dot_product / (magnitude1 * magnitude2)

        angle_rad = np.arccos(np.clip(cosine_theta, -1.0, 1.0))
        angle_deg = np.degrees(angle_rad)

    # Calcular o produto vetorial para determinar a direção
        cross_product = np.cross(v1, v2)

        # Se o produto vetorial for negativo, o objeto alvo está à esquerda
        if cross_product < 0:
            angle_deg *= -1

        return angle_deg

    def distanceBetweenObjects(self, target_coordinates, source_coordinates):
        dx = abs(target_coordinates[0] - source_coordinates[0])
        dy = abs(target_coordinates[1] - source_coordinates[1])
        distance = np.sqrt((dx**2)+(dy**2))

        return distance

    def formatAngle(self, value):
        formatted_value = "{:.2f}".format(value)
        if value >= 0:
            formatted_value = "+" + formatted_value
        formatted_value = formatted_value.zfill(7)

        return formatted_value

    def formatDistance(self, value):
        formatted_value = "{:.2f}".format(value)
        formatted_value = formatted_value.zfill(6)

        return formatted_value

    ################################################################
    # Função principal que recebe os dados das coordenadas dos objetos
    def processControl(self):

        self.getCoordinates()

        kp = '+0.00'
        ki = '+0.00'
        kd = '+0.00'
        pid_constants = kp + ki + kd

        # command = 'c+045.25025.13' #'c+aaa.aaddd.dd'
        command = 's+000.00000.00'

        if self.possibleRecognition[0] and self.ball_coordinates is not None:
            
            angle = self.angleBetweenObjects(self.ball_coordinates, self.allies_coordinates[0], self.allies_direction[0])
            distance = self.distanceBetweenObjects(self.ball_coordinates, self.allies_coordinates[0])

            print(f"Ângulo: {angle} °")
            print(f"Distância: {distance} cm")
            
            # angle = angle*(-1)
            angle_string = self.formatAngle(angle)
            distance_string = self.formatDistance(distance)

            command_mode = 'c'

            if(((abs(angle) < 0.5) and distance < 8) or not(self.allies[0].detected)):
                command_mode = 's'


            command = command_mode + angle_string + distance_string
        
        return command
    
'''
# # Verfificar se o jogador está e posse da bola
# def possession_ball(ball_coord, player_coord, player_direction):

#     dx = abs(ball_coord[0] - player_coord[0])
#     dy = abs(ball_coord[1] - player_coord[1])
#     distance = np.sqrt((dx**2)+(dy**2))

#     angle = angleBetweenObjects(ball_coord, player_coord, player_direction)

#     print(f"Distância: {distance} cm")
#     print(f"Ângulo: {angle}°")

#     if distance < 10 and abs(angle) < 20:
#         return True
#     else:
#         return False


# # Verificar time em posse da bola
# def team_with_possession(ball_coord, allies_coord, allies_direction, enemies_coord, enemies_direction):
#     ally_possession = False
#     enemy_possession = False

#     for i in range(3):
#         if allies_coord[i] is not None and allies_direction[i] is not None:
#             if possession_ball(ball_coord, allies_coord[i], allies_direction[i]):
#                 ally_possession = True

#     for i in range(3):
#         if enemies_coord[i] is not None and enemies_direction[i] is not None:
#             if possession_ball(ball_coord, enemies_coord[i], enemies_direction[i]):
#                 enemy_possession = True

# # Verificar aliado mais próximo da bola 
# def calculate_distance_to_ball(xb, yb, coord_allies):

#     closer = None
#     min_distance = None

#     for i in range(3):
#         if (coord_allies[i] is not None):
#             dx = abs(xb - coord_allies[i][0])
#             dy = abs(yb - coord_allies[i][1])
#             distance = np.sqrt((dx**2)+(dy**2))

#             if min_distance is None:
#                 min_distance = distance
#                 closer = i
#             else:
#                 if distance < min_distance:
#                     min_distance = distance
#                     closer = i

#     return closer
'''
