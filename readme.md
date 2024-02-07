O arquivo principal é o main.py, este arquivo executa o arquivo app.py.
# app.py
Este arquivo contém a criação da tela principal da aplicação, a classe App.
Em seu construtor ```def __init__(self)``` é feita a configuração do design da tela principal em ```self.configure_window()```, a criação dos 3 frames principais da applicação, configurações, imagens e dados, em ```self.create_main_frames()``` e a criação dos frames (subframes de configurações) em ```self.create_settings_frame()```.

Em seguida é feita a criação dos widgets (textos, botões, imagens, etc) dos frames criados em ```widgets_settings_frame()```, ```self.widgets_emulate_frame()``` e ```widgets_images_frame```, para o frame de configurações, de emulação (botão de iniciar emulação) e imagens de debug, respectivamente.

Em seguida são criados objetos MyViewer, as tabs para visualização das imagens de debug.

E por fim, ainda no construtor, é criada a instância do emulador: Emulator.

---
Abaixo, fora do construtor, mas ainda dentro da classe App, estão as funções de configuração e criação de frames e widgets, que são chamadas lá no construtor.

Em especial, a função ```build_tree_menu()``` cria uma lista de árvore com elementos do tipo ```settingsMenu```.

# settingsMenu.py

Este arquivo contém a definição da lista de árvore para as configurações das variáveis de execução do programa.

Possui as funções de criação e acesso aos nós: ```add_node``` e ```att_node_id```
Possui a função para quando um dos campos for clicado ```on_double_click```. Essa função lida com a alteração dos campos.
Possui as funções para leitura de dados ```get_tree_data```, além das funções para leitura e salvamento dos arquivos json ```save_to_json```, ```load_from_json```, ```load_from_json_recursive``` e ```load_from_json_file```.

# viewer.py

Possui a criação das telas para visualização das imagens de debug.
Possui duas classes.
A classe myViewer possui obviamente o construtor e as seguintes funções:
config, reset_config, default_mode e show

# emulator.py

Este arquivo é organizado nos seguintes pontos.

#### Criação da classe e construtor
O construtor cria as variáveis que serão utilizadas depois.

#### Funções gerais
A função ```load_vars``` carrega as variáveis salvas no json e as formata com ```format_var```.
init, stop, 

#### Funções de execução
processUSB, processImage, processVideo

# detector.py

Este arquivo pode ser analisado a partir de trtês blocos:
* Classes
* Funções Auxiliares
* Funções Modulares

#### Classes

Esta parte lida com a criação das classes ```Robot```, ```Ball``` e ```Field```.

#### Funções Auxiliares

Nesta parte são criadas funções que realizam ações simples como filtrar uma imagem, criar máscaras de cores, etc. Essas funções serão utilizadas nas funções principais: as funções modulares.

#### Funções Modulares

São as funções principais no reconhecimento do campo, da bola e dos jogadores.

##### ```detect_field```

##### ```detect_ball```

##### ```detect_players```