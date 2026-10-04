"""
Plotly chart auto-generator.
Picks the most appropriate chart type based on the DataFrame structure.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def auto_chart(df: pd.DataFrame, question: str = "") -> dict | None:
    """
    Attempt to generate a Plotly figure from *df*.
    Returns the figure serialised as a dict (for JSON transport), or None.
    """
    if df is None or df.empty:
        return None

    try:
        fig = _pick_chart(df, question)
        if fig is None:
            return None
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=40, b=20),
        )
        return fig.to_dict()
    except Exception:  # noqa: BLE001
        return None


def _pick_chart(df: pd.DataFrame, question: str) -> go.Figure | None:
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(exclude="number").columns.tolist()

    if len(df.columns) == 1:
        # Single column – value card, no chart needed
        return None

    # Exactly 2 columns: one categorical, one numeric → bar chart
    if len(text_cols) == 1 and len(numeric_cols) == 1:
        x_col = text_cols[0]
        y_col = numeric_cols[0]
        if len(df) <= 2:
            return px.pie(df, names=x_col, values=y_col, title=y_col)
        return px.bar(df, x=x_col, y=y_col, title=y_col)

    # Time-series detection
    time_col = _detect_time_col(df)
    if time_col and numeric_cols:
        y_col = numeric_cols[0]
        fig = px.line(df, x=time_col, y=y_col, title=y_col, markers=True)
        return fig

    # Multiple numeric columns with one category → grouped bar
    if text_cols and len(numeric_cols) >= 2:
        return px.bar(
            df,
            x=text_cols[0],
            y=numeric_cols[0],
            title=numeric_cols[0],
        )

    # Scatter for two numerics
    if len(numeric_cols) >= 2:
        return px.scatter(df, x=numeric_cols[0], y=numeric_cols[1])

    return None


def _detect_time_col(df: pd.DataFrame) -> str | None:
    """Heuristically find a date/time column."""
    for col in df.columns:
        if df[col].dtype == "object":
            sample = df[col].dropna().head(5)
            if sample.str.match(r"\d{4}-\d{2}").any():
                return col
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col
    return None
