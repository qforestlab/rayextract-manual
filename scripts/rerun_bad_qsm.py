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
    """Read a rayextract treefile.

    Behavior:
    - If the file has exactly 3 lines (comment, header, data) it returns a single DataFrame for the one tree.
    - If it has more data lines (multiple trees) it returns a list of DataFrames, one per tree.

    Parsing rules:
    - If the header line contains a space character this is treated as a separator between per-tree attributes (the
      first chunk) and per-segment attributes (the remaining chunk). All headers up to the first space are skipped and
      the corresponding first space-separated data chunk is skipped as well.
    - If the header line does not contain a space, all headers are used (no skipping).
    """
    # Read the file and ignore empty lines
    with open(path, 'r') as file:
        lines = [l for l in (ln.rstrip('\n') for ln in file.readlines()) if l.strip()]

    if len(lines) < 3:
        raise ValueError("File must contain at least 3 non-empty lines: comment, header, data")

    header_line = lines[1]
    headers = [h.strip() for h in header_line.strip().split(',') if h.strip()]
    data_lines = [l.strip() for l in lines[2:] if l.strip()]

    def _parse_one_data_line(data_line):
        # split into space-separated rows, stripping trailing commas from each
        rows = [row.rstrip(',') for row in data_line.split(' ') if row.strip()]

        # If header_line contains a space, treat it as a separator between per-tree and per-segment headers
        if ' ' in header_line:
            # headers up to the first space (prefix) are skipped
            idx = header_line.find(' ')
            prefix_headers = [h.strip() for h in header_line[:idx].split(',') if h.strip()]
            skip_n = len(prefix_headers)
            seg_headers = headers[skip_n:]
            # skip the corresponding first space-separated data chunk (per-tree attributes)
            seg_rows = rows[1:]
        else:
            seg_headers = headers
            seg_rows = rows

        # Parse each segment row (comma-separated values) into floats (robust to missing values)
        parsed = []
        for r in seg_rows:
            parts = [p for p in r.split(',') if p != '']
            row_vals = []
            for p in parts:
                try:
                    row_vals.append(float(p))
                except ValueError:
                    # preserve NaNs for non-parsable values
                    row_vals.append(float('nan'))
            parsed.append(row_vals)

        df = pd.DataFrame(parsed, columns=seg_headers)
        return df

    parsed_dfs = [_parse_one_data_line(dl) for dl in data_lines]

    # If original file had exactly 3 lines (single tree), return single DataFrame, else return list
    if len(lines) == 3:
        return parsed_dfs[0]
    return parsed_dfs


def rerun_bad_qsm(dir_pc, dir_mesh, dir_treefile, df_path, selection='reject', terrain_path=None, bounds=None, diam_min=None, smooth_tree=True):
    """
    Args
        dir_pc: absolute path to directory with tree point clouds
        dir_mesh: absolute path to directory with tree meshes
        dir_treefile: absolute path to directory with tree treefiles 
        df_path: absolute path to dataframe (.csv) with overview of all trees (output from 'make_treefile_dataframe' function)
        selection: tree class in dataframe ('selection' column) to select trees (one of 'reject', 'keep', 'maybe', 'snag' or 'undecided')
        terrain_path: path to terrain mesh. If specified this one will be used for all individual trees.
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

    # Instantiate list to store all trees that lead to multiple extracted instances
    multiple_trees = []

    # Loop over all treefiles
    for _, df_row in df_filtered.iterrows():
        treefile = df_row['filename']
        treefile_path = dir_treefile + treefile

        # Get corresponding pointcloud and mesh file
        pc_path = os.path.join(dir_pc, treefile.replace('treefile', 'segmented').replace('txt', 'ply'))
        mesh_path = os.path.join(dir_mesh, treefile.replace('.txt', '_mesh.ply'))
        
        # Run rayextract terrain
        if terrain_path is None:
            subprocess.run(["rayextract", "terrain", pc_path, "--gradient", "1"])
            terr_path = pc_path[:-4] + '_mesh.ply'
        else:
            terr_path = terrain_path

        # Run rayextract trees if a terrain mesh was made or specified
        if os.path.exists(terr_path):
            subprocess.run(["rayextract", "trees", pc_path, terr_path, "--max_diameter", "2", "--crop_length", "0.15", 
                            "--girth_height_ratio", "0.3", "--gravity_factor", "0.05", "--global_taper", "0.0", "--distance_limit", "1"])
        else:
            continue

        pc_new_path = pc_path[:-4] + '_segmented.ply'
        mesh_new_path = pc_path[:-4] + '_trees_mesh.ply'
        treefile_new_path = pc_path[:-4] + '_trees.txt'

        # Remove unnecessary intermediates
        if terrain_path is None:
            os.remove(terr_path) 
        os.remove(pc_new_path) # keep original point cloud

        if os.path.exists(mesh_new_path): # if rayextract succeeded (and made a tree), then continue
            # Remove old treefile and mesh
            if os.path.exists(treefile_path):
                os.remove(treefile_path)
            if os.path.exists(mesh_path):
                os.remove(mesh_path)

            if smooth_tree:
                # Run treeinfo and treefoliage
                subprocess.run(["treeinfo", treefile_new_path, "--branch_data", "--crop_length", "0.15"])
                treefile_new_info_path =  treefile_new_path[:-4] + '_info.txt'
                subprocess.run(["treefoliage", treefile_new_info_path, pc_path, "0.15"])
                treefile_new_info_foliage_path =  treefile_new_info_path[:-4] + '_foliage.txt'

                # Smooth and decimate treefile
                subprocess.run(["treesmooth", treefile_new_info_foliage_path])
                treefile_new_smooth_path = treefile_new_info_foliage_path[:-4] + '_smoothed.txt'
                subprocess.run(["treedecimate", treefile_new_smooth_path, "8", "segments"])
                treefile_new_smooth_decimated_path = treefile_new_smooth_path[:-4] + '_decimated.txt'

                # Make mesh
                subprocess.run(["treemesh", treefile_new_smooth_decimated_path])
                mesh_new_smooth_decimated_path = treefile_new_smooth_decimated_path[:-4] + '_mesh.ply'

                # Replace old mesh and treefile with new smoothed ones
                shutil.move(treefile_new_smooth_decimated_path, treefile_path) # move new treefile to directory
                shutil.move(mesh_new_smooth_decimated_path, mesh_path) # move new mesh to directory
                
                # Remove intermidiates
                os.remove(treefile_new_info_path)  
                os.remove(treefile_new_info_foliage_path)  
                os.remove(pc_path[:-4] + '_densities.ply')
                os.remove(treefile_new_smooth_path)  
                os.remove(mesh_new_path)
                os.remove(treefile_new_path) 

            else:
                # Replace old mesh and treefile with new ones
                shutil.move(treefile_new_path, treefile_path)
                shutil.move(mesh_new_path, mesh_path) # move new mesh to directory

            # Update tree dataframe
            df_tf = read_rayextract_treefile(treefile_path)
            
            if isinstance(df_tf, list):
                multiple_trees.append(treefile)
            else:
                df.loc[(df['filename'] == treefile, 'x')] = df_tf['x'][0]
                df.loc[(df['filename'] == treefile)]['y'] = df_tf['y'][0]
                df.loc[(df['filename'] == treefile)]['d'] = df_tf['radius'][0] * 2

    print('trees that led to multiple extracted trees:', multiple_trees)
              

if __name__ == "__main__":

    # Path to tree pointclouds and treefiles 
    dir_pc = '/Stor1/wouter/data/chile/FUR001/rayextract/tree_pointclouds/'
    dir_treefile = '/Stor1/wouter/data/chile/FUR001/rayextract/tree_treefiles/'
    dir_mesh = '/Stor1/wouter/data/chile/FUR001/rayextract/tree_meshes/'
    df_path = '/Stor1/wouter/data/chile/FUR001/rayextract/treefiles_dataframe.csv'
    # terrain_path = '/Stor1/wouter/data/chile/FUR001/rayextract/FUR001_0.01m_70x70m_filtered_transformed_raycloud_mesh.ply'
    terrain_path = None

    bounds = None
    diam_min = 0.0
    selection = 'fix'
    smooth_tree = True

    rerun_bad_qsm(dir_pc, dir_mesh, dir_treefile, df_path, selection, terrain_path=terrain_path, bounds=None, diam_min=None, smooth_tree=smooth_tree)

