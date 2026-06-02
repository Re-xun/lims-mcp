"""Command-line entry point for MCP agent documentation generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import DEFAULT_CANDIDATES, DEFAULT_FRONTEND_ROOT, DEFAULT_INVENTORY, DEFAULT_OUTPUT_DIR
from .inventory import build_inventory_groups, select_candidates
from .io import load_candidates, load_inventory
from .render_markdown import render_doc, render_index
from .xml_extractors import build_enum_index, parse_frontend_svars


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate MCP agent docs for listQuery candidates.")
    parser.add_argument("--candidates-csv", default=DEFAULT_CANDIDATES)
    parser.add_argument("--inventory-json", default=DEFAULT_INVENTORY)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--frontend-root", default=DEFAULT_FRONTEND_ROOT)
    parser.add_argument(
        "--class-name",
        action="append",
        default=[],
        help="Generate doc for a specific class even if it is not present in the candidates CSV. Can be passed multiple times.",
    )
    args = parser.parse_args()

    candidates = load_candidates(Path(args.candidates_csv))
    inventory = load_inventory(Path(args.inventory_json))
    java_group, xml_group = build_inventory_groups(inventory)

    backend_root = Path(inventory["backend_root"])
    frontend_root = Path(args.frontend_root) if args.frontend_root else None
    selected_candidates = select_candidates(candidates, args.class_name, java_group, xml_group, backend_root)

    enum_index = build_enum_index(backend_root)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for candidate in selected_candidates:
        class_name = candidate["class_name"]
        content = render_doc(
            candidate,
            java_group.get(class_name, []),
            xml_group.get(class_name, []),
            enum_index,
            parse_frontend_svars(class_name, frontend_root, xml_group.get(class_name, [])),
        )
        (output_dir / f"{class_name}.md").write_text(content, encoding="utf-8")

    (output_dir / "index.md").write_text(render_index(selected_candidates), encoding="utf-8")
    print(f"Generated {len(selected_candidates)} docs in {output_dir}")


if __name__ == "__main__":
    main()
