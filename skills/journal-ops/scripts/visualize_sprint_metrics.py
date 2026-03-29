#!/usr/bin/env python3
"""
Sprint Metrics Visualization Script
Reads sprint-level metrics from CSV and generates charts comparing actual allocation to Q1 plan targets.
"""

import csv
import sys
from datetime import datetime
import argparse

from repo_paths import resolve_private_repo_root

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("Error: matplotlib is required. Install with: pip3 install matplotlib")
    sys.exit(1)

PRIVATE_REPO_ROOT = resolve_private_repo_root()
SPRINT_METRICS_CSV = PRIVATE_REPO_ROOT / "journal" / "sprint_metrics.csv"
TRENDS_DIR = PRIVATE_REPO_ROOT / "journal" / "trends"
QUARTERLY_PLAN = PRIVATE_REPO_ROOT / "journal" / "summaries" / "2026" / "2026-Q1_Quarterly_Plan.md"

# Q1 Plan targets (from quarterly plan)
Q1_TARGETS = {
    'Job/Interview/Skills': (50, 60),  # 50-60%
    'Content': (25, 30),  # 25-30%
    'Personal Project': (10, 15),  # 10-15%
    'Business/Corp': (5, 10),  # 5-10%
}

def parse_int(value):
    """Parse a value to int, handling blanks and nulls"""
    if not value or value.strip().lower() in ['', 'null', 'blank', '-', 'n/a']:
        return None
    try:
        return int(float(value.strip()))
    except (ValueError, AttributeError):
        return None

def load_sprint_metrics():
    """Load sprint metrics from CSV file"""
    if not SPRINT_METRICS_CSV.exists():
        print(f"Error: Sprint metrics CSV file not found: {SPRINT_METRICS_CSV}")
        return []

    sprints = []

    try:
        with open(SPRINT_METRICS_CSV, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                if not row.get('Sprint ID') or not row['Sprint ID'].strip():
                    continue

                sprint = {
                    'id': row['Sprint ID'].strip(),
                    'start_date': row.get('Start Date', '').strip(),
                    'end_date': row.get('End Date', '').strip(),
                    'quarter': row.get('Quarter', '').strip(),
                    'deep_sprints_planned': parse_int(row.get('Deep Sprints Planned', '')),
                    'deep_sprints_done': parse_int(row.get('Deep Sprints Done', '')),
                    'light_blocks_planned': parse_int(row.get('Light Blocks Planned', '')),
                    'light_blocks_done': parse_int(row.get('Light Blocks Done', '')),
                    'job_sprints': parse_int(row.get('Job Deep Sprints', '')) or 0,
                    'interview_sprints': parse_int(row.get('Interview Deep Sprints', '')) or 0,
                    'content_sprints': parse_int(row.get('Content Deep Sprints', '')) or 0,
                    'project_sprints': parse_int(row.get('Project Deep Sprints', '')) or 0,
                    'biz_sprints': parse_int(row.get('Biz Deep Sprints', '')) or 0,
                    'notes': row.get('Notes', '').strip(),
                }

                # Calculate totals and percentages
                total_sprints = sprint['deep_sprints_done'] or 0
                if total_sprints > 0:
                    sprint['job_interview_total'] = sprint['job_sprints'] + sprint['interview_sprints']
                    sprint['job_interview_pct'] = (sprint['job_interview_total'] / total_sprints) * 100
                    sprint['content_pct'] = (sprint['content_sprints'] / total_sprints) * 100
                    sprint['project_pct'] = (sprint['project_sprints'] / total_sprints) * 100
                    sprint['biz_pct'] = (sprint['biz_sprints'] / total_sprints) * 100
                else:
                    sprint['job_interview_total'] = 0
                    sprint['job_interview_pct'] = 0
                    sprint['content_pct'] = 0
                    sprint['project_pct'] = 0
                    sprint['biz_pct'] = 0

                sprints.append(sprint)

    except Exception as e:
        print(f"Error reading sprint metrics CSV: {e}")
        return []

    return sprints

def create_sprint_count_chart(sprints, output_path):
    """Create chart showing deep sprints done per sprint"""
    if not sprints:
        print("No sprint data to visualize")
        return

    sprint_ids = [s['id'] for s in sprints]
    deep_sprints_done = [s['deep_sprints_done'] or 0 for s in sprints]

    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.bar(range(len(sprint_ids)), deep_sprints_done, color='steelblue', alpha=0.7)

    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars, deep_sprints_done)):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                   str(val), ha='center', va='bottom', fontweight='bold')

    ax.set_xlabel('Sprint', fontweight='bold')
    ax.set_ylabel('Deep Sprints Done', fontweight='bold')
    ax.set_title('Deep Sprints Per Sprint', fontweight='bold', fontsize=14)
    ax.set_xticks(range(len(sprint_ids)))
    ax.set_xticklabels(sprint_ids, rotation=45, ha='right')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(bottom=0)

    # Add target line (3-5 sprints/day * 14 days = 42-70 sprints per sprint)
    # Using average of 3.5 sprints/day = 49 sprints per sprint
    target_avg = 49
    ax.axhline(y=target_avg, color='green', linestyle='--', linewidth=2,
               label=f'Target Average ({target_avg} sprints)', alpha=0.7)
    ax.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Created sprint count chart: {output_path}")

def create_allocation_chart(sprints, output_path):
    """Create stacked bar chart showing domain allocation percentages"""
    if not sprints:
        print("No sprint data to visualize")
        return

    sprint_ids = [s['id'] for s in sprints]
    job_interview_pct = [s['job_interview_pct'] for s in sprints]
    content_pct = [s['content_pct'] for s in sprints]
    project_pct = [s['project_pct'] for s in sprints]
    biz_pct = [s['biz_pct'] for s in sprints]

    fig, ax = plt.subplots(figsize=(12, 7))

    x = np.arange(len(sprint_ids))
    width = 0.6

    bars1 = ax.bar(x, job_interview_pct, width, label='Job/Interview/Skills', color='#2E86AB', alpha=0.8)
    bars2 = ax.bar(x, content_pct, width, bottom=job_interview_pct, label='Content', color='#A23B72', alpha=0.8)
    bars3 = ax.bar(x, project_pct, width,
                   bottom=[j + c for j, c in zip(job_interview_pct, content_pct)],
                   label='Personal Project', color='#F18F01', alpha=0.8)
    bars4 = ax.bar(x, biz_pct, width,
                   bottom=[j + c + p for j, c, p in zip(job_interview_pct, content_pct, project_pct)],
                   label='Business/Corp', color='#C73E1D', alpha=0.8)

    # Add target ranges as horizontal bands
    ax.axhspan(Q1_TARGETS['Job/Interview/Skills'][0], Q1_TARGETS['Job/Interview/Skills'][1],
               alpha=0.1, color='blue', label='Job/Interview Target (50-60%)')
    ax.axhspan(Q1_TARGETS['Content'][0], Q1_TARGETS['Content'][1],
               alpha=0.1, color='purple', label='Content Target (25-30%)')

    ax.set_xlabel('Sprint', fontweight='bold')
    ax.set_ylabel('Percentage (%)', fontweight='bold')
    ax.set_title('Sprint Domain Allocation vs Q1 Plan Targets', fontweight='bold', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(sprint_ids, rotation=45, ha='right')
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(loc='upper left', fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Created allocation chart: {output_path}")

def create_target_comparison_chart(sprints, output_path):
    """Create chart comparing actual allocation to Q1 plan targets"""
    if not sprints:
        print("No sprint data to visualize")
        return

    # Calculate averages across all sprints
    avg_job_interview = np.mean([s['job_interview_pct'] for s in sprints])
    avg_content = np.mean([s['content_pct'] for s in sprints])
    avg_project = np.mean([s['project_pct'] for s in sprints])
    avg_biz = np.mean([s['biz_pct'] for s in sprints])

    domains = ['Job/Interview/\nSkills', 'Content', 'Personal\nProject', 'Business/\nCorp']
    actual = [avg_job_interview, avg_content, avg_project, avg_biz]
    target_min = [Q1_TARGETS['Job/Interview/Skills'][0], Q1_TARGETS['Content'][0],
                  Q1_TARGETS['Personal Project'][0], Q1_TARGETS['Business/Corp'][0]]
    target_max = [Q1_TARGETS['Job/Interview/Skills'][1], Q1_TARGETS['Content'][1],
                  Q1_TARGETS['Personal Project'][1], Q1_TARGETS['Business/Corp'][1]]
    target_avg = [(min_val + max_val) / 2 for min_val, max_val in zip(target_min, target_max)]

    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(domains))
    width = 0.35

    bars1 = ax.bar(x - width/2, actual, width, label='Actual Average', color='steelblue', alpha=0.8)
    bars2 = ax.bar(x + width/2, target_avg, width, label='Target Average', color='green', alpha=0.8)

    # Add target range as error bars
    target_range_lower = [target_avg[i] - target_min[i] for i in range(len(domains))]
    target_range_upper = [target_max[i] - target_avg[i] for i in range(len(domains))]
    ax.errorbar(x + width/2, target_avg, yerr=[target_range_lower, target_range_upper],
                fmt='none', color='green', capsize=5, capthick=2, label='Target Range')

    # Add value labels
    for i, (bar, val) in enumerate(zip(bars1, actual)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
               f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')

    for i, (bar, val) in enumerate(zip(bars2, target_avg)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
               f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')

    ax.set_xlabel('Domain', fontweight='bold')
    ax.set_ylabel('Percentage (%)', fontweight='bold')
    ax.set_title('Average Sprint Allocation vs Q1 Plan Targets', fontweight='bold', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(domains)
    ax.set_ylim(0, max(max(actual), max(target_max)) + 10)
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Created target comparison chart: {output_path}")

def create_domain_trend_chart(sprints, output_path):
    """Create line chart showing domain allocation trends over sprints"""
    if not sprints or len(sprints) < 2:
        print("Need at least 2 sprints for trend chart")
        return

    sprint_ids = [s['id'] for s in sprints]
    job_interview_pct = [s['job_interview_pct'] for s in sprints]
    content_pct = [s['content_pct'] for s in sprints]
    project_pct = [s['project_pct'] for s in sprints]
    biz_pct = [s['biz_pct'] for s in sprints]

    fig, ax = plt.subplots(figsize=(12, 7))

    x = range(len(sprint_ids))

    ax.plot(x, job_interview_pct, marker='o', linewidth=2, markersize=8,
            label='Job/Interview/Skills', color='#2E86AB')
    ax.plot(x, content_pct, marker='s', linewidth=2, markersize=8,
            label='Content', color='#A23B72')
    ax.plot(x, project_pct, marker='^', linewidth=2, markersize=8,
            label='Personal Project', color='#F18F01')
    ax.plot(x, biz_pct, marker='d', linewidth=2, markersize=8,
            label='Business/Corp', color='#C73E1D')

    # Add target ranges as horizontal bands
    ax.axhspan(Q1_TARGETS['Job/Interview/Skills'][0], Q1_TARGETS['Job/Interview/Skills'][1],
               alpha=0.1, color='blue', label='Job/Interview Target')
    ax.axhspan(Q1_TARGETS['Content'][0], Q1_TARGETS['Content'][1],
               alpha=0.1, color='purple', label='Content Target')
    ax.axhspan(Q1_TARGETS['Personal Project'][0], Q1_TARGETS['Personal Project'][1],
               alpha=0.1, color='orange', label='Project Target')
    ax.axhspan(Q1_TARGETS['Business/Corp'][0], Q1_TARGETS['Business/Corp'][1],
               alpha=0.1, color='red', label='Business Target')

    ax.set_xlabel('Sprint', fontweight='bold')
    ax.set_ylabel('Percentage (%)', fontweight='bold')
    ax.set_title('Domain Allocation Trends Over Sprints', fontweight='bold', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(sprint_ids, rotation=45, ha='right')
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Created domain trend chart: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Visualize sprint metrics')
    parser.add_argument('--quarter', help='Filter by quarter (e.g., 2026-Q1)')
    args = parser.parse_args()

    # Ensure trends directory exists
    TRENDS_DIR.mkdir(parents=True, exist_ok=True)

    # Load sprint metrics
    sprints = load_sprint_metrics()

    if not sprints:
        print("No sprint metrics found. Make sure sprint_metrics.csv has data.")
        return

    # Filter by quarter if specified
    if args.quarter:
        sprints = [s for s in sprints if s['quarter'] == args.quarter]
        if not sprints:
            print(f"No sprints found for quarter {args.quarter}")
            return

    print(f"Loaded {len(sprints)} sprint(s)")

    # Generate charts
    create_sprint_count_chart(sprints, TRENDS_DIR / 'sprint_counts.png')
    create_allocation_chart(sprints, TRENDS_DIR / 'sprint_allocation.png')
    create_target_comparison_chart(sprints, TRENDS_DIR / 'sprint_target_comparison.png')

    if len(sprints) >= 2:
        create_domain_trend_chart(sprints, TRENDS_DIR / 'sprint_domain_trends.png')

    print(f"\nCharts saved to: {TRENDS_DIR}")
    print("- sprint_counts.png - Deep sprints per sprint")
    print("- sprint_allocation.png - Domain allocation percentages (stacked)")
    print("- sprint_target_comparison.png - Average allocation vs Q1 targets")
    if len(sprints) >= 2:
        print("- sprint_domain_trends.png - Domain allocation trends over time")

if __name__ == '__main__':
    main()










