from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app import app, db

def migrate_database():
    with app.app_context():
        # Drop existing tables (CAUTION: This will delete all existing data)
        db.drop_all()
        
        # Recreate all tables with new schema
        db.create_all()
        
        print("Database migration completed successfully.")

if __name__ == '__main__':
    migrate_database()