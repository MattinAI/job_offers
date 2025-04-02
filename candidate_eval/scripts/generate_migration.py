# scripts/generate_migration.py
import os
import sys
import subprocess

def generate_migration():
    """Generate a migration for database changes"""
    try:
        # Change to the app directory where alembic.ini is located
        os.chdir("app")
        
        # Get a message for the migration
        message = input("Enter a message for the migration (e.g., 'add file path to job offers'): ")
        if not message:
            message = "database changes"
        
        # Run alembic command to generate a migration
        subprocess.run(["alembic", "revision", "--autogenerate", "-m", message])
        print("Migration generated successfully!")
        
        # Change back to the original directory
        os.chdir("..")
    except Exception as e:
        print(f"Error generating migration: {e}")

if __name__ == "__main__":
    generate_migration()