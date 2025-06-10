# Rayextract manual
Repository with explanation and additional functionality for using [Raycloudtools](https://github.com/csiro-robotics/raycloudtools) for forest point cloud processing

## Installation using Docker

See below for a [source install](#install-from-source-alternative-to-docker).

The easiest ways to use Raycloudtools is via using [Docker](https://www.docker.com/). Docker is a software that makes a 'closed of' environment on your computer that contains an operating system (OS) and all required packages for a certain applications. Once you have Docker installed, you can just use/download the pre-made Docker 'image', start the image (a running image is called a 'container') and you're good to go. As the Docker image contains an OS (Ubuntu most often), it works on both Linux and Windows.

1. Install Docker
2. Download the latest raycloudtools docker image:

   ```
   docker pull ghcr.io/csiro-robotics/raycloudtools:latest
   ```

   Here `ghcr.io/csiro-robotics/raycloudtools:latest` is the name of the image that we're downloading ('pulling'), provided by the developers of raycloudtools. You can check the available docker images on you computer with the command ```docker images```.

3. Run the container:

   ```
   docker run -it --rm --name raycloudtools -v /path/to/datafolder_locally:/path/to/datafolder_container ghcr.io/csiro-robotics/raycloudtools:latest /bin/bash
   ```
   (On linux, you might have to use `sudo` before the command for root permissions)

   - The `-it` flag is used to run the container in interactive mode (create an interactive bash shell inside the container)
   - The `--rm` flag is used to automatically remove the container after usage (i.e., after exiting the bash terminal inside the container).
   - We use `--name raycloudtools` to give the name 'raycloudtools' to the running container
   - Normally, all files are packaged within the docker container and hence you don't have access to the filesystem on your computer from within the container. Therefore, we use `-v /path/to/folder_locally:/path/to/folder_container` to map a folder on your pc to a folder inside the container. You will then have access to this folder from within the container (but only to the mapped folder and subfolders!). Usually, you just need access to your datafiles that you want to process with rayextract, so the specified folder can be the one containing all your data. You have to replace `/path/to/folder_locally` with the absolute path to your datafolder on your pc, and `/path/to/folder_container` with the absolute path inside the docker container. Since the container is running linux, the path is specified with forward slashes ('/'), starting from the 'root' (first '/'). The provided raycloudtools docker image has by default a folder called `/workspace`, which is the entry point when running the container. Therefore, for example, you can map your datafolder as follows 
   
      Windows: `C:/Users/YourUsername/.../projectname/data:/workspace/data`

      Linux: `/home/username/.../projectname/data:/workspace/data`

      WSL: `/mnt/c/Users/username/.../projectname/data:/workspace/data`

      Make sure you put your path in between quotation marks (") if it contains spaces!



If all went well you now have access to a bash terminal inside the container:

![](./img/docker_run_snip.PNG)

 Inside this linux terminal you can use all the regular linux commands. For example, use `cd data` ('change directory'), to navigate into the data folder. You can use the `ls` command to list all the files/foldes inside the current folder. Now, you can run all the commands described in the next section. 
 
 To exit the docker container you can press CTRL+d. You will have to restart the container each time you want to use it (step 3), but no need to download the docker image again (only if there are updates made by the rayextract team).


## Usage

It is assumed that you have a forest plot or tree point cloud in '.ply' or '.las(z)' format. Just XYZ is enough. 

### Convert pointcloud to raycloud

The Raycloudtools library normally expects as input a '.ply' file with in the normal fields the scanner location. However, for the Rayextract tools useful for forest point cloud processing these are not actually used. Nonetheless, the normal fields must be there in order for the tool to work. The `rayimport` command can add these (empty) fields to your input file: 

```
rayimport your_pointcloud.ply ray 0,0,-1 --max_intensity 0 --remove_start_pos; 
```

Here, a constant vector of [0,0,-1] is added as scanner location in the normal field for all points. Note that we subtract the start position of the pointcloud (`--remove_start_pos`), to start at 0,0,0. This is optional, but recommended if your pointcloud has large values (potential precision overflow errors).

The output is a file called `your_pointcloud_raycloud.ply` in the same directory. 

### Extract terrain mesh

The first step is to extract the terrain mesh from the pointcloud: 

```
rayextract terrain your_pointcloud_raycloud.ply
```

The output is a file `your_pointcloud_raycloud_mesh.ply`, which is a terrain mesh file.

### Extract trees

To extract the trees we give as input the pointcloud (`your_pointcloud_raycloud.ply`) and the extracted terrain mesh (`your_pointcloud_raycloud_mesh.ply`). The `rayextract trees` command will use the mesh as seed points and simultaniously build a shortest path graph through all the tree points, using some heuristics to guide the connectivity. Hence, it combines the tree instance segmentation step and the cylinder fitting (i.e., QSM) building step.   

```
rayextract trees your_pointcloud_raycloud.ply your_pointcloud_raycloud_mesh.ply
```

The output is:
1) `your_pointcloud_raycloud_trees.txt` file (called 'treefile'), which contains the cylinder models of all the extracted trees (one line per tree)
2) `your_pointcloud_raycloud_segmented.ply` file, which is the original pointcloud with unique color for each extracted tree
3) a `your_pointcloud_raycloud_trees_mesh.ply` file, which contains all tree stems as meshes. 

The format of the treefile is explained in more detail in the [treetools](https://github.com/csiro-robotics/treetools) library, which contains functionality for working with treefiles. The treefiles library is also already installed in the docker image. Below are some examples of commands you can run.

Get more info for all trees:

```
treeinfo treefile.txt 
```

Split treefile with all trees into separate file for each tree:

```
treesplit treefile.txt per-tree
```

You will probably want to use this in combination with splitting the segmented pointcloud into individual trees (the subscript should match the one of the splitted treefile):

```
raysplit pointcloud_raycloud_segmented.ply seg_colour
```

Convert to mesh file:

```
treemesh treefile.txt
```

### Use with large plots

For large point clouds where Rayextract may crash because of memory limitations, you can use the provided [bash script](https://github.com/qforestlab/raycloudtools/blob/main/scripts/rayextract_trees_large.sh), which runs `raysplit` to split point cloud into tiles with a certain buffer, runs `rayextract terrain` and `rayextract trees` for each tile (keeping only trees with base of the stem within the tile), and combines the trees to a single treefile.txt.

For example:
```
bash <path_to_file>/rayextract_trees_large.sh your_pointcloud_raycloud 20
```
To use tiles of 20x20m. We recommend increasing the default buffer size of 5m in the script a bit (depending on the max width of the trees).

## Additional scripts

### Calculate volume for all trees in a treefile

You can use the treefile2volume.py python script:

``` 
python treefile2volume.py <directory_with_treefile(s)> <output_volume.csv>
```

It assumes a file `filename_raycloud_trees.txt` in the specified directory.

### Visualise treefile

You can use the functions in `visualise_treefile.py`

### Run rayextract for single tree point clouds

You can use the bash script `rayextract_single_trees.sh` to loop over single tree point clouds in a directory (.ply format) and run rayimport -> rayextract terrain -> rayextract trees on each tree:

```
bash rayexctract_single_trees.sh <path_to_directory>
```

Alternatively, have a look at the `batch_<command>.sh` scripts. For converting pointclouds in .txt format to .ply format, you can use the `txt2ply.py` python script.

### Convert treefile to TreeQSM format

You can use the functions in `treefile2treeQSM.py`

### Loop over all files in a directory

You can use the bash script loop_directory, which loops over all files in a directory and executes a certain command. For example, to convert all indivdual trees to tree meshes:

```
bash ./loop_directory.sh <your_directory> treemesh
```

## Install From Source (alternative to docker)

If you want an alternative to docker, or a static image of raycloudtools locally, you can install from source with the following instructions:

1. Install the 'extra' libraries needed for our specific funcionality of rayextract and treetools.
   It's recommended to install all the following in /home/user, or another level down in a custom directory

   a. LASzip
   ```
   git clone https://github.com/LASzip/LASzip.git
   cd LASzip
   git checkout tags/2.0.1
   mkdir build
   cd build
   cmake ..
   make
   sudo make install
   ```
   b. libLAS
   ```
   sudo apt-get install libboost-all-dev
   git clone https://github.com/libLAS/libLAS.git
   cd liblas
   mkdir build
   cd build
   cmake .. -DWITH_LASZIP=ON
   make
   sudo make install
   ```
   c. qhull
   ```
   git clone http://github.com/qhull/qhull.git
   cd qhull
   checkout tags/v7.3.2
   mkdir build
   cd build
   cmake .. -DCMAKE_POSITION_INDEPENDENT_CODE:BOOL=true
   make
   sudo make install
   ```
   
2. Install the core of raycloudtools and treetools

   a. Raycloudtools
   ```
   sudo apt-get install libeigen3-dev
   git clone https://github.com/ethz-asl/libnabo.git
   cd libnabo
   git checkout tags/1.0.7
   mkdir build
   cd build
   cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo
   make
   sudo make install
   cd ../..
   git clone https://github.com/csiro-robotics/raycloudtools.git
   cd raycloudtools
   mkdir build
   cd build
   cmake .. -DWITH_LAS=ON -DWITH_QHULL=ON
   make
   ```
   b. TreeTools
   ```
   git clone https://github.com/csiro-robotics/treetools
   mkdir build
   cd build
   cmake ..
   make
   ```
   
3. Edit your bashrc via:
   ```
   sudo nano ~/.bashrc
   ```
   At the end of the file, add three lines:
   ```
   export PATH=$PATH:~/RCT/raycloudtools/build/bin
   export PATH=$PATH:~/RCT/treetools/build/bin
   console export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib
   ```
   These three lines allow you to call tools from both packages in any directory (important for batching scripts), and paths them to required lib files.
   **Restart your console for this step to take effect**
   
