import re
import itertools
from textwrap import wrap
N = 9 
WHITE, BLACK, EMPTY = 'O', 'X', '.'
EMPTY_BOARD = EMPTY*(N**2) 
PASS = -1
class Game():
    '''go.Game: a class to represent a go game. The board is represented as a length N^2 string
    using "squashed coordinates" 0,1,...,N^2-1. PASS is -1
    optional parameters: 
        board: str -- initialize a board position
        ko: int -- the position of the current ko
        turn: int -- the current turn number
        moves: list -- the list of moves played
        sgf: str -- path to an sgf to initialize from
        '''
    def __init__(self, board = EMPTY_BOARD, ko = None, last_move = None, turn = 0, moves = None, komi = 5.5, sgf = None):
        self.turn = turn
        self.ko = ko
        self.board= board
        self.komi = komi
        self.last_move = last_move
        if sgf:
            self.moves = self.get_moves(sgf)
        else:
            self.moves = moves
        self.enc = {BLACK: 1, WHITE: -1, EMPTY: 0}


    def __str__(self):
        out = self.board
        if N == 9:
        #mark flower points
            for i in [20,24,40,56,60]:
                if out[i] == EMPTY:
                    out = place_stone('+', out, i)
        return "\t  " +' '.join(["ABCDEFGHJKLMNOPQRST"[i] for i in range(N)]) +"\n" \
            + '\n'.join(['\t'+str(i + 1)+' '+ ' '.join( out[N*i:N*(i+1)]) for i in range(N)])
    def __len__(self):
        if self.moves:
            return len(self.moves)
        return 0

    def get_board(self):
        return [self.enc[s] for s in self.board]

    def play_pass(self):
        if not self.moves:
            self.moves = [PASS]
        self.last_move = PASS 
        self.turn += 1
        self.ko = None

    def play_move(self, sq_c = None, testing = False):
        '''play move from self.moves. If a coordinate is given that is played instead.
        optional: testing = True stops board from being modified''' 
        if sq_c == None:
            if self.turn >= len(self):
                print("No moves to play.")
                return
            sq_c = self.moves[self.turn]
        if sq_c == PASS:
            self.play_pass()
            return
        if sq_c == self.ko:
            raise IllegalMove(f"\n{self}\n Move at {sq_c} illegally retakes ko.")
        if self.board[sq_c] != EMPTY:
            raise IllegalMove(f"\n{self}\n There is already a stone at {sq_c}")
        color = (WHITE if self.turn%2 ==1 else BLACK) 
        opp_color = (BLACK if color == WHITE else WHITE) 
        possible_ko_color = possible_ko(self.board, sq_c)
        new_board = place_stone(color, self.board, sq_c)
        new_board, opp_captured = get_caps(new_board, sq_c, color)
        if len(opp_captured) == 1 and possible_ko_color == opp_color:
            new_ko = opp_captured[0] 
        else:
            new_ko = None
        # Check for suicide
        new_board, captured = maybe_capture_stones(new_board, sq_c)
        if captured:
            raise IllegalMove(f"\n{self}\n Move at {sq_c} is suicide.")
        if testing: return
        if not self.moves:
            self.moves = [sq_c]
        else:
            self.moves.append(sq_c)
        self.board = new_board
        self.last_move = sq_c
        self.ko = new_ko
        self.turn += 1 

    def is_legal(self, sq_c):
        try:
            self.play_move(sq_c, testing = True)
            return True
        except IllegalMove:
            return False

    def score(self):
        '''Calculated using Chinese rules, assuming dead groups are captured
        and no sekis'''
        board = self.board
        while EMPTY in board:
            empty = board.index(EMPTY)
            empties, borders = flood_fill(board, empty)
            bd_list = [board[sq_b] for sq_b in borders]
            if BLACK in bd_list and not WHITE in bd_list: 
                border_color = BLACK
            elif WHITE in bd_list and not BLACK in bd_list:
                border_color = WHITE
            else:
                border_color = '?'
            board = bulk_place_stones(border_color, board, borders)
            board = bulk_place_stones(border_color, board, empties)
        return board.count(BLACK) - (board.count(WHITE) + self.komi)

    def get_liberties(self):
        board = self.board
        liberties = bytearray(N*N)
        for color in (WHITE, BLACK):
            while color in board:
                sq_c = board.index(color)
                stones, borders = flood_fill(board, sq_c)
                num_libs = len([sq_b for sq_b in borders if board[sq_b] == EMPTY])
                for sq_s in stones:
                    liberties[sq_s] = num_libs
                board = bulk_place_stones('?', board, stones)
        return list(liberties)

    @staticmethod
    def get_moves(sgf):
        with open(sgf, 'r') as f:
            match = re.findall(r";[BW]\[(\w\w)\]", f.read())
        mvs = []
        for mv in match:
            if mv == '': 
                mvs.append(-1)
            else: 
                mvs.append(9*(ord(mv[0])-97) + ord(mv[1])-97 )
        return mvs

def squash(c, alph = False):
    '''squash converts coordinate pair to single integer 0 <= n < N^2.
    alph = True squashes a letter-number coordinate string '''
    if isinstance(c, list):
        return [squash(b) for b in c]
    if alph:
        #Letters skip I
        y = 8 if c[0] == 'J' else ord(c[0]) - 65 
        c = ( int(c[1]) - 1,  y)
        if not is_on_board(c): 
            raise IllegalMove("{} is not on the board".format(c))
    return N * c[0] + c[1]

def unsquash(sq_c, alph = False):
    if isinstance(sq_c, list): 
        return [unsquash(sq_b) for sq_b in sq_c]
    else:
        c = divmod(sq_c, N)
        if alph:
            letr = 'J' if c[1] == 8 else chr(c[1] + 65)
            return letr + str(c[0] +1)
        return c

def is_on_board(c):
    return c[0] % N == c[0] and c[1] % N == c[1]

def flood_fill(board, sq_c):
    '''Flood fill to find the connected component containing sq_c and its boundary'''
    color = board[sq_c]
    chain = set([sq_c])
    reached = set()
    frontier = [sq_c]
    while frontier:
        current_sq_c = frontier.pop()
        chain.add(current_sq_c)
        for sq_n in NEIGHBORS[current_sq_c]:
            if board[sq_n] == color and not sq_n in chain:
                frontier.append(sq_n)
            elif board[sq_n] != color:
                reached.add(sq_n)
    return chain, reached

def get_stone_lib(board, sq_c):
    stones, borders = flood_fill(board, sq_c)
    return len([sq_b for sq_b in borders if board[sq_b] == EMPTY])

def get_caps(board, sq_c, color):
        opp_color = BLACK if color == WHITE else WHITE
        opp_stones = []
        my_stones = []
        for sq_n in NEIGHBORS[sq_c]:
            if board[sq_n] == color:
                my_stones.append(sq_n)
            elif board[sq_n] == opp_color:
                opp_stones.append(sq_n)
        opp_captured = []
        for sq_s in opp_stones:
            new_board, captured = maybe_capture_stones(board, sq_s)
            opp_captured += captured
        new_board = bulk_place_stones(EMPTY, board, opp_captured)
        return new_board, opp_captured

class IllegalMove(Exception): pass

NEIGHBORS = [squash( list( filter(is_on_board, [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]))) \
                for x in range(N) for y in range(N)] 
DIAGONALS = [squash( list( filter(is_on_board, [(x+1,y+1), (x+1, y-1), (x-1, y-1), (x-1, y-1)]))) \
                for x in range(N) for y in range(N)] 
#Helper functions
def place_stone(color, board, sq_c):
    return board[:sq_c] + color + board[sq_c+1:]

def bulk_place_stones(color, board, stones):
    byteboard = bytearray(board, encoding='ascii') 
    color = ord(color)
    for fstone in stones:
        byteboard[fstone] = color
    return byteboard.decode('ascii') 

def maybe_capture_stones(board, sq_c):
    '''see if group at sq_c is captured'''
    chain, reached = flood_fill(board, sq_c)
    if not any(board[sq_r] == EMPTY for sq_r in reached):
        board = bulk_place_stones(EMPTY, board, chain)
        return board, chain
    else:
        return board, []

def play_move_incomplete(board, sq_c, color):
    if board[sq_c] != EMPTY:
        raise IllegalMove
    board = place_stone(color, board, sq_c)

    opp_color = WHITE if color == BLACK else WHITE
    opp_stones = []
    my_stones = []
    for sq_n in NEIGHBORS[sq_c]:
        if board[sq_n] == color:
            my_stones.append(sq_n)
        elif board[sq_n] == opp_color:
            opp_stones.append(sq_n)

    for sq_s in opp_stones:
        board, _ = maybe_capture_stones(board, sq_s)

    for sq_s in my_stones:
        board, _ = maybe_capture_stones(board, sq_s)
    return board

def possible_ko(board, sq_c):
    '''Check if sq_c is surrounded by one color, and return that color'''
    if board[sq_c] != EMPTY: return None
    neighbor_colors = { board[sq_n] for sq_n in NEIGHBORS[sq_c]}
    if len(neighbor_colors) == 1 and not EMPTY in neighbor_colors:
        return list(neighbor_colors)[0]
    else:
        return None

def possible_eye(board, sq_c):
    color = possible_ko(board, sq_c)
    if color is None:
        return None
    diagonal_faults = 0
    diagonals = DIAGONALS[sq_c]
    if len(diagonals) < 4:
        diagonal_faults += 1
    for d in diagonals:
        if not board[d] in (color, EMPTY):
            diagonal_faults += 1
    if diagonal_faults > 1:
        return None
    else:
        return color
