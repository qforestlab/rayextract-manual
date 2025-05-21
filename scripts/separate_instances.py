import os
import argparse

import numpy as np
import open3d as o3d


def seperate_instances(pc):
    points = pc.point.positions.numpy()
    colors = pc.point.colors.numpy()

    unique_colors = np.unique(colors, axis=0)

    instances = []
    for color in unique_colors:
        # color 0,0,0 are all points classified as non-instances
        if (color == np.array([0,0,0])).all():
            continue
        idx_mask = np.all(colors == color, axis=1)
        tree_points = points[idx_mask]
        tree = o3d.t.geometry.PointCloud(tree_points)
        instances.append(tree)

    return instances

def write_instances(instances, odir, prefix):
    for i, instance in enumerate(instances):
        o_name = os.path.join(odir, f"{prefix}_{i}.ply")
        o3d.t.io.write_point_cloud(o_name, instance)
        

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('-i', "--input", type=str, required=True)    
    parser.add_argument('-o', "--odir", type=str)
    parser.add_argument('-p', "--prefix", type=str, default="tree")

    args = parser.parse_args()

    pc = o3d.t.io.read_point_cloud(args.input)

    if args.odir is None:
        # write at location of pc
        args.odir = os.path.join(os.path.dirname(args.input), "trees")
        if not os.path.exists(args.odir):
            os.makedirs(args.odir)
    
    instances = seperate_instances(pc)

    write_instances(instances, args.odir, args.prefix)

if __name__ == "__main__":
    main()
