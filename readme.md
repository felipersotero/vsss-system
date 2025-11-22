# VSSS System ⚽️🤖

Bem-vindo ao VSSS System — um kit modular de visão computacional e controle para Very Small Size Soccer (VSSS).
É prático, extensível e feito para acelerar experimentos com visão, controle e comunicação de robôs pequenos.

Por que o VSSS System?

* Pipeline de visão pronto para detectar campo, bola e robôs em tempo real.
* Emulador multi-thread para orquestrar captura, visão, controle e comunicação.
* Interface gráfica (Tkinter) para experimentar parâmetros sem mexer em código.
* Suporte opcional a GPU (CUDA) para quem quer rodar mais rápido.

---

## Arquitetura e Módulos

O projeto é organizado em módulos para facilitar manutenção, testes e extensibilidade:

1. **Detector (src/modules/VisionSys/detectorV2.py)**

   * Núcleo da visão computacional.
   * Processa imagens para detectar bola, robôs aliados e inimigos.
   * Integração com filtro de Kalman para predição de posições.
   * Utiliza `TreeColors` para identificação de robôs por cores HSV.

2. **Emulador (src/modules/emulator)**

   * Coordena threads de captura, processamento e comunicação.
   * Mantém filas de frames e eventos para garantir execução estável.
   * Exibe métricas de performance e FPS em tempo real.

3. **Interface Gráfica / UI (src/ui)**

   * Cards de informação, ajustes de parâmetros e visualização de ROI.
   * Menu de configuração de cores, thresholds, offsets e modos de captura.
   * Mostra imagens de debug, máscaras binárias e posições detectadas.

4. **Assets e Configurações (src/data, src/images)**

   * Imagens de referência, logos, planos de fundo e presets.
   * Arquivos de configuração para cores, tamanhos e parâmetros de visão.

5. **Entrada Principal (main.py)**

   * Inicializa módulos, threads e UI.
   * Seleciona modo de execução: câmera, vídeo ou imagem estática.
   * Carrega configurações e inicia loop principal do sistema.

Essa divisão modular permite que cada componente seja testado ou substituído independentemente, por exemplo:

* Trocar o módulo de captura de vídeo sem alterar a detecção.
* Atualizar o detector para novas cores de robôs sem modificar o emulador.
* Acrescentar estratégias ou comunicação adicional como módulos separados.

---

## Filtro de Kalman

O **Filtro de Kalman** é utilizado no VSSS System para **predizer posições futuras da bola e dos robôs**, reduzindo o ruído das medições de visão e permitindo criar **ROIs mais precisas**.

Características principais:

* **Previsão e correção**: o filtro estima a posição e velocidade baseada em medições anteriores e corrige com a medição atual.
* **ROI dinâmica**: a posição prevista do objeto define uma região de interesse (ROI), tornando o processamento mais eficiente.
* **Redução de falsos positivos**: mesmo se uma detecção falhar em um frame, a predição mantém a estimativa estável.
* **Multi-objeto**: cada robô possui seu próprio Kalman, permitindo rastrear aliados e inimigos independentemente.

Benefícios:

* Processamento mais rápido, pois apenas pequenas regiões são analisadas.
* Menor chance de "sumir" um robô ou bola em frames consecutivos.
* Integração direta com `search_bot` e `search_ball`.

---

## Detecção com `filtered_detection`

O método `filtered_detection` é o **pipeline central de visão** do VSSS System. Ele combina:

1. **Entrada de imagem completa** (`img`) ou recortada (`fieldReduce`).
2. **Filtros de Kalman** para prever ROI de bola e robôs.
3. **Máscaras globais e locais** para binarização da bola, aliados e inimigos.
4. **Chamadas seguras** (`_safe_call`) para:

   * `search_ball` → detecta a bola dentro da ROI prevista.
   * `search_bots` → detecta robôs na imagem e atualiza posições.
   * `drawAllRobots` → desenha os robôs detectados na imagem final.
5. **Atualização de máscaras globais** (`binaryBall`, `binaryPlayers`, `binaryAllTeam`) compatíveis com `fieldReduce`.

Fluxo resumido:

* Inicializa contadores e máscaras zeradas.
* Ajusta o recorte `fieldReduce` com base na câmera ou ROI da visão.
* Executa predição da bola via Kalman e chama `search_ball`.
* Executa busca de todos os robôs via `search_bots`, atualizando cores, coordenadas e direção.
* Atualiza imagens de debug e máscaras globais.
* Retorna a imagem processada com todos os elementos detectados.

Benefícios:

* Pipeline **leve e seguro**, protegido contra travamentos durante a detecção.
* Processamento **focado apenas nas regiões de interesse**, aumentando FPS.
* Compatível com múltiplos modos de execução: câmera ao vivo, vídeo ou imagens estáticas.

---

## Quick Start (rápido)

1. Clone o repositório:

   ```bash
   git clone <seu-repositorio>
   ```
2. Instale dependências (duas opções, descritas abaixo).
3. Rode:

   ```bash
   python main.py
   ```
4. Abra a interface e ajuste cores / fontes de captura no menu de configurações.

---

## Instalação — escolha sua forma

**Opção A — pip (terminal)**

* Recomendado para usuários confortáveis com terminal:

  ```bash
  python -m pip install -r src/data/requirements.txt
  ```

**Opção B — instalador gráfico (install.py)**

* Executa verificação e instala pacotes via GUI, útil para iniciantes:

  ```bash
  python install.py
  ```
* O instalador confirma pacotes, mostra progresso e permite iniciar o app ao final.

Dica: se preferir, o main.py também pode acionar rotinas de instalação (ver comentários em main.py).

---

## Uso e modos de execução

* **Modo imagem (estático)**: ideal para testes rápidos com screenshots.
* **Modo vídeo**: processa arquivos de vídeo.
* **Modo câmera (USB/interna)**: captura ao vivo e exibe resultados em tempo real.
* Ative debug na UI para ver máscaras binárias e janelas de busca.

---

## Seções úteis

* **Configurações**: ajuste offset, thresholds e cores no menu de configurações (UI).
* **Logs e performance**: o emulador fornece tempos de processamento e FPS via cards.
* **Comunicação**: suporte MQTT e Serial — configure no painel de comunicação.

---

## Conselhos práticos

* Problemas com a câmera? Verifique permissões, índice e drivers.
* Resultado ruim em pouca luz? Aumente saturação ou use iluminação melhor.
* Quer desempenho? Use OpenCV com suporte CUDA e habilite UseCuda.

---

## Comunidade e contribuição

* Abra issues para bugs, discussões ou sugestões.
* PRs pequenas e comentadas são bem-vindas — explique mudanças e teste localmente.
* Siga o padrão de branches: feature/x, fix/x, docs/x.

---

## Código de conduta

* Seja respeitoso nas discussões, mantenha comunicação construtiva e cite referências quando usar código de terceiros.

---

## Colaboradores

* GN0M10
* Contribuidores futuros: seu nome aqui! 🙌

---

## Checklist do projeto

* [x] Sistema de Visão V2
* [x] Emulador multi-thread
* [x] Interface gráfica básica
* [x] Comunicação MQTT/Serial
* [x] Filtro de Kalman integrado
* [x] Pipeline `filtered_detection`
* [ ] Otimizações CUDA
* [ ] Sistema de estratégia
* [ ] Documentação completa
* [ ] Testes unitários
* [ ] Exemplos e tutoriais

---

## Patch Notes (resumido)

### v3.2.2 — 2025-11-21

* Atualização do pipeline de detecção de robôs e bola.
* Integração total com `TreeColors` para identificação de robôs por cores.
* Melhorias no filtro de Kalman para ROI dinâmica e previsões estáveis.
* Máscaras globais agora compatíveis com `fieldReduce`.
* Debug mais detalhado: prints de detecção de cada robô e contornos globais.
* Correção de coordenadas absolutas e janelas internas.
* Estabilidade aumentada no processamento multi-thread.

### v3.2.0

* Melhorias no pré-processamento de imagem e morphologia.
* Atualização de tolerâncias HSV em `TreeColors`.
* Otimizações leves no `search_bot` e cálculo de direção.

### v3.0.1 — 2024-02-14

* Atualização de classes base e documentação.
* Melhor gerenciamento de threads e filas.
* Novo debug com menor overhead.
* Correções de estabilidade no processamento de imagens.

### v3.0.0

* Reescrita parcial do pipeline de detecção.
* Implementação inicial de EKF para robôs.
* Melhorias em pré-processamento e filtragem.

---

## Licença

* MIT — veja o arquivo LICENSE.

---

## Precisa de ajuda?

* Abra uma issue descrevendo:

  1. Ambiente (SO, Python, OpenCV)
  2. Passos para reproduzir
  3. Logs/prints relevantes

---
