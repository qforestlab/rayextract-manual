#!/bin/bash
rm trees/*_raycloud*

echo "Converting all trees in directory to ply via txtlaslaz2ply.py..."
python file2ply.py trees trees

cd trees

echo "Running rayimport..."
for file in ./*.ply; do
  if [ -f "$file" ]; then
    echo "Processing $file"
    # Add your commands here
    rayimport "$file" 0,0,-1 --max_intensity 0 --remove_start_pos
  fi
done

rm -r rayclouds
mkdir rayclouds
mv *_raycloud.ply rayclouds

echo "Running rayextract terrain..."
for file in ./rayclouds/*_raycloud.ply; do
  if [ -f "$file" ]; then
    echo "Processing $file"
    # Add your commands here
    rayextract terrain "$file"
  fi
done

rm -r terrain_meshs
mkdir terrain_meshs
mv ./rayclouds/*_raycloud_mesh.ply ./terrain_meshs

echo "Running rayextract trees..."

for data_file in ./rayclouds/*_raycloud.ply; do
  # Extract the basename without '_raycloud.ply'
  base_name=$(basename "$data_file" | sed 's/_raycloud\.ply//')

  # Find the corresponding mesh file
  mesh_file="./terrain_meshs/${base_name}_raycloud_mesh.ply"
  
  rayextract trees "$data_file" "$mesh_file" --max_diameter 2 --distance_limit 9
#  if [ -f "$mesh_file" ]; then
#    echo "Processing $data_file with $mesh_file"
#    # Replace the following line with your actual command
#    rayextract trees "$data_file" "$mesh_file" --max_diameter 2 --distance_limit 9 --gravity_factor 0.1
#  else
#    echo "No matching mesh file for $cloud_file"
#  fi
done

rm -r qsms
mkdir qsms
mv ./rayclouds/*_trees.txt ./qsms
rm -r trees_mesh
mkdir trees_mesh
mv ./rayclouds/*_trees_mesh.ply ./trees_mesh
rm -r segmented_pcs
mkdir segmented_pcs
mv ./rayclouds/*_segmented.ply ./segmented_pcs

echo "Running batch_tree_info.sh"
for file in ./qsms/*trees.txt; do
  if [ -f "$file" ]; then
    echo "Processing $file"
    # Add your commands here
    treeinfo "$file"
 fi
done

rm -r trees_info
mkdir trees_info
mv ./qsms/*_trees_info.txt ./trees_info

cd ..

echo "All scripts have been executed!"
