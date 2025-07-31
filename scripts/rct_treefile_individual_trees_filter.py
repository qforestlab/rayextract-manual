import os
import argparse
import numpy as np
import shutil
import pdb
import matplotlib.pyplot as plt

#takes input raycloudtools treefile and extracts only trees within x/y boundary, and above dbh

def main():
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', "--input", type=str, required=True)
    #xcoord and ycoord from south east corner, this is where the selection box is centered
    parser.add_argument('-x', "--xcoord", type=int, required=False, default=50)
    parser.add_argument('-y', "--ycoord", type=int, required=False, default=50)
    #width and length of selection box
    parser.add_argument('-xd', "--xdim", type=int, required=False, default=80)
    parser.add_argument('-yd', "--ydim", type=int, required=False, default=80)
    #lower dbh limit
    parser.add_argument('-d', "--dbh", type=int, required=False, default=0.1)
    args = parser.parse_args()

    #get the directory where parent (unsplit) treefile is located
    parent_dir = os.path.abspath(os.path.join(args.input, os.pardir))
    
    #open input treefile in read mode, 
    #open/create selected_trees.txt as a list of selected trees in append mode
    with open(args.input, "r") as file, open(parent_dir + "/selected_trees.txt", "a") as outfile:
    #skip the two lines of header
        next(file)
        next(file)
        #for every line in input file, store values split by ','
        for line in file:
            values = line.strip().split(',')
            x = float(values[0])
            y = float(values[1])
            dbh = float(values[3])*2
            #if values are in desired range, move input treefile into 'selected' directory
            if ((x < args.xcoord+(args.xdim/2)) and 
                (x > args.xcoord-(args.xdim/2)) and 
                (y < args.ycoord+(args.ydim/2)) and 
                (y > args.ycoord-(args.ydim/2)) and
                (dbh > args.dbh)):
                shutil.move(args.input, "./selected/" + args.input)
                outfile.write(args.input + "\n")
                #search for matching pc file and move to pc 'selected' directory
                pc_file = args.input.replace('trees','segmented').replace('txt','ply')
                shutil.move("../individual_pcs/" + pc_file, "../individual_pcs/selected/" + pc_file)

if __name__ == "__main__":

    main()