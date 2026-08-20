"""
Render one glb from several yaw angles so we can pick the "front" view.
Run inside Blender via render_multiview.py driver.

    blender -b -P blender_render_multiview.py -- \
        --object model.glb --output_dir out/ --resolution 512 --pitch 20 --num_views 8
"""

import argparse
import math
import os
import sys

import bpy
import numpy as np

# Reuse the single-view helpers.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blender_render_thumbnail import (  # noqa: E402
    init_scene,
    load_object,
    normalize_scene,
    init_camera,
    init_uniform_lighting,
    init_render,
)


def main(arg: argparse.Namespace) -> None:
    init_scene()
    load_object(arg.object)
    normalize_scene()
    cam = init_camera()
    init_uniform_lighting()
    init_render(engine=arg.engine, resolution=arg.resolution)

    pitch = math.radians(arg.pitch)
    fov = math.radians(40)
    radius = math.sqrt(3) / 2 / math.sin(fov / 2)
    cam.data.lens = 16 / math.tan(fov / 2)

    os.makedirs(arg.output_dir, exist_ok=True)
    for i in range(arg.num_views):
        yaw_deg = 360 * i / arg.num_views
        yaw = math.radians(yaw_deg)
        cam_dir = np.array(
            [
                math.cos(yaw) * math.cos(pitch),
                math.sin(yaw) * math.cos(pitch),
                math.sin(pitch),
            ]
        )
        cam.location = (radius * cam_dir[0], radius * cam_dir[1], radius * cam_dir[2])
        out = os.path.join(arg.output_dir, f"yaw_{int(yaw_deg):03d}.png")
        bpy.context.scene.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print(f"[INFO] Rendered {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--object", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--pitch", type=float, default=20)
    parser.add_argument("--num_views", type=int, default=8)
    parser.add_argument("--engine", type=str, default="CYCLES")
    argv = sys.argv[sys.argv.index("--") + 1 :]
    main(parser.parse_args(argv))
