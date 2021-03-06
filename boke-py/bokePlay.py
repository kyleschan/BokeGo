import go
import re
import sys
import os
from itertools import cycle
from bokeNet import PolicyNet, ValueNet, policy_dist
from mcts import MCTS, Go_MCTS
from threading import Thread
import torch
from torch import load, device, set_grad_enabled 
import argparse
from time import sleep

parser = argparse.ArgumentParser(description = "Play against Boke")
parser.add_argument("-p", metavar="PATH", type = str, dest = 'p', help = "path to policy", default = "v0.2/RL_policy_29.pt")
parser.add_argument("-v", metavar="PATH", type = str, dest = 'v', help = "path to value net", default = "v0.2/value_2020-11-13_6.pt")
parser.add_argument("-c", type = str, action = 'store', choices = ['W','B'], dest = 'c', help = "Boke's color", default = ['W'])
parser.add_argument("-r", nargs = 1, metavar="ROLLOUTS", action = 'store', type = int, default = [100], dest = 'r', help = "number of rollouts per move")
parser.add_argument("--mode", type = str, choices = ["gui","gtp"], default = "gui", help = "Graphical or GTP mode") 
args = parser.parse_args()

NUM_ROLLOUTS = args.r[0]

def get_input(in_ref):
    in_ref[0] = input("Your Move: ")

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

done = False #toggle thinking
def loading():
    for c in cycle(['|', '/', '-', '\\']):
        if done:
            break
        sys.stdout.write('\rThinking ' + c)
        sys.stdout.flush()
        sleep(0.1)

def gtp(tree, device):
    '''Go Text Protocol (GTP) interface'''
    commands = ["name","boardsize", "clear_board", "komi", "play", "genmove", "final_score", "quit",\
                "version", "showboard", "known_command", "protocol_version", "list_commands"]
    board = Go_MCTS()
    first_pass = False 
    while True:
        try:
            line = input().strip()
        except EOFError:
            break
        if line == '':
            continue
        cmd = line.split() 
        out = None 
        #optional command ID
        cmd_id = ''
        if re.match('\d+', cmd[0]):
            cmd_id = cmd[0]
            cmd = cmd[1:]
        if cmd[0] not in commands:
            print("? " + cmd_id + "unknown command\n\n", end = '')
        elif cmd[0] == "protocol_version":
            out = "2"
        elif cmd[0] == "version":
            out = "0.2-alpha"
        elif cmd[0] == "known_command":
            if len(cmd) == 1:
                out = "false"
            else:
                out = "true" if cmd[2] in commands else "false"
        elif cmd[0] == "boardsize":
            if int(cmd[1]) != 9:
                print("?"+cmd_id + " Boke only plays on boardsize 9\n\n", end = '')
            else:
                out = ""
        elif cmd[0] == "clear_board":
            board = Go_MCTS(device = device)
            out = ""
        elif cmd[0] == "komi":
            board = Go_MCTS(komi = float(cmd[1]))
            out = ""
        #assume alternating play
        elif cmd[0] == "play":
            if len(cmd) <3 or not cmd[1] in ["black", "B", "W", "white"]: 
                print("?{} Invalid color or move\n\n".format(cmd_id), end = '')
            if cmd[2] == "PASS":
                first_pass = True
                board.play_pass()
                out = ""
            else:
                turn = 0 if (cmd[1] == "black" or cmd[1] == "B") else 1
                if turn != board.turn%2: 
                    print("?{} It is {}'s turn\n\n".format(cmd_id, cmd[1]), end='') 
                else:
                    try:
                        c = go.squash(cmd[2], alph = True)
                        board = board.make_move(c)
                        out = ""
                    except:
                        print("?{} Illegal Move\n\n".format(cmd_id), end = '') 
        elif cmd[0] == "showboard":
            out = "\n" + str(board)
        elif cmd[0] == "genmove":
            if len(cmd) != 2 or not cmd[1] in ["black", "B", "W", "white"]: 
                print("?{} Invalid color\n\n".format(cmd_id), end = '')
            elif first_pass or board.terminal:
                #always pass if opponent did
                out = "PASS"
            else:
                turn = 0 if (cmd[1] == "black" or cmd[1] == "B") else 1
                if turn != board.turn%2:
                    print("?{} It is not {}'s turn\n\n".format(cmd_id, cmd[1]), end='') 
                else:
                    R = 13 if board.turn < 12 else NUM_ROLLOUTS
                    tree.do_rollout(board, R) 
                    board = tree.choose(board)
                    out = go.unsquash(board.last_move, alph = True)
        elif cmd[0] == "name":
            out = "boke"
        elif cmd[0] == "quit":
            print("={} \n\n".format(cmd_id), end = '')
            break 
        elif cmd[0] == "list_commands":
            out = '\n'.join(commands)
        elif cmd[0] == "final_score":
            score = board.score()
            if score>0:
                out = "B+{}".format(score)
            else:
                out = "W+{}".format(-score)
        if out != None:
            print("={} {}\n\n".format(cmd_id, out), end = '')
        sys.stdout.flush()
    
if  __name__ == "__main__":
    device = device("cuda:0" if torch.cuda.is_available() else "cpu")
    pi = PolicyNet()
    checkpt = load(args.p, map_location = device)
    pi.load_state_dict(checkpt["model_state_dict"])
    pi.to(device)
    pi.eval()
    #val = ValueNet()
    #checkpt = load(args.v, map_location = device)
    #val.load_state_dict(checkpt["model_state_dict"])
    #val.to(device)
    #val.eval()
    board = Go_MCTS(device = device)
    tree = MCTS(policy_net=pi, exploration_weight = 0.5)
    set_grad_enabled(False)

    if args.mode == 'gtp':
        gtp(tree, device)
        sys.exit()

    if args.c[0] == 'B': 
        print(board)
        tree.do_rollout(board, NUM_ROLLOUTS)
        board = tree.choose(board)
    
    in_ref = [None]
    while(True):
        clear()
        print(board)

        #thread waiting for opponent's move
        thread = Thread(target=get_input, args = (in_ref,))
        thread.start()

        #rollouts while waiting
        while in_ref[0] == None:
            tree.do_rollout(board)
        
        uin = in_ref[0]
        if uin == 'h':
            move = torch.argmax(policy_dist(pi, board, device = device).probs).item()
            print("Boke's hint: " + go.unsquash(move, alph = True)) 
            sleep(3)
        elif uin == 'q':
            sys.exit() 
        else:
            if board.turn > 60 and tree.winrate < 0.1:
                print("Boke resigns.")
                sys.exit()
            try:
                done = False
                board = board.make_move(go.squash(uin, alph = True))
                clear()
                print(board)

                t = Thread(target = loading)
                t.start() 
                
                rolls = 13 if board.turn < 13 else NUM_ROLLOUTS
                tree.do_rollout(board,rolls)
                done = True
                board = tree.choose(board)
            except go.IllegalMove:
                print("Illegal move")
            except: 
                print("Enter coordinate to play a move\nEnter h to show hint\nEnter q to quit" )
                sleep(3)
        if board.terminal:
            s = board.score()
            if s > 0:
                print("B+{}".format(s))
            else:
                print("W+{}".format(-s))
            sys.exit()
        in_ref[0] = None
