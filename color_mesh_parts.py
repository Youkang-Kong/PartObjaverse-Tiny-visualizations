"""
Color meshes from the PartObjaverse-Tiny dataset based on their part labels,
for visualization purposes.

Supports two modes:
  - semantic: color faces by semantic GT (same class -> same color)
  - instance: color faces by instance GT (each instance -> its own color)

    python color_mesh_parts.py                 # semantic (default)
    python color_mesh_parts.py --mode instance # instance
"""

import argparse
import multiprocessing as mp
import os

import numpy as np
import trimesh
from rich.progress import track

from utils import (
    get_label_set,
    hex2rgb,
    COLORS,
    download_meshes,
    download_semantic_gt,
    download_instance_gt,
    MESHES_DIR,
    SEMANTIC_GT_DIR,
    INSTANCE_GT_DIR,
    COLORED_MESHES_DIR,
    INSTANCE_COLORED_MESHES_DIR,
)

MODES = {
    "semantic": (SEMANTIC_GT_DIR, COLORED_MESHES_DIR),
    "instance": (INSTANCE_GT_DIR, INSTANCE_COLORED_MESHES_DIR),
}

# Set by main() so the pool workers know which GT / output dirs to use.
_gt_dir = SEMANTIC_GT_DIR
_out_dir = COLORED_MESHES_DIR


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=list(MODES), default="semantic")
    opt = parser.parse_args()

    global _gt_dir, _out_dir
    _gt_dir, _out_dir = MODES[opt.mode]

    download_meshes(".")
    if opt.mode == "semantic":
        download_semantic_gt(".")
    else:
        download_instance_gt(".")

    label_set = get_label_set()
    uids = [
        uid for mesh_label_set in label_set.values() for uid in mesh_label_set.keys()
    ]

    os.makedirs(_out_dir, exist_ok=True)
    with mp.Pool() as pool:
        for _ in track(
            pool.imap_unordered(process_mesh, uids),
            description=f"Processing meshes ({opt.mode})...",
            total=len(uids),
        ):
            pass


def process_mesh(uid: str) -> None:
    mesh_file = os.path.join(MESHES_DIR, f"{uid}.glb")
    mesh = trimesh.load_scene(mesh_file).to_mesh()
    gt_file = os.path.join(_gt_dir, f"{uid}.npy")
    gt = np.load(gt_file)
    colored_mesh_file = os.path.join(_out_dir, f"{uid}.glb")
    colored_mesh = color_mesh_parts(mesh, gt)
    colored_mesh.export(colored_mesh_file)


def color_mesh_parts(mesh: trimesh.Trimesh, gt: np.ndarray) -> trimesh.Trimesh:
    """
    Color mesh based on per-face GT labels from the PartObjaverse-Tiny dataset.
    :param mesh: Mesh to be colored, with N faces.
    :param gt: Length-N array indicating the (semantic or instance) label of each face.
    :return: Colored mesh.
    """
    assert len(gt) == len(mesh.faces)
    mesh.visual = trimesh.visual.ColorVisuals(mesh=mesh)
    for face_idx, label in enumerate(gt):
        color = hex2rgb(COLORS[label % len(COLORS)]) + (255,)
        mesh.visual.face_colors[face_idx] = color
    return mesh


if __name__ == "__main__":
    main()
