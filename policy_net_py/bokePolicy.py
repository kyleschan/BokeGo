import go
import os
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import argparse

class PolicyNet(nn.Module):
    def __init__(self):
        super(PolicyNet, self).__init__()
        '''7 9x9 input features
        5x5 convolution 9x9 -> 9x9
        3x3 convolution 9x9 -> 7x7
        1 fully connected hidden layer
        output distribution over coords 0-81'''
        self.conv1 = nn.Conv2d(7, 10, 5, padding = 2)
        self.conv2 = nn.Conv2d(10, 15, 3) 
        self.l1 = nn.Linear(15*7*7, 200)
        self.l2 = nn.Linear(200, 81)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = x.view(-1, self.num_flat_features(x))
        x = F.relu(self.l1(x))
        x = self.l2(x)
        return F.softmax(x, dim = 1)

    def num_flat_features(self, x):
        size = x.size()[1:]
        num_features = 1
        for s in size:
            num_features *= s
        return num_features

class NinebyNineGames(Dataset):
    def __init__(self, path, transform = None, scale = 1):
        '''Read from csv''' 
        self.boards = pd.read_csv(path)
        self.path = path
        self.transform = transform
        self.scale = scale
    def __len__(self):
        return len(self.boards)

    def __getitem__(self, idx):
        board, ko, move = self.boards.iloc[idx]
        ko = (None if ko == "None" else int(ko))
        g = go.Game(board = board, ko = ko)
        return torch.Tensor(features(g, self.scale)), move

def features(game: go.Game, scale = 1):
    ''' layer : feature
        0: black stones
        1: white stones
        2: empty 
        4: legal
        5: liberties
        6: liberties after playing'''
    empty = np.array(game.get_board()).reshape(9,9)
    black = empty.copy()
    white = empty.copy()
    black[black == -1] = 0
    white[white == 1] = 0
    white *= -1
    empty[empty == 0] = 2 
    empty[empty != 2] = 0
    legal = np.array([game.is_legal((i,j)) for i in range(9) for j in range(9)]).reshape(9,9)
    libs = np.array(game.get_liberties()).reshape(9,9)
    color = (go.BLACK if game.turn%2 == 0 else go.WHITE)
    libs_after = np.array([go.get_stone_lib(go.place_stone(color, game.board,\
            go.squash((i,j))), (i,j)) for i in range(9) for j in range(9)]).reshape(9,9)
    return scale*np.stack((black, white, empty, legal, libs, libs_after)) 

def policy_predict(policy: PolicyNet, game: go.Game , device = "cpu"):
    fts = torch.Tensor(features(game, 10)).unsqueeze(0)
    predicts = torch.topk(policy(fts).squeeze(0), 5)
    return {go.unsquash(sq_c): predicts[0].item for sq_c in predicts[1].tolist()}

if  __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "BokeGo Policy Prediction")
    parser.add_argument("path", metavar="MODEL", type = str, nargs = 1, help = "path to model")
    parser.add_argument("--sgf", metavar="SGF", type = str, nargs = 1, help = "path to sgf")
    args = parser.parse_args()
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pi = PolicyNet()
    pi.load_state_dict(torch.load(args.path[0], map_location=device))
    pi.eval()
    
    if args.sgf != None:
        mvs = get_moves(args.sgf[0])
        g = go.Game(moves = mvs)

    else:
        g = go.Game()

    uin = ""
    while(uin != 'q'):
        print(g)
        uin = input("\t- press p to show prediction\n\
        - enter coordinate to play move\n\
        - press q to quit\n")
        if uin == 'p':
            print(policy_predict(pi, g, device))
        else:
            g.play_move(tuple([int(i) for i in uin.split(' ')]))
