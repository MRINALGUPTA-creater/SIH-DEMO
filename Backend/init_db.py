import os
import sys
import re
from dotenv import load_dotenv

load_dotenv()

def init_mysql():
    host = os.getenv("MYSQL_HOST", "localhost")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "bis_compliance")

    print(f"Connecting to MySQL server at {host}:{port} as user '{user}'...")

    try:
        import pymysql
    except ImportError:
        print("pymysql is required. Run: pip install pymysql")
        sys.exit(1)

    # 1. Connect without database to ensure DB exists
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            autocommit=True
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database};")
            print(f"Database '{database}' ensured.")
        conn.close()
    except Exception as e:
        print(f"Could not connect to MySQL server: {e}")
        print("Please check that MySQL server is running and credentials in .env are correct.")
        sys.exit(1)

    # 2. Connect to database and execute SQL file
    sql_file = os.path.join(os.path.dirname(__file__), "..", "bis_compliance.sql")
    if not os.path.exists(sql_file):
        sql_file = os.path.join(os.path.dirname(__file__), "bis_compliance.sql")

    if not os.path.exists(sql_file):
        print(f"SQL file not found at {sql_file}")
        sys.exit(1)

    print(f"Loading schema from {sql_file}...")
    with open(sql_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Split statements
    statements = [s.strip() for s in sql_content.split(";") if s.strip()]

    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        autocommit=True
    )

    success_count = 0
    with conn.cursor() as cursor:
        for stmt in statements:
            if not stmt:
                continue
            try:
                cursor.execute(stmt)
                success_count += 1
            except Exception as e:
                # Ignore duplicate or already exists errors gracefully
                if "already exists" in str(e) or "Duplicate entry" in str(e):
                    continue
                print(f"Notice on statement: {e}")

    conn.close()
    print(f"Successfully executed {success_count} SQL statements into '{database}'.")
    print("Database initialization complete!")

if __name__ == "__main__":
    init_mysql()
