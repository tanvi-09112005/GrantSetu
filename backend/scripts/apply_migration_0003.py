from app.db import pool

def run():
    with open("migrations/0003_fcra_status.sql", "r", encoding="utf-8") as f:
        sql = f.read()
    pool.execute(sql)
    pool.execute("update grants set is_foreign_contribution = true where funder_type = 'international'")
    print("Migration 0003 applied successfully!")

if __name__ == "__main__":
    run()
