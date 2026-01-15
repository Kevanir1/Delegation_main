"""
Migration script to update database schema
Run this script to add missing columns and tables to existing database
"""
from flask import Flask
from models import db
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/delegations_db')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def run_migration():
    """Run database migration"""
    with app.app_context():
        print("[MIGRATION] Starting database migration...")
        
        try:
            # Read migration SQL file
            with open('migration.sql', 'r', encoding='utf-8') as f:
                migration_sql = f.read()
            
            # Execute migration
            with db.engine.connect() as connection:
                connection.execute(text(migration_sql))
                connection.commit()
            
            print("[MIGRATION] ✓ Migration completed successfully")
            
        except Exception as e:
            print(f"[MIGRATION] ✗ Migration failed: {e}")
            raise

if __name__ == '__main__':
    run_migration()
