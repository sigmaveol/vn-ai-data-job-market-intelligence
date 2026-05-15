"""Shared chart styling: theme, color palette, font settings."""


def apply_default_style(fig):
    """Apply project-wide Plotly layout theme to a figure."""
    # TODO Phase 5:
    #   - fig.update_layout(template=CHART_THEME, font_family='...')
    #   - set consistent margins, background, title font size
    raise NotImplementedError


def get_color_sequence(n: int) -> list[str]:
    """Return n colors from the project color palette (cycling if needed)."""
    # TODO Phase 5: cycle through COLOR_PALETTE from config.py
    raise NotImplementedError


def save_chart(fig, filename: str, output_dir=None) -> str:
    """Save Plotly figure to CHARTS_DIR as PNG and HTML. Returns file path."""
    # TODO Phase 5: fig.write_image() + fig.write_html()
    raise NotImplementedError
