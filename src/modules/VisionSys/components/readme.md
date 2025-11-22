

# 🚀 **O QUE É A TREECOLORS E POR QUE EXISTE?**

A ideia é simples:

Quando você detecta um robô no frame, você extrai **três cores**:

* **main** – geralmente a cor dominante do time ou a cor maior no topo
* **primary** – cor de identificação principal do robô
* **secondary** – cor auxiliar/identificadora

O problema:

* HSV tem ruído (sombras, reflexos, iluminação)
* HUE é circular (0 é parecido com 179!)
* Comparar tudo “na mão” é lento e manual
* O pipeline roda por **ROI**, então você quer uma forma *barata* de testar candidatos

A **TreeColors** resolve isso criando uma estrutura *rápida*, *em memória*, com pré-cálculo de ranges e funções de lookup quase O(1) para descobrir:

👉 “Qual robô tem essa combinação de cores?”
👉 “Quais são as cores salvas do robô X?”
👉 “Essas cores batem com os limites permitidos do robô Y?”

Ou seja: **é um dicionário inteligente com bounds + distância circular entre cores**.

---

# 🧠 **ESTRUTURA INTERNA**

## **1) Dicionário principal `_store`**

```python
self._store: Dict[Any, Dict[str, Any]]
```

Cada entrada é:

```
robot_id → {
    team: ...
    colors: { main: HSV, primary: HSV, secondary: HSV },
    bounds: { main: (low, high), ... },
    tolerances: { hue_tol, sat_tol, val_tol }
}
```

**Por que isso é top?**
Porque tudo fica em memória → lookup instantâneo → zero custo de disco.

---

# 🎯 **2) Pré-cálculo de bounds (faixa HSV permitida)**

Cada cor (main/primary/secondary) recebe:

```python
lower = [h - tolH, s - tolS, v - tolV]
upper = [h + tolH, s + tolS, v + tolV]
```

==> **Mas o HUE é circular**, então usamos módulo 180 para wrap-around.

**Por que bounds?**
Porque testar se uma cor está dentro de um range é ridiculamente barato:

```python
if H está entre H_low e H_high  
   E S está entre S_low e S_high  
   E V está entre V_low e V_high:
          passou!
```

Esse teste evita você rodar distância circular em cada robô → **ganho enorme de desempenho**.

---

# 🔄 **3) Função de distância circular no HUE**

```python
def hue_circ_dist(h1, h2):
    d = abs(h1 - h2)
    return min(d, 180 - d)
```

Por que isso importa?

* Se um robô é vermelho (H = 175) e o outro vermelho (H = 5)
  → diferença real é 10°, mas diferença linear é 170°
  → circular = **perfeito**

---

# 🏎️ **4) _score_distance()**

A métrica fina usada **só nos candidatos que passaram no bound**.

```python
score = w_hue*dh + w_sat*ds + w_val*dv
```

* HUE tem peso maior (é mais confiável)
* Saturation/Value têm influência pequena (ruído de iluminação)

**Por que isso?**
Porque HSV tem tolerância diferente por canal:

* Hue carrega a identidade da cor
* Saturation/Value flutuam mais por sombras/iluminação

Resultado: um número tipo 0..200.

Menor = mais parecido.

---

# 🔍 **5) find_by_colors()**

Esse é o coração da classe.

Pipeline interno:

### **(1) Filtragem por bounds — baratíssimo**

Vai para cada robô armazenado e checa:

```
main dentro do bound?
primary dentro do bound?
secondary dentro do bound?
```

Se sim → entra como candidato.

### **(2) Se nenhum candidato passou**

Relaxamos:

* Aceitar somente main + primary
* Ou até só main (dependendo da config)

Isso evita perder robôs quando a secondary estiver ruim.

### **(3) Métrica final**

Entre os candidatos restantes, calcula score via `_score_distance`.

### **(4) Pega o menor score**

Se estiver abaixo do threshold (200 por padrão):

```python
return { robot_id, team, score, colors }
```

senão:

```python
return None
```

---

# 📦 **6) get_colors(robot_id)**

Retorna:

```
array([
   [H,S,V]  main,
   [H,S,V]  primary,
   [H,S,V]  secondary
])
```

Sempre na ordem correta, exatamente como você pediu.

---

# 🧱 **7) update_robot_colors()**

Permite atualizar cores dos inimigos **durante o jogo**.

Isso é MUITO útil se:

* iluminação muda
* o sistema começa a convergir para cores reais do frame live

E automaticamente recalcula bounds.

---

# 🤝 **8) integrate com seu pipeline**

## No início do jogo:

```python
tree = TreeColors()
tree.add_robot(robot.id, robot.team, main_hsv, pri_hsv, sec_hsv)
```

## Dentro de search_bot() ou no pipeline pós-detecção:

```python
result = tree.find_by_colors(main, primary, secondary)

if result:
    rob_id = result['robot_id']
    # acabou, você encontrou o robô!
```

## Quando quiser salvar as cores do robô detectado:

```python
tree.update_robot_colors(robot_id, main, pri, sec)
```

---

# 🧠 **DECISÕES DE ALGORITMO — POR QUE FEITO ASSIM?**

## **1) Dicionário ao invés de árvore real**

Porque você trabalha com algo como ~6 robôs.
Estruturas como *k-d trees*, *quadtrees* ou *BK trees* seriam overhead.

Dicionário → acesso O(1).
Bounds + filtragem → O(robôs) = 6.
Score refinado → geralmente 1~3 candidatos.

Ou seja: **máximo performance com mínimo overhead**.

---

## **2) Pré-cálculo dos bounds**

Se você calculasse cada bound a cada lookup → ~200 operações por frame → desperdício.

Pré-calcular torna o lookup muito rápido.

---

## **3) Bound check antes da distância**

É *crucial*.

Imagine que ROI inclui 4 robôs.
Você extrai uma cor qualquer.

Bounds filtram 3 robôs imediatamente.
Só 1 vai pra métrica.

É isso que deixa o pipeline viável em 30/60 FPS.

---

## **4) Distância circular apenas quando necessário**

Evita custo desnecessário:

* sem trigonometria
* sem raiz quadrada
* sem operações lentas

A fórmula é leve.

---

# 🏁 **RESUMO MENTAL**

Quando você extrai cores do robô detectado:

1. **TreeColors.find_by_colors()**
2. Bound filter → rápido
3. Score → preciso
4. Retorna robô correto

Quando detectar corretamente, você salva o contorno global dele, atualiza posição, marca status True.

É exatamente o que você quer para evitar processar a mesma cor repetidamente.


