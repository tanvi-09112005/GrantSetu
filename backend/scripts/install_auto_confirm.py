from app.db import pool

sql = """
CREATE OR REPLACE FUNCTION auth.auto_confirm_users()
RETURNS trigger AS $$
BEGIN
  IF NEW.email_confirmed_at IS NULL THEN
    NEW.email_confirmed_at := now();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'tr_auto_confirm_users'
  ) THEN
    CREATE TRIGGER tr_auto_confirm_users
    BEFORE INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION auth.auto_confirm_users();
  END IF;
END $$;
"""

pool.execute(sql)
print("Auto-confirm trigger permanently installed on auth.users!")
