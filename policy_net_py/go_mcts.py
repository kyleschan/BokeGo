from copy import copy
from random import choice, randrange

import torch

from bokePolicy import PolicyNet, policy_sample
import go
from mcts import MCTS, Node

MAX_TURNS = 60

class Go_MCTS(go.Game, Node):
    """Wraps go.Game to turn it into a Node for search tree expansion
    in MCTS

    Implements all abstract methods from Node as well as a few helper
    functions for determining if the game is legally finished.

    Attributes:
        policy: a PolicyNet for move selection
        terminal: a boolean indicating whether the game is legally finished
        color: a boolean indicating the current player's color;
               True = Black, False = White
    """
    def __init__(self, board=go.EMPTY_BOARD, ko=None, turn=0, moves=[],
                 sgf=None, policy: PolicyNet=None, terminal=False,
                 color=True):
        super().__init__(board, ko, turn, moves, sgf)
        self.policy = policy
        self.terminal = terminal
        self.color = color

    def __eq__(self, node2):
        return self.board == node2.board

    def __hash__(self):
        return self.board.__hash__()

    def __copy__(self):
        return Go_MCTS(board=self.board, ko=self.ko, turn=self.turn,
                       moves=self.moves, policy=self.policy,
                       terminal=self.terminal, color=self.color)
    
    def find_children(self):
        '''Returns a set of boards (Go_MCTS objects) derived from legal
        moves'''
        if self.terminal:
            return set()      
        return {self.make_move(i) for i in self.get_all_legal_moves()}
    
    def find_random_child(self):
        '''Draws legal move from distribution given by policy. If no
        policy is given, a legal move is drawn uniformly.
        Returns a copy of the board (Go_MCTS object) after the move has
        been played.'''
        if self.terminal:
            return self # Game is over; no moves can be made
        return self.make_move(self.get_move())

    def reward(self):
        '''Returns 1 for a win, 0 for a loss.'''
        if not self.terminal:
            raise RuntimeError(f"reward called on nonterminal board {self}")
        # Black = True, White = False
        return int(self.color and self.current_winner())

    def make_move(self, index):
        '''Returns a copy of the board (Go_MCTS object) after the move
        given by index has been played.'''
        game_copy = copy(self)
        game_copy.play_move(index)
        # It's now the other player's turn
        game_copy.color = not self.color
        # Check if the move ended the game
        game_copy.terminal = game_copy.turn > MAX_TURNS
        return game_copy

    def is_terminal(self):
        return self.terminal

    # VERY expensive call, need improve this.
    def get_all_legal_moves(self):
        return [i for i in range(go.N ** 2) if self.is_legal(i)]

    def get_move(self):
        if self.policy:
            return policy_sample(policy=self.policy, game=self) # NEEDS TO BE FIXED
        else:
            move = randrange(0, go.N ** 2)
            while not self.is_legal(move):
                move = randrange(0, go.N ** 2)
            return move 

    # Do not use until we figure out how to best terminate the game
    def is_game_over(self):
        '''Game is over if there are no more legal moves
        (or if both players pass consecutively, or if a
        player resigns...)'''
        return len(self.get_all_legal_moves()) == 0

    def current_winner(self):
        return self.score() > 0

if __name__ == '__main__':
    pi = PolicyNet()
    checkpt = torch.load("v0.5/policy_v0.5_2020-10-29_1.pt", map_location = torch.device("cpu"))
    pi.load_state_dict(checkpt["model_state_dict"])
    NUMBER_OF_ROLLOUTS = 500
    tree = MCTS(exploration_weight=0.5)
    board = Go_MCTS(policy=pi)
    print(board)
    while True:
        while True:
            try:
                row_col = input("enter 'row col': ")
                if row_col == 'q':
                    break
                index = go.squash(tuple([int(i) for i in row_col.split(' ') ]))
                if board.is_legal(index):
                    break
            except:
                print("Enter a valid option, or type 'q' to quit")
        if row_col == 'q':
            break
        board = board.make_move(index)
        print(board)
        if board.terminal:
            break
        for _ in range(NUMBER_OF_ROLLOUTS):
            tree.do_rollout(board)
        board = tree.choose(board)
        print(board)
        if board.terminal:
            break
