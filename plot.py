#!/usr/bin/python3
# Display commit statistics as pie charts with plotly.

import sys
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def main():
    filename = sys.argv[1] if len(sys.argv) > 1 else "data.csv"
    df = pd.read_csv(filename)
    fig = make_subplots(rows=1, cols=3, specs=[[{"type": "domain"}]*3])
    fig.add_trace(go.Pie(labels=df.name, values=df.commits, title=f"Commits {sum(df.commits)}", hole=0.3), row=1, col=1)
    fig.add_trace(go.Pie(labels=df.name, values=df.added, title="Added Lines", hole=0.3), row=1, col=2)
    fig.add_trace(go.Pie(labels=df.name, values=df.deleted, title="Deleted Lines", hole=0.3), row=1, col=3)
    fig.update_traces(hoverinfo='label+value+percent', textinfo='label', textposition='inside', insidetextorientation='radial')
    fig.update_layout(height=800, width=1400, title_text="Commit Metrics", uniformtext_minsize=12, uniformtext_mode='hide')
    fig.show()

if __name__ == '__main__':
    main()
