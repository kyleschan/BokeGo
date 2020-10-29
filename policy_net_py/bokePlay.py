import go
from bokePolicy import features, PolicyNet, policy_predict
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import argparse

if  __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Boke Policy Prediction")
    parser.add_argument("path", metavar="MODEL", type = str, nargs = 1, help = "path to model")
    parser.add_argument("--sgf", metavar="SGF", type = str, nargs = 1, help = "path to sgf")
    args = parser.parse_args()
   
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pi = PolicyNet()
    checkpt = torch.load(args.path[0], map_location = device)
    pi.load_state_dict(checkpt["model_state_dict"])
    pi.eval()
    
    if args.sgf:
        g = go.Game(sgf = args.sgf[0])
    else:
        g = go.Game()

    while(True):
        print(g)
        
        if args.sgf:
            uin = input("\t- press n to see next move in sgf\n\
        - press p to show prediction\n\
        - press q to quit\n")
        else:
            uin = input("\t- press b to play Boke's top move\n\
        - press p to show prediction\n\
        - enter coordinate \"x y\" to play move\n\
        - press q to quit\n")

        if not args.sgf and uin == 'b':
            probs , moves  = policy_predict(pi, g, device, k = 2)
            try: 
                g.play_move(moves[0])
            except:
                #Boke tried an illegal move?!
                g.play_move(moves[1])
        
        elif args.sgf and uin == 'n':
            g.play_move()

        elif uin == 'p':
            probs, moves = policy_predict(pi, g, device, k = 5)
            print(go.unsquash(moves.tolist()))   
            print(probs.tolist())
        
        elif uin == 'q':
            break
        
        else:
            try:
                g.play_move(go.squash(tuple([int(i) for i in uin.split(' ') ])) )
            except:
                print("Enter a valid option")

