# TreeColors

`TreeColors` é uma estrutura de dados em memória projetada para **armazenar, gerenciar e buscar cores de robôs** em sistemas de visão computacional de futebol robótico. Ela permite identificar robôs em uma imagem a partir de suas cores **principais e secundárias** com tolerâncias ajustáveis.

---

## 📌 Motivação

Em cenários de robótica, especialmente em **VSSS (Very Small Size Soccer Simulation)**:

* Cada robô possui cores distintas (ex: corpo principal, detalhes primários e secundários).
* A detecção visual precisa identificar **qual robô específico** está sendo observado, mesmo quando múltiplos robôs estão presentes na mesma ROI (Região de Interesse).
* Para isso, precisamos de:

  * Um cadastro das cores dos robôs.
  * Filtros rápidos para descartar candidatos que não correspondem.
  * Métricas de similaridade para escolher o robô mais provável.

`TreeColors` resolve esse problema fornecendo uma **lookup table otimizada por cores** com suporte a tolerâncias e métricas de correspondência.

---

## ⚙ Estrutura de Dados

Cada robô registrado no `TreeColors` possui:

* **Identificador**: `(team_id, robot_id)`

  * `team_id`: 0 = aliado, 1 = inimigo
  * `robot_id`: 0 = goleiro, 1 = atacante1, 2 = atacante2
* **Cores HSV**:

  * `main`: cor principal do robô
  * `primary`: cor secundária principal
  * `secondary`: cor secundária menor
* **Bounds pré-calculados**:

  * Faixas de HSV para cada cor considerando tolerâncias (`hue_tol`, `sat_tol`, `val_tol`)
* **Metadados**:

  * Tolerâncias de cor
  * Informações adicionais, se necessário

---

## 🔹 Funcionalidades Principais

### 1. Cadastro de robôs

```python
tree = TreeColors()
tree.add_robot(team_id, robot_id, main_hsv, primary_hsv, secondary_hsv)
```

* Armazena as cores do robô e pré-calcula **intervalos de tolerância** (bounds) para buscas rápidas.
* Pode atualizar um robô existente usando `replace=True`.

---

### 2. Atualização de cores

```python
tree.update_robot_colors(team_id, robot_id, main_hsv, primary_hsv, secondary_hsv)
```

* Permite ajustar cores de um robô existente e recalcular os bounds.

---

### 3. Consulta de cores

```python
colors = tree.get_colors(team_id, robot_id)
```

* Retorna um array com `[main, primary, secondary]` do robô.

---

### 4. Busca por cores (`matching`)

```python
match = tree.find_by_colors(main_hsv, primary_hsv, secondary_hsv)
```

* Recebe um conjunto de cores detectadas de um candidato visual.
* Filtra rapidamente candidatos usando os **bounds HSV**.
* Calcula uma métrica de distância de cor (`_score_distance`) considerando:

  * Distância circular do Hue
  * Diferenças de Saturação e Valor
* Retorna o robô mais provável (`robot_id`, `team`, `score`, `colors`) ou `None`.

💡 Caso nenhum robô passe no filtro completo, o filtro é relaxado para **apenas main + primary**, evitando falsos negativos.

---

### 5. Gerenciamento

* `remove_robot(team_id, robot_id)` → remove um robô.
* `list_robots()` → lista todos os robôs cadastrados.
* `clear()` → limpa a árvore.

---

## 🔹 Considerações Técnicas

1. **Hue circular**

   * Como o Hue em OpenCV varia de 0 a 179, o cálculo considera wrap-around para comparação.
2. **Eficiência**

   * O filtro por bounds é aplicado antes do cálculo de score para evitar computações desnecessárias.
3. **Tolerâncias ajustáveis**

   * Permite lidar com variações de iluminação ou pequenas diferenças de cor entre robôs reais e a calibração.

---

## 📌 Exemplo de Uso

```python
tree = TreeColors()

# Adiciona robôs
tree.add_robot(0, 0, [60, 200, 200], [50, 180, 180], [40, 150, 150])  # aliado goleiro
tree.add_robot(1, 0, [0, 200, 200], [10, 180, 180], [20, 150, 150])  # inimigo goleiro

# Detecta cores de um candidato
candidate_main = [62, 198, 210]
candidate_primary = [48, 175, 190]
candidate_secondary = [41, 152, 148]

match = tree.find_by_colors(candidate_main, candidate_primary, candidate_secondary)

if match:
    print(f"Robô detectado: Team={match['team']}, Robot={match['robot_id']}, Score={match['score']}")
```

---

## ✅ Benefícios

* Permite **identificação robusta de robôs mesmo com múltiplos na mesma ROI**.
* Facilita **detecção rápida** sem precisar comparar cada pixel.
* Reduz **falsos positivos** via bounds e score.
* Suporte a **atualização dinâmica** de cores.


