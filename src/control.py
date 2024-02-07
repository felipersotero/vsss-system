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

# Calcular ângulo entre jogador e bola
def angle_player_ball(ball_coord, player_coord, player_direction):

    v1 = player_direction
    v2 = np.array([ball_coord[0]-player_coord[0], ball_coord[1]-player_coord[1]])

    dot_product = np.dot(v1, v2)
    magnitude1 = np.linalg.norm(v1)
    magnitude2 = np.linalg.norm(v2)

    cosine_theta = dot_product / (magnitude1 * magnitude2)

    angle_rad = np.arccos(np.clip(cosine_theta, -1.0, 1.0))
    angle_deg = np.degrees(angle_rad)

    return angle_deg


# Verfificar se o jogador está e posse da bola
def possession_ball(ball_coord, player_coord, player_direction):

    dx = abs(ball_coord[0] - player_coord[0])
    dy = abs(ball_coord[1] - player_coord[1])
    distance = np.sqrt((dx**2)+(dy**2))

    angle = angle_player_ball(ball_coord, player_coord, player_direction)

    print(f"Distância: {distance} cm")
    print(f"Ângulo: {angle}°")

    if distance < 10 and angle < 20:
        return True
    else:
        return False


# Verificar time em posse da bola
def team_with_possession(ball_coord, allies_coord, allies_direction, enemies_coord, enemies_direction):
    ally_possession = False
    enemy_possession = False

    for i in range(3):
        if allies_coord[i] is not None and allies_direction[i] is not None:
            if possession_ball(ball_coord, allies_coord[i], allies_direction[i]):
                ally_possession = True

    for i in range(3):
        if enemies_coord[i] is not None and enemies_direction[i] is not None:
            if possession_ball(ball_coord, enemies_coord[i], enemies_direction[i]):
                enemy_possession = True


    if ally_possession and not enemy_possession:
        print("ATACAR!")
    elif enemy_possession and not ally_possession:
        print("DEFENDER!")
    elif ally_possession and enemy_possession:
        print("BOLA DIVIDIDA!")
    else:
        print("BOLA LIVRE!")


# Verificar aliado mais próximo da bola 
def calculate_distance_to_ball(xb, yb, coord_allies):

    closer = None
    min_distance = None

    for i in range(3):
        if (coord_allies[i] is not None):
            dx = abs(xb - coord_allies[i][0])
            dy = abs(yb - coord_allies[i][1])
            distance = np.sqrt((dx**2)+(dy**2))

            if min_distance is None:
                min_distance = distance
                closer = i
            else:
                if distance < min_distance:
                    min_distance = distance
                    closer = i

    return closer

################################################################
# Função principal que recebe os dados das coordenadas dos objetos
def recieve_data(self, ball, allies, enemies, clientMQTT):
    print("Dados recebidos")

    if ball is not None:
        ball_coord = np.array([ball.position[0], ball.position[1]])

    allies_coord = [None, None, None]
    allies_direction = [None, None, None]

    for i in range(3):
        if allies[i] is not None:
            allies_coord[i] = np.array([allies[i].position[0], allies[i].position[1]])
    for i in range(3):
        if allies[i] is not None:
            allies_direction[i] = np.array([allies[i].direction[0], allies[i].direction[1]])

    enemies_coord = [None, None, None]
    enemies_direction = [None, None, None]

    for i in range(3):
        if enemies[i] is not None:
            enemies_coord[i] = np.array([enemies[i].position[0], enemies[i].position[1]])
    for i in range(3):
        if enemies[i] is not None:
            enemies_direction[i] = np.array([enemies[i].direction[0], enemies[i].direction[1]])


    if ball_coord is not None:
        team_with_possession(ball_coord, allies_coord, allies_direction, enemies_coord, enemies_direction)
    # angle = angle_player_ball(ball_coord, allies_coord[0], allies_direction[0])
    # print(f"Ângulo jogador/bola: {angle}°")
    # print(f"Jogador com a posse da bola: {possession_ball(ball_coord, allies_coord[0], angle)}")


    xb = ball.position[0]
    yb = ball.position[1]
    # Chamada de outras funções
    ally_closest = calculate_distance_to_ball(xb, yb, allies_coord)

    # O retorno desta função deverá conter um array ou json com todos os comandos dos robôs
    return ally_closest
