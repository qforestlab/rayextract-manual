import pandas as pd
import shutil
from pathlib import Path
import argparse


def copy_selected_trees(dir, trees_df_path, selection='keep', bounds=None, diam_min=None):
    ''' Copy selected trees (treefiles, tree pointclouds, tree meshes) into new directory.
        Trees can be selected based on a bounding box, minimum diameter or selection status
        as given in a dataframe.csv (see 'make_tree_dataframe.py')

        Assumes a main directory with subdirectories 'trees_treefiles, 'trees_pointclouds' and
        'trees_mesh'. It will be copied to new directories called <dir_original>_selection.
    '''
    # Main working directory
    dir = Path(dir)

    # Filepaths to directories containing tree pointclouds and meshes
    dir_tf = dir / 'trees_treefiles'
    dir_pc = dir / 'trees_pointclouds'
    dir_mesh = dir / 'trees_meshes'

    # Make new directories in working directory to copy the selected trees to
    dir_tf_sel = dir / 'trees_treefiles_selection'
    dir_pc_sel = dir / 'trees_pointclouds_selection'
    dir_mesh_sel = dir / 'trees_meshes_selection'
    dir_tf_sel.mkdir(parents=True, exist_ok=True)
    dir_pc_sel.mkdir(parents=True, exist_ok=True)
    dir_mesh_sel.mkdir(parents=True, exist_ok=True)
    
    # Read dataframe with tree overview and 
    df = pd.read_csv(trees_df_path)

    # keep only selected trees
    if selection is not None:
        df = df[df['selection'] == selection]

    # Keep only trees within rectangular bounds
    if bounds is not None:
        x_min, x_max, y_min, y_max = bounds
        df = df[
            (df['x'] > x_min) & 
            (df['x'] < x_max) & 
            (df['y'] > y_min) & 
            (df['y'] < y_max)
        ]

    # Keep only trees larger than minimum diameter
    if diam_min is not None:
        df = df[(df['d'] > diam_min)]

    # Get names of filtered trees
    tf_names = df['filename'].values
    print(f'Copying {len(tf_names)} trees')

    # Loop over all selected trees (tf + pc + mesh) and copy them to new dirs
    for tf_name in tf_names:
        pc_file = tf_name.replace('trees', 'segmented').replace('txt', 'ply')
        mesh_file = tf_name.replace('.txt', '_mesh.ply')

        shutil.copy(dir_tf / tf_name, dir_tf_sel / tf_name)
        shutil.copy(dir_pc / pc_file, dir_pc_sel / pc_file)
        shutil.copy(dir_mesh / mesh_file, dir_mesh_sel / mesh_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy selected trees to new directories")
    parser.add_argument("dir", help="Directory containing treefiles")
    parser.add_argument("df_path", help="Path to dataframe.csv ")
    parser.add_argument("--selection", default='keep', help="one of 'keep', 'undecided', 'maybe' or 'reject'")
    parser.add_argument("--bounds", default=None, help="[x_min, x_max, y_min, y_max]")
    parser.add_argument("--diam_min", default=None, help="minimum diameter [m]")
    args = parser.parse_args()

    copy_selected_trees(args.dir, args.df_path, args.selection, args.bounds, args.diam_min)