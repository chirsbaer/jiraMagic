# jiraMagic

Create an API token from your Atlassian account:

Log in to https://id.atlassian.com/manage-profile/security/api-tokens.

Select Create API token.

Give your API token a name that describes what it does.

Select an expiration date for the API token.

Token expiration is 1 to 365 days.

Select Create.

Select Copy to clipboard, then paste the token to your script, or save it somewhere safe.

You can't recover the API token after you’re done with this step. We recommend you save your API token in a password manager.


How to configure your JQL (jira search string):

Fetch Data Script

python fetchDataFromJira.py [options]

Arguments

-d, --delete
Delete folders with YYYY-MM-DD format.

-s, --start
Start date. Accepts:

Absolute: YYYY,MM,DD (example: 2025,08,20)

Relative: -Nd, -Nw, -Nm, -Ny (days, weeks, months, years)

-e, --end
End date. Same formats as --start.

-p, --projects
One or more Jira projects. Example: -p ABC XYZ

-t, --types
One or more issue types. Example: -t Story Task Bug

-c, --components
One or more components. Supports spaces via quotes.
Example: -c DEVOPS urgent Deploy "3rd party"

-exc, --excomponents
Components to exclude. Same input rules as --components.

-l, --labels
One or more labels. Example: -l DEVOPS urgent Deploy

-exl, --exlabels
Labels to exclude. Same input rules as --labels.

-a, --assignee
One or more assignees. Example: -a "John Smith" "Jane Doe"

-r, --reporter
One or more reporters. Example: -r "John Smith" "Jane Doe"

-alt, --alternative
How to read configuration. Allowed values: code, file, parameter.

-f, --filename
Name of parameter file located in ./.env/. Will be created if it does not exist with a template.

Date input details

Absolute date: YYYY,MM,DD
Example: --start 2025,08,20

Relative date: -Nd, -Nw, -Nm, -Ny
Examples:

--start=-5d (5 days ago)

--end=-4w (4 weeks ago)

--start=-3m (3 months ago)

--end=-1y (1 year ago)

Important for values starting with -:
Use = or the end-of-options marker so argparse treats it as a value:

--start=-13w
# or
--start -- -13w

Examples
# Absolute start/end, multiple projects and types
python your_script.py \
  --start 2025,08,20 \
  --end 2025,09,20 \
  --projects ABC XYZ \
  --types Story Task Bug

# Relative dates, components with spaces
python your_script.py \
  --start=-4w \
  --end=-1w \
  --components DEVOPS urgent Deploy "3rd party"

# Excluding components and labels
python your_script.py \
  --excomponents legacy archive \
  --exlabels wontfix duplicate

Using a config file in ./.env/

Provide --filename when --alternative=file. The file lives in ./.env/ and contains key = value1, value2, ... lines. Lines starting with # are ignored.

Example ./.env/myconfig.env:

jira_projects = PROJ1, PROJ2, PROJ3
issue_types = Story, Task, Bug
include_components = Login, Onboarding
include_labels = urgent, backend
exclude_components = legacy, archive
exclude_labels = wontfix, duplicate
assignee = John Smith
reporter = Jane Doe
start = 2025,08,20
end = -4w


Comment-only template that may be created for you:

# jira_projects =
# issue_types =
# include_components =
# include_labels =
# exclude_components =
# exclude_labels =
# assignee =
# reporter =
# start =
# stop =

Notes

For values with spaces, quote them: "3rd party", "John Smith".

For list arguments (projects, types, components, labels, etc.), pass multiple values separated by spaces.

For relative date values that begin with -, prefer --arg=-13w or --arg -- -13w.