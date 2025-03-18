import os
import argparse
import open3d as o3d

def txt_to_ply(input_file, output_file):
    # Read txt file
    points = []
    with open(input_file, 'r') as f:
        for line in f:
            data = line.strip().split()
            if len(data) >= 3:
                points.append([float(data[0]), float(data[1]), float(data[2])])

    # Create PointCloud object
    point_cloud = o3d.geometry.PointCloud()
    point_cloud.points = o3d.utility.Vector3dVector(points)

    # Write to ply file
    o3d.io.write_point_cloud(output_file, point_cloud)
    print(f"Converted {input_file} to {output_file}")

def txt_files_to_ply(input_dir, output_dir):
    # Create output directory if not exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Iterate through txt files in input directory
    for filename in os.listdir(input_dir):
        if filename.endswith('.txt'):
            input_file = os.path.join(input_dir, filename)
            output_file = os.path.join(output_dir, filename.replace('.txt', '.ply'))
            txt_to_ply(input_file, output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert TXT files to PLY files using Open3D.')
    parser.add_argument('input_dir', type=str, help='Input directory containing TXT files')
    parser.add_argument('output_dir', type=str, help='Output directory to save PLY files')
    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir
    txt_files_to_ply(input_dir, output_dir)
