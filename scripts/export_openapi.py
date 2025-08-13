#!/usr/bin/env python3
"""
Export OpenAPI schema from FastAPI application
This schema is used to generate TypeScript types and Python clients
"""

import json
import sys
import os
from pathlib import Path

# Add parent directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app


def export_schema():
    """Export OpenAPI schema to JSON file"""

    # Get the OpenAPI schema
    openapi_schema = app.openapi()

    # Add additional metadata
    openapi_schema["info"]["x-logo"] = {"url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"}

    # Ensure the openapi directory exists
    output_dir = Path(__file__).parent.parent.parent / "openapi"
    output_dir.mkdir(exist_ok=True)

    # Write schema to file
    output_file = output_dir / "schema.json"
    with open(output_file, "w") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)

    print(f"✅ OpenAPI schema exported to {output_file}")
    print(f"📊 Schema contains {len(openapi_schema.get('paths', {}))} endpoints")

    # Also create a version without x- extensions for better compatibility
    clean_schema = remove_x_properties(openapi_schema)
    clean_output_file = output_dir / "schema-clean.json"
    with open(clean_output_file, "w") as f:
        json.dump(clean_schema, f, indent=2, ensure_ascii=False)

    print(f"✅ Clean schema exported to {clean_output_file}")

    return output_file


def remove_x_properties(obj):
    """Remove x- vendor extensions for cleaner schema"""
    if isinstance(obj, dict):
        return {k: remove_x_properties(v) for k, v in obj.items() if not k.startswith("x-")}
    elif isinstance(obj, list):
        return [remove_x_properties(item) for item in obj]
    else:
        return obj


if __name__ == "__main__":
    export_schema()
