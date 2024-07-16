"""
This script creates a Flask web application to display and manage progress data
from a CSV file. The data is downloaded from a GitHub repository, loaded, sorted,
and displayed in an HTML template with additional filters for parsing status and
calculating progress. The CSV file is reloaded each time the page is accessed.

Author: Rafael Sene, rafael@riscv.org - Initial implementation
"""

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
    """
    Remove any existing CSV files in the current directory.
    """
    for file in os.listdir('.'):
        if file.endswith('.csv'):
            os.remove(file)

def download_csv_from_github():
    """
    Download the latest CSV asset from the GitHub repository.
    """
    try:
        # Authenticate to GitHub
        g = Github(GITHUB_TOKEN)

        # Repository details
        repo_name = "riscv-admin/bod-report"
        repo = g.get_repo(repo_name)

        # Get the latest release
        latest_release = repo.get_latest_release()

        # Print the fetched release information for debugging
        print("Latest release information:")
        print(latest_release)

        # Extract the URLs of the assets and filter for the CSV file pattern
        csv_assets = [asset for asset in latest_release.get_assets() if asset.name.startswith('specs_') and asset.name.endswith('.csv')]

        # Check if there are any CSV assets
        if not csv_assets:
            raise Exception("No CSV assets found in the latest release.")

        # Remove any existing CSV files
        remove_existing_csv_files()

        # Download each CSV asset using the asset URL for authenticated download
        for asset in csv_assets:
            asset_url = asset.url
            print(f"Downloading {asset.name} from {asset_url}")

            # Use requests to get the asset data
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/octet-stream"
            }
            file_response = requests.get(asset_url, headers=headers)
            if file_response.status_code != 200:
                raise Exception(f"Failed to download asset: {file_response.status_code}, {file_response.text}")

            # Save the file
            with open(asset.name, 'wb') as file:
                file.write(file_response.content)

        print("Download complete.")
        return csv_assets[0].name

    except Exception as e:
        print(f"Error downloading CSV from GitHub: {e}")
        return None

def load_data():
    """
    Load data from a CSV file, sort it based on ratification progress, and return
    the processed DataFrame.
    """
    print("Loading data...")
    try:
        # Download the latest CSV from GitHub
        csv_filename = download_csv_from_github()
        if csv_filename is None:
            raise Exception("CSV download failed, cannot load data.")

        # Load the CSV file into a DataFrame
        df = pd.read_csv(csv_filename)
        sort_order = {
            'Late': 0,
            'Exposed': 1,
            'On Track': 2,
            'Completed': 3
        }
        # Add a column for sorting order based on 'Ratification Progress'
        df['SortOrder'] = df['Ratification Progress'].map(sort_order)
        # Sort the DataFrame and drop the 'SortOrder' column
        df = df.sort_values(by='SortOrder').drop(columns=['SortOrder'])
        return df

    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def parse_status(value):
    """
    Parse the status value to identify specific phases of the progress.
    """
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
    """
    Calculate the current and next phase of progress based on the status value.
    """
    phases = ['Inception', 'Planning', 'Development', 'Freeze', 'Ratification-Ready', 'Ratified']
    current_phase = next((phase for phase in phases if phase in status), None)
    if current_phase:
        current_index = phases.index(current_phase)
        next_phase = phases[current_index + 1] if current_index + 1 < len(phases) else 'Ratified'
        return current_phase, next_phase
    return status, 'N/A'

# Register filters to be used in Jinja2 templates
app.jinja_env.filters['parse_status'] = parse_status
app.jinja_env.filters['calculate_progress'] = calculate_progress

@app.route('/')
def index():
    """
    Main route for the web application. Loads data and renders the index template.
    """
    data = load_data()
    if data is None:
        return "Failed to load data.", 500
    last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return render_template('index.html', data=data, last_updated=last_updated)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')