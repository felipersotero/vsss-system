def sort_points(points):
    # Ordena os pontos primeiro pelo y (crescente) e depois pelo x (crescente)
    points = sorted(points, key=lambda p: (p[1], p[0]))
    
    # Depois de ordenados pelo y, verifica os pontos de menor y para definir ponto 0 e ponto 1
    if points[0][0] > points[1][0]:
        points[0], points[1] = points[1], points[0]
    
    # Verifica os pontos de maior y para definir ponto 2 e ponto 3
    if points[2][0] > points[3][0]:
        points[2], points[3] = points[3], points[2]
    
    return points

# Exemplo de uso
points = [(3, 1), (2, 1), (4, 3), (1, 2)]
sorted_points = sort_points(points)

print("Ponto 1:", sorted_points[0])
print("Ponto 0:", sorted_points[1])
print("Ponto 2:", sorted_points[2])
print("Ponto 3:", sorted_points[3])
