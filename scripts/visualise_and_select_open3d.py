import open3d as o3d
import numpy as np
import pandas as pd
import os

def find_matching_file(directory, tree_id, required_parts=None, extension=".ply"):
    required_parts = required_parts or []

    matches = []
    for filename in os.listdir(directory):
        if not filename.endswith(extension):
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

class Toggle:
    def __init__(self, geom, visible=True):
        self.geom = geom
        self.visible = visible

    def __call__(self, vis):
        if self.visible:
            vis.remove_geometry(self.geom, reset_bounding_box=False)
        elif not self.visible:
            vis.add_geometry(self.geom, reset_bounding_box=False)
        self.visible = not self.visible
        return False
    


class Selection:
    def __init__(self, df_path, treefile, mode):
        self.df_path = df_path
        self.df = pd.read_csv(df_path)
        self.treefile = treefile
        if mode == 'understory':
            self.select_fn = self._understory
        elif mode == 'tree':
            self.select_fn = self._tree
        elif mode == 'snag':
            self.select_fn = self._snag
        elif mode == 'fix':
            self.select_fn = self._fix
        elif mode == 'reject':
            self.select_fn = self._reject
         
    def _understory(self, vis):
        self.df.loc[self.df['filename'] == self.treefile, 'selection'] = 'understory'
        self.df.to_csv(self.df_path, index=False)
        print(self.treefile, '--> understory')
        return False
        
    def _tree(self, vis):
        self.df.loc[self.df['filename'] == self.treefile, 'selection'] = 'tree'
        self.df.to_csv(self.df_path, index=False)
        print(self.treefile, '--> tree')
        return False
    
    def _snag(self, vis):
        self.df.loc[self.df['filename'] == self.treefile, 'selection'] = 'snag'
        self.df.to_csv(self.df_path, index=False)
        print(self.treefile, '--> snag')
        return False
    
    def _fix(self, vis):
        self.df.loc[self.df['filename'] == self.treefile, 'selection'] = 'fix'
        self.df.to_csv(self.df_path, index=False)
        print(self.treefile, '--> fix')
        return False
    
    def _reject(self, vis):
        self.df.loc[self.df['filename'] == self.treefile, 'selection'] = 'reject'
        self.df.to_csv(self.df_path, index=False)
        print(self.treefile, '--> reject')
        return False
    
    def __call__(self, vis):
        self.select_fn(vis)



def visualize_mesh_with_pc(dir_pc, dir_mesh, treefiles_df_path, selection='undecided', bounds=None, diam_min=None):
    # Read treefiles dataframe
    df = pd.read_csv(treefiles_df_path)

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

    # Loop over all treefiles
    for _, df_row in df_filtered.iterrows():
        treefile = df_row['filename']
        tree_id = df_row['id']

        pc_file = find_matching_file(dir_pc, tree_id, required_parts=["segmented"])
        mesh_file = find_matching_file(dir_mesh, tree_id, required_parts=["mesh"])

        # Read point cloud
        if os.path.exists(os.path.join(dir_pc, pc_file)):
            print(f'reading pointcloud:{os.path.join(dir_pc, pc_file)}')
            pcd = o3d.io.read_point_cloud(os.path.join(dir_pc, pc_file))
        else:
            raise ValueError(f'pointcloud {os.path.join(dir_pc, pc_file)} does not exist')
        
        # Read mesh
        if os.path.exists(os.path.join(dir_mesh, mesh_file)):
            print(f'reading mesh:{os.path.join(dir_mesh, mesh_file)}')
            mesh = o3d.io.read_triangle_mesh(os.path.join(dir_mesh, mesh_file))
            mesh.compute_vertex_normals()
        else:
            mesh = o3d.geometry.TriangleMesh()
            Warning(f'mesh {os.path.join(dir_mesh, mesh_file)} does not exist')     

        # Compute height of the point cloud
        points = np.asarray(pcd.points)
        p2 = points[:,2].min()
        p1 = points[:,1].min()
        p0 = points[:,0].min()
        height = points[:, 2].max() - p2
        width_x = points[:, 0].max() - p0
        width_y = points[:, 1].max() - p1
        print(f"Height of point cloud: {height:.2f} m")
        print(f"diameter: {df_row['d']:.2f} m")
        #Translate pcd
        points[:,2] -= p2
        points[:,1] -= p1
        points[:,0] -= p0

        #Translate mesh
        vertices = np.asarray(mesh.vertices)
        vertices[:,2] -= p2
        vertices[:,1] -= p1
        vertices[:,0] -= p0

        # Print potential current selection state
        print('current decision:', df[df['filename'] == treefile]['selection'].values[0])

        # Create Visualizer
        vis = o3d.visualization.VisualizerWithKeyCallback()
        vis.create_window()

        # Add pointcloud and mesh
        vis.add_geometry(pcd)
        vis.add_geometry(mesh)

        # Set default view
        vc = vis.get_view_control()
        vc.set_up([0, 0, 1])
        vc.set_lookat([points[:, 0].min() + width_x / 2, points[:, 1].min() + width_y / 2, points[:, 2].min() + height / 2,])
        vc.set_front([0.5, 0.5, 0])
        vc.set_zoom(0.7)
    
        # Set default rendering
        ro = vis.get_render_option()
        ro.light_on = False
        ro.mesh_show_wireframe = True
        ro.point_size = 0.1
        ro.show_coordinate_frame = False
        ro.point_show_normal = False

        # Define callback functions
        toggle_pcd = Toggle(pcd)
        toggle_mesh = Toggle(mesh)
        understory = Selection(treefiles_df_path, treefile, mode='understory')
        tree = Selection(treefiles_df_path, treefile, mode='tree')
        snag = Selection(treefiles_df_path, treefile, mode='snag')
        fix = Selection(treefiles_df_path, treefile, mode='fix')
        reject = Selection(treefiles_df_path, treefile, mode='reject')

        # Register key callbacks
        vis.register_key_callback(ord("["), toggle_pcd) # --> press '[' to toggle point cloud
        vis.register_key_callback(ord("]"), toggle_mesh)
        vis.register_key_callback(ord("U"), understory) # --> press 'u' to set selection column in csv file to 'understory' for that treefile 
        vis.register_key_callback(ord("T"), tree)
        vis.register_key_callback(ord("S"), snag)
        vis.register_key_callback(ord("F"), fix)
        vis.register_key_callback(ord("R"), reject)

        # Run the visualizer
        vis.run()
        vis.close()
        vis.destroy_window()

        # Detlete variables (if I don't do this the second and furter geometries don't show for some reason)
        del vis, pcd, mesh, vc, ro



if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description="Visualize tree point clouds and meshes, and update tree selection labels.")

    parser.add_argument("dir_pc", help="Directory containing tree point cloud .ply files")
    parser.add_argument("dir_mesh", help="Directory containing tree mesh .ply files")
    parser.add_argument("treefiles_dataframe", help="Path to treefiles dataframe CSV")

    parser.add_argument("--selection", default="undecided", choices=["undecided", "fix", "reject", "tree", "understory", "snag"], help="Selection status to filter on (default: %(default)s)")
    parser.add_argument("--bounds", nargs=4, type=float, metavar=("X_MIN", "X_MAX", "Y_MIN", "Y_MAX"), default=None, help="Optional spatial bounds: x_min x_max y_min y_max") #bounds are optional xoxo
    parser.add_argument("--diam-min", type=float, default=0.0, help="Minimum diameter filter (default: %(default)s)")

    args = parser.parse_args()

    visualize_mesh_with_pc(dir_pc=args.dir_pc, dir_mesh=args.dir_mesh, treefiles_df_path=args.treefiles_dataframe, selection=args.selection, bounds=args.bounds, diam_min=args.diam_min)
