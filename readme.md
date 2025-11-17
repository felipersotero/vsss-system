# VSSS System ⚽️🤖

Bem-vindo ao VSSS System — um kit modular de visão computacional e controle para Very Small Size Soccer (VSSS).  
É prático, extensível e feito para acelerar experimentos com visão, controle e comunicação de robôs pequenos.

Por que o VSSS System?
- Pipeline de visão pronto para detectar campo, bola e robôs em tempo real.
- Emulador multi-thread para orquestrar captura, visão, controle e comunicação.
- Interface gráfica (Tkinter) para experimentar parâmetros sem mexer em código.
- Suporte opcional a GPU (CUDA) para quem quer rodar mais rápido.

Vamos lá — rápido overview
- Detector (src/modules/VisionSys/detectorV2.py): núcleo de visão, detecção e predição.
- Emulador (src/modules/emulator): coordena captura, threads, UI e comunicação.
- UI (src/ui): visualização, cards e menu de configurações.
- Assets e configuração: src/data, src/images
- Entrada principal: main.py

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

## Instalação — escolha sua forma

**Opção A — pip (terminal)**
- Recomendado para usuários confortáveis com terminal:
  ```bash
  python -m pip install -r src/data/requirements.txt
  ```

**Opção B — instalador gráfico (install.py)**
- Executa verificação e instala pacotes via GUI, útil para iniciantes:
  ```bash
  python install.py
  ```
- O instalador confirma pacotes, mostra progresso e permite iniciar o app ao final.

Dica: se preferir, o main.py também pode acionar rotinas de instalação (ver comentários em main.py).

## Uso e modos de execução
- **Modo imagem (estático)**: ideal para testes rápidos com screenshots.
- **Modo vídeo**: processa arquivos de vídeo.
- **Modo câmera (USB/interna)**: captura ao vivo e exibe resultados em tempo real.
- Ative debug na UI para ver máscaras binárias e janelas de busca.

## Seções úteis
- **Configurações**: ajuste ofset, thresholds e cores no menu de configurações (UI).
- **Logs e performance**: o emulador fornece tempos de processamento e FPS via cards.
- **Comunicação**: suporte MQTT e Serial — configure no painel de comunicação.

## Conselhos práticos
- Problemas com a câmera? Verifique permissões, índice e drivers.
- Resultado ruim em pouca luz? Aumente saturação ou use iluminação melhor.
- Quer desempenho? Use OpenCV com suporte CUDA e habilite UseCuda.

## Comunidade e contribuição
- Abra issues para bugs, discussões ou sugestões.
- PRs pequenas e comentadas são bem-vindas — explique mudanças e teste localmente.
- Siga o padrão de branches: feature/x, fix/x, docs/x.

## Código de conduta
- Seja respeitoso nas discussões, mantenha comunicação construtiva e cite referências quando usar código de terceiros.

## Colaboradores
- GN0M10
- Contribuidores futuros: seu nome aqui! 🙌

## Checklist do projeto
- [x] Sistema de Visão V2
- [x] Emulador multi-thread
- [x] Interface gráfica básica
- [x] Comunicação MQTT/Serial
- [ ] Otimizações CUDA
- [ ] Sistema de estratégia
- [ ] Documentação completa
- [ ] Testes unitários
- [ ] Exemplos e tutoriais

## Patch Notes (resumido)
### v3.0.1 — 2024-02-14
- Atualização de classes base e documentação.
- Melhor gerenciamento de threads e filas.
- Novo debug com menor overhead.
- Correções de estabilidade no processamento de imagens.

### v3.0.0
- Reescrita parcial do pipeline de detecção.
- Implementação inicial de EKF para robôs.
- Melhorias em pré-processamento e filtragem.

## Licença
- MIT — veja o arquivo LICENSE.

## Precisa de ajuda?
- Abra uma issue descrevendo:
  1) Ambiente (SO, Python, OpenCV)
  2) Passos para reproduzir
  3) Logs/prints relevantes


