#!/bin/bash

for file in ./trees/*trees.txt; do
  if [ -f "$file" ]; then
    echo "Processing $file"
    # Add your commands here
    treeinfo "$file"
 fi
done
