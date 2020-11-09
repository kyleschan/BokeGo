#!/usr/bin/python3
from tqdm import tqdm, trange
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from bokeNet import PolicyNet, ValueNet, NinebyNineGames 
from datetime import date 
import argparse 

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description = "training script for Boke policy")
    parser.add_argument("-d", metavar="DATA", type = str, nargs=1, help = "path to csv", required = True)
    parser.add_argument("-c", metavar="CHECKPOINT", type = str, nargs = 1, help = "path to saved torch model")
    parser.add_argument("-e", metavar="EPOCHS", type = int, nargs =1, help = "number of epochs", default = [1])
    args = parser.parse_args() 
    
    print("Loading data...")
    data = NinebyNineGames(args.d[0])
    dataloader = DataLoader(data, batch_size = 32, shuffle = True, num_workers = 10)
    #validation_set = NinebyNineGames("/home/jupyter/BokeGo/data/validation.csv") 
    #validloader = DataLoader(validation_set, batch_size = 128, shuffle = True, num_workers = 10)
    print("Number of board positions: {}".format(len(data)))

    v = ValueNet()
    v.cuda()
    err = nn.L1Loss()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu") 
    optimizer = torch.optim.Adam(v.parameters())
    if args.c:
        print("Loading checkpoint...")
        checkpt = torch.load(args.c[0], map_location = device)
        pi.load_state_dict(checkpt["model_state_dict"] )
        optimizer.load_state_dict(checkpt["optimizer_state_dict"]) 
        epochs_trained = checkpt["epoch"]

        for state in optimizer.state.values():
            for k, t in state.items():
                if torch.is_tensor(t):
                    state[k] = t.cuda()
        v.train()
    else:
        epochs_trained = 0 

    epochs = args.e[0] 

    for epoch in range(epochs):
        epochs_trained += 1
        print("Epoch: {}".format(epochs_trained + epoch))
        running_loss = 0.0
        for i, data in tqdm(enumerate(dataloader,0)):
            inputs, res = data
            inputs, res = inputs.to(device), res.to(device).float()
            
            optimizer.zero_grad()
            outputs = v(inputs)
            
            #backprop
            loss = err(outputs, res)
            loss.backward()
            optimizer.step()
        
            running_loss += loss.item()
            if i%2000 == 1999:
                print(" Loss: ", running_loss)
                running_loss = 0.0
                #pi.eval()
                #with torch.no_grad():
                    #valid_loss = 0.0
                    #for j, v_data in enumerate(validloader, 0):
                        #if j == 2000:
                        #    break
                        #inputs, moves = v_data
                        #inputs, moves = inputs.to(device), moves.to(device)
                        #outputs = pi(inputs)
                        #loss = err( outputs, moves)
                        #valid_loss += loss
                    #print(" Validation Loss: {}".format(valid_loss))
                #pi.train()
     
        out_path = r"/home/jupyter/BokeGo/policy_net_py/" + "value_" \
                    + str(date.today()) + "_" + str(epochs_trained)+ ".pt"  
        torch.save({"model_state_dict": pi.state_dict(), "optimizer_state_dict": optimizer.state_dict(), "epoch": epochs_trained}, out_path)

