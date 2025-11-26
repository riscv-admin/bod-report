import os
from datetime import datetime
from typing import Optional

import pandas as pd
import requests
from flask import Flask, render_template

# PyGithub (modern auth)
from github import Github, Auth

# --- Config / Env ----------------------------------------------------------------

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise EnvironmentError("GITHUB_TOKEN is not set. Please set it as an environment variable.")

REPO_NAME = "riscv-admin/bod-report"
ASSET_PREFIX = "specs_"
ASSET_SUFFIX = ".csv"

# Expected CSV schema (for sanity checks / future use if needed)
EXPECTED_COLUMNS = [
    "Jira URL",
    "Summary",
    "Status",
    "ISA or NON-ISA?",
    "GitHub",
    "Baseline Ratification Quarter",
    "Target Ratification Quarter",
    "Ratification Progress",
    "Previous Ratification Progress",
]

# --- Flask -----------------------------------------------------------------------

app = Flask(__name__)

# --- Helpers ---------------------------------------------------------------------


def remove_existing_csv_files() -> None:
    """Purge any prior CSVs to avoid stale reads."""
    for file in os.listdir("."):
        if file.endswith(".csv"):
            try:
                os.remove(file)
            except Exception as e:
                print(f"Warning: failed to remove {file}: {e}")


def download_csv_from_github() -> Optional[str]:
    """Download the latest release CSV asset matching prefix/suffix."""
    try:
        gh = Github(auth=Auth.Token(GITHUB_TOKEN))
        repo = gh.get_repo(REPO_NAME)
        latest_release = repo.get_latest_release()

        csv_assets = [
            asset for asset in latest_release.get_assets()
            if asset.name.startswith(ASSET_PREFIX) and asset.name.endswith(ASSET_SUFFIX)
        ]
        if not csv_assets:
            raise RuntimeError("No CSV assets found in the latest release.")

        asset = csv_assets[0]
        remove_existing_csv_files()

        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/octet-stream",
        }
        resp = requests.get(asset.url, headers=headers, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to download asset: {resp.status_code}, {resp.text}")

        csv_filename = asset.name
        with open(csv_filename, "wb") as f:
            f.write(resp.content)

        return csv_filename

    except Exception as e:
        print(f"Error downloading CSV from GitHub: {e}")
        return None


def safe_read_csv(csv_filename: str) -> pd.DataFrame:
    """
    User-proof CSV loader:
    - first try strict/fast parsing,
    - on failure, retry with more tolerant settings,
    - finally, try single-quote as quotechar (for hand-edited rows).
    """
    try:
        # First attempt: normal, fast path
        return pd.read_csv(csv_filename)
    except pd.errors.ParserError as e:
        print(f"[WARN] Strict CSV parse failed: {e}")
        print("[INFO] Retrying with engine='python', on_bad_lines='warn'")

        try:
            df = pd.read_csv(
                csv_filename,
                engine="python",
                on_bad_lines="warn",  # or "skip" if you prefer to drop bad rows
            )
            return df
        except pd.errors.ParserError as e2:
            print(f"[WARN] Python engine parse failed: {e2}")
            print("[INFO] Retrying with quotechar=\"'\" (single-quote fields)")

            # Last resort for cases like 'Packed Single Instruction, Multiple Data - SIMD (P)'
            df = pd.read_csv(
                csv_filename,
                engine="python",
                on_bad_lines="warn",
                quotechar="'",
            )
            return df


def load_data() -> Optional[pd.DataFrame]:
    """Load, normalize, sort."""
    try:
        csv_filename = download_csv_from_github()
        if not csv_filename:
            raise RuntimeError("CSV download failed, cannot load data.")

        df = safe_read_csv(csv_filename)

        # Optional sanity log
        missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
        if missing:
            print(f"[WARN] Missing expected columns in CSV: {missing}")

        df.rename(
            columns={
                "Baseline Ratification Quarter": "Planned Ratification Quarter",
                "Target Ratification Quarter": "Trending Ratification Quarter",
            },
            inplace=True,
        )

        # Normalize status strings
        if "Status" in df.columns:
            df["Status"] = df["Status"].fillna("").astype(str)

        # Sort by ratification progress + trending quarter
        sort_order = {"Late": 0, "Exposed": 1, "On Track": 2, "Completed": 3}
        df["SortOrder"] = df.get("Ratification Progress", "").map(sort_order)
        df.sort_values(
            by=["SortOrder", "Trending Ratification Quarter"],
            ascending=[True, True],
            inplace=True,
        )
        df.drop(columns=["SortOrder"], errors="ignore", inplace=True)

        return df

    except Exception as e:
        print(f"Error loading data: {e}")
        return None

# --- Jinja Filters ---------------------------------------------------------------

WORKFLOW_PHASES = [
    "Inception",
    "Planning",
    "Development",
    "Stabilization",
    "Freeze",
    "Ratification-Ready",
    "Specification in Publication",
]


def parse_status(value: str) -> str:
    if not value:
        return value

    v = str(value)

    if "Ratification-Ready" in v or "Rat-Ready" in v:
        return "Ratification-Ready"
    if "Specification in Publication" in v or "Publication" in v:
        return "Specification in Publication"
    if "Freeze" in v:
        return "Freeze"
    if "Stabilization" in v:
        return "Stabilization"
    if "Under Development" in v or "Development" in v:
        return "Development"
    if "Planning" in v:
        return "Planning"
    if "Inception" in v:
        return "Inception"
    if "Cancelled" in v:
        return "Cancelled"

    return v


def calculate_progress(status: str):
    if not status:
        return None, None

    normalized = parse_status(status)

    if normalized not in WORKFLOW_PHASES:
        return normalized, None

    idx = WORKFLOW_PHASES.index(normalized)
    next_phase = WORKFLOW_PHASES[idx + 1] if idx + 1 < len(WORKFLOW_PHASES) else "Ratified"
    return normalized, next_phase


app.jinja_env.filters["parse_status"] = parse_status
app.jinja_env.filters["calculate_progress"] = calculate_progress

# --- Routes ----------------------------------------------------------------------


@app.route("/")
def index():
    data = load_data()
    if data is None:
        return "Failed to load data.", 500

    # FILTER CANCELLED SPECS
    if "Status" in data.columns:
        mask = ~data["Status"].fillna("").str.contains(r"\bcancelled\b", case=False, regex=True)
        data = data[mask].copy()

    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template("index.html", data=data, last_updated=last_updated)

# --- Main ------------------------------------------------------------------------


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)