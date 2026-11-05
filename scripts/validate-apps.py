from pathlib import Path
import os
import re
import sys
import yaml
from PIL import Image

apps_dir = str(Path(__file__).resolve().parents[1] / "apps")
if not os.path.exists(apps_dir):
    print("No apps directory found.")
    sys.exit(1)

errors = []
apps = [d for d in os.listdir(apps_dir) if os.path.isdir(os.path.join(apps_dir, d))]
if not apps:
    errors.append("No application packages found")

for app in apps:
    app_path = os.path.join(apps_dir, app)
    print(f"--> Validating {app}...")

    # Check root files
    for req in ["data.yml", "README.md", "logo.png"]:
        fpath = os.path.join(app_path, req)
        if not os.path.exists(fpath):
            errors.append(f"{app}: Missing root file {req}")

    # Check logo
    logo_path = os.path.join(app_path, "logo.png")
    if os.path.exists(logo_path):
        size_kb = os.path.getsize(logo_path) / 1024
        if size_kb > 100:
            errors.append(f"{app}/logo.png: Image size exceeds 100 KB ({size_kb:.1f} KB)")
        try:
            with Image.open(logo_path) as im:
                if im.size != (180, 180):
                    errors.append(f"{app}/logo.png: Image dimensions must be 180x180, got {im.size}")
        except Exception as e:
            errors.append(f"{app}/logo.png: Invalid image format ({e})")

    # Check root data.yml
    root_yaml_path = os.path.join(app_path, "data.yml")
    if os.path.exists(root_yaml_path):
        try:
            with open(root_yaml_path, encoding='utf-8') as f:
                data = yaml.safe_load(f)
            props = data.get("additionalProperties", {})
            if props.get("key") != app:
                errors.append(f"{app}/data.yml: additionalProperties.key '{props.get('key')}' != directory '{app}'")
            for field in ["name", "tags", "type", "shortDescZh"]:
                if not props.get(field):
                    errors.append(f"{app}/data.yml: Missing required additionalProperties.{field}")
        except Exception as e:
            errors.append(f"{app}/data.yml: YAML parse error: {e}")

    # Check version directories
    versions = [d for d in os.listdir(app_path) if os.path.isdir(os.path.join(app_path, d))]
    if not versions:
        errors.append(f"{app}: No version directory found")
    for v in versions:
        v_path = os.path.join(app_path, v)
        if v.startswith("v"):
            errors.append(f"{app}/{v}: Version directory must not start with 'v'")
        for vf in ["data.yml", "docker-compose.yml"]:
            vf_path = os.path.join(v_path, vf)
            if not os.path.exists(vf_path):
                errors.append(f"{app}/{v}: Missing {vf}")
            else:
                try:
                    with open(vf_path, encoding='utf-8') as f:
                        yaml.safe_load(f)
                except Exception as e:
                    errors.append(f"{app}/{v}/{vf}: YAML parse error: {e}")

        # Keep install form variables and Compose references in sync.
        try:
            version_path = Path(v_path)
            form = yaml.safe_load((version_path / "data.yml").read_text(encoding="utf-8"))
            fields = form["additionalProperties"]["formFields"]
            if not isinstance(fields, list):
                raise ValueError("formFields must be a list")
            keys = [field["envKey"] for field in fields]
            if len(keys) != len(set(keys)):
                errors.append(f"{app}/{v}: duplicate form envKey")
            compose = (version_path / "docker-compose.yml").read_text(encoding="utf-8")
            used = set(re.findall(r"(?<!\$)\$\{([A-Za-z_][A-Za-z0-9_]*)", compose))
            missing = used - set(keys) - {"CONTAINER_NAME"}
            if missing:
                errors.append(f"{app}/{v}: undeclared Compose variables: {', '.join(sorted(missing))}")
        except Exception as e:
            errors.append(f"{app}/{v}: invalid install form or Compose file: {e}")

if errors:
    print("\nValidation failed with errors:")
    for err in errors:
        print(f"  ERROR: {err}")
    sys.exit(1)
else:
    print("\nAll application packages passed validation.")
