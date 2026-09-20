import requests
from requests.auth import HTTPBasicAuth
import datetime
import json
import csv
import random
import os
import subprocess
import sys
import cleanUpFiles
import argparse
import re
from calendar import monthrange
from pathlib import Path

now = datetime.datetime.now()
delta = datetime.timedelta(days=1)

TEMPLATE = """#jira_projects = 
#issue_types = 
#include_components = 
#include_labels = 
#exclude_components = 
#exclude_labels = 
#assignee = 
#reporter = 
#start = 
#stop = 
"""


def main():
    parser = argparse.ArgumentParser(description="Fetch data script options")
    parser.add_argument("-d", "--delete", action="store_true", help="Delete folders with YYYY-MM-DD format")
    parser.add_argument("-s", "--start", type=valid_date, help="Start date in the format: 2025,8,20 OR relative -5d / -4w / -3m / -1y")
    parser.add_argument("-e", "--end", type=valid_date, help="End date in the format: 2025,8,20 OR relative -5d / -4w / -3m / -1y")
    parser.add_argument("-p", "--projects", nargs="+", help="Jira projects in the format: ABC XYZ")
    parser.add_argument("-t", "--types", nargs="+", help="Issue types in the list format: Story Task Bug")
    parser.add_argument("-c", "--components", nargs="+", help="Components in the list format: DEVOPS urgent Deploy \"3rd party\"")
    parser.add_argument("-exc", "--excomponents", nargs="+", help="Exclude components in the list format: DEVOPS urgent Deploy \"3rd party\"")
    parser.add_argument("-l", "--labels", nargs="+", help="Labels in the list format: DEVOPS urgent Deploy")
    parser.add_argument("-exl", "--exlabels", nargs="+", help="Exclude labels in the list format: DEVOPS urgent Deploy")
    parser.add_argument("-a", "--assignee", nargs="+", help="Assignee in the list format: \"John Smith\" \"Jane Doe\"")
    parser.add_argument("-r", "--reporter", nargs="+", help="Reporter in the list format: \"John Smith\" \"Jane Doe\"")
    parser.add_argument("-alt", "--alternative", type=str, help="How to read the config, choose one: file/parameter")
    parser.add_argument("-f", "--filename", type=str, help="Name of parameter file located in /.env/. Will be created if it does not exists with a template")
    parser.add_argument("-db", "--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()
    
    if args.delete:
        print("Removing all YYYY-MM-DD folders since you used the -d option")
        cleanUpFiles.delete_date_folders()
        sys.exit("Cleanup complete")
    
    file = False
    parameter = False
    
    if args.alternative == "file":
        file = True
    if args.alternative == "parameter":
        parameter = True

    api_url = ""
    api_user = ""
    api_key = ""
    
    # Set time for files to be written
    global file_current_time
    file_current_time = now.strftime("%Y-%m-%d_%H-%M-%S")

    global debug
    debug = args.debug

    # Read credentials from config file, creating a template if missing
    file_path_credentials = ".env/config.env"
    default_api_url  = "https://company.atlassian.net/rest/api/3/search/jql"
    default_api_user = "firstname.lastname@email.com"
    default_api_key  = "ABC123"

    if not os.path.exists(file_path_credentials):
        os.makedirs(os.path.dirname(file_path_credentials), exist_ok=True)
        with open(file_path_credentials, "w") as f:
            f.write(f"API_URL={default_api_url}\nAPI_USER={default_api_user}\nAPI_KEY={default_api_key}\n")
        print(f"\n{file_path_credentials} not found.\n\nA template has been created. Please update it with your credentials.\n")
        sys.exit(1)

    credentials = read_credentials(file_path_credentials)
    api_url  = credentials.get("API_URL",  "Not found")
    api_user = credentials.get("API_USER", "Not found")
    api_key  = credentials.get("API_KEY",  "Not found")

    if api_url == default_api_url or api_user == default_api_user or api_key == default_api_key:
        print(f"\n{file_path_credentials} still contains default values. Please update it with your credentials.\n")
        sys.exit(1)
    
    global jira_projects
    
    if(parameter):
        jira_projects = args.projects
        issue_types = args.types
        include_components = args.components
        include_labels = args.labels
        exclude_components = args.excomponents
        exclude_labels = args.exlabels
        assignee = args.assignee
        reporter = args.reporter
        start = args.start 
        stop = args.end
    
    if file:
        print("Getting config from file")
        
        if not args.filename:
            sys.exit("No filename included as a parameter, include -f file")
        
        filepath = os.path.join(".env", args.filename)
        if not os.path.exists(filepath):
            ensure_env_file(".env", args.filename)

        config = {}
        used_lines = 0

        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    values = [v.strip() for v in value.split(",") if v.strip()]
                    if values:
                        config[key.strip()] = values
                        used_lines += 1

        if used_lines == 0:  # or: if not config:
            sys.exit(f"No config found in {filepath}. Edit the file and try again.")
                    
        # Set the values
        jira_projects       = config.get("jira_projects", [])
        issue_types         = config.get("issue_types", [])
        include_components  = config.get("include_components", [])
        include_labels      = config.get("include_labels", [])
        exclude_components  = config.get("exclude_components", [])
        exclude_labels      = config.get("exclude_labels", [])
        assignee            = config.get("assignee", [])
        reporter            = config.get("reporter", [])
        start               = valid_date(",".join(config.get("start")))
        stop                = valid_date(",".join(config.get("stop")))
    
    if not file and not parameter:
        sys.exit("No input file or parameters selected \nTry the -h command to see the options")
    
    jql_query = build_jql(jira_projects,issue_types, include_components, include_labels,exclude_components,exclude_labels, start, stop, assignee, reporter)
    
    print("##### JIRA JQL #####\n" + str(jql_query))
    #sys.exit("Stopping here for debugging")
    write_data_to_file(str(jql_query), "JQL")

    issues = fetch_issues(api_url, api_user, api_key, jql_query)
    get_status_datetime(issues)

    refine_CSV_file = "refineDataFromCSVfile.py"

    # Check if the file exists in the same directory
    if os.path.isfile(refine_CSV_file):
        # Run the script if it exists
        subprocess.run(['python', refine_CSV_file])
    else:
        # Do nothing if the file does not exist
        pass
        

def ensure_env_file(folder: str, filename: str) -> Path:
    # Start from the folder where the script is executed
    base_dir = Path.cwd() / folder
    base_dir.mkdir(parents=True, exist_ok=True)

    target = base_dir / filename
    if not target.exists():
        target.write_text(TEMPLATE, encoding="utf-8")
    
    sys.exit(f"Config file not found but a template file has been created for you here: {target}")

def shift_months(dt: datetime.datetime, months: int) -> datetime.datetime:
    # Convert to an absolute month index, subtract, then back to year+month
    total = dt.year * 12 + (dt.month - 1) - months
    y, m0 = divmod(total, 12)
    m = m0 + 1
    day = min(dt.day, monthrange(y, m)[1])
    return dt.replace(year=y, month=m, day=day, hour=0, minute=0, second=0, microsecond=0)

def shift_years(dt: datetime.datetime, years: int) -> datetime.datetime:
    y = dt.year - years
    m = dt.month
    day = min(dt.day, monthrange(y, m)[1])
    return dt.replace(year=y, month=m, day=day, hour=0, minute=0, second=0, microsecond=0)


def valid_date(s: str) -> datetime.datetime:
    today = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

    if s in ("0", "today"):
        return today

    elif "-" in s:
        m = re.fullmatch(r"-\s*(\d+)\s*([dwmy])", s.strip(), re.IGNORECASE)
        if not m:
            raise argparse.ArgumentTypeError(
                f"Not a valid relative date: '{s}'. Expected '-Nd', '-Nw', '-Nm', or '-Ny'"
            )
        n = int(m.group(1))
        unit = m.group(2).lower()

        if unit == "d":
            return today - datetime.timedelta(days=n)
        elif unit == "w":
            return today - datetime.timedelta(weeks=n)
        elif unit == "m":
            return shift_months(today, n)
        elif unit == "y":
            return shift_years(today, n)
        else:
            raise argparse.ArgumentTypeError(f"Unsupported unit in '{s}'")

    else:
        try:
            return datetime.datetime.strptime(s, "%Y,%m,%d")
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"Not a valid date: '{s}'. Expected 'YYYY,MM,DD' or relative like -90d"
            )


# Read credentials from a file
def read_credentials(filename):
    credentials = {}
    with open(filename, "r") as file:
        for line in file:
            if "=" in line:
                key, value = line.split("=", 1)
                credentials[key.strip()] = value.strip()
    return credentials

# Build the JQL query
def build_jql(
    project_ids=None,
    types_issues=None,
    component_names=None,
    label_names=None,
    exclude_component_names=None,
    exclude_label_names=None,
    start_date=None,
    end_date=None,
    assignee=None,
    reporter=None,
):
    clauses = []

    # Add project_ids clause if not empty
    if project_ids:
        clauses.append(f'project in ({",".join(project_ids)})')

    # Add types_issues clause if not empty
    if types_issues:
        clauses.append(f'type in ({",".join(types_issues)})')

    # Add component_names clause if not empty
    if component_names:
        component_names_with_quotes = [f'"{name}"' for name in component_names]
        clause = f'component in ({",".join(component_names_with_quotes)})'
        clauses.append(clause)

    # Add label_names clause if not empty
    if label_names:
        clauses.append(f'labels in ({",".join(label_names)})')

    # Add exclude_component_names clause if not empty
    if exclude_component_names:
        #clauses.append(f'(component not in ({",".join(exclude_component_names)}) OR component IS EMPTY)')
        excluded_component_names_with_quotes = [f'"{name}"' for name in exclude_component_names]
        clause = f'(component not in ({",".join(excluded_component_names_with_quotes)}) OR component IS EMPTY)'
        clauses.append(clause)

    # Add exclude_label_names clause if not empty
    if exclude_label_names:
        clauses.append(f'(labels not in ({",".join(exclude_label_names)}) OR labels IS EMPTY)')

    # Add date clauses if dates are provided
    if start_date:
        clauses.append(f'resolved >= "{start_date.strftime("%Y/%m/%d")}"')
    if end_date:
        clauses.append(f'resolved <= "{end_date.strftime("%Y/%m/%d")}"')
        
    # Add assignee clause if not empty
    if assignee:
        assignee_with_quotes = [f'"{name}"' for name in assignee]
        clause = f'assignee in ({",".join(assignee_with_quotes)})'
        clauses.append(clause)
        
    # Add reporter clause if not empty
    if reporter:
        reporter_with_quotes = [f'"{name}"' for name in reporter]
        clause = f'reporter in ({",".join(reporter_with_quotes)})'
        clauses.append(clause)

    # Add a fixed status Done
    clauses.append('status = "Done"')

    # Join all clauses with 'AND'
    return " AND ".join(clauses)
    
# Wrapper classes to make v3 API JSON compatible with get_status_datetime()
class DotDict:
    """Allows dict access via dot notation."""
    def __init__(self, data):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, DotDict(value))
            elif isinstance(value, list):
                setattr(self, key, [DotDict(item) if isinstance(item, dict) else item for item in value])
            else:
                setattr(self, key, value)

    def __getattr__(self, name):
        return None

# Fetch issues from Jira with api 3
def fetch_issues(api_url, api_user, api_key, jql_query):
    base_url = api_url.split("/rest/")[0] if "/rest/" in api_url else api_url.rstrip("/")

    auth = HTTPBasicAuth(api_user, api_key)
    headers = {"Accept": "application/json"}

    # Test authentication first
    if debug:
        myself_url = f"{base_url}/rest/api/3/myself"
        test_response = requests.get(myself_url, headers=headers, auth=auth)
        print(f"Auth test ({myself_url}): {test_response.status_code}")
        if test_response.status_code == 200:
            print(f"Authenticated as: {test_response.json().get('displayName', 'unknown')}")
        else:
            print(f"Auth failed: {test_response.text[:300]}")
            return []

    # Use /rest/api/3/search/jql endpoint (GET)
    search_url = f"{base_url}/rest/api/3/search/jql"

    all_issues = []
    next_page_token = None
    page = 0

    while True:
        params = {
            "jql": jql_query,
            "fields": "created,assignee,issuetype,customfield_10002,customfield_10004",
            "expand": "changelog",
            "maxResults": 50
        }
        if next_page_token:
            params["nextPageToken"] = next_page_token

        response = requests.get(search_url, params=params, headers=headers, auth=auth)

        if debug:
            print(f"Request URL: {response.url}")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")

        if response.status_code != 200:
            print(f"API Error {response.status_code}: {response.text}")
            return []

        data = response.json()
        page += 1
        page_count = len(data.get("issues", []))
        print(f"\r  Page {page} — {len(all_issues) + page_count} issues fetched...", end="", flush=True)

        # Convert JSON issues to DotDict objects for compatibility with get_status_datetime()
        for issue_data in data.get("issues", []):
            if debug:
                if len(all_issues) == 0:
                    # Debug: print first issue structure
                    print(f"First issue keys: {issue_data.keys()}")
                    if "fields" in issue_data:
                        print(f"Fields keys: {issue_data['fields'].keys()}")
            all_issues.append(DotDict(issue_data))

        # Check for more pages
        if data.get("isLast", True):
            break
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    print(f"\r  Done — {len(all_issues)} issues fetched in {page} page(s).    ")
    return all_issues

def get_status_datetime(issues):
    total_hours = 0
    outputfile = []
    obfuscated_keys = replace_team_key(jira_projects)
    replace_names_with_animals = {}
    print("Number of issues: " + str(len(issues)))

    for issue in issues:
        creation_time = datetime.datetime.strptime(issue.fields.created, "%Y-%m-%dT%H:%M:%S.%f%z")
        start_time = None
        review_time = None
        end_time = None
        done_transitions = []
        changelog = issue.changelog

        for history in changelog.histories:
            for item in history.items:
                if item.field == "status" or item.field == "resolution":
                    if item.toString == "Done":
                        # Collect all 'Done' transitions to determine the last one later
                        done_transitions.append((history.created, history))
                    elif item.toString == "In Progress":
                        # Always set start_time to the oldest occurrence of 'In Progress'
                        current_time = datetime.datetime.strptime(history.created, "%Y-%m-%dT%H:%M:%S.%f%z")
                        if start_time is None or current_time < start_time:
                            start_time = current_time
                    elif item.toString == "Review":
                        # Always set review_time to the oldest occurrence of 'Review'
                        current_time = datetime.datetime.strptime(history.created, "%Y-%m-%dT%H:%M:%S.%f%z")
                        if review_time is None or current_time < review_time:
                            review_time = current_time

        # If start_time was not set, use the creation date of the issue
        if start_time is None:
            start_time = datetime.datetime.strptime(issue.fields.created, "%Y-%m-%dT%H:%M:%S.%f%z")

        # If review_time is earlier than start_time, use the creation date instead for start_time
        if review_time and review_time < start_time:
            start_time = datetime.datetime.strptime(issue.fields.created, "%Y-%m-%dT%H:%M:%S.%f%z")

        # Sorting the 'Done' list to get the last done state timestamp and set that to end_time
        if done_transitions:
            done_transitions.sort(key=lambda x: datetime.datetime.strptime(x[0], "%Y-%m-%dT%H:%M:%S.%f%z"), reverse=True)
            most_recent = done_transitions[0]
            end_time = datetime.datetime.strptime(str(most_recent[0]), "%Y-%m-%dT%H:%M:%S.%f%z")

        # Replace JIRA keys with obfuscated keys
        project, issue_number = str(issue.key).split("-")
        new_issue_id = obfuscated_keys[project] + "-" + issue_number

        # Calculate the time spent in each status
        total_time = end_time - start_time if end_time else None
        # Reformat the time to be consistent for sorting in Excel to add or pad days
        sort_total_time = format_timedelta(total_time)
        
        in_progress_time = ""
        in_review_time = ""
        if review_time:
            in_progress_time = review_time - start_time
            in_review_time = end_time - review_time if end_time else None

        # Add story points
        #story_point = str(issue.fields.customfield_10002)
        story_point = str(getattr(issue.fields, "customfield_10002", None))
        if story_point.endswith(".0"):
            story_point = story_point[:-2]

        # Set the number of sprints the issue has been in
        sprints = getattr(issue.fields, "customfield_10004", None)
        number_of_sprints = len(sprints) if sprints else 0

        # Obfuscate assignee names
        assignee_obj = issue.fields.assignee
        issue_assignee = assignee_obj.displayName if assignee_obj else "Unassigned"
        if issue_assignee not in replace_names_with_animals:
            random_animal = generate_random_pairs(replace_names_with_animals)
            replace_names_with_animals[issue_assignee] = random_animal
        assignee = replace_names_with_animals[issue_assignee]

        # Create the entry to add to the output file
        entry = {
            "project": obfuscated_keys[project],
            "ticket-id": new_issue_id,
            "creation": creation_time,
            "start": start_time,
            "review": review_time,
            "end": end_time,
            "total_time": total_time,
            "sort_total_time": sort_total_time,
            "in_progress_time": in_progress_time,
            "in_review_time": in_review_time,
            "story_point": story_point,
            "type": issue.fields.issuetype.name,
            "number_of_sprints": number_of_sprints,
            "assignee": assignee,
        }
        outputfile.append(entry)

    write_data_to_file(outputfile, "data")
    write_data_to_file(replace_names_with_animals, "names")

def format_timedelta(td: datetime.timedelta) -> str:
    days = td.days
    # Zero-pad days to three digits
    day_str = f"{days:03d} day, "
    
    # Subtract the day part to get the remainder
    remainder = td - datetime.timedelta(days=days)
    
    # Extract hours, minutes, seconds, microseconds
    hours, rem = divmod(remainder.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    microseconds = remainder.microseconds
    
    # Build the final time string
    time_str = f"{hours}:{minutes:02d}:{seconds:02d}.{microseconds:06d}"
    
    return day_str + time_str
    
def replace_team_key(keys):
    team_keys = {}
    for index, key in enumerate(keys):
        team_keys[key] = f"JIRA{index + 1}"
        print("Jira key " + key + " is now written as " + team_keys[key])
    write_data_to_file(team_keys, "jira_keys")
    return team_keys

def generate_random_pairs(dictionary):
    pairs = ""

    pairs = get_verb_animal_number()

    # Check once for duplication and try one more time
    for value in dictionary.items():
        if str(value[1]) == pairs:
            print(
                "############################# "
                + pairs
                + " already exists, trying only once more and hoping for not another conflict :-)"
            )
            pairs = get_verb_animal_number()
            print("New name is: " + pairs)

    return pairs

def get_verb_animal_number():
    verbs = [
        "Flying",
        "Fast",
        "Lazy",
        "Quick",
        "Running",
        "Zooming",
        "Jumping",
        "Crawling",
        "Rolling",
        "Hunting",
        "Sleeping",
        "Climbing",
    ]
    animals = [
        "Eagle",
        "Bear",
        "Dog",
        "Cat",
        "Fox",
        "Tiger",
        "Sloth",
        "Lion",
        "Elephant",
        "Giraffe",
        "Wolf",
        "Llama",
        "Panda",
    ]

    verb = random.choice(verbs)
    animal = random.choice(animals)
    number = random.randint(1000, 9999)
    
    return verb + "-" + animal + "-" + str(number)

# Write data to file
def write_data_to_file(data, datatype):
    folder = datetime.datetime.today().strftime('%Y-%m-%d')
    path = os.getcwd()

    # Create "YYYY-MM-DD" folder if it doesn't exist
    folder_path = os.path.join(path, folder)
    os.makedirs(folder_path, exist_ok=True)

    file_current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    txt_file = os.path.join(folder_path, f"{file_current_time}_{datatype}.txt")
    csv_file = os.path.join(folder_path, f"{file_current_time}_{datatype}.csv")


    if isinstance(data, dict):
        with open(txt_file, "w") as file:
            for key, value in data.items():
                file.write(f"{value}: {key}\n")
        print(f"Metadata written to {txt_file}")

    elif isinstance(data, list) and datatype != "data":
        with open(txt_file, "w") as file:
            for line in data:
                file.write(f"{line}\n")
        print(f"Metadata written to {txt_file}")

    elif datatype != "data":
        with open(txt_file, "w") as file:
            file.write(f"{data}")
        print(f"Metadata written to {txt_file}")

    else:
        with open(csv_file, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=[
                "project",
                "ticket-id",
                "creation",
                "start",
                "review",
                "end",
                "total_time",
                "sort_total_time",
                "in_progress_time",
                "in_review_time",
                "story_point",
                "type",
                "number_of_sprints",
                "assignee",
            ])
            writer.writeheader()
            writer.writerows(data)

        print(f"Data written to {csv_file}")

def debug_dump_fields(jira, jql_query, limit):
    data = jira.enhanced_search_issues(
        jql_str=jql_query,
        maxResults=limit,
        json_result=True,
        fields="*all",     # include all available fields
    )
    import json
    with open("jira_debug_dump.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Wrote jira_debug_dump.json")

if __name__ == "__main__":
    main()
