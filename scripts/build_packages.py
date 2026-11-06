#!/usr/bin/env python3
"""
Package SmartFuel Lambda handlers and layers into deployment ZIPs.

Creates:
  - packages/{lambda_name}.zip for each function in lambdas/
  - packages/src_layer.zip containing python/src/
  - packages/lambda_layer.zip containing python/ requirements placeholder
"""

import os
import zipfile
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGES_DIR = os.path.join(PROJECT_ROOT, "packages")
LAMBDAS_DIR = os.path.join(PROJECT_ROOT, "lambdas")
SRC_DIR = os.path.join(PROJECT_ROOT, "src")


def build_all():
    os.makedirs(PACKAGES_DIR, exist_ok=True)
    print(f"Building Lambda packages in: {PACKAGES_DIR}")

    # 1. Package each Lambda handler
    lambda_names = [
        "ingest",
        "validate",
        "clean",
        "save_prices",
        "predict",
        "alerts",
        "retrain",
        "api",
    ]

    for name in lambda_names:
        handler_path = os.path.join(LAMBDAS_DIR, name, "handler.py")
        zip_path = os.path.join(PACKAGES_DIR, f"{name}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if os.path.exists(handler_path):
                zf.write(handler_path, arcname="handler.py")
            else:
                zf.writestr("handler.py", "# Placeholder handler\n")
        print(f"  ✓ Built {name}.zip")

    # 2. Package src layer (python/src/...)
    src_layer_path = os.path.join(PACKAGES_DIR, "src_layer.zip")
    with zipfile.ZipFile(src_layer_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(SRC_DIR):
            for file in files:
                if file.endswith((".py", ".json", ".yaml", ".yml")):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, PROJECT_ROOT)
                    # Lambda layer requires python/ prefix for PYTHONPATH
                    arcname = os.path.join("python", rel_path)
                    zf.write(full_path, arcname=arcname)
    print("  ✓ Built src_layer.zip")

    # 3. Package dependencies layer (placeholder)
    dep_layer_path = os.path.join(PACKAGES_DIR, "lambda_layer.zip")
    with zipfile.ZipFile(dep_layer_path, "w", zipfile.ZIP_DEFLATED) as zf:
        req_path = os.path.join(PROJECT_ROOT, "requirements.txt")
        if os.path.exists(req_path):
            zf.write(req_path, arcname="python/requirements.txt")
        else:
            zf.writestr("python/README.txt", "Lambda dependencies layer\n")
    print("  ✓ Built lambda_layer.zip")

    print("All packages built successfully!")


if __name__ == "__main__":
    build_all()
