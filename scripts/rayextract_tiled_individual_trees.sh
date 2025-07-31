# grids the large raycloud file $1, performs rayextract trees on each grid cell, and combines the results into a single $1_trees.txt file
# also splits out individual tree segmented point clouds, individual tree.txt files, and corresponding tree_mesh files
# these individual tree files can be found in individual_pcs, individual_trees, and individual_mesh respectively.

# $1 is cloudname without file extension
# $2 is grid tile dimensions (in meters)
# $3 is overlap on tiles to avoid edge artifacts (in meters). Recommended to be width of largest tree crown.

# example:
# bash ./rayextract_tiled_individual_trees.sh cloudname 50 15

set -x
#raysplit into grid tiles using input parameters
raysplit $1.ply grid $2,$2,0 $3
#create directories to organize outputs
rm -rf gridfiles_cloud
rm -rf gridfiles_mesh
rm -rf gridfiles_trees
rm -rf gridfiles_segmented
rm -rf gridfiles_trees_mesh
rm -rf individual_pcs
rm -rf individual_trees
rm -rf individual_meshs
mkdir gridfiles_cloud   
mkdir gridfiles_mesh      
mkdir gridfiles_trees      
mkdir gridfiles_segmented
mkdir gridfiles_trees_mesh
mkdir individual_pcs
mkdir individual_trees
mkdir individual_meshs

# move tiles point clouds into directory and then rayextract terrain/trees on each tile,
# places outputs in previously created directories
mv $1_*.ply gridfiles_cloud
cd gridfiles_cloud
for f in $1_*.ply;
do
   rayextract terrain $f
   mv *_mesh.ply ../gridfiles_mesh
   rayextract trees $f ../gridfiles_mesh/${f%.ply}_mesh.ply --grid_width $2 --max_diameter 5 #max diameter of trees set to 5m
   mv *_segmented.ply ../gridfiles_segmented
   mv *_trees.txt ../gridfiles_trees
   mv *_trees_mesh.ply ../gridfiles_trees_mesh
done

# runs raysplit seg_colour to assign index to segmented trees by colour
# creates directory to store individual tree point clouds
# places individual trees in individual_pcs directory
cd ../gridfiles_segmented
for f in $1_*.ply;
do
    raysplit $f seg_colour
    mv *_segmented_* ../individual_pcs
done

# runs treesplit per-tree to assign index to individual tree files by colour
# creates directory to store individual tree files
# places individual trees in individual_trees directory, within gridfiles_trees
cd ../gridfiles_trees
for f in $1_*.txt;
do
    treesplit $f per-tree
    mv *_trees_* ../individual_trees
done

# calls rct_treefile_individual_trees_filter.py
# selects the trees that are within dbh & x/y filter parameters
cd ../individual_trees
rm -rf selected
mkdir selected
rm -rf ../individual_pcs/selected
mkdir ../individual_pcs/selected
rm selected_trees.txt
for f in *.txt;
do
    python ../../../rct_treefile_individual_trees_filter.py -i $f
done
cd ..

# runs treemesh on individual treefiles to generate mesh for each tree
# creates directory to store individual mesh files
# places individual meshs in individual_trees_mesh directory, within gridfiles_trees_mesh
cd individual_trees/selected
for f in $1_*.txt;
do
    treemesh $f
    mv *_mesh.ply ../../individual_meshs
done
cd ../..

#combines tiled tree files into one single tree file for the whole plot, placed in main directory
cd gridfiles_trees
treecombine $1_*_trees.txt
mv *_combined.txt ..
cd ..
set +x
