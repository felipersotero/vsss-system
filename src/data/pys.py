import concurrent.futures
import time

# Função que será executada de forma linear
def process_data_linear(data):
    result = sum(data) * 1000  # Simulação de uma operação complexa
    return result

# Função que será executada de forma paralela
def process_data_parallel(data):
    results = []
    for d in data:
        result = d * 1000  # Simulação de uma operação complexa
        results.append(result)
    return results

# Dados de entrada
data = list(range(100000))  # Lista com 100000 itens

# Processamento linear
start_time = time.time()
result_linear = process_data_linear(data)
end_time = time.time()
linear_time = end_time - start_time

# Processamento paralelo
start_time = time.time()
with concurrent.futures.ThreadPoolExecutor() as executor:
    # Mapeando a função para cada elemento dos dados de entrada
    results = executor.map(process_data_parallel, [data]*10)

# Convertendo os resultados em uma lista
end_time = time.time()
result_parallel = list(results)

parallel_time = end_time - start_time

print("Tempo de execução do processamento linear:", linear_time)
print("Tempo de execução do processamento paralelo:", parallel_time)
