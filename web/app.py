import os
from github import Github
import requests
from flask import Flask, render_template
import pandas as pd
from datetime import datetime

# Ensure the GitHub token is set as an environment variable
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    raise EnvironmentError("GITHUB_TOKEN is not set. Please set it as an environment variable.")

# Initialize Flask application
app = Flask(__name__)

def remove_existing_csv_files():
    for file in os.listdir('.'):
        if file.endswith('.csv'):
            os.remove(file)

def download_csv_from_github():
    try:
        g = Github(GITHUB_TOKEN)
        repo_name = "riscv-admin/bod-report"
        repo = g.get_repo(repo_name)
        latest_release = repo.get_latest_release()

        csv_assets = [asset for asset in latest_release.get_assets() if asset.name.startswith('specs_') and asset.name.endswith('.csv')]
        if not csv_assets:
            raise Exception("No CSV assets found in the latest release.")

        remove_existing_csv_files()
        asset_url = csv_assets[0].url
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/octet-stream"}
        response = requests.get(asset_url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to download asset: {response.status_code}, {response.text}")

        csv_filename = csv_assets[0].name
        with open(csv_filename, 'wb') as file:
            file.write(response.content)

        return csv_filename

    except Exception as e:
        print(f"Error downloading CSV from GitHub: {e}")
        return None

def load_data():
    try:
        csv_filename = download_csv_from_github()
        if not csv_filename:
            raise Exception("CSV download failed, cannot load data.")

        df = pd.read_csv(csv_filename)
        sort_order = {'Late': 0, 'Exposed': 1, 'On Track': 2, 'Completed': 3}
        df['SortOrder'] = df['Ratification Progress'].map(sort_order)
        df = df.sort_values(by='SortOrder').drop(columns=['SortOrder'])
        return df

    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def parse_status(value):
    if 'Freeze' in value:
        return 'Freeze'
    elif 'Ratification-Ready' in value:
        return 'Ratification-Ready'
    elif 'Under Development' in value:
        return 'Under Development'
    elif 'Planning' in value:
        return 'Planning'
    elif 'Inception' in value:
        return 'Inception'
    return value

def calculate_progress(status):
    phases = ['Inception', 'Planning', 'Development', 'Freeze', 'Ratification-Ready', 'Ratified']
    current_phase = next((phase for phase in phases if phase in status), None)
    if current_phase:
        current_index = phases.index(current_phase)
        next_phase = phases[current_index + 1] if current_index + 1 < len(phases) else 'Ratified'
        return current_phase, next_phase
    return status, 'N/A'

app.jinja_env.filters['parse_status'] = parse_status
app.jinja_env.filters['calculate_progress'] = calculate_progress

@app.route('/')
def index():
    data = load_data()
    if data is None:
        return "Failed to load data.", 500
    last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return render_template('index.html', data=data, last_updated=last_updated)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')