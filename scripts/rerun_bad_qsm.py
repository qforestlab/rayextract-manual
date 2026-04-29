#########################
#
# Python script to (re-)run Rayextract on a selection of single trees, after having run it on plot-level
# and split into single trees. Typically run on ok-looking tree point clouds, but which gave non satisfactory QSM results. 
# There is the option to run it with or without cylinder smoothing
# 
# ####################### 


import pandas as pd
import os
import subprocess
import shutil

#function to find matching parts in filename, so it works for any filename structure
def find_matching_file(directory, tree_id, required_parts=None, extension=None):
    required_parts = required_parts or []

    matches = []
    for filename in os.listdir(directory):
        if extension is not None and not filename.endswith(extension):
            continue
        if not filename.startswith(tree_id):
            continue
        if all(part in filename for part in required_parts):
            matches.append(filename)

    if len(matches) == 0:
        raise FileNotFoundError(f"No file found in {directory} for tree_id={tree_id}, required_parts={required_parts}")

    if len(matches) > 1:
        raise ValueError(f"Multiple files found in {directory} for tree_id={tree_id}, required_parts={required_parts}: {matches}")

    return matches[0]

def read_rayextract_treefile(path):
    """Read a rayextract treefile.

    Behavior:
    - If the file has exactly 3 lines (comment, header, data) it returns a single DataFrame for the one tree.
    - If it has more data lines (multiple trees) it returns a list of DataFrames, one per tree.

    Parsing rules:
    - If the header line contains a space character this is treated as a separator between per-tree attributes (the
      first chunk) and per-segment attributes (the remaining chunk). All headers up to the first space are skipped and
      the corresponding first space-separated data chunk is skipped as well.
    - If the header line does not contain a space, all headers are used (no skipping).
    """
    # Read the file and ignore empty lines
    with open(path, 'r') as file:
        lines = [l for l in (ln.rstrip('\n') for ln in file.readlines()) if l.strip()]

    if len(lines) < 3:
        raise ValueError("File must contain at least 3 non-empty lines: comment, header, data")

    header_line = lines[1]
    headers = [h.strip() for h in header_line.strip().split(',') if h.strip()]
    data_lines = [l.strip() for l in lines[2:] if l.strip()]

    def _parse_one_data_line(data_line):
        # split into space-separated rows, stripping trailing commas from each
        rows = [row.rstrip(',') for row in data_line.split(' ') if row.strip()]

        # If header_line contains a space, treat it as a separator between per-tree and per-segment headers
        if ' ' in header_line:
            # headers up to the first space (prefix) are skipped
            idx = header_line.find(' ')
            prefix_headers = [h.strip() for h in header_line[:idx].split(',') if h.strip()]
            skip_n = len(prefix_headers)
            seg_headers = headers[skip_n:]
            # skip the corresponding first space-separated data chunk (per-tree attributes)
            seg_rows = rows[1:]
        else:
            seg_headers = headers
            seg_rows = rows

        # Parse each segment row (comma-separated values) into floats (robust to missing values)
        parsed = []
        for r in seg_rows:
            parts = [p for p in r.split(',') if p != '']
            row_vals = []
            for p in parts:
                try:
                    row_vals.append(float(p))
                except ValueError:
                    # preserve NaNs for non-parsable values
                    row_vals.append(float('nan'))
            parsed.append(row_vals)

        df = pd.DataFrame(parsed, columns=seg_headers)
        return df

    parsed_dfs = [_parse_one_data_line(dl) for dl in data_lines]

    # If original file had exactly 3 lines (single tree), return single DataFrame, else return list
    if len(lines) == 3:
        return parsed_dfs[0]
    return parsed_dfs


def rerun_bad_qsm(dir_pc, dir_mesh, dir_treefile, df_path, dir_mesh_out=None, dir_treefile_out=None, df_out=None, selection='reject', terrain_path=None, bounds=None, diam_min=None, smooth_tree=True, params=None):
    """
    Args
        dir_pc: absolute path to directory with tree point clouds
        dir_mesh: absolute path to directory with tree meshes
        dir_treefile: absolute path to directory with tree treefiles 
        df_path: absolute path to dataframe (.csv) with overview of all trees (output from 'make_treefile_dataframe' function)
        selection: tree class in dataframe ('selection' column) to select trees (one of 'reject', 'keep', 'maybe', 'snag' or 'undecided')
        terrain_path: path to terrain mesh. If specified this one will be used for all individual trees.
        bounds: (xmin, xmax, ymin, ymax)
        diam_min: minimum tree diameter
        smooth_tree: runs the 'treesmooth' and 'treedecimate' raycloudtools commands to smooth and reduce the number of cylinders  

    Remarks
        This function calls raycloudtools bash commands, so they should be installed on your path
        Does not overwrite original folders but creates new out paths.
    """
    # parameter dictionary with defaults
    if params is None:
        params = {}
    gradient = params.get('gradient', 1)
    max_diameter = params.get('max_diameter', 1.5)
    crop_length = params.get('crop_length', 0.15)
    girth_height_ratio = params.get('girth_height_ratio', 0.12)
    gravity_factor = params.get('gravity_factor', 0.3)
    global_taper = params.get('global_taper', 0.024)
    distance_limit = params.get('distance_limit', 1)

    # Read tree dataframne
    df = pd.read_csv(df_path).copy()

    if dir_mesh_out is None:
        dir_mesh_out = dir_mesh.rstrip("/\\") + "_fixed"

    if dir_treefile_out is None:
        dir_treefile_out = dir_treefile.rstrip("/\\") + "_fixed"

    if df_out is None:
        base, ext = os.path.splitext(df_path)
        df_out = base + "_fixed" + ext

    os.makedirs(dir_mesh_out, exist_ok=True)
    os.makedirs(dir_treefile_out, exist_ok=True)

    # Select only trees according to criterium
    df_filtered = df[(df['selection'] == selection)]

    # Filter on location
    if bounds is not None:
        x_min, x_max, y_min, y_max = bounds
        df_filtered = df_filtered[
            (df_filtered['x'] > x_min) & 
            (df_filtered['x'] < x_max) & 
            (df_filtered['y'] > y_min) & 
            (df_filtered['y'] < y_max)            
        ]

    # Filter on minimum diameter
    if diam_min:
        df_filtered = df_filtered[(df_filtered['d'] > diam_min)]

    print('number of trees to go:', df_filtered.shape[0])

    # Instantiate list to store all trees that lead to multiple extracted instances
    multiple_trees = []

    # Loop over all treefiles
    for _, df_row in df_filtered.iterrows():
        treefile = df_row['filename']
        tree_id = df_row['id']

        pc_file = find_matching_file(dir_pc, tree_id, required_parts=["segmented"], extension=".ply")
        mesh_file = find_matching_file(dir_mesh, tree_id, required_parts=["mesh"], extension=".ply")

        pc_path = os.path.join(dir_pc, pc_file)
        treefile_out_path = os.path.join(dir_treefile_out, treefile)
        mesh_out_path = os.path.join(dir_mesh_out, mesh_file)
        
        # Run rayextract terrain
        if terrain_path is None:
            subprocess.run(["rayextract", "terrain", pc_path, "--gradient", str(gradient)])
            terr_path = pc_path[:-4] + '_mesh.ply'
        else:
            terr_path = terrain_path

        # Run rayextract trees if a terrain mesh was made or specified
        if os.path.exists(terr_path):
            trees_cmd = [
                "rayextract", "trees", pc_path, terr_path,
                "--max_diameter", str(max_diameter),
                "--crop_length", str(crop_length),
                "--girth_height_ratio", str(girth_height_ratio),
                "--gravity_factor", str(gravity_factor),
                "--global_taper", str(global_taper),
                "--distance_limit", str(distance_limit)
            ]
            subprocess.run(trees_cmd)
        else:
            print('Terrain does not existfor treefile:', treefile)
            continue

        pc_new_path = pc_path[:-4] + '_segmented.ply'
        mesh_new_path = pc_path[:-4] + '_trees_mesh.ply'
        treefile_new_path = pc_path[:-4] + '_trees.txt'

        # Remove unnecessary intermediates
        if terrain_path is None:
            os.remove(terr_path) 

        if os.path.exists(mesh_new_path) and os.path.exists(pc_new_path) and os.path.exists(treefile_new_path): # if rayextract succeeded (and made a tree), then continue
            # Remove old treefile and mesh
            if os.path.exists(treefile_path):
                os.remove(treefile_path)
            if os.path.exists(mesh_path):
                os.remove(mesh_path)
            # Remove new segmented pc
            os.remove(pc_new_path)

            if smooth_tree:
                # Run treeinfo and treefoliage
                subprocess.run(["treeinfo", treefile_new_path, "--branch_data", "--crop_length", "0.15"])
                treefile_new_info_path =  treefile_new_path[:-4] + '_info.txt'
                subprocess.run(["treefoliage", treefile_new_info_path, pc_path, "0.15"])
                treefile_new_info_foliage_path =  treefile_new_info_path[:-4] + '_foliage.txt'

                # Smooth and decimate treefile
                subprocess.run(["treesmooth", treefile_new_info_foliage_path])
                treefile_new_smooth_path = treefile_new_info_foliage_path[:-4] + '_smoothed.txt'
                subprocess.run(["treedecimate", treefile_new_smooth_path, "8", "segments"])
                treefile_new_smooth_decimated_path = treefile_new_smooth_path[:-4] + '_decimated.txt'

                # Make mesh
                subprocess.run(["treemesh", treefile_new_smooth_decimated_path])
                mesh_new_smooth_decimated_path = treefile_new_smooth_decimated_path[:-4] + '_mesh.ply'

                # Replace old mesh and treefile with new smoothed ones
                shutil.move(treefile_new_smooth_decimated_path, treefile_out_path)
                shutil.move(mesh_new_smooth_decimated_path, mesh_out_path)
                
                # Remove intermidiates
                os.remove(treefile_new_info_path)  
                os.remove(treefile_new_info_foliage_path)  
                os.remove(pc_path[:-4] + '_densities.ply')
                os.remove(treefile_new_smooth_path)  
                os.remove(mesh_new_path)
                os.remove(treefile_new_path) 

            else:
                # Replace old mesh and treefile with new ones
                shutil.move(treefile_new_path, treefile_out_path)
                shutil.move(mesh_new_path, mesh_out_path) # move new mesh to directory

            # Update tree dataframe
            df_tf = read_rayextract_treefile(treefile_out_path)
            
            if isinstance(df_tf, list):
                multiple_trees.append(treefile)
            else:
                mask = df['filename'] == treefile

                df.loc[mask, 'x'] = df_tf['x'].iloc[0]
                df.loc[mask, 'y'] = df_tf['y'].iloc[0]
                df.loc[mask, 'd'] = df_tf['radius'].iloc[0] * 2

        else:
            os.remove(pc_new_path) if os.path.exists(pc_new_path) else None
            os.remove(mesh_new_path) if os.path.exists(mesh_new_path) else None
            os.remove(treefile_new_path) if os.path.exists(treefile_new_path) else None

            print('Rayextract failed for treefile:', treefile)
            continue
    
    df.to_csv(df_out, index=False)
    print(f"Updated dataframe written to: {df_out}")
    print(f"Fixed treefiles written to: {dir_treefile_out}")
    print(f"Fixed meshes written to: {dir_mesh_out}")
    print('trees that led to multiple extracted trees:', multiple_trees)
              

if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description="Rerun Rayextract on selected trees")

    # required inputs
    parser.add_argument("dir_pc")
    parser.add_argument("dir_mesh")
    parser.add_argument("dir_treefile")
    parser.add_argument("df_path")

    # otpions
    parser.add_argument("--selection", default="fix")
    parser.add_argument("--bounds", nargs=4, type=float, default=None)
    parser.add_argument("--diam-min", type=float, default=None)
    parser.add_argument("--smooth", action="store_true") # when --smoooth is added as an arg it will become true and if loop will happen in function

    # Editable arguments to fix qsm's
    parser.add_argument("--gradient", type=float, default=0.2)
    parser.add_argument("--max-diameter", type=float, default=0.9)
    parser.add_argument("--crop-length", type=float, default=1.0)
    parser.add_argument("--girth-height-ratio", type=float, default=0.12)
    parser.add_argument("--gravity-factor", type=float, default=0.3)
    parser.add_argument("--global-taper", type=float, default=0.024)
    parser.add_argument("--distance-limit", type=float, default=1)

    args = parser.parse_args()

    params = {
        "gradient": args.gradient,  
        "max_diameter": args.max_diameter,
        "crop_length": args.crop_length,
        "girth_height_ratio": args.girth_height_ratio,
        "gravity_factor": args.gravity_factor,
        "global_taper": args.global_taper,
        "distance_limit": args.distance_limit,
    }

    rerun_bad_qsm(
        dir_pc=args.dir_pc,
        dir_mesh=args.dir_mesh,
        dir_treefile=args.dir_treefile,
        df_path=args.df_path,
        selection=args.selection,
        bounds=args.bounds,
        diam_min=args.diam_min,
        smooth_tree= args.smooth,
        params=params,
    )
