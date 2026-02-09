# =====================================
# A/B Test Analysis
# File: analysis_ab_test.py
# Author: Aleks T. Mitkov
# =====================================
#
#
#
# Main Purpose:
#   1) Quantify the effect of the Home Try-On A/B test on purchase behavior:
#        Variant A: 3 pairs  vs  Variant B: 5 pairs
#   2) Summarize purchase conversion rates by variant and visualize results.
#
#
#
# Outputs:
#   - outputs/figures/ab_test_purchase_rate.png
#   - outputs/tables/ab_test_summary.csv
#
# Important Notes:
#   - Static image export requires: pip install -U kaleido
#

import sqlite3
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# -----------------------------
# Configuration
# -----------------------------
DB_PATH = "warby_parker.db"
FIGURES_DIR = Path("outputs/figures")
TABLES_DIR = Path("outputs/tables")
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR.mkdir(parents=True, exist_ok=True)

AB_TEST_FIG_PATH = FIGURES_DIR / "ab_test_purchase_rate.png"
AB_TEST_TABLE_PATH = TABLES_DIR / "ab_test_summary.csv"


def build_user_funnel(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Build a user-level funnel table:
      - One row per quiz taker
      - Flags for home try-on and purchase
      - Includes number_of_pairs when home try-on occurred
    """
    return pd.read_sql_query(
        """
        WITH funnel AS (
          SELECT
            q.user_id,
            CASE WHEN h.user_id IS NOT NULL THEN 1 ELSE 0 END AS is_home_try_on,
            h.number_of_pairs,
            CASE WHEN p.user_id IS NOT NULL THEN 1 ELSE 0 END AS is_purchase
          FROM quiz q
          LEFT JOIN home_try_on h ON q.user_id = h.user_id
          LEFT JOIN purchase p ON q.user_id = p.user_id
        )
        SELECT * FROM funnel;
        """,
        conn,
    )


def summarize_ab_test(df_funnel: pd.DataFrame) -> pd.DataFrame:
    """
    Compute A/B test summary for Home Try-On users only:
      - users: number of users receiving each variant
      - purchases: number of purchasers within each variant
      - purchase_rate: purchases / users
    """
    ab = (
        df_funnel[df_funnel["is_home_try_on"] == 1]
        .groupby("number_of_pairs", dropna=False)
        .agg(
            users=("user_id", "count"),
            purchases=("is_purchase", "sum"),
        )
        .reset_index()
    )

    ab["purchase_rate"] = ab["purchases"] / ab["users"]
    ab = ab.sort_values("number_of_pairs")

    return ab


def plot_ab_test(ab: pd.DataFrame):
    """
    Create a bar chart showing purchase conversion rate by Home Try-On variant.
    """
    x = ab["number_of_pairs"].astype(str)
    y = ab["purchase_rate"]

    plt.figure(figsize=(8, 5))

    colors = []
    for s in x:
        if "3" in s:
            colors.append("deepskyblue")
        elif "5" in s:
            colors.append("lightsalmon")
        else:
            colors.append("tan")

    plt.bar(
        x,
        y,
        color=colors,
        edgecolor="wheat",
        alpha=0.65,
    )

    plt.xlabel("Number of Pairs Sent")
    plt.ylabel("Purchase Conversion Rate")
    plt.title("Purchase Rate by Home Try-On Variant")

    for i, rate in enumerate(y):
        plt.text(
            i,
            rate,
            f"{rate:.1%}",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    plt.tight_layout()
    return plt.gcf()


def main() -> None:
    """
    Run the A/B test analysis and save outputs to disk.
    """
    conn = sqlite3.connect(DB_PATH)

    try:
        # -----------------------------
        # Build funnel + summarize A/B test
        # -----------------------------
        df_funnel = build_user_funnel(conn)
        ab = summarize_ab_test(df_funnel)

        # -----------------------------
        # Save summary table
        # -----------------------------
        ab.to_csv(AB_TEST_TABLE_PATH, index=False)

        # -----------------------------
        # Plot + save figure
        # -----------------------------
        fig = plot_ab_test(ab)
        fig.savefig(AB_TEST_FIG_PATH, dpi=300)
        plt.close(fig)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
