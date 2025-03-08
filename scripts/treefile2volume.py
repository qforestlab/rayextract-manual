import os
import pandas as pd
import numpy as np
import argparse

def calculate_volume(tree_cylinders):
    ''' Expects one tree as input
    '''
    tree_arr = np.array(tree_cylinders).reshape((-1,6))
    vertices = tree_arr[:,0:3].astype(float)
    radius = tree_arr[:,3].astype(float)
    parent_id = tree_arr[:,4].astype(int)
    section_id = tree_arr[:,5].astype(int)

    nsegments = parent_id.shape[0] - 1
    segment_volume = np.zeros(nsegments, dtype=float)

    for i in range(1,parent_id.shape[0],1):
        j = parent_id[i]
        p0 = vertices[j]
        p1 = vertices[i]
        v = p1 - p0
        r0 = radius[j]
        r1 = radius[i]
        l = np.sqrt(np.sum(v**2))
        segment_volume[i-1] = np.pi * l / 3 * (r0**2 + r0*r1 + r1**2)

    volume = np.sum(segment_volume)
    return volume


def read_tree_cylinders(file_path):
    with open(file_path,'r') as f:
        for i, line in enumerate(f):
            if i > 1:
                tree_cylinders = line.strip().split(',')
    return tree_cylinders


def process_raycloud_files(input_dir):
    volume_data = []
    for filename in os.listdir(input_dir):
        if filename.endswith('_raycloud_trees.txt'):
            file_path = os.path.join(input_dir, filename)
            # Read file according to some function
            tree_cylinders = read_tree_cylinders(file_path)

            # Calculate volume according to some function
            volume = calculate_volume(tree_cylinders)

            # Append filename and volume to data list
            volume_data.append((filename, volume))

    return volume_data

def save_to_csv(volume_data, output_file):
    df = pd.DataFrame(volume_data, columns=['Filename', 'Volume'])
    df.to_csv(output_file, index=False)
    print(f"Volume data saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process raycloud files and calculate volumes.')
    parser.add_argument('input_dir', type=str, help='Input directory containing raycloud files')
    parser.add_argument('output_file', type=str, help='Output CSV file to save volume data')
    args = parser.parse_args()

    input_dir = args.input_dir
    output_file = args.output_file

    # Process raycloud files
    volume_data = process_raycloud_files(input_dir)

    # Save volume data to CSV
    save_to_csv(volume_data, output_file)
