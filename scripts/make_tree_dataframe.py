import os
import pandas as pd
import argparse


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


def make_treefiles_dataframe(treefile_dir, df_out):
    ''' makes a dataframe with columns 'filename, tree id, x-coordinate first cylinder, 
        y-coordinate first cylinder, diameter, selection status (default = undecided)' 
    '''
    # Loop over all treefiles in directory
    data = []
    for treefile in os.listdir(treefile_dir):
        # Get tree index from filename
        idx = treefile[:-4].split('_')[-1]

        # Read treefile into dataframe
        df = read_rayextract_treefile(treefile_dir + treefile)

        # Store name. id, base coordinates and radius
        data.append({
            'filename': treefile,
            'id': idx,
            'x': df['x'][0],
            'y': df['y'][0],
            'd': df['radius'][0] * 2,
            'selection': 'undecided',
        })

    # Convert to pandas dataframe and store as CSV
    df = pd.DataFrame(data)
    return df.to_csv(df_out, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Make csv dataframe with all treenames and attributes")
    parser.add_argument("dir_treefile", help="Directory containing treefiles")
    parser.add_argument("df_out", help="Path to dataframe.csv ")
    args = parser.parse_args()

    make_treefiles_dataframe(args.dir_treefile, args.df_out)