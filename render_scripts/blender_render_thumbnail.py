"""
Render a single fixed-view thumbnail of a 3D model with Blender.

Adapted from partsgen_trellis.2/data_toolkit/blender_script/render_cond.py,
trimmed down to render one image from a fixed camera angle. Run inside Blender:

    blender -b -P blender_render_thumbnail.py -- \
        --object model.glb --output thumb.png --resolution 512
"""

import argparse
import math
import os
import sys
from typing import Callable, Dict, Tuple

import bpy
from mathutils import Vector
import numpy as np


IMPORT_FUNCTIONS: Dict[str, Callable] = {
    "obj": bpy.ops.import_scene.obj,
    "glb": bpy.ops.import_scene.gltf,
    "gltf": bpy.ops.import_scene.gltf,
    "usd": bpy.ops.import_scene.usd,
    "fbx": bpy.ops.import_scene.fbx,
    "stl": bpy.ops.import_mesh.stl,
    "usda": bpy.ops.import_scene.usda,
    "dae": bpy.ops.wm.collada_import,
    "ply": bpy.ops.import_mesh.ply,
    "abc": bpy.ops.wm.alembic_import,
    "blend": bpy.ops.wm.append,
}


def init_render(engine: str = "CYCLES", resolution: int = 512) -> None:
    bpy.context.scene.render.engine = engine
    bpy.context.scene.render.resolution_x = resolution
    bpy.context.scene.render.resolution_y = resolution
    bpy.context.scene.render.resolution_percentage = 100
    bpy.context.scene.render.image_settings.file_format = "PNG"
    bpy.context.scene.render.image_settings.color_mode = "RGBA"
    bpy.context.scene.render.film_transparent = True

    bpy.context.scene.cycles.device = "GPU"
    bpy.context.scene.cycles.samples = 32
    bpy.context.scene.cycles.filter_type = "BOX"
    bpy.context.scene.cycles.filter_width = 1
    bpy.context.scene.cycles.diffuse_bounces = 1
    bpy.context.scene.cycles.glossy_bounces = 1
    bpy.context.scene.cycles.transparent_max_bounces = 3
    bpy.context.scene.cycles.transmission_bounces = 3
    bpy.context.scene.cycles.use_denoising = True

    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "CUDA"
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == "CUDA"


def init_scene() -> None:
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    for material in bpy.data.materials:
        bpy.data.materials.remove(material, do_unlink=True)
    for texture in bpy.data.textures:
        bpy.data.textures.remove(texture, do_unlink=True)
    for image in bpy.data.images:
        bpy.data.images.remove(image, do_unlink=True)


def init_camera():
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.sensor_height = cam.data.sensor_width = 32
    cam_constraint = cam.constraints.new(type="TRACK_TO")
    cam_constraint.track_axis = "TRACK_NEGATIVE_Z"
    cam_constraint.up_axis = "UP_Y"
    cam_empty = bpy.data.objects.new("Empty", None)
    cam_empty.location = (0, 0, 0)
    bpy.context.scene.collection.objects.link(cam_empty)
    cam_constraint.target = cam_empty
    return cam


def init_uniform_lighting() -> None:
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.select_by_type(type="LIGHT")
    bpy.ops.object.delete()

    if bpy.context.scene.world is None:
        bpy.context.scene.world = bpy.data.worlds.new("World")
    world = bpy.context.scene.world

    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    for node in nodes:
        nodes.remove(node)

    bg_node = nodes.new(type="ShaderNodeBackground")
    bg_node.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg_node.inputs["Strength"].default_value = 1.0
    output_node = nodes.new(type="ShaderNodeOutputWorld")
    links.new(bg_node.outputs["Background"], output_node.inputs["Surface"])


def load_object(object_path: str) -> None:
    file_extension = object_path.split(".")[-1].lower()
    import_function = IMPORT_FUNCTIONS[file_extension]
    if file_extension == "blend":
        import_function(directory=object_path, link=False)
    elif file_extension in {"glb", "gltf"}:
        import_function(
            filepath=object_path, merge_vertices=True, import_shading="NORMALS"
        )
    else:
        import_function(filepath=object_path)


def scene_bbox() -> Tuple[Vector, Vector]:
    bbox_min = (math.inf,) * 3
    bbox_max = (-math.inf,) * 3
    found = False
    scene_meshes = [
        obj
        for obj in bpy.context.scene.objects.values()
        if isinstance(obj.data, bpy.types.Mesh)
    ]
    for obj in scene_meshes:
        found = True
        for coord in obj.bound_box:
            coord = obj.matrix_world @ Vector(coord)
            bbox_min = tuple(min(x, y) for x, y in zip(bbox_min, coord))
            bbox_max = tuple(max(x, y) for x, y in zip(bbox_max, coord))
    if not found:
        raise RuntimeError("no objects in scene to compute bounding box for")
    return Vector(bbox_min), Vector(bbox_max)


def normalize_scene() -> None:
    """Scale and translate the scene to fit in a unit cube centered at origin."""
    scene_root_objects = [
        obj for obj in bpy.context.scene.objects.values() if not obj.parent
    ]
    if len(scene_root_objects) > 1:
        scene = bpy.data.objects.new("ParentEmpty", None)
        bpy.context.scene.collection.objects.link(scene)
        for obj in scene_root_objects:
            obj.parent = scene
    else:
        scene = scene_root_objects[0]

    bbox_min, bbox_max = scene_bbox()
    scale = 1 / max(bbox_max - bbox_min)
    scene.scale = scene.scale * scale

    bpy.context.view_layer.update()
    bbox_min, bbox_max = scene_bbox()
    offset = -(bbox_min + bbox_max) / 2
    scene.matrix_world.translation += offset
    bpy.ops.object.select_all(action="DESELECT")


def main(arg: argparse.Namespace) -> None:
    init_scene()
    load_object(arg.object)
    print("[INFO] Scene initialized.")

    normalize_scene()
    print("[INFO] Scene normalized.")

    cam = init_camera()
    init_uniform_lighting()
    init_render(engine=arg.engine, resolution=arg.resolution)
    print("[INFO] Camera, lighting, render initialized.")

    # Four views starting from the front (yaw 270°, model faces -Y) and
    # rotating 90° each step; slightly above the horizon.
    pitch = math.radians(arg.pitch)
    fov = math.radians(40)
    radius = math.sqrt(3) / 2 / math.sin(fov / 2)
    cam.data.lens = 16 / math.tan(fov / 2)

    outputs = [o for o in arg.output.split(",") if o]
    start_yaw = arg.start_yaw
    for i, out in enumerate(outputs):
        yaw = math.radians(start_yaw + 90 * i)
        cam_dir = np.array(
            [
                math.cos(yaw) * math.cos(pitch),
                math.sin(yaw) * math.cos(pitch),
                math.sin(pitch),
            ]
        )
        cam.location = (
            radius * cam_dir[0],
            radius * cam_dir[1],
            radius * cam_dir[2],
        )
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        bpy.context.scene.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print(f"[INFO] Rendered view {i} (yaw={start_yaw + 90 * i}) to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Render fixed-view thumbnail(s) of a 3D model."
    )
    parser.add_argument("--object", type=str, required=True, help="Path to the model.")
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Comma-separated output PNG paths, one per view.",
    )
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--pitch", type=float, default=20)
    parser.add_argument(
        "--start_yaw", type=float, default=270, help="Yaw of the first (front) view."
    )
    parser.add_argument("--engine", type=str, default="CYCLES")
    argv = sys.argv[sys.argv.index("--") + 1 :]
    main(parser.parse_args(argv))
