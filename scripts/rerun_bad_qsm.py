#########################
#
# Python script to (re-)run Rayextract on a selection of single trees, after having run it on plot-level
# and split into single trees. Typically run on ok-looking tree point clouds, but which gave non satisfactory QSM results. 
# There is the option to run it with or without cylinder smoothing
# 
# ####################### 


import pandas as pd
import os
import subprocess
import shutil

def read_rayextract_treefile(path):
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


def rerun_bad_qsm(dir_pc, dir_mesh, dir_treefile, df_path, selection='reject', bounds=None, diam_min=None, smooth_tree=True):
    """
    Args
        dir_pc: absolute path to directory with tree point clouds
        dir_mesh: absolute path to directory with tree meshes
        dir_treefile: absolute path to directory with tree treefiles 
        df_path: absolute path to dataframe (.csv) with overview of all trees (output from 'make_treefile_dataframe' function)
        selection: tree class in dataframe ('selection' column) to select trees (one of 'reject', 'keep', 'maybe', 'snag' or 'undecided')
        bounds: (xmin, xmax, ymin, ymax)
        diam_min: minimum tree diameter
        smooth_tree: runs the 'treesmooth' and 'treedecimate' raycloudtools commands to smooth and reduce the number of cylinders  

    Remarks
        This function calls raycloudtools bash commands, so they should be installed on your path
    """
    # Read tree dataframne
    df = pd.read_csv(df_path)

    # Select only trees according to criterium
    df_filtered = df[(df['selection'] == selection)]

    # Filter on location
    if bounds:
        x_min, x_max, y_min, y_max = bounds
        df_filtered = df_filtered[
            (df_filtered['x'] > x_min) & 
            (df_filtered['x'] < x_max) & 
            (df_filtered['y'] > y_min) & 
            (df_filtered['y'] < y_max)            
        ]

    # Filter on minimum diameter
    if diam_min:
        df_filtered = df_filtered[(df_filtered['d'] > diam_min)]

    print('number of trees to go:', df_filtered.shape[0])

    # Loop over all treefiles
    for _, df_row in df_filtered.iterrows():
        treefile = df_row['filename']
        treefile_path = dir_treefile + treefile

        # Get corresponding pointcloud and mesh file
        if 'trees_smoothed_decimated' in treefile:
            pc_path = dir_pc + treefile.replace('trees_smoothed_decimated', 'segmented').replace('txt', 'ply')
        else:
            pc_path = dir_pc + treefile.replace('trees', 'segmented').replace('txt', 'ply')

        mesh_path = dir_mesh + treefile.replace('.txt', '_mesh.ply')
        
        # Run rayextract terrain
        subprocess.run(["rayextract", "terrain", pc_path])

        # Run rayextract trees
        terrain_path = pc_path[:-4] + '_mesh.ply'
        subprocess.run(["rayextract", "trees", pc_path, terrain_path, "--max_diameter", "1.5", "--crop_length", "0.15"])

        pc_new_path = pc_path[:-4] + '_segmented.ply'
        mesh_new_path = pc_path[:-4] + '_trees_mesh.ply'
        treefile_new_path = pc_path[:-4] + '_trees.txt'

        # Remove unnecessary intermediates
        os.remove(terrain_path) 
        os.remove(pc_new_path) # keep original point cloud

        if os.path.exists(mesh_new_path): # if rayextract succeeded (and made a tree), then continue
            # Remove old treefile and mesh
            os.remove(treefile_path)
            os.remove(mesh_path)

            if smooth_tree:
                # Smooth and decimate treefile
                subprocess.run(["treesmooth", treefile_new_path])
                treefile_new_smooth_path = treefile_new_path[:-4] + '_smoothed.txt'
                subprocess.run(["treedecimate", treefile_new_smooth_path, "8", "segments"])
                treefile_new_smooth_decimated_path = treefile_new_path[:-4] + '_smoothed_decimated.txt'

                # Make mesh
                subprocess.run(["treemesh", treefile_new_smooth_decimated_path])
                mesh_new_smooth_decimated_path = treefile_new_path[:-4] + '_smoothed_decimated_mesh.ply'

                # Replace old mesh and treefile with new smoothed ones
                shutil.move(treefile_new_smooth_decimated_path, treefile_path) # move new treefile to directory
                shutil.move(mesh_new_smooth_decimated_path, mesh_path) # move new mesh to directory
                
                # Remove intermidiates
                os.remove(treefile_new_smooth_path)  
                os.remove(mesh_new_path)
                os.remove(treefile_new_path) 

            else:
                # Replace old mesh and treefile with new ones
                shutil.move(treefile_new_path, treefile_path)
                shutil.move(mesh_new_path, mesh_path) # move new mesh to directory

            # Update tree dataframe
            df_tf = read_rayextract_treefile(treefile_path)
            df.loc[(df['filename'] == treefile, 'x')] = df_tf['x'][0]
            df.loc[(df['filename'] == treefile)]['y'] = df_tf['y'][0]
            df.loc[(df['filename'] == treefile)]['d'] = df_tf['radius'][0] * 2
              

if __name__ == "__main__":

    # Path to tree pointclouds and treefiles 
    dir_pc = '/Stor1/wouter/data/chile/FUR006/rayextract/trees_pointclouds/'
    dir_treefile = '/Stor1/wouter/data/chile/FUR006/rayextract/trees_treefiles/'
    dir_mesh = '/Stor1/wouter/data/chile/FUR006/rayextract/trees_meshes/'
    df_path = '/Stor1/wouter/data/chile/FUR006/rayextract/treefiles_dataframe.csv'

    bounds = None
    diam_min = 0.0
    selection = 'maybe'
    smooth_tree = True

    rerun_bad_qsm(dir_pc, dir_mesh, dir_treefile, df_path, selection, bounds=None, diam_min=None, smooth_tree=smooth_tree)

