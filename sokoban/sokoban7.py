import sys
import pygame
import queue

# Função lambda de alta ordem (aceita uma função como argumento)
quit_action_higher_order = lambda quit: lambda: print('quit') or quit()
# Aplicando da função lambda de alta ordem
quit_action = quit_action_higher_order(quit)

# Função lambda recursiva para verificar se o jogo foi concluído
is_completed_recursive = lambda matrix, y=0: all('$' not in row for row in matrix) if y == len(matrix) else is_completed_recursive(matrix, y + 1)

# Monad
class Result:
    def __init__(self, value, error=None):
        self.value = value
        self.error = error

    def is_ok(self):
        return self.error is None

    def is_error(self):
        return not self.is_ok()

    def unwrap(self):
        if self.is_ok():
            return self.value
        else:
            raise RuntimeError("Cannot unwrap an error result")

    def bind(self, func):
        if self.is_ok():
            try:
                return func(self.value)
            except Exception as e:
                return Result(error=str(e))
        else:
            return self

    def __str__(self):
        if self.is_ok():
            return f"Ok({self.value})"
        else:
            return f"Error({self.error})"

# Classe que representa o jogo Sokoban
class Game:

    # Inicializa uma LIFO para acompanhar os movimentos do jogador
    def __init__(self, filename, level, quit_action):
        self.queue = queue.LifoQueue()
        self.matrix = []
        self.quit_action = quit_action

        # Verificação de nível no jogo
        if level < 1:
            error_message = f"Level {level} is out of range"
            print(f"ERROR: {error_message}")
            sys.exit(1)
        else:
            result = self.load_level(filename, level)
            if result.is_error():
                print(f"ERROR: {result.error}")
                sys.exit(1)

    def load_level(self, filename, level):
        try:
            with open(filename, 'r') as file:
                level_found = False
                for line in file:
                    row = []
                    if not level_found:
                        if f"Level {level}" == line.strip():
                            level_found = True
                    else:
                        if line.strip() != "":
                            row = [c for c in line if c != '\n' and self.is_valid_value(c)]
                            self.matrix.append(row)
                        else:
                            break
            return Result(value=None)
        except Exception as e:
            return Result(error=str(e))

    # Verifica se um caractere é um valor válido no jogo
    def is_valid_value(self, char):
        return char in [' ', '#', '@', '.', '*', '$', '+']

    # Calcula o tamanho da tela com base na matriz do jogo
    def load_size(self):
        x = max(len(row) for row in self.matrix)
        y = len(self.matrix)
        return (x * 32, y * 32)

    # Retorna a matriz do jogo
    def get_matrix(self):
        return self.matrix

    # Obtém o conteúdo da posição (x, y) na matriz
    def get_content(self, x, y):
        return self.matrix[y][x]

    # Define o conteúdo da posição (x, y) na matriz
    def set_content(self, x, y, content):
        if self.is_valid_value(content):
            self.matrix[y][x] = content
        else:
            print("ERROR: Value '" + content + "' to be added is not valid")
    
    # Localiza a posição do trabalhador na matriz
    def worker(self):
        for y, row in enumerate(self.matrix):
            for x, char in enumerate(row):
                if char == '@' or char == '+':
                    return (x, y, char)

    # Verifica se é possível mover o trabalhador na direção (x, y)
    def can_move(self, x, y):
        return self.get_content(self.worker()[0] + x, self.worker()[1] + y) not in ['#', '*', '$']

    # Retorna o conteúdo da próxima posição na direção (x, y)
    def next(self, x, y):
        return self.get_content(self.worker()[0] + x, self.worker()[1] + y)
    
    # Verifica se é possível empurrar uma caixa na direção (x, y)
    def can_push(self, x, y):
        next_char = self.next(x, y)
        next_next_char = self.next(x + x, y + y)
        return next_char in ['*', '$'] and next_next_char in [' ', '.']

    # Verifica se o jogo foi concluído (todas as caixas estão nas docas)
    def is_completed(self):
        #return all('$' not in row for row in self.matrix)
        return is_completed_recursive(self.matrix)

    # Move uma caixa de (x, y) para (x + a, y + b)
    def move_box(self, x, y, a, b):
        current_box = self.get_content(x, y)
        future_box = self.get_content(x + a, y + b)
        if current_box == '$' and future_box == ' ':
            self.set_content(x + a, y + b, '$')
            self.set_content(x, y, ' ')
        elif current_box == '$' and future_box == '.':
            self.set_content(x + a, y + b, '*')
            self.set_content(x, y, ' ')
        elif current_box == '*' and future_box == ' ':
            self.set_content(x + a, y + b, '$')
            self.set_content(x, y, ' ')
        elif current_box == '*' and future_box == '.':
            self.set_content(x + a, y + b, '*')
            self.set_content(x, y, '.')

    # Desfaz o último movimento
    def unmove(self):
        if not self.queue.empty():
            movement = self.queue.get()
            if movement[2]:
                current = self.worker()
                self.move(movement[0] * -1, movement[1] * -1, False)
                self.move_box(current[0] + movement[0], current[1] + movement[1], movement[0] * -1, movement[1] * -1)
            else:
                self.move(movement[0] * -1, movement[1] * -1, False)

    # Move o trabalhador na direção (x, y)
    def move(self, x, y, save):
        if self.can_move(x, y):
            current = self.worker()
            future = self.next(x, y)
            if current[2] == '@' and future == ' ':
                self.set_content(current[0] + x, current[1] + y, '@')
                self.set_content(current[0], current[1], ' ')
                if save:
                    self.queue.put((x, y, False))
            elif current[2] == '@' and future == '.':
                self.set_content(current[0] + x, current[1] + y, '+')
                self.set_content(current[0], current[1], ' ')
                if save:
                    self.queue.put((x, y, False))
            elif current[2] == '+' and future == ' ':
                self.set_content(current[0] + x, current[1] + y, '@')
                self.set_content(current[0], current[1], '.')
                if save:
                    self.queue.put((x, y, False))
            elif current[2] == '+' and future == '.':
                self.set_content(current[0] + x, current[1] + y, '+')
                self.set_content(current[0], current[1], '.')
                if save:
                    self.queue.put((x, y, False))
        elif self.can_push(x, y):
            current = self.worker()
            future = self.next(x, y)
            future_box = self.next(x + x, y + y)
            if current[2] == '@' and future == '$' and future_box == ' ':
                self.move_box(current[0] + x, current[1] + y, x, y)
                self.set_content(current[0], current[1], ' ')
                self.set_content(current[0] + x, current[1] + y, '@')
                if save:
                    self.queue.put((x, y, True))
            elif current[2] == '@' and future == '$' and future_box == '.':
                self.move_box(current[0] + x, current[1] + y, x, y)
                self.set_content(current[0], current[1], ' ')
                self.set_content(current[0] + x, current[1] + y, '@')
                if save:
                    self.queue.put((x, y, True))
            elif current[2] == '@' and future == '*' and future_box == ' ':
                self.move_box(current[0] + x, current[1] + y, x, y)
                self.set_content(current[0], current[1], ' ')
                self.set_content(current[0] + x, current[1] + y, '+')
                if save:
                    self.queue.put((x, y, True))
            elif current[2] == '@' and future == '*' and future_box == '.':
                self.move_box(current[0] + x, current[1] + y, x, y)
                self.set_content(current[0], current[1], ' ')
                self.set_content(current[0] + x, current[1] + y, '+')
                if save:
                    self.queue.put((x, y, True))
            if current[2] == '+' and future == '$' and future_box == ' ':
                self.move_box(current[0] + x, current[1] + y, x, y)
                self.set_content(current[0], current[1], '.')
                self.set_content(current[0] + x, current[1] + y, '@')
                if save:
                    self.queue.put((x, y, True))
            elif current[2] == '+' and future == '$' and future_box == '.':
                self.move_box(current[0] + x, current[1] + y, x, y)
                self.set_content(current[0], current[1], '.')
                self.set_content(current[0] + x, current[1] + y, '+')
                if save:
                    self.queue.put((x, y, True))
            elif current[2] == '+' and future == '*' and future_box == ' ':
                self.move_box(current[0] + x, current[1] + y, x, y)
                self.set_content(current[0], current[1], '.')
                self.set_content(current[0] + x, current[1] + y, '+')
                if save:
                    self.queue.put((x, y, True))

    # Move o trabalhador na direção (x, y) usando Currying
    def curried_move(self, x):
        return lambda y: lambda save: self.move(x, y, save)

    # Função para sair do jogo
    def quit(self):
        print("....")
        self.quit_action()
        
# Interface de Usuário
# Função para imprimir a representação gráfica do jogo na tela
def print_game(matrix, screen, images):
    screen.fill(background)
    x = 0
    y = 0
    for row in matrix:
        for char in row:
            screen.blit(images[char], (x, y))
            x = x + 32
        x = 0
        y = y + 32

# Função para obter a tecla pressionada pelo jogador
def get_key():
    while True:
        event = pygame.event.poll()
        if event.type == pygame.KEYDOWN:
            return event.key

# Função para exibir uma mensagem na tela
def display_box(screen, message):
    "Print a message in a box in the middle of the screen"
    font_object = pygame.font.Font(None, 18)
    pygame.draw.rect(screen, (0, 0, 0),
                     ((screen.get_width() / 2) - 100,
                      (screen.get_height() / 2) - 10,
                      200, 20), 0)
    pygame.draw.rect(screen, (255, 255, 255),
                     ((screen.get_width() / 2) - 102,
                      (screen.get_height() / 2) - 12,
                      204, 24), 1)
    if len(message) != 0:
        screen.blit(font_object.render(message, 1, (255, 255, 255)),
                    ((screen.get_width() / 2) - 100, (screen.get_height() / 2) - 10))
    pygame.display.flip()

# Função para exibir a mensagem de conclusão do nível
def display_end(screen):
    message = "Level Completed"
    font_object = pygame.font.Font(None, 18)
    pygame.draw.rect(screen, (0, 0, 0),
                     ((screen.get_width() / 2) - 100,
                      (screen.get_height() / 2) - 10,
                      200, 20), 0)
    pygame.draw.rect(screen, (255, 255, 255),
                     ((screen.get_width() / 2) - 102,
                      (screen.get_height() / 2) - 12,
                      204, 24), 1)
    screen.blit(font_object.render(message, 1, (255, 255, 255)),
                ((screen.get_width() / 2) - 100, (screen.get_height() / 2) - 10))
    pygame.display.flip()

# Função para solicitar ao jogador que selecione um nível
def ask(screen, question):
    "ask(screen, question) -> answer"
    pygame.font.init()
    current_string = []
    display_box(screen, question + ": " + ''.join(current_string))
    while True:
        inkey = get_key()
        if inkey == pygame.K_BACKSPACE:
            current_string = current_string[0:-1]
        elif inkey == pygame.K_RETURN:
            break
        elif inkey == pygame.K_MINUS:
            current_string.append("_")
        elif inkey <= 127:
            current_string.append(chr(inkey))
        display_box(screen, question + ": " + ''.join(current_string))
    return ''.join(current_string)

# Função para iniciar o jogo e selecionar um nível
def start_game():
    start = pygame.display.set_mode((320, 240))
    level_str = ask(start, "Select Level")
    try:
        level = int(level_str)
        if level > 0:
            return level
        else:
            print("ERROR: Invalid Level: " + str(level))
            sys.exit(2)
    except ValueError:
        print("ERROR: Invalid input. Please enter a valid level.")
        sys.exit(2)

# Configuração da cor de fundo
background = (255, 226, 191)

# Inicialização da biblioteca Pygame
pygame.init()

# Função lambda com um dicionário no retorno
images = lambda: Result(value={
    '#': pygame.image.load('images/wall.png'),
    ' ': pygame.image.load('images/floor.png'),
    '.': pygame.image.load('images/dock.png'),
    '@': pygame.image.load('images/worker.png'),
    '$': pygame.image.load('images/box.png'),
    '*': pygame.image.load('images/box_docked.png'),
    '+': pygame.image.load('images/worker_dock.png'),
})

# Função lambda com um functor (map) e uma List Comprehension
load_images = lambda: Result(value=list(map(lambda path: pygame.image.load(path), ['images/wall.png', 'images/floor.png', 'images/dock.png', 'images/worker.png', 'images/box.png', 'images/box_docked.png', 'images/worker_dock.png'])))

# Início do jogo: seleção de nível
level_result = Result(value=start_game())
game = game_result = level_result.bind(lambda level: Result(value=Game('levels', level, quit_action=quit_action)))
size_result = game_result.bind(lambda g: Result(value=g.load_size()))
screen = screen_result = size_result.bind(lambda size: Result(value=pygame.display.set_mode(size)))

# Obtendo o dicionário de imagens fora do loop
images_dict = images().unwrap()
# Desempacotando o Result do jogo
game = game_result.unwrap()

while True:
    # Verificamos se o jogo foi concluído
    is_completed_result = game_result.bind(lambda g: Result(value=g.is_completed()))

    if is_completed_result.unwrap():
        display_end(screen_result.unwrap())

     # Obtemos a matriz do jogo
    matrix_result = game_result.bind(lambda g: Result(value=g.get_matrix()))

    # Exibimos o jogo
    matrix = matrix_result.unwrap()
    screen = screen_result.unwrap()

    screen.fill(background)
    x = 0
    y = 0
    for row in matrix:
        for char in row:
            screen.blit(images_dict[char], (x, y))
            x = x + 32
        x = 0
        y = y + 32

    print_game(matrix, screen, images_dict)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game.quit() 
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                game.move(0, -1, True)
            elif event.key == pygame.K_DOWN:
                game.move(0, 1, True)
            elif event.key == pygame.K_LEFT:
                game.move(-1, 0, True)
            elif event.key == pygame.K_RIGHT:
                #game.move(1, 0, True)
                game.curried_move(1)(0)(True)  # Move para a direita e salva o movimento (currying)
            elif event.key == pygame.K_q:
                game.quit()
            elif event.key == pygame.K_d:
              game.unmove() 
    pygame.display.update()
