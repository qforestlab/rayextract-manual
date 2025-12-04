from scipy.io import loadmat, savemat
import numpy as np
import pandas as pd
import os
import argparse
from pathlib import Path
import open3d as o3d
from tqdm import tqdm


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


def extend_cylinder(start, end, extra=0.1):
    """
    Args
        start (numpy.array): Start points of final cylinders. Array of shape nx3 with x, y, z columns.
        end (numpy.array): End points of final cylinders. Array of shape nx3 with x, y, z columns.
        extra (float): distance to extend cylinder (in meter)

    Returns
        numpy.array: array with new extended end points. Array of shape nx3 with x, y, z columns.
    """
    # translate vector to start at (0, 0, 0)
    x, y, z = (end - start).T
    x_end, y_end, z_end = end.T

    # Calculate angles and 
    theta = np.arctan(z / np.sqrt(x**2 + y**2)) # positive from x-y plane towards z
    phi = np.arctan(y / x) # positive from x axis towards y
    z_new = z_end + extra * np.sin(theta)
    x_new = x_end + extra * np.cos(phi) * np.cos(theta)
    y_new = y_end + extra * np.sin(phi) * np.cos(theta)

    return np.column_stack((x_new, y_new, z_new))


def extend_QSM(df, extra=0.1):
    """
    Args
        df (pandas.DataFrame): dataframe output from function `read_raycloud_treefile()`
        extra (float): additional distance to add to cylinder

    Returns
        df: same dataframe but with x,y,z values for end cylinders linearly extended by 'extra'
    """
    # Get end points mask
    mask = np.ones((df.shape[0], 1), dtype=bool)
    unique = df['parent_id'].unique()[1:] # all points that are not referenced as parent
    mask[unique.astype(np.uint64)] = False

    # Get end points
    endpt = df.loc[mask, ['x', 'y', 'z']]

    # Get start point corresponding to endpoint cylinders
    parentid = df.loc[mask, 'parent_id']
    startpt = df.loc[parentid.astype(np.uint64), ['x', 'y', 'z']]

    # Calculate new extended end points
    endpt_new = extend_cylinder(startpt.values, endpt.values, extra)

    # Replace original by new end points
    df.loc[mask.flatten(), ['x', 'y', 'z']] = endpt_new

    return df


def find_foliated_cylinders(df, path_pointcloud, radius_multipler=2.0, ax_dist_multipler=0.4, leaf_points_threshold=2):
    # TODO: optimize this function
    """
    Args
        df (pandas.DataFrame): dataframe output from function `read_raycloud_treefile()`
        path_pointcloud (str): path to point cloud file (e.g. .ply) used to build the treefile
        radius_multipler (float): multiplier to define max radius around cylinder to search for points
        ax_dist_multipler (float): axial distance multipler to consider a point as leaf point
        leaf_points_threshold (float): minimum number of leaf points to consider a cylinder as foliated

    Returns
        df (pandas.DataFrame): dataframe with an additional boolean column 'foliated' indicating whether a cylinder is foliated or not
    """
    # Read point cloud into numpy array
    if os.path.exists(path_pointcloud):
        points = o3d.io.read_point_cloud(path_pointcloud).points
        points = np.asarray(points, dtype=np.float32)
    else:
        raise FileNotFoundError(f"Pointcloud file not found: {path_pointcloud}")
    
    # Pre-allocate foliated column
    df['foliated'] = True

    n = df.shape[0] - 1
    for i in tqdm(range(n)):
        # Get cylinder end and start points
        xyz_end = df.values[i + 1][0:3]
        pid = int(df.values[i + 1][4])
        xyz_start = df.values[pid][0:3]
        radius = df.values[i + 1][3] # Radius is the one of the current point

        # Compute cylinder geometry
        vec_cyl = xyz_end - xyz_start
        length_cyl = np.linalg.norm(vec_cyl)
        axis_cyl = vec_cyl / length_cyl
        center = (xyz_start + xyz_end) / 2.0

        # Subselect points within spherical radius around the cylinder center
        dists_center = np.linalg.norm(points - center.astype(np.float32), axis=1)
        max_radius = radius_multipler * max(radius, length_cyl / 2)
        mask_center = dists_center <= max_radius
        points_near_center = points[mask_center]

        # Compute perpendicular distance to the axis and 
        vec_start_to_sub = points_near_center - xyz_start
        proj_length_sub = np.dot(vec_start_to_sub, axis_cyl) # projection length along axis
        proj_points_sub = np.outer(proj_length_sub, axis_cyl)
        vec_perp_sub = vec_start_to_sub - proj_points_sub
        dist_perp_sub = np.linalg.norm(vec_perp_sub.astype(np.float32), axis=1)

        # Define leaf points as those that are sufficiently far from the cylinder axis
        # and within axial bounds
        mask_axial = (proj_length_sub >= 0.0) & (proj_length_sub <= length_cyl)
        ax_dist_threshold = ax_dist_multipler * radius
        mask_far = dist_perp_sub > (radius + ax_dist_threshold)

        # Get number of leaf points
        leaf_points = points_near_center[mask_axial & mask_far]
        n_leaf_points = np.shape(leaf_points)[0]

        # Set cylinder as non-foliated if below threshold
        if n_leaf_points < leaf_points_threshold:   
            df.loc[i + 1, 'foliated'] = False

        # Mark the base point as non-foliated
        df.loc[[0,1], 'foliated'] = False

    print(f'{(df['foliated'] == False).sum()} out of {n} cylinders marked as non-foliated')

    return df


def treefile_to_treeqsm(path_in, path_out, outer_cylinder_extention=None, path_pointcloud=None):
    ''' Function to convert qsm from raycloudtools (=treefile) TreeQSM style qsm.mat file
        Assumes a treefile with only one tree.

        Args:
            path_in: treefile.txt, output from raycloudtools
            path_out: output matlab file (.mat)
            outer_cylinder_extention: distance to linearly extend outer cylinders (in meter)
    '''
    # Read treefile.txt
    df = read_raycloud_treefile(path_in)

    # Optionally extend outer cylinders in QSM by 'extra' distance
    if outer_cylinder_extention:
        print(f"Extending outer cylinders by {outer_cylinder_extention} meter")
        extend_QSM(df, outer_cylinder_extention)

    # Optionally find foliated cylinders
    if path_pointcloud:
        print(f"Finding dead branches based on point cloud")
        df = find_foliated_cylinders(df, path_pointcloud)
                            
    # Pre-allocate QSM
    n = df.shape[0] - 1
    qsm = {
        'start': np.zeros((n, 3), dtype=np.float32),
        'axis': np.zeros((n, 3), dtype=np.float32),
        'length': np.zeros((n, 1), dtype=np.float32),
        'radius': np.zeros((n, 1), dtype=np.float32),
        'parent': np.zeros((n, 1), dtype=np.int64), 
        'branch': np.zeros((n, 1), dtype=np.int64),
        'foliated': df['foliated'].values[1:].astype(bool).reshape((n, 1)) if 'foliated' in df.columns else np.ones((n, 1), dtype=np.int64),
    }

    # Initialize branch number as 1
    branch = 1
    qsm['branch'][0] = branch

    # Loop over rows (=cylinders) in df
    for i in range(n):
        # Get cylinder end and start points
        current = df.values[i + 1] # End point of current cylinder
        previous = df.values[i] # Previous point
        pid = int(current[4])
        parent = df.values[pid] # Starting point of current cylinder

        # Calculate euclidean distance 
        length = np.sqrt(np.sum((current[0:3] - parent[0:3])**2))
        
        # Store cylinder values
        qsm['start'][i, :] = parent[0:3] # Start point of cylinder
        qsm['axis'][i, :] = (current[0:3] - parent[0:3]) / length # Normalized direction vector
        qsm['length'][i] = length # Length of cylinder
        qsm['radius'][i] = current[3] # Radius of cylinder
        qsm['parent'][i] = pid # parent ID

        # TODO: branch number doesn't work yet
        # Branch number: branch number equals that of parent, unless subsequent cylinders have the same parent, then increase the branch number
        if pid == previous[4]:
            # Two options: new branch number after every split (uncomment two lines below), or one main branch that keeps continuing with 'secondary' branches having a diffent number
            branch += 1
            qsm['branch'][i - 1] = branch
            branch += 1
            qsm['branch'][i] = branch
        else:
            row = pid - 1 if pid > 0 else 0 # row of the parent cylinder, set to 0 for first cylinder (otherwise row = -1)
            qsm['branch'][i] = qsm['branch'][row] # branch number of the parent

    # Format data into how it looks like when reading a qsm.mat file (see read_qsm_mat function)
    arr = np.array([[(qsm['start'], qsm['axis'], qsm['length'], qsm['radius'], qsm['parent'], qsm['branch'], qsm['foliated'])]], dtype=[(key, 'O') for key in qsm.keys()])
    cyl = np.array([[(arr,)]], dtype=[('cylinder', 'O')])

    # Save arrays as matlab structure
    print(f"Saving QSM to {path_out}")
    savemat(path_out, {'qsm': cyl})

    return qsm


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert treefiles to matlab QSMs")
    parser.add_argument("dir_treefile", help="Directory containing treefiles")
    parser.add_argument("dir_qsm", help="Directory to save matlab qsms")
    parser.add_argument('--extend_qsm', help='distance to linearly extend outer cylinders (in meter)', default=None, type=float)
    parser.add_argument('--dir_pointclouds', help='directory to pointclouds to find foliated cylinders', default=None, type=str)
    args = parser.parse_args()

    dir_treefile = Path(args.dir_treefile)
    dir_qsm = Path(args.dir_qsm)
    dir_qsm.mkdir(parents=True, exist_ok=True)
    dir_pointclouds = Path(args.dir_pointclouds) if args.dir_pointclouds else None
    outer_cylinder_extention = args.extend_qsm

    treefiles = os.listdir(args.dir_treefile)

    # Loop over all treefiles and convert to matlab qsm
    for treefile in treefiles:
        path_in = dir_treefile / treefile
        path_out = (dir_qsm / treefile).with_suffix('.mat')
        path_pointcloud = dir_pointclouds / (treefile.replace('_trees_smoothed_decimated.txt', '.ply')) if dir_pointclouds else None

        print(f"Processing {path_in}...")
        treefile_to_treeqsm(path_in, path_out, outer_cylinder_extention, path_pointcloud)
