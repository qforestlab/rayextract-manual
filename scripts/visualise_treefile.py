import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import norm

def visualise_forest(treefile):
    forest = []
    with open(treefile,'r') as f:
        for i,line in enumerate(f):
            if i > 1:
                tree = line.strip().split(',')
                forest.append(tree)

    for tid, tree in enumerate(forest):
        tree_arr = np.array(tree).reshape((-1,6))
        vertices = tree_arr[:,0:3].astype(float)
        radius = tree_arr[:,3].astype(float)
        parent_id = tree_arr[:,4].astype(int)
        section_id = tree_arr[:,5].astype(int)
        
        # if np.max(vertices[:,2]) > 30:
        
        fig = plt.figure(figsize=[16,16])
        ax = fig.add_subplot(111, projection='3d')
        ax.set_box_aspect([np.ptp(vertices[:,0]), np.ptp(vertices[:,1]), np.ptp(vertices[:,2])])
        for i in range(1,parent_id.shape[0],1):
            j = parent_id[i]
            p0 = vertices[j]
            p1 = vertices[i]
            v = p1 - p0
            mag = norm(v)
            v = v / mag

            not_v = np.array([1, 0, 0])
            if (v == not_v).all():
                not_v = np.array([0, 1, 0])
            n1 = np.cross(v, not_v)
            n1 /= norm(n1)
            n2 = np.cross(v, n1)

            r0 = radius[j]
            r1 = radius[i]
            rv = np.array([r0, r1])[np.newaxis]

            t = np.linspace(0, mag, 2)
            theta = np.linspace(0, 2 * np.pi, 15)
            t, theta = np.meshgrid(t, theta)
            x,y,z = [p0[k] + v[k] * t + rv * np.sin(theta) * n1[k] + rv * np.cos(theta) * n2[k] for k in range(3)]

            ax.plot_surface(x, y, z, color='brown')
        
        ax.set_title(f'Tree {tid:d}')
        plt.grid(False)
        plt.show()