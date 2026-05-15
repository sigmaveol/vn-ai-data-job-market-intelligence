"""Reusable Plotly chart components for the VN Job Market dashboard."""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils.style import PLOTLY_LAYOUT, PLOTLY_CONFIG, COLORWAY, C, SEQUENTIAL


def _base(fig, height=340, title='', margin=None):
    kw = dict(**PLOTLY_LAYOUT, height=height)
    if title:
        kw['title'] = dict(text=title, font_size=14, font_color=C['text'])
    if margin:
        kw['margin'] = margin
    fig.update_layout(**kw)
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def hbar(df, x_col, y_col, title='', height=340, color=None, text_fmt=',.0f') -> go.Figure:
    """Horizontal bar chart — good for rankings."""
    df = df.sort_values(x_col)
    colors = [color or C['accent']] * len(df) if isinstance(color, str) or color is None else color
    fig = go.Figure(go.Bar(
        x=df[x_col], y=df[y_col], orientation='h',
        marker_color=colors,
        text=df[x_col].map(lambda v: f'{v:{text_fmt}}'),
        textposition='auto',
        textfont_color=C['text'],
        hovertemplate='<b>%{y}</b><br>%{x:,.1f}<extra></extra>',
    ))
    return _base(fig, height, title, margin=dict(t=40, b=40, l=170, r=40))


def bar_chart(df, x_col, y_col, title='', height=340, color=None, orientation='h') -> go.Figure:
    """Compatibility wrapper for simple bar charts."""
    if orientation == 'h':
        return hbar(df, x_col, y_col, title=title, height=height, color=color)
    return vbar(df, x_col, y_col, title=title, height=height, color=color or C['accent'])


def vbar(df, x_col, y_col, title='', height=320, color=C['accent']) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=df[x_col], y=df[y_col],
        marker_color=color,
        text=df[y_col].map(lambda v: f'{v:,.0f}'),
        textposition='outside',
        textfont_color=C['muted'],
        hovertemplate='<b>%{x}</b><br>%{y:,.1f}<extra></extra>',
    ))
    return _base(fig, height, title)


def pie_donut(labels, values, title='', height=300) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.45,
        textinfo='label+percent',
        textfont_size=11,
        marker_colors=COLORWAY,
        hovertemplate='<b>%{label}</b><br>%{value:,} tin (%{percent})<extra></extra>',
    ))
    layout = dict(**PLOTLY_LAYOUT)
    layout.update(
        height=height,
        showlegend=True,
        legend=dict(orientation='h', y=-0.15, font_color=C['muted']),
        margin=dict(t=30, b=60, l=10, r=10),
    )
    fig.update_layout(**layout)
    return fig


def pie_chart(labels, values, title='', height=300) -> go.Figure:
    """Compatibility wrapper for donut/pie charts."""
    return pie_donut(labels, values, title=title, height=height)


def histogram_chart(series: pd.Series, title='', height=320, bins=35, color=C['accent']) -> go.Figure:
    fig = go.Figure(go.Histogram(
        x=series.dropna(), nbinsx=bins,
        marker_color=color, opacity=0.85,
        hovertemplate='Khoảng: $%{x}<br>Số tin: %{y}<extra></extra>',
    ))
    return _base(fig, height, title)


def boxplot_chart(df, x_col, y_col, title='', height=340, order=None) -> go.Figure:
    cats = order or sorted(df[x_col].dropna().unique().tolist())
    colors = dict(zip(cats, COLORWAY))
    traces = []
    for cat in cats:
        sub = df[df[x_col] == cat][y_col].dropna()
        if len(sub) < 3:
            continue
        traces.append(go.Box(
            y=sub, name=str(cat),
            marker_color=colors.get(cat, C['accent']),
            boxpoints='outliers', jitter=0.3, pointpos=0,
            hovertemplate=f'<b>{cat}</b><br>%{{y:,.0f}} USD<extra></extra>',
        ))
    fig = go.Figure(traces)
    return _base(fig, height, title)


def box_chart(df, x_col, y_col, title='', height=340, order=None) -> go.Figure:
    """Compatibility wrapper for boxplot charts."""
    return boxplot_chart(df, x_col, y_col, title=title, height=height, order=order)


def line_chart(df, x_col, y_cols, title='', height=340) -> go.Figure:
    if isinstance(y_cols, str):
        y_cols = [y_cols]
    fig = go.Figure()
    for i, yc in enumerate(y_cols):
        fig.add_trace(go.Scatter(
            x=df[x_col], y=df[yc], name=yc, mode='lines+markers',
            line=dict(color=COLORWAY[i % len(COLORWAY)], width=2.5),
            marker=dict(size=6),
            hovertemplate=f'<b>{yc}</b><br>%{{x}}: %{{y:,}}<extra></extra>',
        ))
    return _base(fig, height, title)


def heatmap_chart(matrix_df: pd.DataFrame, title='', height=380) -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=matrix_df.values,
        x=matrix_df.columns.tolist(),
        y=matrix_df.index.tolist(),
        colorscale=SEQUENTIAL,
        text=matrix_df.values,
        texttemplate='%{text}',
        textfont_size=10,
        showscale=True,
        hovertemplate='<b>%{y}</b> × <b>%{x}</b><br>%{z} lần<extra></extra>',
    ))
    layout = dict(**PLOTLY_LAYOUT)
    layout.update(
        height=height,
        margin=dict(t=40, b=80, l=120, r=20),
        xaxis_tickangle=-35,
    )
    fig.update_layout(**layout)
    if title:
        fig.update_layout(title=dict(text=title, font_size=14))
    return fig


def grouped_bar(categories, groups: dict, title='', height=340) -> go.Figure:
    """Multiple series bar chart — groups is {name: [values]}."""
    fig = go.Figure()
    for i, (name, vals) in enumerate(groups.items()):
        fig.add_trace(go.Bar(
            x=categories, y=vals, name=name,
            marker_color=COLORWAY[i % len(COLORWAY)],
            hovertemplate=f'<b>{name}</b><br>%{{x}}: %{{y:,.0f}}<extra></extra>',
        ))
    fig.update_layout(**PLOTLY_LAYOUT, barmode='group', height=height)
    if title:
        fig.update_layout(title=dict(text=title, font_size=14))
    return fig


def skill_tag_cloud_html(skill_counts: list[tuple], max_count: int = None) -> str:
    if not skill_counts:
        return ''
    if max_count is None:
        max_count = skill_counts[0][1]
    min_count = skill_counts[-1][1]
    tags = []
    for sk, cnt in skill_counts:
        ratio = (cnt - min_count) / max(max_count - min_count, 1)
        size = round(12 + ratio * 14)
        hue = round(200 + ratio * 60)
        opacity = 0.5 + ratio * 0.5
        tags.append(
            f'<span class="skill-tag" title="{cnt} lần" '
            f'style="font-size:{size}px;opacity:{opacity};'
            f'border-color:hsl({hue},60%,45%);color:hsl({hue},80%,75%)">'
            f'{sk}</span>'
        )
    return '<div style="display:flex;flex-wrap:wrap;gap:4px;padding:8px 0">' + ''.join(tags) + '</div>'
