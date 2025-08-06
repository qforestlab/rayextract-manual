import open3d as o3d
import numpy as np
import pandas as pd
import os


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
        if mode == 'keep':
            self.select_fn = self._keep
        elif mode == 'reject':
            self.select_fn = self._reject
        elif mode == 'maybe':
            self.select_fn = self._maybe
        elif mode == 'snag':
            self.select_fn = self._snag
         
    def _keep(self, vis):
        self.df.loc[self.df['filename'] == self.treefile, 'selection'] = 'keep'
        self.df.to_csv(self.df_path, index=False)
        print(self.treefile, '--> keep')
        return False
        
    def _reject(self, vis):
        self.df.loc[self.df['filename'] == self.treefile, 'selection'] = 'reject'
        self.df.to_csv(self.df_path, index=False)
        print(self.treefile, '--> reject')
        return False

    def _maybe(self, vis):
        self.df.loc[self.df['filename'] == self.treefile, 'selection'] = 'maybe'
        self.df.to_csv(self.df_path, index=False)
        print(self.treefile, '--> maybe')
        return False
    
    def _snag(self, vis):
        self.df.loc[self.df['filename'] == self.treefile, 'selection'] = 'snag'
        self.df.to_csv(self.df_path, index=False)
        print(self.treefile, '--> snag')
        return False
    
    def __call__(self, vis):
        self.select_fn(vis)



def visualize_mesh_with_pc(dir_pc, dir_mesh, treefiles_df_path):
    # Read treefiles dataframe
    df = pd.read_csv(treefiles_df_path)

    # filter treefiles on location and minimum diameter
    x_min, x_max = 15, 55
    y_min, y_max = 15, 55
    d_min = 0.1

    tf_filtered = df[
        (df['x'] > x_min) & 
        (df['x'] < x_max) & 
        (df['y'] > y_min) & 
        (df['y'] < y_max) & 
        (df['d'] > d_min) &
        (df['selection'] == 'undecided')
    ]

    print('number of trees to go:', tf_filtered.shape[0])

    # Loop over all treefiles
    for treefile in tf_filtered['filename'].values:

        # Get corresponding pointcloud and mesh file
        pc_file = treefile.replace('trees', 'segmented').replace('txt', 'ply')
        mesh_file = treefile.replace('.txt', '_mesh.ply')

        # Read point cloud and mesh
        print(f'reading {dir_pc + pc_file}')
        pcd = o3d.io.read_point_cloud(dir_pc + pc_file)
        print(f'reading {dir_mesh + mesh_file}')
        mesh = o3d.io.read_triangle_mesh(dir_mesh + mesh_file)
        mesh.compute_vertex_normals()

        # Compute height of the point cloud
        points = np.asarray(pcd.points)
        height = points[:, 2].max() - points[:, 2].min()
        width_x = points[:, 0].max() - points[:, 0].min()
        width_y = points[:, 1].max() - points[:, 1].min()
        print(f"Height of point cloud: {height:.2f} m")

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
        keep = Selection(treefiles_df_path, treefile, mode='keep')
        reject = Selection(treefiles_df_path, treefile, mode='reject')
        maybe = Selection(treefiles_df_path, treefile, mode='maybe')
        snag = Selection(treefiles_df_path, treefile, mode='snag')

        # Register key callbacks
        vis.register_key_callback(ord("["), toggle_pcd) # --> press '1' to toggle point cloud
        vis.register_key_callback(ord("]"), toggle_mesh)
        vis.register_key_callback(ord("K"), keep) # --> press 'k' to set selection column in csv file to 'keep' for that treefile 
        vis.register_key_callback(ord("R"), reject)
        vis.register_key_callback(ord("M"), maybe)
        vis.register_key_callback(ord("S"), snag)

        # Run the visualizer
        vis.run()
        vis.close()
        vis.destroy_window()

        # Detlete variables (if I don't do this the second and furter geometries don't show for some reason)
        del vis, pcd, mesh, vc, ro



if __name__ == "__main__":

    # Path to tree pointclouds and treefiles 
    dir_pc = '/Stor1/wouter/data/chile/FUR002/rayextract/trees_pointclouds/'
    dir_tf = '/Stor1/wouter/data/chile/FUR002/rayextract/trees_treefiles/'
    dir_mesh = '/Stor1/wouter/data/chile/FUR002/rayextract/trees_meshes/'
    treefiles_dataframe = '/Stor1/wouter/data/chile/FUR002/rayextract/treefiles_dataframe.csv'

    visualize_mesh_with_pc(dir_pc, dir_mesh, treefiles_dataframe)

