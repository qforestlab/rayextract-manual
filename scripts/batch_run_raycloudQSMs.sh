#!/bin/bash
rm trees/*_raycloud*

echo "Running txt2ply.py on all trees in directory..."
python txt2ply.py trees trees

echo "Running rayimport..."
bash batch_rayimport.sh

echo "Running rayextract terrain..."
bash batch_rayextract_terrain.sh

echo "Running rayextract trees..."
bash batch_rayextract_trees.sh

echo "Running batch_tree_info.sh"
bash batch_tree_info.sh

echo "All scripts have been executed!"
