#!/usr/bin/env python3
"""
Daily Metrics Visualization Script
Reads daily metrics from CSV and generates time series charts.
"""

import csv
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import argparse

from repo_paths import resolve_private_repo_root

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.gridspec import GridSpec
except ImportError:
    print("Error: matplotlib is required. Install with: pip3 install matplotlib")
    sys.exit(1)

# Read and write against private state in <private-repo>.
PRIVATE_REPO_ROOT = resolve_private_repo_root()
METRICS_CSV = PRIVATE_REPO_ROOT / "journal" / "daily_metrics.csv"
TRENDS_DIR = PRIVATE_REPO_ROOT / "journal" / "trends"

# Metric names and their display info
METRICS = {
    'energy': {'label': 'Energy', 'scale': (1, 5), 'unit': '(1-5)'},
    'mood': {'label': 'Mood', 'scale': (1, 5), 'unit': '(1-5)'},
    'focus': {'label': 'Focus', 'scale': (1, 5), 'unit': '(1-5)'},
    'productivity': {'label': 'Productivity', 'scale': (1, 5), 'unit': '(1-5)'},
    'deep_sprints': {'label': 'Deep Sprints (count)', 'scale': None, 'unit': ''},
    'light_blocks': {'label': 'Light Blocks (count)', 'scale': None, 'unit': ''},
    'deep_focus_time': {'label': 'Deep Focus Time (hours)', 'scale': None, 'unit': '(hours)'},
    'light_focus_time': {'label': 'Light Focus Time (hours)', 'scale': None, 'unit': '(hours)'},
}

def parse_float(value):
    """Parse a value to float, handling blanks and nulls"""
    if not value or value.strip().lower() in ['', 'null', 'blank', '-', 'n/a']:
        return None
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return None

def load_all_metrics(start_date=None, end_date=None):
    """Load metrics from CSV file"""
    if not METRICS_CSV.exists():
        print(f"Error: Metrics CSV file not found: {METRICS_CSV}")
        print("Make sure daily summaries are being created with metrics.")
        return []

    all_data = []

    # Column name mapping from CSV to our internal keys
    column_map = {
        'Date': 'date',
        'Energy (1-5)': 'energy',
        'Mood (1-5)': 'mood',
        'Focus (1-5)': 'focus',
        'Productivity (1-5)': 'productivity',
        'Deep Sprints (count)': 'deep_sprints',
        'Light Blocks (count)': 'light_blocks',
        'Deep Focus Time (hours)': 'deep_focus_time',
        'Light Focus Time (hours)': 'light_focus_time',
    }

    try:
        with open(METRICS_CSV, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            # Map column names (handle variations)
            fieldnames = reader.fieldnames
            if not fieldnames:
                print("Error: CSV file appears to be empty or has no header")
                return []

            # Create mapping from actual CSV headers to our keys
            csv_to_key = {}
            for csv_col in fieldnames:
                csv_col_lower = csv_col.strip().lower()
                for expected_col, key in column_map.items():
                    if expected_col.lower() == csv_col_lower or csv_col_lower in expected_col.lower():
                        csv_to_key[csv_col] = key
                        break

            for row in reader:
                # Parse date
                date_str = row.get('Date', '').strip()
                if not date_str:
                    continue

                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    # Try other date formats
                    try:
                        date = datetime.strptime(date_str, '%Y/%m/%d').date()
                    except ValueError:
                        print(f"Warning: Could not parse date '{date_str}', skipping row")
                        continue

                # Filter by date range if specified
                if start_date and date < start_date:
                    continue
                if end_date and date > end_date:
                    continue

                # Extract metrics
                metrics = {}
                for csv_col, key in csv_to_key.items():
                    if csv_col in row:
                        value = parse_float(row[csv_col])
                        if value is not None:
                            metrics[key] = value

                if metrics:  # Only add if we have at least one metric
                    all_data.append({
                        'date': date,
                        'metrics': metrics
                    })

    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []

    return sorted(all_data, key=lambda x: x['date'])

def create_time_series_chart(data, output_path):
    """Create time series charts for all metrics"""
    if not data:
        print("No data to visualize")
        return

    # Prepare data by metric
    dates = [d['date'] for d in data]

    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(4, 2, figure=fig, hspace=0.3, wspace=0.3)

    # 1-5 scale metrics (first 4)
    scale_metrics = ['energy', 'mood', 'focus', 'productivity']
    for idx, metric_key in enumerate(scale_metrics):
        ax = fig.add_subplot(gs[idx // 2, idx % 2])

        values = [d['metrics'].get(metric_key) for d in data]
        valid_data = [(d, v) for d, v in zip(dates, values) if v is not None]

        if valid_data:
            valid_dates = [d for d, v in valid_data]
            valid_values = [v for d, v in valid_data]

            ax.plot(valid_dates, valid_values, marker='o', linewidth=2, markersize=4)
            ax.set_ylim(0.5, 5.5)
            ax.set_yticks(range(1, 6))
            ax.grid(True, alpha=0.3)
            ax.set_title(f"{METRICS[metric_key]['label']} {METRICS[metric_key]['unit']}", fontsize=11, fontweight='bold')
            ax.set_ylabel('Score')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f"{METRICS[metric_key]['label']} {METRICS[metric_key]['unit']}", fontsize=11, fontweight='bold')

    # Sprint/time metrics
    other_metrics = ['deep_sprints', 'light_blocks', 'deep_focus_time', 'light_focus_time']
    for idx, metric_key in enumerate(other_metrics):
        ax = fig.add_subplot(gs[(idx + 4) // 2, (idx + 4) % 2])

        values = [d['metrics'].get(metric_key) for d in data]
        valid_data = [(d, v) for d, v in zip(dates, values) if v is not None]

        if valid_data:
            valid_dates = [d for d, v in valid_data]
            valid_values = [v for d, v in valid_data]

            ax.plot(valid_dates, valid_values, marker='o', linewidth=2, markersize=4, color='steelblue')
            ax.grid(True, alpha=0.3)
            ax.set_title(f"{METRICS[metric_key]['label']} {METRICS[metric_key]['unit']}", fontsize=11, fontweight='bold')
            ax.set_ylabel(METRICS[metric_key]['unit'])
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f"{METRICS[metric_key]['label']} {METRICS[metric_key]['unit']}", fontsize=11, fontweight='bold')

    # Add overall title
    date_range = f"{dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}"
    fig.suptitle(f'Daily Metrics Over Time\n{date_range}', fontsize=14, fontweight='bold', y=0.995)

    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Created time series chart: {output_path}")

def create_correlation_chart(data, output_path):
    """Create correlation scatter plots"""
    if not data:
        return

    # Prepare data
    dates = [d['date'] for d in data]

    # Correlation pairs to analyze
    correlations = [
        ('deep_sprints', 'productivity', 'Deep Sprints vs Productivity'),
        ('deep_focus_time', 'productivity', 'Deep Focus Time vs Productivity'),
        ('light_blocks', 'mood', 'Light Blocks vs Mood'),
        ('focus', 'productivity', 'Focus vs Productivity'),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()

    for idx, (x_key, y_key, title) in enumerate(correlations):
        ax = axes[idx]

        x_values = [d['metrics'].get(x_key) for d in data]
        y_values = [d['metrics'].get(y_key) for d in data]

        # Filter to valid pairs
        valid_pairs = [(x, y) for x, y in zip(x_values, y_values) if x is not None and y is not None]

        if len(valid_pairs) >= 2:
            x_vals, y_vals = zip(*valid_pairs)
            ax.scatter(x_vals, y_vals, alpha=0.6, s=50)
            ax.set_xlabel(METRICS[x_key]['label'])
            ax.set_ylabel(METRICS[y_key]['label'])
            ax.set_title(title, fontweight='bold')
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Insufficient data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(title, fontweight='bold')

    fig.suptitle('Metric Correlations', fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Created correlation chart: {output_path}")

def create_weekly_averages(data, output_path):
    """Create weekly average bar charts"""
    if not data:
        return

    # Group by week
    weekly_data = defaultdict(lambda: defaultdict(list))

    for entry in data:
        date = entry['date']
        # Get Monday of the week
        days_since_monday = date.weekday()
        week_start = date - timedelta(days=days_since_monday)
        week_key = week_start.strftime('%Y-%m-%d')

        for metric_key, value in entry['metrics'].items():
            if value is not None:
                weekly_data[week_key][metric_key].append(value)

    # Calculate averages
    weekly_avgs = {}
    for week, metrics in weekly_data.items():
        weekly_avgs[week] = {
            key: sum(values) / len(values) if values else None
            for key, values in metrics.items()
        }

    if not weekly_avgs:
        return

    weeks = sorted(weekly_avgs.keys())

    # Create charts for 1-5 scale metrics
    scale_metrics = ['energy', 'mood', 'focus', 'productivity']
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for idx, metric_key in enumerate(scale_metrics):
        ax = axes[idx]
        values = [weekly_avgs[week].get(metric_key) for week in weeks]
        valid_data = [(w, v) for w, v in zip(weeks, values) if v is not None]

        if valid_data:
            valid_weeks, valid_values = zip(*valid_data)
            ax.bar(range(len(valid_weeks)), valid_values, alpha=0.7)
            ax.set_xticks(range(len(valid_weeks)))
            ax.set_xticklabels([w.split('-')[1] + '/' + w.split('-')[2] for w in valid_weeks], rotation=45, ha='right')
            ax.set_ylim(0, 5.5)
            ax.set_ylabel('Average Score')
            ax.set_title(f"Weekly Average: {METRICS[metric_key]['label']}", fontweight='bold')
            ax.grid(True, alpha=0.3, axis='y')

    fig.suptitle('Weekly Averages (1-5 Scale Metrics)', fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Created weekly averages chart: {output_path}")

def create_sprint_overview_charts(data, counts_output_path, scatter_output_path):
    """Create simple charts for sprint counts and their relationship to productivity"""
    if not data:
        return

    dates = [d['date'] for d in data]

    # Deep vs light sprint counts over time
    deep_counts = [d['metrics'].get('deep_sprints') for d in data]
    light_counts = [d['metrics'].get('light_blocks') for d in data]
    has_any_counts = any(v is not None for v in deep_counts + light_counts)

    if has_any_counts:
        fig, ax = plt.subplots(figsize=(12, 5))

        valid_deep = [(dt, v) for dt, v in zip(dates, deep_counts) if v is not None]
        valid_light = [(dt, v) for dt, v in zip(dates, light_counts) if v is not None]

        if valid_deep:
            d_dates, d_vals = zip(*valid_deep)
            ax.plot(d_dates, d_vals, marker='o', linewidth=2, markersize=4, label='Deep sprints')
        if valid_light:
            l_dates, l_vals = zip(*valid_light)
            ax.plot(l_dates, l_vals, marker='o', linewidth=2, markersize=4, label='Light blocks')

        ax.set_title('Deep Sprints and Light Blocks Over Time', fontweight='bold')
        ax.set_ylabel('Count')
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        ax.legend()

        plt.tight_layout()
        plt.savefig(counts_output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Created sprint counts chart: {counts_output_path}")

    # Deep sprint count vs productivity scatter
    deep_counts = [d['metrics'].get('deep_sprints') for d in data]
    productivity = [d['metrics'].get('productivity') for d in data]
    pairs = [(c, p) for c, p in zip(deep_counts, productivity) if c is not None and p is not None]

    if len(pairs) >= 2:
        x_vals, y_vals = zip(*pairs)
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(x_vals, y_vals, alpha=0.6, s=50)
        ax.set_xlabel('Deep Sprints (count)')
        ax.set_ylabel('Productivity (1-5)')
        ax.set_title('Deep Sprints vs Productivity', fontweight='bold')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(scatter_output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Created sprint vs productivity chart: {scatter_output_path}")

def export_to_csv(data, output_path):
    """Export metrics to CSV"""
    if not data:
        return

    import csv

    # Get all metric keys
    all_metric_keys = set()
    for entry in data:
        all_metric_keys.update(entry['metrics'].keys())
    all_metric_keys = sorted(all_metric_keys)

    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        # Header
        header = ['Date'] + [METRICS.get(key, {}).get('label', key) for key in all_metric_keys]
        writer.writerow(header)

        # Data rows
        for entry in data:
            row = [entry['date'].strftime('%Y-%m-%d')]
            for key in all_metric_keys:
                value = entry['metrics'].get(key)
                row.append(value if value is not None else '')
            writer.writerow(row)

    print(f"Exported CSV: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Visualize daily metrics from journal summaries')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--export-csv', action='store_true', help='Export metrics to CSV')
    args = parser.parse_args()

    # Parse date arguments
    start_date = None
    end_date = None
    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
    if args.end_date:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()

    # Create trends directory
    TRENDS_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    print(f"Loading daily metrics from {METRICS_CSV}...")
    data = load_all_metrics(start_date=start_date, end_date=end_date)

    if not data:
        print(f"No metrics data found in {METRICS_CSV}")
        print("Make sure daily summaries are being created with metrics.")
        return

    print(f"Loaded {len(data)} days of metrics")

    # Generate charts
    print("Generating charts...")

    # Time series chart
    time_series_path = TRENDS_DIR / "daily_metrics_timeseries.png"
    create_time_series_chart(data, time_series_path)

    # Correlation chart
    correlation_path = TRENDS_DIR / "metric_correlations.png"
    create_correlation_chart(data, correlation_path)

    # Weekly averages
    weekly_avg_path = TRENDS_DIR / "weekly_averages.png"
    create_weekly_averages(data, weekly_avg_path)

    # Sprint-related overview charts (use data if sprint columns are present)
    sprint_counts_path = TRENDS_DIR / "sprint_counts_timeseries.png"
    sprint_scatter_path = TRENDS_DIR / "sprint_counts_vs_productivity.png"
    create_sprint_overview_charts(data, sprint_counts_path, sprint_scatter_path)

    # CSV export (optional, for filtered date ranges)
    if args.export_csv:
        csv_path = TRENDS_DIR / "metrics_export.csv"
        export_to_csv(data, csv_path)

    print(f"\nAll charts saved to: {TRENDS_DIR}")
    print(f"  - Time series: {time_series_path.name}")
    print(f"  - Correlations: {correlation_path.name}")
    print(f"  - Weekly averages: {weekly_avg_path.name}")
    print(f"  - Sprint counts: {sprint_counts_path.name}")
    print(f"  - Sprints vs productivity: {sprint_scatter_path.name}")
    if args.export_csv:
        print(f"  - CSV export: {csv_path.name}")

if __name__ == '__main__':
    main()
