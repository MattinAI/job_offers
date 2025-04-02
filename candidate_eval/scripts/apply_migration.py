# scripts/apply_migration.py
import os
import sys
import subprocess

def apply_migration():
    """Apply database migrations using Alembic"""
    try:
        # Change to the app directory where alembic.ini is located
        os.chdir("app")
        
        # Run alembic command to apply migrations
        subprocess.run(["alembic", "upgrade", "head"])
        print("Migrations applied successfully!")
        
        # Change back to the original directory
        os.chdir("..")
    except Exception as e:
        print(f"Error applying migrations: {e}")

if __name__ == "__main__":
    apply_migration()