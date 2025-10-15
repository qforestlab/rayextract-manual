#!/bin/bash
rm trees/*_raycloud*

echo "Converting all trees in directory to ply via txtlaslaz2ply.py..."
python txtlaslaz2ply.py trees trees

echo "Running rayimport..."
for file in ./trees/*.ply; do
  if [ -f "$file" ]; then
    echo "Processing $file"
    # Add your commands here
    rayimport "$file" 0,0,-1 --max_intensity 0 --remove_start_pos
  fi
done

echo "Running rayextract terrain..."
for file in ./trees/*_raycloud.ply; do
  if [ -f "$file" ]; then
    echo "Processing $file"
    # Add your commands here
    rayextract terrain "$file"
  fi
done
mkdir 

echo "Running rayextract trees..."
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

echo "Running batch_tree_info.sh"
for file in ./trees/*trees.txt; do
  if [ -f "$file" ]; then
    echo "Processing $file"
    # Add your commands here
    treeinfo "$file"
 fi
done

cd trees
rm -r rayclouds
mkdir rayclouds
mv *_raycloud.ply rayclouds
rm -r terrain_meshs
mkdir terrain_meshs
mv *_raycloud_mesh.ply terrain_meshs
rm -r qsms
mkdir qsms
mv *_trees.txt qsms
rm -r trees_info
mkdir trees_info
mv *_trees_info.txt trees_info
rm -r trees_mesh
mkdir trees_mesh
mv *_trees_mesh.ply trees_mesh
rm *_segmented.ply
cd ..

echo "All scripts have been executed!"
echo "Note: All '_segemented.ply' files removed (they are duplicates of input rayclouds)" 
