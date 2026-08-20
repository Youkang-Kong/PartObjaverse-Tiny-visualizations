import logging
import os

import streamlit as st
from PIL import Image
from streamlit.components.v1 import html

from utils import (
    COLORS,
    download_meshes,
    download_semantic_gt,
    get_label_set as _get_label_set,
    MESHES_DIR,
    COLORED_MESHES_DIR,
    INSTANCE_COLORED_MESHES_DIR,
    SEMANTIC_GT_DIR,
    THUMBNAILS_DIR,
    download_colored_meshes,
)


@st.cache_resource
def get_label_set() -> dict[str, dict[str, list]]:
    return _get_label_set()


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)
MESHES_PATH = os.path.join(STATIC_DIR, MESHES_DIR)
COLORED_MESHES_PATH = os.path.join(STATIC_DIR, COLORED_MESHES_DIR)
INSTANCE_COLORED_MESHES_PATH = os.path.join(STATIC_DIR, INSTANCE_COLORED_MESHES_DIR)
SEMANTIC_GT_PATH = os.path.join(".", SEMANTIC_GT_DIR)
THUMBNAILS_PATH = os.path.join(STATIC_DIR, THUMBNAILS_DIR)
NUM_VIEWS = 4  # rendered views per model (see render_thumbnails.py)


def main() -> None:
    download_meshes(STATIC_DIR)
    download_colored_meshes(STATIC_DIR)
    download_semantic_gt(".")
    label_set = get_label_set()
    uids = [
        uid for mesh_label_set in label_set.values() for uid in mesh_label_set.keys()
    ]

    # Streamlit app
    st.set_page_config(
        page_title="PartObjaverse-Tiny", page_icon=":robot:", layout="wide"
    )
    st.title("PartObjaverse-Tiny")
    st.write(
        "This app visualizes samples from the "
        "[PartObjaverse-Tiny](https://yhyang-myron.github.io/SAMPart3D-website/) dataset (Yang et al., 2024). "
        f"There are **{len(uids)}** sample meshes in total, across **{len(label_set)}** categories."
    )
    st.write(
        "<small style='color: #9ca3af;'>"
        "PartObjaverse-Tiny is licenced under [CC-BY-NC-4.0](https://spdx.org/licenses/CC-BY-NC-4.0). "
        "This app is not affiliated with the creators of PartObjaverse-Tiny."
        "</small>",
        unsafe_allow_html=True,
    )
    st.html("<div style='height: 16px;'></div>")

    # Category selection
    select_cols = st.columns([4, 4], width=600)
    with select_cols[0]:
        category_select = st.selectbox(
            "Category",
            options=list(label_set.keys()),
            format_func=lambda category: f"{category} ({len(label_set[category])} samples)",
        )

    page_size = 16
    max_pages = (len(label_set[category_select]) + page_size - 1) // page_size

    # Reset page when the category changes
    if st.session_state.get("_last_category") != category_select:
        st.session_state["_last_category"] = category_select
        st.session_state["page"] = 0
    page_select = min(st.session_state.get("page", 0), max_pages - 1)

    # Display samples for the selected category and page
    start_idx = page_select * page_size
    end_idx = start_idx + page_size
    uids_subset = list(label_set[category_select].keys())[start_idx:end_idx]
    part_labels_subset = list(label_set[category_select].values())[start_idx:end_idx]
    samples = list(zip(uids_subset, part_labels_subset))

    # Arrange samples in a two-column grid
    for i in range(0, len(samples), 2):
        st.html("<div style='height: 8px;'></div>")
        grid_cols = st.columns(2)
        for grid_col, (uid, part_labels) in zip(grid_cols, samples[i : i + 2]):
            with grid_col:
                display_sample_cell(uid, part_labels)

    # Pagination buttons at the bottom
    render_pagination(page_select, max_pages)


def render_pagination(page_select: int, max_pages: int) -> None:
    st.html("<div style='height: 16px;'></div>")
    nav_cols = st.columns([1, 2, 1], width=600)
    with nav_cols[0]:
        if st.button("← Previous", disabled=page_select <= 0, width="stretch"):
            st.session_state["page"] = page_select - 1
            st.rerun()
    with nav_cols[1]:
        st.markdown(
            f"<div style='text-align: center; padding-top: 6px;'>"
            f"Page {page_select + 1} of {max_pages}</div>",
            unsafe_allow_html=True,
        )
    with nav_cols[2]:
        if st.button("Next →", disabled=page_select >= max_pages - 1, width="stretch"):
            st.session_state["page"] = page_select + 1
            st.rerun()


def display_sample_cell(uid: str, part_labels: list[str]) -> None:
    mesh_file = os.path.join(MESHES_PATH, f"{uid}.glb")
    colored_mesh_file = os.path.join(COLORED_MESHES_PATH, f"{uid}.glb")
    instance_mesh_file = os.path.join(INSTANCE_COLORED_MESHES_PATH, f"{uid}.glb")
    thumb_files = [
        os.path.join(THUMBNAILS_PATH, f"{uid}_{i}.png") for i in range(NUM_VIEWS)
    ]
    thumb_files = [f for f in thumb_files if os.path.exists(f)]

    with st.container(border=True):
        st.markdown(f"**UID:** {uid}")
        linked_model_viewers(mesh_file, colored_mesh_file, instance_mesh_file, uid)

        info_cols = st.columns([3, 2])
        with info_cols[0]:
            if thumb_files:
                thumbnail_row_with_dialog(thumb_files, uid)
        with info_cols[1]:
            legend_html = (
                "<div style='max-height: 200px; overflow-y: auto; "
                "font-size: 12px; columns: 2;'>"
            )
            for label_idx, part_label in enumerate(part_labels):
                color = COLORS[label_idx % len(COLORS)]
                legend_html += legend_entry(color, part_label)
            legend_html += "</div>"
            st.html(legend_html)


# Semi-transparent checkerboard, so the rendered PNG's transparent background
# reads as "transparent" rather than plain white.
_CHECKER_CSS = (
    "background-color: #fff;"
    "background-image:"
    "linear-gradient(45deg, #d9d9d9 25%, transparent 25%),"
    "linear-gradient(-45deg, #d9d9d9 25%, transparent 25%),"
    "linear-gradient(45deg, transparent 75%, #d9d9d9 75%),"
    "linear-gradient(-45deg, transparent 75%, #d9d9d9 75%);"
    "background-size: 16px 16px;"
    "background-position: 0 0, 0 8px, 8px -8px, -8px 0;"
)


def thumbnail_row_with_dialog(thumb_files: list[str], uid: str) -> None:
    """A row of clickable thumbnails; clicking one opens a full-page lightbox.

    Uses a pure-CSS :target lightbox (no JS), so it survives st.html
    sanitization and can overlay the entire page.
    """
    safe_id = uid.replace("-", "_")

    thumbs_html = ""
    boxes_html = ""
    for i, thumb_file in enumerate(thumb_files):
        try:
            with Image.open(thumb_file) as im:
                width, height = im.size
        except Exception:
            width, height = 0, 0
        resolution = f"{width}×{height}"
        src = f"app/{thumb_file}"
        box_id = f"lb_{safe_id}_{i}"

        thumbs_html += f"""
            <div style="text-align: center;">
                <a href="#{box_id}">
                    <img src="{src}" alt="view {i}"
                         style="width: 82px; height: 82px; object-fit: contain;
                                border-radius: 6px; cursor: zoom-in; {_CHECKER_CSS}" />
                </a>
                <div style="font-size: 10px; color: #9ca3af; margin-top: 1px;">
                    {resolution}
                </div>
            </div>
        """
        boxes_html += f"""
            <div id="{box_id}" class="lb">
                <a href="#" class="lb-bg"></a>
                <div class="lb-inner">
                    <img src="{src}" alt="enlarged view {i}" />
                    <div class="lb-cap">
                        {resolution} &nbsp;·&nbsp; click outside to close
                    </div>
                </div>
            </div>
        """

    st.html(
        f"""
        <style>
            .lb {{
                display: none; position: fixed; inset: 0; z-index: 9999;
                align-items: center; justify-content: center;
                background: rgba(0, 0, 0, 0.7);
            }}
            .lb:target {{ display: flex; }}
            .lb .lb-bg {{ position: absolute; inset: 0; }}
            .lb .lb-inner {{
                position: relative; border-radius: 10px; padding: 12px;
                max-width: 92vw; max-height: 92vh; {_CHECKER_CSS}
            }}
            .lb .lb-inner img {{
                display: block; max-width: 84vw; max-height: 82vh;
                width: auto; height: auto;
            }}
            .lb .lb-cap {{
                text-align: center; margin-top: 6px; font-family: sans-serif;
                font-size: 12px; color: #374151;
            }}
        </style>
        <div style="display: flex; gap: 6px; flex-wrap: wrap;
                    font-family: sans-serif;">
            {thumbs_html}
        </div>
        {boxes_html}
        """
    )


def legend_entry(color: str, label: str) -> str:
    return f"""
        <div style="display: flex; align-items: center; margin-bottom: 3px;">
            <div style="width: 11px; height: 11px; flex-shrink: 0; background-color: {color}; margin-right: 6px; border-radius: 2px;"></div>
            <span>{label}</span>
        </div>
        """


def linked_model_viewers(
    mesh_file: str, colored_mesh_file: str, instance_mesh_file: str, uid: str
) -> None:
    # Two model-viewers whose cameras stay in sync: dragging or scrolling one
    # updates the other. The right viewer can toggle between semantic- and
    # instance-colored meshes; the camera is preserved across the swap.
    safe_id = uid.replace("-", "_")
    left_id = f"mv_left_{safe_id}"
    right_id = f"mv_right_{safe_id}"
    btn_id = f"toggle_{safe_id}"
    has_instance = os.path.exists(instance_mesh_file)
    toggle_html = (
        f"""
                <button id="{btn_id}" style="position: absolute; top: 8px; right: 8px;
                        z-index: 5; padding: 4px 10px; font-size: 12px; cursor: pointer;
                        border: none; border-radius: 6px; background: #374151; color: #fff;
                        font-family: sans-serif;">
                    Semantic
                </button>
        """
        if has_instance
        else ""
    )
    html(
        f"""
            <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js"></script>
            <div style="display: flex; gap: 12px;">
                <model-viewer id="{left_id}" src="app/{mesh_file}" alt="3D Model" camera-controls interaction-prompt="none"
                              style="width: 384px; height: 384px; background-color: #1f2937; border-radius: 8px;">
                </model-viewer>
                <div style="position: relative; width: 384px; height: 384px;">
                    <model-viewer id="{right_id}" src="app/{colored_mesh_file}" alt="3D Model" camera-controls interaction-prompt="none"
                                  style="width: 384px; height: 384px; background-color: #1f2937; border-radius: 8px;">
                    </model-viewer>
                    {toggle_html}
                </div>
            </div>
            <script type="module">
                const left = document.getElementById("{left_id}");
                const right = document.getElementById("{right_id}");
                let syncing = false;
                function link(from, to) {{
                    from.addEventListener("camera-change", (e) => {{
                        // Only mirror user-initiated changes to avoid feedback loops.
                        if (syncing || e.detail.source !== "user-interaction") return;
                        syncing = true;
                        try {{
                            to.cameraOrbit = from.getCameraOrbit().toString();
                            to.cameraTarget = from.getCameraTarget().toString();
                            to.fieldOfView = from.getFieldOfView() + "deg";
                            to.jumpCameraToGoal();
                        }} finally {{
                            syncing = false;
                        }}
                    }});
                }}
                link(left, right);
                link(right, left);

                // Render both faces of every triangle so thin/open meshes
                // don't show holes or see-through backfaces.
                function makeDoubleSided(viewer) {{
                    viewer.addEventListener("load", () => {{
                        for (const material of viewer.model.materials) {{
                            material.setDoubleSided(true);
                        }}
                    }});
                }}
                makeDoubleSided(left);
                makeDoubleSided(right);

                // Toggle the right viewer between semantic and instance coloring,
                // keeping the current camera on the swapped-in model.
                const btn = document.getElementById("{btn_id}");
                if (btn) {{
                    const sources = {{
                        Semantic: "app/{colored_mesh_file}",
                        Instance: "app/{instance_mesh_file}",
                    }};
                    let mode = "Semantic";
                    btn.addEventListener("click", () => {{
                        mode = mode === "Semantic" ? "Instance" : "Semantic";
                        btn.textContent = mode;
                        const orbit = right.getCameraOrbit().toString();
                        const target = right.getCameraTarget().toString();
                        const fov = right.getFieldOfView() + "deg";
                        right.src = sources[mode];
                        right.addEventListener("load", () => {{
                            right.cameraOrbit = orbit;
                            right.cameraTarget = target;
                            right.fieldOfView = fov;
                            right.jumpCameraToGoal();
                        }}, {{ once: true }});
                    }});
                }}
            </script>
            """,
        height=430,
    )


if __name__ == "__main__":
    main()
