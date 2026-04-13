
import os
from sqlalchemy import text
from app.database import SessionLocal, engine
from app import models
from dotenv import load_dotenv

load_dotenv()

def fix():
    db = SessionLocal()
    try:
        print("Starting manual migration...")
        columns = [
            ("site_config", "why_title", "VARCHAR", "'Pourquoi rider avec nous ?'"),
            ("site_config", "why_description", "TEXT", "''"),
            ("site_config", "why_image_filename", "VARCHAR", "NULL"),
            ("site_config", "why_feature1_icon", "VARCHAR", "'👨‍🏫'"),
            ("site_config", "why_feature1_title", "VARCHAR", "'Moniteurs Diplômés d\'État'"),
            ("site_config", "why_feature1_desc", "VARCHAR", "''"),
            ("site_config", "why_feature2_icon", "VARCHAR", "'🏄'"),
            ("site_config", "why_feature2_title", "VARCHAR", "'Matériel Premium'"),
            ("site_config", "why_feature2_desc", "VARCHAR", "''"),
            ("site_config", "why_feature3_icon", "VARCHAR", "'🌊'"),
            ("site_config", "why_feature3_title", "VARCHAR", "'Choix des Spots'"),
            ("site_config", "why_feature3_desc", "VARCHAR", "''"),
        ]
        
        for table, col, col_type, default in columns:
            try:
                print(f"Adding {col} to {table}...")
                db.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type} DEFAULT {default}"))
                db.commit()
                print(f"Success: {col}")
            except Exception as e:
                db.rollback()
                print(f"Failed to add {col}: {e}")
                
        print("Migration complete.")
    finally:
        db.close()

if __name__ == "__main__":
    fix()
