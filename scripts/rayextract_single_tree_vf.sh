#!/bin/bash

# Bash script for running Rayextract commands in batch for multiple single tree point cloud files (.ply format)
# This is a variation for 'virtual_forest' creation: the difference is that we here use --crop_length 0.15 to
# make branches grow up to 15cm from the end instead of 1m by default. This ensures the tree doesn't shrink when
# populating leaves and using it for radiative transfer modelling. We also use treesmooth and treedecimate to reduce
# the amount of cylinders.
#
# Usage: bash rayexctract_single_trees.sh <path_to_directory>
#
# Input: <path_to_directory> is the (absolute) path to the directory containing a number of single tree point cloud .ply files
# Output: a new directory called <path_to_directory>_rayextract, containing 5 subdirectories with all the rayextract output 
#         for all trees. (1) original point clouds as 'raycloud' files,  (2) Ground mesh files, (3) segmented tree point cloud
#         (for individual trees this is normally just the whole point cloud), (4) Tree QSM files as treefile.txt, (5) Tree QSM
#         as mesh (.ply) file

# Check if input directory is provided
if [ -z "$1" ]; then
    echo "Usage: $1 <input_directory>"
    exit 1
fi

# Define directories
INPUT_DIR="$1"
RAYCLOUD_DIR="${INPUT_DIR}_rayextract/raycloud_files"
MESH_DIR="${INPUT_DIR}_rayextract/ground_mesh_files"
TREES_DIR="${INPUT_DIR}_rayextract/trees_mesh_files"
TREES_QSM_DIR="${INPUT_DIR}_rayextract/trees_treefile_files"
TREES_SEGM_DIR="${INPUT_DIR}_rayextract/trees_segmented_files"

# Create output directories if they don't exist
mkdir -p "$RAYCLOUD_DIR" "$MESH_DIR" "$TREES_DIR" "$TREES_QSM_DIR" "$TREES_SEGM_DIR"

# Loop over all .ply files in the input directory
for ply_file in "$INPUT_DIR"/*.ply; do
    # Skip if no .ply files exist
    [ -e "$ply_file" ] || continue
    
    # Extract filename without extension
    base_name=$(basename "$ply_file" .ply)
    echo $base_name

    # Define output filenames
    raycloud_file="$RAYCLOUD_DIR/${base_name}_raycloud.ply"
    mesh_file="$MESH_DIR/${base_name}_raycloud_mesh.ply"
    trees_file="$TREES_DIR/${base_name}_raycloud_trees_smoothed_decimated_mesh.ply"
    trees_segm_file="$TREES_SEGM_DIR/${base_name}_raycloud_segmented.ply"
    trees_qsm_file="$TREES_QSM_DIR/${base_name}_raycloud_trees_smoothed_decimated.txt"
    
    # Run rayimport only if the raycloud file does not already exist
    if [ ! -f "$raycloud_file" ]; then
        rayimport "$ply_file" ray 0,0,-0.1 --max_intensity 0 # --remove_start_pos
        mv "$INPUT_DIR/${base_name}_raycloud.ply" "$raycloud_file"
    fi
    
    # Run rayextract only if the mesh file does not already exist
    if [ ! -f "$mesh_file" ]; then
        rayextract terrain "$raycloud_file"
        mv "$RAYCLOUD_DIR/${base_name}_raycloud_mesh.ply" "$mesh_file"
    fi
    
    # Run rayextract trees only if the trees file does not already exist
    if [ ! -f "$trees_file" ]; then
        rayextract trees "$raycloud_file" "$mesh_file" --max_diameter 1.5 --crop_length 0.15 # max diameter = 1.5, branches up to 0.15m from end
        # Smooth and decimate treefile
        treesmooth "$RAYCLOUD_DIR/${base_name}_raycloud_trees.txt"
        treedecimate "$RAYCLOUD_DIR/${base_name}_raycloud_trees_smoothed.txt" 8 segments
        # Make mesh
        treemesh "$RAYCLOUD_DIR/${base_name}_raycloud_trees_smoothed_decimated.txt"

        mv "$RAYCLOUD_DIR/${base_name}_raycloud_trees_smoothed_decimated_mesh.ply" "$trees_file"
        mv "$RAYCLOUD_DIR/${base_name}_raycloud_segmented.ply" "$trees_segm_file"
        mv "$RAYCLOUD_DIR/${base_name}_raycloud_trees_smoothed_decimated.txt" "$trees_qsm_file"

        rm "$RAYCLOUD_DIR/${base_name}_raycloud_trees.txt"
        rm "$RAYCLOUD_DIR/${base_name}_raycloud_trees_smoothed.txt"
        rm "$RAYCLOUD_DIR/${base_name}_raycloud_trees_mesh.ply"

    fi
    
    echo "Processing complete for: $ply_file"
done

echo "All files processed."