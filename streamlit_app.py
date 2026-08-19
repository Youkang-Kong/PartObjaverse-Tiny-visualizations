import logging
import os

import streamlit as st
from streamlit.components.v1 import html

from utils import (
    COLORS,
    download_meshes,
    download_semantic_gt,
    get_label_set as _get_label_set,
    MESHES_DIR,
    COLORED_MESHES_DIR,
    SEMANTIC_GT_DIR,
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
SEMANTIC_GT_PATH = os.path.join(".", SEMANTIC_GT_DIR)


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

    with st.container(border=True):
        st.markdown(f"**UID:** {uid}")
        linked_model_viewers(mesh_file, colored_mesh_file, uid)
        legend_html = "<div style='max-height: 200px; overflow-y: auto; font-size: 12px; columns: 2;'>"
        for label_idx, part_label in enumerate(part_labels):
            color = COLORS[label_idx % len(COLORS)]
            legend_html += legend_entry(color, part_label)
        legend_html += "</div>"
        st.html(legend_html)


def legend_entry(color: str, label: str) -> str:
    return f"""
        <div style="display: flex; align-items: center; margin-bottom: 3px;">
            <div style="width: 11px; height: 11px; flex-shrink: 0; background-color: {color}; margin-right: 6px; border-radius: 2px;"></div>
            <span>{label}</span>
        </div>
        """


def linked_model_viewers(mesh_file: str, colored_mesh_file: str, uid: str) -> None:
    # Two model-viewers whose cameras stay in sync: dragging or scrolling one
    # updates the other. We disable auto-rotate so manual control is authoritative.
    safe_id = uid.replace("-", "_")
    left_id = f"mv_left_{safe_id}"
    right_id = f"mv_right_{safe_id}"
    html(
        f"""
            <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js"></script>
            <div style="display: flex; gap: 12px;">
                <model-viewer id="{left_id}" src="app/{mesh_file}" alt="3D Model" camera-controls interaction-prompt="none"
                              style="width: 384px; height: 384px; background-color: #1f2937; border-radius: 8px;">
                </model-viewer>
                <model-viewer id="{right_id}" src="app/{colored_mesh_file}" alt="3D Model" camera-controls interaction-prompt="none"
                              style="width: 384px; height: 384px; background-color: #1f2937; border-radius: 8px;">
                </model-viewer>
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
            </script>
            """,
        height=430,
    )


if __name__ == "__main__":
    main()
