import os
import glob
import pandas as pd
import inspect
import sys
import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

break_point_seconds = 59
outlier_percentile = 0.98  # exclude tickets above this percentile of total_time (e.g. 0.98 = top 2%)

# Redirect print statements to both console and a file
def print_and_log(*args, **kwargs):
    print(*args, **kwargs)
    if hasattr(sys, 'stdout_log') and sys.stdout_log is not None:
        print(*args, **kwargs, file=sys.stdout_log)

def get_newest_csv():
    current_function = inspect.currentframe().f_code.co_name
    print_and_log(f"\nFunction: {current_function}")
    
    folder = datetime.datetime.today().strftime('%Y-%m-%d')
    folder_path = os.path.join(os.path.dirname(__file__), folder)
    
    if not os.path.exists(folder_path):
        print_and_log(f"Folder not found: {folder_path}")
        return None

    # Get the list of all CSV files in the specified folder
    csv_files = glob.glob(os.path.join(folder_path, "*_data.csv"))
    if not csv_files:
        print_and_log("No CSV files found in the directory.")
        return None

    # Find the newest CSV file by modification time
    newest_csv = max(csv_files, key=os.path.getmtime)
    print_and_log(f"File found! {newest_csv}\n")
    return newest_csv

def file_info(data):
    current_function = inspect.currentframe().f_code.co_name
    print_and_log(f"Function: {current_function}")
    # Get the number of rows in the CSV file
    line_count = len(data)
    
    # Convert 'end' column to datetime to find the first and last closed dates
    data['end'] = pd.to_datetime(data['end'], errors='coerce', utc=True)
    
    # Determine the first and last closed ticket dates and convert to date format
    first_closed = data['end'].min().date() if pd.notna(data['end'].min()) else None
    last_closed = data['end'].max().date() if pd.notna(data['end'].max()) else None
    
    # Print the results
    print_and_log(f"Number of lines in file: {line_count}")
    print_and_log(f"First closed ticket: {first_closed}")
    print_and_log(f"Last closed ticket: {last_closed}\n")

def exclude_short_lived_tickets(data):
    current_function = inspect.currentframe().f_code.co_name
    print_and_log(f"Function: {current_function}")
    
    # Convert 'total_time' to timedelta to filter by duration
    data['total_time'] = pd.to_timedelta(data['total_time'], errors='coerce')
    
    # Filter out tickets that are alive less than 60 seconds
    excluded_data = data[data['total_time'] < pd.Timedelta(seconds=break_point_seconds)]
    remaining_data = data[data['total_time'] >= pd.Timedelta(seconds=break_point_seconds)]
    
    # Count the occurrences of each type in the excluded data
    excluded_counts = excluded_data['type'].value_counts()
    
    # Print the results
    print_and_log(f"Excluded tickets (alive less than {break_point_seconds} seconds):")
    for ticket_type, count in excluded_counts.items():
        print_and_log(f"{ticket_type}: {count} tickets")
    
    if len(excluded_counts) == 0:
        print_and_log(f"0 tickets with {break_point_seconds} seconds lifetime")
    
    print_and_log("\n")
    
    return remaining_data
    

def exclude_longest_tickets(data):
    current_function = inspect.currentframe().f_code.co_name
    print_and_log(f"Function: {current_function}")

    # Convert total_time to a Timedelta if not already
    data['total_time'] = pd.to_timedelta(data['total_time'], errors='coerce')

    # Use percentile cutoff to exclude extreme outliers
    upper_fence = data['total_time'].quantile(outlier_percentile)

    excluded_data = data[data['total_time'] > upper_fence]
    remaining_data = data[data['total_time'] <= upper_fence]

    excluded_counts = excluded_data['type'].value_counts()

    print_and_log(f"Excluded outlier tickets (total_time > {round(upper_fence.total_seconds() / 86400, 1)} days, top {round((1 - outlier_percentile) * 100, 1)}% cutoff):")
    for ticket_type, count in excluded_counts.items():
        print_and_log(f"{ticket_type}: {count} tickets")

    if len(excluded_counts) == 0:
        print_and_log("No outlier tickets found.")

    print_and_log("\n")
    return remaining_data



def count_each_ticket_type(data):
    current_function = inspect.currentframe().f_code.co_name
    print_and_log(f"Function: {current_function}")
    # Count the occurrences of each type
    ticket_type_counts = data['type'].value_counts()
    
    # Total tickets after short lived and longest tickets
    print_and_log(f"Total {len(data)} tickets")
    
    # Print the results
    for ticket_type, count in ticket_type_counts.items():
        print_and_log(f"{ticket_type}: {count} tickets")
    print_and_log("\n")


def _save_distribution_graph(times_in_days, label, images_folder):
    sorted_days = sorted(times_in_days)
    n = len(sorted_days)
    percentiles = [100 * (i + 1) / n for i in range(n)]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(percentiles, sorted_days, color='steelblue', linewidth=1.5)
    ax.set_xlabel('Percentile')
    ax.set_ylabel('Time (days)')
    ax.set_xlim(0, 100)
    ax.set_ylim(bottom=0)
    ax.set_title(f'Cycle Time Distribution - {label}')
    ax.grid(True, linestyle='--', alpha=0.5)
    fig.tight_layout()

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    safe_label = label.replace(' ', '_').replace('/', '_')
    filename = f"{timestamp}_{safe_label}.png"
    filepath = os.path.join(images_folder, filename)
    plt.savefig(filepath)
    plt.close()
    print_and_log(f"Saved graph: {filepath}")


def _fmt_days(td):
    return f"{td.total_seconds() / 86400:.2f}" if pd.notna(td) else " N/A"


def closed_ticket_types_per_month(data, images_folder):
    current_function = inspect.currentframe().f_code.co_name
    print_and_log(f"Function: {current_function}")

    data['end'] = pd.to_datetime(data['end'], errors='coerce', utc=True)
    data['end'] = data['end'].dt.tz_convert(None)
    data['total_time'] = pd.to_timedelta(data['total_time'], errors='coerce')

    # Collect rows first so we can compute column widths
    rows = []
    for (ticket_type, month), group in data.groupby(['type', data['end'].dt.to_period('M')]):
        count = group.shape[0]
        p25 = _fmt_days(group['total_time'].quantile(0.25))
        p50 = _fmt_days(group['total_time'].quantile(0.50))
        p75 = _fmt_days(group['total_time'].quantile(0.75))
        rows.append((ticket_type, str(month), count, p25, p50, p75))

    count_w = max(len(str(r[2])) for r in rows)
    p25_w   = max(len(r[3]) for r in rows)
    p50_w   = max(len(r[4]) for r in rows)
    p75_w   = max(len(r[5]) for r in rows)

    current_type = None
    for ticket_type, month_str, count, p25, p50, p75 in rows:
        if ticket_type != current_type:
            if current_type is not None:
                print_and_log("")
            current_type = ticket_type
            print_and_log(f"{ticket_type} tickets closed per month, Percentile 25/50/75 in days:")
        print_and_log(
            f"  {month_str} : {str(count).rjust(count_w)} tickets, "
            f"{p25.rjust(p25_w)}, {p50.rjust(p50_w)}, {p75.rjust(p75_w)}"
        )

    print_and_log("\n")

    # Generate one percentile distribution graph per ticket type
    for ticket_type, type_group in data.groupby('type'):
        valid_times = type_group['total_time'].dropna()
        times_in_days = [t.total_seconds() / 86400 for t in valid_times]
        _save_distribution_graph(times_in_days, ticket_type, images_folder)


def closed_tickets_per_month(data, images_folder):
    current_function = inspect.currentframe().f_code.co_name
    print_and_log(f"Function: {current_function}")

    data['end'] = pd.to_datetime(data['end'], errors='coerce', utc=True)
    data['end'] = data['end'].dt.tz_convert(None)
    data['total_time'] = pd.to_timedelta(data['total_time'], errors='coerce')

    # Collect rows first so we can compute column widths
    rows = []
    for month, group in data.groupby(data['end'].dt.to_period('M')):
        count = group.shape[0]
        p25 = _fmt_days(group['total_time'].quantile(0.25))
        p50 = _fmt_days(group['total_time'].quantile(0.50))
        p75 = _fmt_days(group['total_time'].quantile(0.75))
        rows.append((str(month), count, p25, p50, p75))

    count_w = max(len(str(r[1])) for r in rows)
    p25_w   = max(len(r[2]) for r in rows)
    p50_w   = max(len(r[3]) for r in rows)
    p75_w   = max(len(r[4]) for r in rows)

    print_and_log("Tickets closed per month, Percentile 25/50/75 in days:")
    for month_str, count, p25, p50, p75 in rows:
        print_and_log(
            f"  {month_str} : {str(count).rjust(count_w)} tickets, "
            f"{p25.rjust(p25_w)}, {p50.rjust(p50_w)}, {p75.rjust(p75_w)}"
        )

    print_and_log("\n")

    # Generate percentile distribution graph for all tickets combined
    valid_times = data['total_time'].dropna()
    times_in_days = [t.total_seconds() / 86400 for t in valid_times]
    _save_distribution_graph(times_in_days, 'all', images_folder)

def main():
    newest_csv = get_newest_csv()
    if newest_csv is None:
        return

    read_file_name = os.path.splitext(newest_csv)[0]
    log_filename = read_file_name + "_refined.txt"

    date_folder = os.path.dirname(newest_csv)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    images_folder = os.path.join(date_folder, f"{timestamp}_images")
    os.makedirs(images_folder, exist_ok=True)

    with open(log_filename, 'w') as log_file:
        sys.stdout_log = log_file
        print(f"Refined data written to {log_filename}\n")
        print(f"File found! {newest_csv}\n", file=sys.stdout_log)

        # Read the CSV file using pandas
        data = pd.read_csv(newest_csv)

        # Call the functions
        file_info(data)
        data = exclude_short_lived_tickets(data)
        data = exclude_longest_tickets(data)
        count_each_ticket_type(data)
        closed_ticket_types_per_month(data, images_folder)
        closed_tickets_per_month(data, images_folder)
        calculate_cycle_time(data, read_file_name)

        # Close the log file
        sys.stdout_log = None

# Function to calculate cycle times
def calculate_cycle_time(df, read_file_name):
    current_function = inspect.currentframe().f_code.co_name
    print_and_log(f"Function: {current_function}")

    # Ensure necessary columns are present, fill missing columns with NaT
    for col in ['creation', 'start', 'review', 'end']:
        if col not in df.columns:
            df[col] = pd.NaT

    # Convert date columns to datetime format
    for col in ['creation', 'start', 'review', 'end']:
        df[col] = pd.to_datetime(df[col], errors='coerce', utc=True)

    # Function to calculate durations in hours
    def calculate_duration(start, end):
        if pd.isnull(start) or pd.isnull(end):
            return float('nan')  # Explicitly return NaN for missing dates
        return (end - start).total_seconds() / 3600  # Duration in hours

    # Calculate lead time, cycle time, in-progress time, review time, and idle time for each ticket
    df['lead_time'] = df.apply(lambda row: calculate_duration(row['creation'], row['end']), axis=1)
    df['cycle_time'] = df.apply(
        lambda row: calculate_duration(row['start'], row['end'])
        if pd.notnull(row['start']) else float('nan'),
        axis=1
    )
    df['in_progress_time'] = df.apply(
        lambda row: calculate_duration(row['start'], row['review']) 
        if pd.notnull(row['review']) else calculate_duration(row['start'], row['end']), 
        axis=1
    )
    df['in_review_time'] = df.apply(
        lambda row: calculate_duration(row['review'], row['end']) 
        if pd.notnull(row['review']) and pd.notnull(row['end']) 
        else float('nan'), 
        axis=1
    )
    df['idle_time'] = df.apply(
        lambda row: calculate_duration(row['creation'], row['start']) 
        if pd.notnull(row['creation']) and pd.notnull(row['start']) 
        else float('nan'), 
        axis=1
    )

    # Convert times from hours to days with two decimals
    df['lead_time'] /= 24
    df['cycle_time'] /= 24
    df['in_progress_time'] /= 24
    df['in_review_time'] /= 24
    df['idle_time'] /= 24

    # Median lead time — creation to end
    median_lead = (
        df[df['lead_time'].notnull()]
        .groupby('type')['lead_time']
        .median()
        .round(2)
        .rename('median_lead_time')
    )

    # Median cycle time — start to end (only tickets with a start time)
    median_cycle = (
        df[df['cycle_time'].notnull()]
        .groupby('type')['cycle_time']
        .median()
        .round(2)
        .rename('median_cycle_time')
    )

    # Median in‑progress time — require only in_progress_time
    median_in_progress = (
        df[df['in_progress_time'].notnull()]
        .groupby('type')['in_progress_time']
        .median()
        .round(2)
        .rename('median_in_progress_time')
    )

    # Median in‑review time — require only in_review_time
    median_in_review = (
        df[df['in_review_time'].notnull()]
        .groupby('type')['in_review_time']
        .median()
        .round(2)
        .rename('median_in_review_time')
    )

    # Median idle time — require only idle_time
    median_idle = (
        df[df['idle_time'].notnull()]
        .groupby('type')['idle_time']
        .median()
        .round(2)
        .rename('median_idle_time')
    )

    # Combine into a single DataFrame
    cycle_time_summary = (
        pd.concat([median_lead, median_cycle, median_idle, median_in_progress, median_in_review], axis=1)
        .reset_index()
    )

    # Add units to column names
    cycle_time_summary.rename(columns={
        'median_lead_time': 'median_lead_time (days)',
        'median_cycle_time': 'median_cycle_time (days)',
        'median_idle_time': 'median_idle_time (days)',
        'median_in_progress_time': 'median_in_progress_time (days)',
        'median_in_review_time': 'median_in_review_time (days)'
    }, inplace=True)

    # Display summary
    print_and_log(cycle_time_summary)

    # Save to CSV
    cycle_time_summary.to_csv(f'{read_file_name}cycle_time.csv', index=False)

    return cycle_time_summary



if __name__ == "__main__":
    main()
