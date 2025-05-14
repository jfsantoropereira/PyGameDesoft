
# ===== Inicialização =====
# ----- Importa e inicia pacotes
import pygame

pygame.init()

# ----- Gera tela principal
WIDTH = 1200
HEIGHT = 700
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Goal Masters')

# ----- Inicia estruturas de dados
game = True

# ----- Inicia assets
imagem_original = pygame.image.load(r"C:\Users\Pe\Downloads\ChatGPT Image 14 de mai. de 2025, 08_12_27.png").convert()
image = pygame.transform.scale(imagem_original, (WIDTH, HEIGHT))

# ----- Inicia fonte para o texto
font = pygame.font.SysFont("Arial", 80)  # Fonte Arial, tamanho 36
text = font.render("Let's play Goal Masters!", True, (0, 0, 0))  # Texto branco

# ===== Loop principal =====
while game:
# ----- Trata eventos
    for event in pygame.event.get():
# ----- Verifica consequências
        if event.type == pygame.QUIT:
            game = False

    # ----- Gera saídas
    window.fill((0, 0, 0))  # Preenche com a cor preta
    window.blit(image, (10, 10))  # Exibe a imagem

    # ----- Exibe o texto na tela
    window.blit(text, (WIDTH // 2 - text.get_width() // 2, 50))  # Centraliza o texto na parte superior da tela

    # ----- Atualiza estado do jogo
    pygame.display.update()  # Mostra o novo frame para o jogador

# ===== Finalização =====
pygame.quit()