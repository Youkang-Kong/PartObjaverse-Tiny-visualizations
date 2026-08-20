"""
One-shot driver to render a fixed-view thumbnail PNG for every original glb in
the PartObjaverse-Tiny dataset, using Blender (CYCLES + GPU).

Usage:
    python render_thumbnails.py                 # render all missing thumbnails
    python render_thumbnails.py --limit 2       # render only the first 2 (smoke test)

Thumbnails are written to static/PartObjaverse-Tiny_thumbnails/<uid>.png so that
Streamlit's static file server can serve them at app/static/...
"""

import argparse
import glob
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from subprocess import DEVNULL, call

from tqdm import tqdm

BLENDER_LINK = (
    "https://download.blender.org/release/Blender3.0/blender-3.0.1-linux-x64.tar.xz"
)
BLENDER_INSTALLATION_PATH = "/tmp"
BLENDER_PATH = f"{BLENDER_INSTALLATION_PATH}/blender-3.0.1-linux-x64/blender"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BLENDER_SCRIPT = os.path.join(SCRIPT_DIR, "render_scripts", "blender_render_thumbnail.py")

STATIC_DIR = "static"
MESHES_DIR = os.path.join(STATIC_DIR, "PartObjaverse-Tiny_mesh")
THUMBNAILS_DIR = os.path.join(STATIC_DIR, "PartObjaverse-Tiny_thumbnails")


def _install_blender() -> None:
    if not os.path.exists(BLENDER_PATH):
        os.system("sudo apt-get update")
        os.system(
            "sudo apt-get install -y libxrender1 libxi6 libxkbcommon-x11-0 "
            "libsm6 libxfixes3 libgl1"
        )
        os.system(f"wget {BLENDER_LINK} -P {BLENDER_INSTALLATION_PATH}")
        os.system(
            f"tar -xvf {BLENDER_INSTALLATION_PATH}/blender-3.0.1-linux-x64.tar.xz "
            f"-C {BLENDER_INSTALLATION_PATH}"
        )


NUM_VIEWS = 4
START_YAW = 270  # front view; subsequent views rotate +90° each


def _view_paths(uid: str) -> list[str]:
    return [os.path.join(THUMBNAILS_DIR, f"{uid}_{i}.png") for i in range(NUM_VIEWS)]


def _render_one(uid: str, resolution: int) -> tuple[str, bool]:
    glb = os.path.join(MESHES_DIR, f"{uid}.glb")
    outs = _view_paths(uid)
    if all(os.path.exists(o) for o in outs):
        return uid, True
    args = [
        BLENDER_PATH,
        "-b",
        "-P",
        BLENDER_SCRIPT,
        "--",
        "--object", os.path.abspath(glb),
        "--output", ",".join(os.path.abspath(o) for o in outs),
        "--resolution", str(resolution),
        "--start_yaw", str(START_YAW),
        "--engine", "CYCLES",
    ]
    call(args, stdout=DEVNULL, stderr=DEVNULL)
    return uid, all(os.path.exists(o) for o in outs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--max_workers", type=int, default=4)
    parser.add_argument(
        "--limit", type=int, default=None, help="Render only the first N (smoke test)."
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Only render UIDs in this dataset category.",
    )
    opt = parser.parse_args()

    print("Checking blender...", flush=True)
    _install_blender()

    os.makedirs(THUMBNAILS_DIR, exist_ok=True)

    if opt.category is not None:
        from utils import get_label_set

        label_set = get_label_set()
        if opt.category not in label_set:
            raise SystemExit(
                f"Unknown category '{opt.category}'. "
                f"Available: {list(label_set.keys())}"
            )
        uids = sorted(label_set[opt.category].keys())
    else:
        uids = sorted(
            os.path.splitext(os.path.basename(p))[0]
            for p in glob.glob(os.path.join(MESHES_DIR, "*.glb"))
        )
    if not uids:
        raise SystemExit(
            f"No meshes found in {MESHES_DIR}. "
            "Run color_mesh_parts.py or the app once to download meshes first."
        )
    if opt.limit is not None:
        uids = uids[: opt.limit]

    todo = [u for u in uids if not all(os.path.exists(o) for o in _view_paths(u))]
    print(f"Rendering {len(todo)} / {len(uids)} models ({NUM_VIEWS} views each)...")

    failures = []
    with ThreadPoolExecutor(max_workers=opt.max_workers) as executor:
        futures = {
            executor.submit(_render_one, uid, opt.resolution): uid for uid in todo
        }
        for future in tqdm(as_completed(futures), total=len(futures), desc="Rendering"):
            uid, ok = future.result()
            if not ok:
                failures.append(uid)

    if failures:
        print(f"[WARN] {len(failures)} thumbnails failed to render:")
        for uid in failures:
            print(f"  - {uid}")
    else:
        print("All thumbnails rendered successfully.")


if __name__ == "__main__":
    main()
