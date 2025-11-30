import os 
import psycopg2

DB_CONFIG = {
    "host": "db",
    "user": os.getenv("DB_USER"),
    "database": os.getenv("DB_NAME"),
    "password": os.getenv("DB_PASSWORD")
}
    
BASE_DIR = "/app"

def apply_migrations():

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        migration_file = os.path.join(os.path.dirname(__file__), BASE_DIR, 'migrations','001_create_users_table.sql')
        with open(migration_file, 'r') as f:
            sql_script = f.read()
        
        print("Applying migration: 001_create_users_table.sql")
        cursor.execute(sql_script)
        conn.commit()
        print("Migration applied successfully.")
    except Exception as e:
        print(f"Error applying migration: {e}")
        raise
    finally:
        if conn:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    apply_migrations()

