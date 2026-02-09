# =====================================
# Style Preference Analysis
# File: analysis_style_preference.py
# Author: Aleks T. Mitkov
# =====================================
#
#
#
# Main Purpose:
#   1) Quantify purchase conversion rate by Style Quiz preference:
#        Men's Styles vs Women's Styles vs "I'm not sure. Let's skip it."
# 
#
#
# Outputs:
#   - outputs/figures/conversion_by_style_preference.png
#   - outputs/tables/conversion_by_style_preference.csv
#
#
# Important Notes:
#   - Static image export requires: pip install -U kaleido
#

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px


# -----------------------------
# Configuration
# -----------------------------
DB_PATH = "warby_parker.db"

FIGURES_DIR = Path("outputs/figures")
TABLES_DIR = Path("outputs/tables")
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR.mkdir(parents=True, exist_ok=True)

FIG_PATH = FIGURES_DIR / "conversion_by_style_preference.png"
TABLE_PATH = TABLES_DIR / "conversion_by_style_preference.csv"


def compute_style_conversion(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Compute user-level purchase conversion by declared style preference in the quiz.
    Output columns:
      - style
      - users
      - purchasers
      - conversion_rate
    """
    return pd.read_sql_query(
        """
        WITH purchase_flag AS (
          SELECT DISTINCT user_id
          FROM purchase
        )
        SELECT
          q.style,
          COUNT(*) AS users,
          SUM(CASE WHEN pf.user_id IS NOT NULL THEN 1 ELSE 0 END) AS purchasers,
          ROUND(
            1.0 * SUM(CASE WHEN pf.user_id IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*),
            4
          ) AS conversion_rate
        FROM quiz q
        LEFT JOIN purchase_flag pf
          ON q.user_id = pf.user_id
        GROUP BY q.style
        ORDER BY conversion_rate DESC;
        """,
        conn,
    )


def plot_style_conversion(df_style_conv: pd.DataFrame):
    """
    Create a bar chart for conversion rate by style preference with categorical colors:
      - "not sure" → tan
      - Women's → lightsalmon
      - Men's → deepskyblue
    """
    fig = px.bar(
        df_style_conv,
        x="style",
        y="conversion_rate",
        text=df_style_conv["conversion_rate"].map(lambda x: f"{x:.1%}"),
        title="Purchase Conversion Rate by Style Preference",
    )

    fig.update_traces(
        marker=dict(
            color=[
                "tan" if "not sure" in str(s).lower()
                else "lightsalmon" if str(s).lower().startswith("women")
                else "deepskyblue"
                for s in df_style_conv["style"]
            ],
            line=dict(color="wheat", width=1),
        )
    )

    fig.update_layout(
        width=900,
        height=500,
        margin=dict(l=80, r=40, t=80, b=80),
        template="simple_white",
        title=dict(x=0.5, xanchor="center"),
        yaxis=dict(
            tickformat=".0%",
            title="Conversion Rate",
            showgrid=True,
            gridcolor="rgba(0,0,0,0.05)",
        ),
        xaxis=dict(
            title="Style Preference",
            showgrid=False,
        ),
    )

    return fig


def main() -> None:
    """
    Run style preference conversion analysis and save outputs to disk.
    """
    conn = sqlite3.connect(DB_PATH)

    try:
        df_style_conv = compute_style_conversion(conn)

        df_style_conv.to_csv(TABLE_PATH, index=False)

        fig = plot_style_conversion(df_style_conv)
        fig.write_image(FIG_PATH)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
