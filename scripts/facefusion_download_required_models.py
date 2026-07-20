#!/usr/bin/env python
"""
Download the exact FaceFusion models needed for Veloura face-swap validation.

This intentionally avoids `force-download --download-scope full`, which pulls
models for unrelated processors. The image should contain only the face-swap
bake-off set plus the common face analysis models required by face_swapper.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


DEFAULT_MODELS = [
    "hyperswap_1a_256",
    "hyperswap_1b_256",
    "hyperswap_1c_256",
    "ghost_1_256",
    "ghost_2_256",
    "ghost_3_256",
    "simswap_unofficial_512",
    "inswapper_128_fp16",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=os.environ.get("FACEFUSION_ROOT", "/workspace/facefusion"),
        help="FaceFusion repository root inside the image.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Face swapper model names to bake into the image.",
    )
    parser.add_argument(
        "--providers",
        nargs="+",
        default=["github", "huggingface"],
        help="FaceFusion download providers in priority order.",
    )
    parser.add_argument(
        "--min-files",
        type=int,
        default=24,
        help="Fail if fewer files than this exist in .assets/models afterwards.",
    )
    return parser.parse_args()


def merge_download_set(target: Dict[str, Any], source: Dict[str, Any], prefix: str) -> None:
    for key, value in source.items():
        target[f"{prefix}:{key}"] = value


def collect_direct_model(
    hashes: Dict[str, Any],
    sources: Dict[str, Any],
    module: Any,
    model_name: str,
    prefix: str,
) -> None:
    model_set = module.create_static_model_set("full")
    if model_name not in model_set:
        available = ", ".join(sorted(model_set.keys()))
        raise ValueError(f"Unknown model {model_name!r}. Available: {available}")

    model = model_set[model_name]
    merge_download_set(hashes, model.get("hashes", {}), f"{prefix}:{model_name}")
    merge_download_set(sources, model.get("sources", {}), f"{prefix}:{model_name}")


def collect_module_defaults(
    hashes: Dict[str, Any],
    sources: Dict[str, Any],
    module: Any,
    prefix: str,
) -> None:
    if hasattr(module, "collect_model_downloads"):
        module_hashes, module_sources = module.collect_model_downloads()
        merge_download_set(hashes, module_hashes, prefix)
        merge_download_set(sources, module_sources, prefix)
        return

    if hasattr(module, "get_model_options"):
        model_options = module.get_model_options()
        merge_download_set(hashes, model_options.get("hashes", {}), prefix)
        merge_download_set(sources, model_options.get("sources", {}), prefix)
        return

    raise ValueError(f"Module {module.__name__} has no downloadable model API")


def iter_download_paths(download_set: Dict[str, Any]) -> Iterable[Path]:
    for item in download_set.values():
        path = item.get("path")
        if path:
            yield Path(path)


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if not (root / "facefusion.py").is_file():
        print(f"ERROR: FaceFusion root not found: {root}", file=sys.stderr)
        return 2

    os.chdir(root)
    sys.path.insert(0, str(root))

    from facefusion import logger, state_manager
    from facefusion.download import conditional_download_hashes, conditional_download_sources
    from facefusion import face_classifier, face_detector, face_landmarker, face_masker, face_recognizer
    from facefusion.processors.modules.face_swapper import core as face_swapper

    logger.init("info")
    state_manager.init_item("download_providers", args.providers)
    state_manager.init_item("log_level", "info")

    # Match FaceFusion CLI defaults. These common models are needed by the
    # face_swapper pre_check path before any individual swapper model runs.
    state_manager.init_item("face_detector_model", "yolo_face")
    state_manager.init_item("face_landmarker_model", "2dfan4")
    state_manager.init_item("face_occluder_model", "xseg_1")
    state_manager.init_item("face_parser_model", "bisenet_resnet_34")

    hashes: Dict[str, Any] = {}
    sources: Dict[str, Any] = {}

    for prefix, module in [
        ("face_classifier", face_classifier),
        ("face_detector", face_detector),
        ("face_landmarker", face_landmarker),
        ("face_masker", face_masker),
        ("face_recognizer", face_recognizer),
    ]:
        collect_module_defaults(hashes, sources, module, prefix)

    for model_name in args.models:
        collect_direct_model(hashes, sources, face_swapper, model_name, "face_swapper")

    print("download_providers:", " ".join(args.providers))
    print("face_swapper_models:", " ".join(args.models))
    print("hash_count:", len(hashes))
    print("source_count:", len(sources))

    if not conditional_download_hashes(hashes):
        print("ERROR: hash downloads or validation failed", file=sys.stderr)
        return 1
    if not conditional_download_sources(sources):
        print("ERROR: source downloads or validation failed", file=sys.stderr)
        return 1

    model_dir = root / ".assets" / "models"
    files = sorted(path for path in model_dir.rglob("*") if path.is_file())
    missing = [path for path in iter_download_paths({**hashes, **sources}) if not path.is_file()]

    print("model_dir:", model_dir)
    print("model_file_count:", len(files))
    print("model_total_mb:", round(sum(path.stat().st_size for path in files) / 1024 / 1024, 2))

    if missing:
        print("ERROR: expected downloaded paths are missing:", file=sys.stderr)
        for path in missing:
            print(str(path), file=sys.stderr)
        return 1

    if len(files) < args.min_files:
        print(f"ERROR: model_file_count below minimum {args.min_files}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
