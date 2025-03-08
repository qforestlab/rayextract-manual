#!/bin/bash

# Check if directory is passed as argument
if [ -z "$1" ]; then
  echo "Usage: $0 <directory> <command>"
  exit 1
fi

# Check if command is passed as argument
if [ -z "$2" ]; then
  echo "Usage: $0 <directory> <command>"
  exit 1
fi

# Assign variables to arguments
directory=$1
shift
command="$@"
echo $command

# Check if the provided directory exists
if [ ! -d "$directory" ]; then
  echo "Directory $directory does not exist."
  exit 1
fi

# Iterate over each file in the directory
for file in "$directory"/*; do
  if [ -f "$file" ]; then
    filename=$(basename "$file")
    echo "Running $command $filename"
    eval "$command \"$filename\""
  fi
done
