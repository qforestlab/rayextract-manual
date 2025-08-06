from scipy.io import loadmat, savemat
import numpy as np
import pandas as pd
import os
import argparse
from pathlib import Path


def read_raycloud_treefile(path):
    ''' Function to read a treefile.txt (=QSM), which is the output from using raycloudtools 'rayextract trees pointcloud.ply' 
        Assumes a single tree on the third line of the txt file.

        Args:
            path (str): path to file

        Returns
            (pandas.DataFrame): dataframe with columns 'x', 'y', 'z', 'radius', 'parent_id', 'section_id'.
    '''
    # Read the file
    with open(path, 'r') as file:
        lines = file.readlines()

    # Extract the header and the data line
    headers = lines[1].strip().split(',')  # Second line contains the headers
    data_line = lines[2].strip()            # Third line contains all the data of a single tree

    # Split the data into rows using space as the delimiter
    rows = [row.rstrip(',') for row in data_line.split(' ')]

    # Split each row by commas to get individual values
    data = [list(map(float, row.split(','))) for row in rows]

    # Create the DataFrame
    return pd.DataFrame(data, columns=headers)


def treefile_to_treeqsm(path_in, path_out):
    ''' Function to convert qsm from raycloudtools (=treefile) TreeQSM style qsm.mat file
        Assumes a treefile with only one tree.

        Args:
            path_in: treefile.txt, output from raycloudtools
            path_out: output matlab file (.mat)
    '''
    # Read treefile.txt
    df = read_raycloud_treefile(path_in)

    # Pre-allocate QSM
    n = df.shape[0] - 1
    qsm = {
        'start': np.zeros((n, 3), dtype=np.float32),
        'axis': np.zeros((n, 3), dtype=np.float32),
        'length': np.zeros((n, 1), dtype=np.float32),
        'radius': np.zeros((n, 1), dtype=np.float32),
        'parent': np.zeros((n, 1), dtype=np.int64), 
        'branch': np.zeros((n, 1), dtype=np.int64),
    }

    # Initialize branch number as 1
    branch = 1
    qsm['branch'][0] = branch

    # Loop over rows (=cylinders) in df
    for i in range(n):
        # Get cylinder end and start points
        current = df.values[i + 1]
        pid = int(current[4])
        parent = df.values[pid]

        # Calculate euclidean distance 
        length = np.sqrt(np.sum((current[0:3] - parent[0:3])**2))
        
        # Store cylinder values
        qsm['start'][i, :] = parent[0:3] # Start point of cylinder
        qsm['axis'][i, :] = (current[0:3] - parent[0:3]) / length # Normalized direction vector
        qsm['length'][i] = length # Length of cylinder
        qsm['radius'][i] = current[3] # Radius of cylinder
        qsm['parent'][i] = pid # parent ID

        # Branch number: branch number equals that of parent, unless subsequent cylinders have the same parent, then increase the branch number
        if current[4] - parent[4] == 0:
            # Two options: new branch number after every split (uncomment two lines below), or one main branch that keeps continuing with 'secondary' branches having a diffent number
            # branch += 1
            # qsm['branch'][i - 1] = branch
            branch += 1
            qsm['branch'][i] = branch
        else:
            row = int(current[4] - 1) if current[4] > 0 else 0 # row of the parent cylinder, set to 0 for first cylinder (otherwise row = -1)
            qsm['branch'][i] = qsm['branch'][row] # branch number of the parent

    # Format data into how it looks like when reading a qsm.mat file (see read_qsm_mat function)
    arr = np.array([[(qsm['start'], qsm['axis'], qsm['length'], qsm['radius'], qsm['parent'], qsm['branch'])]], dtype=[(key, 'O') for key in qsm.keys()])
    cyl = np.array([[(arr,)]], dtype=[('cylinder', 'O')])

    # Save arrays as matlab structure
    savemat(path_out, {'qsm': cyl})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert treefiles to matlab QSMs")
    parser.add_argument("dir_treefile", help="Directory containing treefiles")
    parser.add_argument("dir_qsm", help="Directory to save matlab qsms")
    args = parser.parse_args()

    dir_treefile = Path(args.dir_treefile)
    dir_qsm = Path(args.dir_qsm)
    dir_qsm.mkdir(parents=True, exist_ok=True)

    treefiles = os.listdir(args.dir_treefile)

    # Loop over all treefiles and convert to matlab qsm
    for treefile in treefiles:
        path_in = dir_treefile / treefile
        path_out = (dir_qsm / treefile).with_suffix('.mat')
        treefile_to_treeqsm(path_in, path_out)
