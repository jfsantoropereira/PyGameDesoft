# ===== Inicialização =====
# ----- Importa e inicia pacotes
import pygame
import pygame.mixer
import os
import sys
import json

# Add the parent directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try:
    from goal_masters.main import Game
except ImportError as e:
    print(f"Error importing game: {e}")
    print("Make sure you're running the script from the correct directory")
    sys.exit(1)

pygame.init()
pygame.mixer.init()

# ----- Gera tela principal
WIDTH = 1200
HEIGHT = 700
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Goal Masters')

# ----- Inicia estruturas de dados
game = True

# ----- Inicia assets
imagem_original = pygame.image.load("PyGameDesoft/imagens/imagem inicial.png").convert()
image = pygame.transform.scale(imagem_original, (WIDTH, HEIGHT))

# ----- Inicia fonte para o texto
font = pygame.font.SysFont("Arial", 80)  # Fonte Arial, tamanho 80
title_font = pygame.font.SysFont("Arial", 80)
button_font = pygame.font.SysFont("Arial", 50)

# Adicionar uma fonte menor para o contador de moedas
coin_font = pygame.font.SysFont("Arial", 28)

# ----- Cores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

# ===== Classe para botões
class Button:
    def __init__(self, x, y, width, height, text, color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.is_hovered = False

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
        pygame.draw.rect(surface, BLACK, self.rect, 2)
        text_surface = button_font.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

# ----- Função para tela da loja

def store_screen():
    # Carrega imagens dos jogadores
    elvis_img = pygame.image.load("PyGameDesoft/imagens/Elvis.png").convert_alpha()
    neymar_img = pygame.image.load("PyGameDesoft/imagens/Neymar.png").convert_alpha()
    ronaldinho_img = pygame.image.load("PyGameDesoft/imagens/Ronaldinho.png").convert_alpha()
    roberto_img = pygame.image.load("PyGameDesoft/imagens/Roberto Carlos.png").convert_alpha()
    juninho_img = pygame.image.load("PyGameDesoft/imagens/Juninho Pernambucano.png").convert_alpha()
    cadeado_img = pygame.image.load("PyGameDesoft/imagens/cadeado.png").convert_alpha()

    # Redimensiona as imagens para caberem na tela
    char_width, char_height = 200, 250
    cadeado_size = 80
    elvis_img = pygame.transform.scale(elvis_img, (char_width, char_height))
    neymar_img = pygame.transform.scale(neymar_img, (char_width, char_height))
    ronaldinho_img = pygame.transform.scale(ronaldinho_img, (char_width, char_height))
    roberto_img = pygame.transform.scale(roberto_img, (char_width, char_height))
    juninho_img = pygame.transform.scale(juninho_img, (char_width, char_height))
    cadeado_img = pygame.transform.scale(cadeado_img, (char_width, char_height))

    # Botão de voltar
    back_button = Button(50, 50, 200, 70, "Back", (180, 180, 180))

    # Dados dos personagens
    characters = [
        {"name": "Elvis", "img": elvis_img, "pos": None, "price": 0},
        {"name": "Neymar", "img": neymar_img, "pos": None, "price": 50},
        {"name": "Ronaldinho", "img": ronaldinho_img, "pos": None, "price": 100},
        {"name": "Roberto Carlos", "img": roberto_img, "pos": None, "price": 200},
        {"name": "Juninho Pernambucano", "img": juninho_img, "pos": None, "price": 500},
    ]

    # Posições
    y_top = 140
    y_bottom = 370
    characters[0]["pos"] = (WIDTH//2 - 250, y_top)
    characters[1]["pos"] = (WIDTH//2 + 50, y_top)
    characters[2]["pos"] = (WIDTH//2 - 400, y_bottom)
    characters[3]["pos"] = (WIDTH//2 - 100, y_bottom)
    characters[4]["pos"] = (WIDTH//2 + 200, y_bottom)

    running = True
    global player_data
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if back_button.is_clicked(event.pos):
                    running = False
                else:
                    for char in characters:
                        rect = pygame.Rect(char["pos"][0], char["pos"][1], char_width, char_height)
                        if rect.collidepoint(event.pos):
                            if char["name"] in player_data['unlocked']:
                                player_data['selected'] = char["name"]
                                save_player_data(player_data)
                            elif player_data['coins'] >= char["price"] and char["price"] > 0:
                                player_data['coins'] -= char["price"]
                                player_data['unlocked'].append(char["name"])
                                player_data['selected'] = char["name"]
                                save_player_data(player_data)

        # Fundo igual ao da tela inicial
        window.fill((0, 0, 0))
        window.blit(image, (10, 10))

        # Título
        store_title = title_font.render("Character Store", True, BLACK)
        window.blit(store_title, (WIDTH // 2 - store_title.get_width() // 2, 50))

        # Desenha personagens
        for char in characters:
            window.blit(char["img"], char["pos"])
            if char["name"] != "Elvis":
                coin_image = pygame.image.load(os.path.join(os.path.dirname(__file__), 'imagens', 'moeda.png'))
                coin_image = pygame.transform.scale(coin_image, (40, 40))
                price_text = coin_font.render(str(char["price"]), True, (255, 255, 0))
                window.blit(coin_image, (char["pos"][0] + 80, char["pos"][1] + 230))
                window.blit(price_text, (char["pos"][0] + 125, char["pos"][1] + 245))
            # Cadeado se não desbloqueado
            if char["name"] not in player_data['unlocked']:
                window.blit(cadeado_img, char["pos"])
            # Destaque se selecionado
            if char["name"] == player_data['selected']:
                pygame.draw.rect(window, (255, 215, 0), (char["pos"][0], char["pos"][1], char_width, char_height), 5)

        # Botão de voltar
        back_button.draw(window)

        # Exibe moedas do jogador
        coin_image = pygame.image.load(os.path.join(os.path.dirname(__file__), 'imagens', 'moeda.png'))
        coin_image = pygame.transform.scale(coin_image, (50, 50))
        window.blit(coin_image, (10, 10))
        coin_text = coin_font.render(str(player_data['coins']), True, (255, 255, 0))
        window.blit(coin_text, (65, 35))

        pygame.display.update()

# ----- Cria os botões
start_button = Button(WIDTH//2 - 200, HEIGHT//2, 400, 100, "Start", GREEN)
store_button = Button(WIDTH//2 - 200, HEIGHT//2 + 150, 400, 100, "Store", RED)

# Adiciona botão de opções de música (agora menor e no canto inferior direito)
music_options_button = Button(WIDTH - 170, HEIGHT - 70, 150, 40, "Music", (100, 100, 255))

# Função para menu de música
def music_menu():
    # Define botões das músicas
    music1_button = Button(WIDTH//2 - 150, HEIGHT//2 - 100, 300, 70, "POMPEII", (200, 200, 200))
    music2_button = Button(WIDTH//2 - 150, HEIGHT//2, 300, 70, "Kids", (200, 200, 200))
    music3_button = Button(WIDTH//2 - 150, HEIGHT//2 + 100, 300, 70, "My Type", (200, 200, 200))
    back_button = Button(WIDTH//2 - 60, HEIGHT//2 + 200, 120, 50, "Voltar", (180, 180, 180))

    # Variável para controlar a música atual
    current_music = None
    is_playing = False

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if music1_button.is_clicked(event.pos):
                    if current_music == "pompeii" and is_playing:
                        pygame.mixer.music.stop()
                        is_playing = False
                    else:
                        pygame.mixer.music.stop()
                        pygame.mixer.music.load("PyGameDesoft/imagens/Bastile- Pompeii.mp3")
                        pygame.mixer.music.play(-1)
                        current_music = "pompeii"
                        is_playing = True
                elif music2_button.is_clicked(event.pos):
                    if current_music == "kids" and is_playing:
                        pygame.mixer.music.stop()
                        is_playing = False
                    else:
                        pygame.mixer.music.stop()
                        pygame.mixer.music.load("PyGameDesoft/imagens/MGMT - Kids (1.1x).mp3")
                        pygame.mixer.music.play(-1)
                        current_music = "kids"
                        is_playing = True
                elif music3_button.is_clicked(event.pos):
                    if current_music == "mytype" and is_playing:
                        pygame.mixer.music.stop()
                        is_playing = False
                    else:
                        pygame.mixer.music.stop()
                        pygame.mixer.music.load("PyGameDesoft/imagens/SAINT MOTEL - My Type.mp3")
                        pygame.mixer.music.play(-1)
                        current_music = "mytype"
                        is_playing = True
                elif back_button.is_clicked(event.pos):
                    running = False

        window.fill((0, 0, 0))
        window.blit(image, (10, 10))
        title = title_font.render("Escolha a Música", True, BLACK)
        window.blit(title, (WIDTH//2 - title.get_width()//2, 80))
        music1_button.draw(window)
        music2_button.draw(window)
        music3_button.draw(window)
        back_button.draw(window)
        pygame.display.update()

# ===== Loop principal =====
while game:
    # ----- Trata eventos
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if store_button.is_clicked(event.pos):
                store_screen()
            elif start_button.is_clicked(event.pos):
                try:
                    # Initialize and run the game
                    game_instance = Game()
                    game_instance.run()
                except Exception as e:
                    print(f"Error starting game: {e}")
            elif music_options_button.is_clicked(event.pos):
                music_menu()

    # ----- Gera saídas
    window.fill((0, 0, 0))  # Preenche com a cor preta
    window.blit(image, (10, 10))  # Exibe a imagem

    # ----- Exibe o texto na tela
    title_text = title_font.render("Let's play Goal Masters!", True, BLACK)
    window.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, 50))

    # ----- Desenha os botões
    start_button.draw(window)
    store_button.draw(window)
    music_options_button.draw(window)

    # ----- Desenhar a moeda e o contador de moedas
    coin_image = pygame.image.load(os.path.join(os.path.dirname(__file__), 'imagens', 'moeda.png'))
    coin_image = pygame.transform.scale(coin_image, (50, 50))
    window.blit(coin_image, (10, 10))
    coin_text = coin_font.render(str(0), True, (255, 255, 0))
    window.blit(coin_text, (65, 35))

    # ----- Atualiza estado do jogo
    pygame.display.update()  # Mostra o novo frame para o jogador

# ===== Finalização =====
pygame.quit()

PLAYER_DATA_FILE = os.path.join(os.path.dirname(__file__), 'player_data.json')

DEFAULT_PLAYER_DATA = {
    'coins': 0,
    'unlocked': ['Elvis'],
    'selected': 'Elvis'
}

def load_player_data():
    if not os.path.exists(PLAYER_DATA_FILE):
        save_player_data(DEFAULT_PLAYER_DATA)
        return DEFAULT_PLAYER_DATA.copy()
    with open(PLAYER_DATA_FILE, 'r') as f:
        return json.load(f)

def save_player_data(data):
    with open(PLAYER_DATA_FILE, 'w') as f:
        json.dump(data, f)

player_data = load_player_data()