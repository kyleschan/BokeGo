import go
from bokePolicy import features, PolicyNet
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import argparse

def policy_predict(policy: PolicyNet, game: go.Game , device = "cpu"):
    fts = torch.Tensor(features(game, policy.scal)).unsqueeze(0)
    predicts = torch.topk(policy(fts).squeeze(0), 5)
    return {go.unsquash(sq_c): predicts[0].item for sq_c in predicts[1].tolist()}

if  __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Boke Policy Prediction")
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
