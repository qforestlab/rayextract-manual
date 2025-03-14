#!/bin/bash

for file in ./trees/*_raycloud.ply; do
  if [ -f "$file" ]; then
    echo "Processing $file"
    # Add your commands here
    rayextract terrain "$file"
  fi
done
