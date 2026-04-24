class BoardView:
    def __init__(self, loader, board, render, cell_size):
        self.loader = loader
        self.board = board
        self.render = render
        self.cell_size = cell_size
        self.nodePath = self.render.attachNewNode("board")
        self.cell_nodes = []
        self.node_textures = {1: self.loader.loadTexture("assets/1.png"),
                              2: self.loader.loadTexture("assets/2.png"),
                              3: self.loader.loadTexture("assets/3.png"),
                              4: self.loader.loadTexture("assets/4.png"),
                              5: self.loader.loadTexture("assets/5.png")}
        self.win = self.board.win
        self.mines_left = self.board.num_mines
        self.game_over = self.board.game_over
    
    def create_board(self):
        self.cell_nodes = [[self._create_cell(x, y) for y in range(self.board.height)] for x in range(self.board.width)]
    
    def _create_cell(self, x, y):
        node = self.loader.loadModel("models/box.egg")
        node.reparentTo(self.nodePath)
        node.setScale(self.cell_size * 0.5, self.cell_size * 0.5, 0.2)
        node.setPos(x * self.cell_size, y * self.cell_size, 0)
        return node

    def update_cell(self, x, y, content):
        node = self.cell_nodes[x][y]
        if content == "bomb":
            node.setColor(1, 0, 0, 1)  
        elif content == "empty":
            node.setColor(0.5, 0.5, 0.5, 1)  
        else:
            node.setTexture(self.node_textures.get(content))
    
    def update_data(self, win, mines_left, game_over):
        self.win = win
        self.mines_left = mines_left
        self.game_over = game_over