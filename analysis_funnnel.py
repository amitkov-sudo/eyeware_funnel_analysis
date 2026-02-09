# =====================================
# Funnel Analysis
# File: analysis_funnel.py
# Author: Aleks T. Mitkov
# =====================================
#
#
#
# Main Purpose:
#   1) Quantify end-to-end conversion through the core funnel:
#        Quiz → Home Try-On → Purchase
#   2) Quantify drop-off within the onboarding flow:
#        Survey Question 1 → ... → Survey Question 5
#
#
#
# Outputs:
#   - outputs/figures/conversion_funnel.png
#   - outputs/figures/survey_completion_funnel.png
#
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
OUTPUT_DIR = Path("outputs/figures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CONVERSION_FUNNEL_PATH = OUTPUT_DIR / "conversion_funnel.png"
SURVEY_FUNNEL_PATH = OUTPUT_DIR / "survey_completion_funnel.png"


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


def compute_funnel_metrics(df_funnel: pd.DataFrame) -> dict:
    """
    Compute counts and conversion rates for the core funnel.
    Returns a dict suitable for reporting and plotting.
    """
    n_quiz = int(len(df_funnel))
    n_try = int(df_funnel["is_home_try_on"].sum()) if n_quiz else 0
    n_buy = int(df_funnel["is_purchase"].sum()) if n_quiz else 0

    quiz_to_try = (n_try / n_quiz) if n_quiz else 0
    try_to_buy = (n_buy / n_try) if n_try else 0
    quiz_to_buy = (n_buy / n_quiz) if n_quiz else 0

    return {
        "counts": {"quiz": n_quiz, "home_try_on": n_try, "purchase": n_buy},
        "rates": {
            "quiz_to_try": quiz_to_try,
            "try_to_buy": try_to_buy,
            "quiz_to_buy": quiz_to_buy,
        },
    }


def plot_conversion_funnel(metrics: dict):
    """
    Create the conversion funnel figure (Quiz → Home Try-On → Purchase).
    """
    counts = metrics["counts"]
    data = dict(
        number=[counts["quiz"], counts["home_try_on"], counts["purchase"]],
        stage=["Quiz", "Home Try-On", "Purchase"],
    )

    fig = px.funnel(
        data,
        x="number",
        y="stage",
        title="Warby Parker User Conversion Funnel",
    )

    fig.update_traces(
        marker=dict(
            color=["deepskyblue", "lightsalmon", "tan"],
            line=dict(color="wheat", width=1),
        ),
        textfont=dict(family="Old Standard TT, serif", size=13, color="black"),
        opacity=0.65,
        textinfo="value+percent initial",
    )

    fig.update_layout(
        width=900,
        height=500,
        template="simple_white",
        title=dict(x=0.5, xanchor="center"),
    )

    return fig


def build_survey_funnel(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Build a survey completion view:
      - users_answered = distinct users who answered each question
    """
    return pd.read_sql_query(
        """
        SELECT
          s.question,
          COUNT(DISTINCT s.user_id) AS users_answered
        FROM survey s
        GROUP BY 1
        ORDER BY 2 DESC;
        """,
        conn,
    )


def plot_survey_funnel(df_quiz_funnel: pd.DataFrame):
    """
    Create the survey completion funnel figure (top 5 questions by responses).
    """
    stages = [
        "What are you looking for?",
        "What's your fit?",
        "Which shapes do you like?",
        "Which colors do you like?",
        "When was your last eye exam?",
    ]

    q1 = int(df_quiz_funnel.iloc[0]["users_answered"])
    q2 = int(df_quiz_funnel.iloc[1]["users_answered"])
    q3 = int(df_quiz_funnel.iloc[2]["users_answered"])
    q4 = int(df_quiz_funnel.iloc[3]["users_answered"])
    q5 = int(df_quiz_funnel.iloc[4]["users_answered"])

    data = dict(number=[q1, q2, q3, q4, q5], stage=stages)

    fig = px.funnel(
        data,
        x="number",
        y="stage",
        title="Survey Completion Funnel",
    )

    fig.update_traces(
        marker=dict(
            color=["deepskyblue", "steelblue", "darkseagreen", "lightsalmon", "tan"],
            line=dict(color="wheat", width=1),
        ),
        textfont=dict(family="Old Standard TT, serif", size=13, color="black"),
        opacity=0.65,
        textinfo="value+percent initial",
    )

    fig.update_layout(
        width=900,
        height=500,
        template="simple_white",
        title=dict(x=0.5, xanchor="center"),
    )

    return fig


def main() -> None:
    """
    Run both funnel analyses and save outputs to disk.
    """
    conn = sqlite3.connect(DB_PATH)

    try:
        # -----------------------------
        # Funnel 1: Core conversion
        # -----------------------------
        df_funnel = build_user_funnel(conn)
        metrics = compute_funnel_metrics(df_funnel)

        df_conversion_rates = pd.DataFrame(
            {
                "metric": ["Quiz → Home Try-On", "Home Try-On → Purchase", "Quiz → Purchase"],
                "rate": [
                    metrics["rates"]["quiz_to_try"],
                    metrics["rates"]["try_to_buy"],
                    metrics["rates"]["quiz_to_buy"],
                ],
            }
        )

        fig_conversion = plot_conversion_funnel(metrics)

        # -----------------------------
        # Funnel 2: Survey completion
        # -----------------------------
        df_quiz_funnel = build_survey_funnel(conn)
        fig_survey = plot_survey_funnel(df_quiz_funnel)

        # -----------------------------
        # Save output
        # -----------------------------
        fig_conversion.write_image(CONVERSION_FUNNEL_PATH)
        fig_survey.write_image(SURVEY_FUNNEL_PATH)
        tables_dir = Path("outputs/tables")
        tables_dir.mkdir(parents=True, exist_ok=True)
        df_conversion_rates.to_csv(tables_dir / "conversion_rates.csv", index=False)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
