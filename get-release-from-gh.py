import os
from github import Github
import requests

# Ensure the GitHub token is set as an environment variable
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    raise EnvironmentError("GITHUB_TOKEN is not set. Please set it as an environment variable.")

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