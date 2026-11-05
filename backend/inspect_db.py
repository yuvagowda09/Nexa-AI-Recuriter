
from sqlalchemy import text
from sqlalchemy import inspect, text
from database import engine

inspector = inspect(engine)
tables = inspector.get_table_names()

print("\n=== DATABASE TABLES ===")

for table in tables:
    print(f"\nTable: {table}")

    columns = inspector.get_columns(table)
    print("Columns:", ", ".join(column["name"] for column in columns))

    with engine.connect() as connection:
        count = connection.execute(
            text(f'SELECT COUNT(*) FROM "{table}"')
        ).scalar_one()

    print(f"Record count: {count}")

print("\n=== INSPECTION COMPLETE ===")


with engine.connect() as connection:
    print("\n=== ORGANIZATIONS ===")
    rows = connection.execute(
        text("SELECT id, name FROM organizations ORDER BY id")
    ).fetchall()

    for row in rows:
        print(row)

    print("\n=== JOBS ===")
    rows = connection.execute(
        text(
            "SELECT id, organization_id, title "
            "FROM jobs ORDER BY id"
        )
    ).fetchall()

    for row in rows:
        print(row)
