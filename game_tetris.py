from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, QBasicTimer
from PyQt5.QtGui import QPainter, QColor, QFont
import random

BOARD_WIDTH = 10
BOARD_HEIGHT = 22
CELL = 20

SHAPES = {
    'NoShape': [],
    'ZShape':  [(-1,0), (0,0), (0,1), (1,1)],
    'SShape':  [(-1,1), (0,1), (0,0), (1,0)],
    'LineShape':[(-2,0), (-1,0), (0,0), (1,0)],
    'TShape':  [(-1,0), (0,0), (1,0), (0,1)],
    'SquareShape':[(0,0), (1,0), (0,1), (1,1)],
    'LShape':  [(-1,0), (0,0), (1,0), (-1,1)],
    'MirroredLShape':[(-1,0), (0,0), (1,0), (1,1)],
}

COLORS = {
    'NoShape': QColor(0,0,0),
    'ZShape': QColor(204, 0, 0),
    'SShape': QColor(0, 153, 0),
    'LineShape': QColor(0, 153, 204),
    'TShape': QColor(153, 0, 153),
    'SquareShape': QColor(204, 153, 0),
    'LShape': QColor(255, 102, 0),
    'MirroredLShape': QColor(0, 102, 204),
}

class Piece:
    def __init__(self, shape='NoShape'):
        self.shape = shape
        self.coords = SHAPES[shape][:]

    def rotated(self):
        if self.shape == 'SquareShape':
            return self
        rot = Piece(self.shape)
        rot.coords = [(-y, x) for (x, y) in self.coords]
        return rot

class TetrisWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tetris")
        self.setMinimumSize(20 + BOARD_WIDTH*CELL + 180, 20 + BOARD_HEIGHT*CELL + 40)

        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

        self.timer = QBasicTimer()
        self.is_paused = False
        self.game_over = False

        self.board = [['NoShape'] * BOARD_WIDTH for _ in range(BOARD_HEIGHT)]
        self.cur_piece = Piece()
        self.cur_x = 0
        self.cur_y = 0
        self.next_piece = self.random_piece()

        self.score = 0
        self.lines_cleared = 0
        self.level = 1

        # UI elements
        self.score_label = QLabel("Score: 0")
        self.lines_label = QLabel("Lines: 0")
        self.level_label = QLabel("Level: 1")
        for lab in (self.score_label, self.lines_label, self.level_label):
            lab.setFont(QFont("Arial", 10, QFont.Bold))
            lab.setFocusPolicy(Qt.NoFocus)

        self.next_title_label = QLabel("Next:")
        self.next_title_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.next_title_label.setFocusPolicy(Qt.NoFocus)

        self.btn_restart = QPushButton("Restart")
        self.btn_restart.clicked.connect(self.restart)
        self.btn_restart.setFocusPolicy(Qt.NoFocus)

        self.btn_pause = QPushButton("Pause")
        self.btn_pause.clicked.connect(self.pause_toggle)
        self.btn_pause.setFocusPolicy(Qt.NoFocus)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.score_label)
        right_layout.addWidget(self.lines_label)
        right_layout.addWidget(self.level_label)
        right_layout.addSpacing(10)
        right_layout.addWidget(self.next_title_label)
        right_layout.addSpacing(150)
        right_layout.addWidget(self.btn_restart)
        right_layout.addWidget(self.btn_pause)
        right_layout.addStretch(1)

        main_layout = QHBoxLayout()
        main_layout.addSpacing(BOARD_WIDTH*CELL + 60)  # left space for board
        main_layout.addLayout(right_layout)
        self.setLayout(main_layout)

        self.start()

    # ---- Game control ----

    def start(self):
        self.clear_board()
        self.score = 0
        self.lines_cleared = 0
        self.level = 1
        self.update_labels()
        self.game_over = False
        self.is_paused = False
        self.setWindowTitle("Tetris")

        self.next_piece = self.random_piece()
        self.new_piece()
        self.timer.start(self.current_interval(), self)

    def restart(self):
        self.start()
        self.setFocus()

    def pause_toggle(self):
        if self.game_over:
            return
        if not self.is_paused:
            self.is_paused = True
            self.timer.stop()
            self.setWindowTitle("Tetris - Paused")
            self.btn_pause.setText("Resume")
        else:
            self.is_paused = False
            self.setWindowTitle("Tetris")
            self.timer.start(self.current_interval(), self)
            self.btn_pause.setText("Pause")
        self.setFocus()

    def current_interval(self):
        return max(80, 400 - (self.level - 1) * 30)

    def clear_board(self):
        self.board = [['NoShape'] * BOARD_WIDTH for _ in range(BOARD_HEIGHT)]

    def random_piece(self):
        shape = random.choice(list(SHAPES.keys())[1:])
        return Piece(shape)

    def new_piece(self):
        self.cur_piece = self.next_piece
        self.next_piece = self.random_piece()
        self.cur_x = BOARD_WIDTH // 2
        self.cur_y = 0

        if not self.is_valid_position(self.cur_piece, self.cur_x, self.cur_y):
            self.game_over = True
            self.timer.stop()
            self.setWindowTitle("Tetris - Game Over")
            return

    # ---- Qt events ----

    def timerEvent(self, event):
        if event.timerId() == self.timer.timerId():
            if not self.is_paused and not self.game_over:
                if not self.try_move(self.cur_piece, self.cur_x, self.cur_y + 1):
                    self.piece_dropped()
        else:
            super().timerEvent(event)

    def keyPressEvent(self, event):
        self.setFocus()
        if self.game_over:
            return

        key = event.key()
        if key == Qt.Key_P:
            self.pause_toggle()
            return

        if self.is_paused:
            return

        if key == Qt.Key_Left:
            self.try_move(self.cur_piece, self.cur_x - 1, self.cur_y)
        elif key == Qt.Key_Right:
            self.try_move(self.cur_piece, self.cur_x + 1, self.cur_y)
        elif key == Qt.Key_Down:
            self.try_move(self.cur_piece, self.cur_x, self.cur_y + 1)
        elif key == Qt.Key_Up:
            self.try_move(self.cur_piece.rotated(), self.cur_x, self.cur_y)
        elif key == Qt.Key_Space:
            self.drop_down()
        elif key == Qt.Key_R:
            self.restart()

        self.update()

    # ---- Core mechanics ----

    def is_valid_position(self, piece, x, y):
        for (px, py) in piece.coords:
            bx = x + px
            by = y + py
            if bx < 0 or bx >= BOARD_WIDTH:
                return False
            if by < 0 or by >= BOARD_HEIGHT:
                return False
            if self.board[by][bx] != 'NoShape':
                return False
        return True

    def try_move(self, piece, new_x, new_y):
        if self.is_valid_position(piece, new_x, new_y):
            self.cur_piece = piece
            self.cur_x = new_x
            self.cur_y = new_y
            self.update()
            return True
        return False

    def piece_dropped(self):
        for (px, py) in self.cur_piece.coords:
            bx = self.cur_x + px
            by = self.cur_y + py
            if 0 <= by < BOARD_HEIGHT:
                self.board[by][bx] = self.cur_piece.shape

        cleared = self.remove_full_lines()
        if cleared > 0:
            self.lines_cleared += cleared
            self.score += [0, 100, 300, 500, 800][cleared]
            self.level = 1 + self.lines_cleared // 10
            self.timer.start(self.current_interval(), self)
            self.update_labels()

        self.new_piece()

    def remove_full_lines(self):
        new_board = []
        removed = 0
        for row in self.board:
            if all(cell != 'NoShape' for cell in row):
                removed += 1
            else:
                new_board.append(row)
        while len(new_board) < BOARD_HEIGHT:
            new_board.insert(0, ['NoShape'] * BOARD_WIDTH)
        self.board = new_board
        return removed

    def drop_down(self):
        while self.try_move(self.cur_piece, self.cur_x, self.cur_y + 1):
            pass
        self.piece_dropped()

    def update_labels(self):
        self.score_label.setText(f"Score: {self.score}")
        self.lines_label.setText(f"Lines: {self.lines_cleared}")
        self.level_label.setText(f"Level: {self.level}")

    # ---- Painting ----

    def paintEvent(self, event):
        painter = QPainter(self)
        self.draw_board(painter)
        self.draw_current_piece(painter)
        self.draw_next_piece_preview(painter)

    def draw_board(self, painter):
        # Border around game area
        painter.setPen(QColor(0,0,0))
        painter.drawRect(20, 20, BOARD_WIDTH*CELL, BOARD_HEIGHT*CELL)

        for i in range(BOARD_HEIGHT):
            for j in range(BOARD_WIDTH):
                shape = self.board[i][j]
                self.draw_cell(painter, j, i, COLORS[shape])

    def draw_current_piece(self, painter):
        for (px, py) in self.cur_piece.coords:
            x = self.cur_x + px
            y = self.cur_y + py
            if 0 <= y < BOARD_HEIGHT:
                self.draw_cell(painter, x, y, COLORS[self.cur_piece.shape])

    def draw_cell(self, painter, x, y, color):
        if color == COLORS['NoShape']:
            return
        left = 20 + x * CELL
        top = 20 + y * CELL
        painter.fillRect(left+1, top+1, CELL-2, CELL-2, color)

    def draw_next_piece_preview(self, painter):
        start_x = 20 + BOARD_WIDTH*CELL + 40
        start_y = 120
        painter.setPen(Qt.NoPen)
        painter.fillRect(start_x-10, start_y-10, 120, 120, QColor(230,230,230))
        painter.setPen(QColor(180,180,180))
        painter.drawRect(start_x-10, start_y-10, 120, 120)

        for (px, py) in self.next_piece.coords:
            x = start_x + (px+1) * CELL
            y = start_y + (py+1) * CELL
            painter.fillRect(x+1, y+1, CELL-2, CELL-2, COLORS[self.next_piece.shape])
