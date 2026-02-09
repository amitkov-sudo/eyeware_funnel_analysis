import sqlite3
import pandas as pd

DB_NAME = "warby_parker.db"

tables = {
    "survey": "survey.csv",
    "quiz": "quiz.csv",
    "home_try_on": "home_try_on.csv",
    "purchase": "purchase.csv",
}

conn = sqlite3.connect(DB_NAME)

for table, csv_file in tables.items():
    df = pd.read_csv(csv_file)
    df.to_sql(table, conn, if_exists="replace", index=False)

# optional: indexes (nice for joins)
conn.execute("CREATE INDEX IF NOT EXISTS idx_quiz_user_id ON quiz(user_id);")
conn.execute("CREATE INDEX IF NOT EXISTS idx_home_user_id ON home_try_on(user_id);")
conn.execute("CREATE INDEX IF NOT EXISTS idx_purchase_user_id ON purchase(user_id);")
conn.execute("CREATE INDEX IF NOT EXISTS idx_survey_user_id ON survey(user_id);")

conn.commit()
conn.close()

print(f"Created {DB_NAME}")

