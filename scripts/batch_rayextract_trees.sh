#!/bin/bash

data_folder="./trees"

for data_file in "$data_folder"/*_raycloud.ply; do
  # Extract the basename without '_raycloud.ply'
  base_name=$(basename "$data_file" | sed 's/_raycloud\.ply//')

  # Find the corresponding mesh file
  mesh_file="$data_folder/${base_name}_raycloud_mesh.ply"
  
  rayextract trees "$data_file" "$mesh_file" --max_diameter 2 --distance_limit 9
#  if [ -f "$mesh_file" ]; then
#    echo "Processing $data_file with $mesh_file"
#    # Replace the following line with your actual command
#    rayextract trees "$data_file" "$mesh_file" --max_diameter 2 --distance_limit 9 --gravity_factor 0.1
#  else
#    echo "No matching mesh file for $cloud_file"
#  fi
done
