#!/bin/bash

for file in ./trees/*.ply; do
  if [ -f "$file" ]; then
    echo "Processing $file"
    # Add your commands here
    rayimport "$file" 0,0,-1 --max_intensity 0 --remove_start_pos
  fi
done
