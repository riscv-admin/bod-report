import os
import requests
from github import Github

# Ensure the GitHub token is set as an environment variable
def get_github_token():
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        raise EnvironmentError("GITHUB_TOKEN is not set. Please set it as an environment variable.")
    return token

# Authenticate to GitHub
def authenticate_to_github(token):
    return Github(token)

# Fetch the latest release of the specified repository
def get_latest_release(repo):
    return repo.get_latest_release()

# Filter assets to get CSV files matching a specific pattern
def get_csv_assets(release):
    return [
        asset for asset in release.get_assets()
        if asset.name.startswith('specs_') and asset.name.endswith('.csv')
    ]

# Download a file from a given asset URL
def download_asset(asset, token):
    print(f"Downloading {asset.name} from {asset.url}")
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/octet-stream"
    }
    response = requests.get(asset.url, headers=headers)
    response.raise_for_status()  # Raise an HTTPError if the request failed
    with open(asset.name, 'wb') as file:
        file.write(response.content)
    print(f"Downloaded {asset.name}")

# Main function to orchestrate the workflow
def main():
    token = get_github_token()
    github_client = authenticate_to_github(token)

    repo_name = "riscv-admin/bod-report"
    repo = github_client.get_repo(repo_name)

    latest_release = get_latest_release(repo)
    print("Latest release information:", latest_release)

    csv_assets = get_csv_assets(latest_release)
    if not csv_assets:
        raise Exception("No CSV assets found in the latest release.")

    for asset in csv_assets:
        download_asset(asset, token)

    print("All downloads completed successfully.")

if __name__ == "__main__":
    main()
