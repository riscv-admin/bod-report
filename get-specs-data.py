import csv
import os
from datetime import datetime
from jira import JIRA

def get_data_from_jira(jira_token):
    """
    Fetch data from JIRA with the given JIRA_TOKEN and JQL (JIRA Query Language).

    Parameters:
    jira_token (str): The JIRA token used for authentication.
    """
    print("Fetching data from JIRA...")
    jira = JIRA("https://jira.riscv.org", token_auth=jira_token)

    # JQL query to fetch required issues
    jql = ('project = RVS AND '
           'issuetype not in subTaskIssueTypes() AND '
           '"BoD Report" = Yes ORDER BY priority DESC, updated DESC')

    # Generating the CSV filename with current date and time
    print("Generating csv file...")
    csv_filename = f"specs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    # Open (or create) a CSV file and write data to it
    with open(csv_filename, 'w', newline='') as file:
        writer = csv.writer(file, quotechar="'", quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            'Jira URL',
            'Summary',
            'Status',
            'ISA or NON-ISA?',
            'Baseline Ratification Quarter',
            'Target Ratification Quarter',
            'Ratification Progress'
        ])

        start = 0
        while True:
            # Fetch issues from JIRA
            issues = jira.search_issues(jql, startAt=start, expand='changelog')

            if len(issues) == 0:
                break

            for issue in issues:
                # Skip issues without subtasks
                if not issue.fields.subtasks:
                    continue

                # Write issue data to CSV
                if issue.fields.customfield_10713:
                    writer.writerow([
                        f"https://jira.riscv.org/browse/{issue.key}",
                        issue.fields.summary,
                        issue.fields.status.name,
                        issue.fields.customfield_10440,
                        issue.fields.customfield_10715,
                        issue.fields.customfield_10713,
                        issue.fields.customfield_10714
                    ])

            start += len(issues)

def get_csv_content(csv_filepath):
    """
    Read a CSV file and return its content as a list of rows.

    Parameters:
    csv_filepath (str): The path to the CSV file.

    Returns:
    list: List of rows from the CSV file.
    """
    with open(csv_filepath, 'r') as csv_file:
        csv_reader = csv.reader(csv_file, quotechar="'")
        return list(csv_reader)

def read_csv_file(file_path):
    """
    Function to read a CSV file and return its content as a list of rows.

    Parameters:
    file_path (str): The path to the CSV file.

    Returns:
    list: List of rows from the CSV file.
    """
    with open(file_path, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        return list(csv_reader)

def main():
    """
    The main function to run the whole script.
    """

    # Check if the required environment variables are set
    if not os.getenv('JIRA_TOKEN'):
        raise EnvironmentError("""
            Error: Required environment variable is not set.
            Please check that you have set the following environment variable:
            - JIRA_TOKEN
        """)

    # Fetch data from JIRA and write to CSV
    get_data_from_jira(os.getenv('JIRA_TOKEN'))

if __name__ == '__main__':
    main()