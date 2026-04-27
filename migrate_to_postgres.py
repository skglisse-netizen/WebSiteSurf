import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Ajout du chemin parent pour importer l'application
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import models
from app.auth import get_password_hash

def migrate():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url or not db_url.startswith("postgresql"):
        print("ERREUR : DATABASE_URL n'est pas configuré pour PostgreSQL.")
        print("Vérifiez votre fichier .env.")
        return

    print(f"Connexion à la base de données PostgreSQL...")
    try:
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # 1. Création des tables
        print("Création des tables...")
        models.Base.metadata.create_all(bind=engine)
        
        # 2. Migrations de colonnes (pour synchroniser si la DB existe déjà)
        print("Vérification des colonnes...")
        migrations = [
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS school_name VARCHAR DEFAULT 'Moroccan Wave Vibes'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS contact_address VARCHAR DEFAULT 'Plage de Mehdia, Kenitra, Maroc'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS contact_phone VARCHAR DEFAULT '+212 6 00 00 00 00'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS contact_email VARCHAR DEFAULT 'contact@mwv.sytes.net'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS contact_email VARCHAR DEFAULT 'contact@mwv.sytes.net'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS navbar_bg_color VARCHAR DEFAULT '#ffffff'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS navbar_text_color VARCHAR DEFAULT '#1f2937'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS footer_bg_color VARCHAR DEFAULT '#111827'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS footer_text_color VARCHAR DEFAULT '#ffffff'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret VARCHAR DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN DEFAULT FALSE",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS logo_filename VARCHAR DEFAULT NULL",
            "ALTER TABLE services ADD COLUMN IF NOT EXISTS discount_percent NUMERIC(5,2) DEFAULT 0",
            "ALTER TABLE services ADD COLUMN IF NOT EXISTS level VARCHAR",
            "ALTER TABLE inquiries ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'en_attente'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_title VARCHAR DEFAULT 'Pourquoi rider avec nous ?'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_description TEXT DEFAULT ''",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_image_filename VARCHAR DEFAULT NULL",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature1_icon VARCHAR DEFAULT '👨‍🏫'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature1_title VARCHAR DEFAULT 'Moniteurs Diplômés d''État'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature1_desc VARCHAR DEFAULT ''",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature2_icon VARCHAR DEFAULT '🏄'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature2_title VARCHAR DEFAULT 'Matériel Premium'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature2_desc VARCHAR DEFAULT ''",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature3_icon VARCHAR DEFAULT '🌊'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature3_title VARCHAR DEFAULT 'Choix des Spots'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature3_desc VARCHAR DEFAULT ''",
            "ALTER TABLE inquiries ADD COLUMN IF NOT EXISTS service_id INTEGER REFERENCES services(id)",
            "ALTER TABLE inquiries ADD COLUMN IF NOT EXISTS booking_date VARCHAR",
            "ALTER TABLE inquiries ADD COLUMN IF NOT EXISTS people_count INTEGER",
            "ALTER TABLE inquiries ADD COLUMN IF NOT EXISTS level VARCHAR",
            "ALTER TABLE course_schedules ADD COLUMN IF NOT EXISTS description TEXT",
            "ALTER TABLE course_schedules ADD COLUMN IF NOT EXISTS spots_available INTEGER DEFAULT 10",
            "ALTER TABLE course_schedules ADD COLUMN IF NOT EXISTS level TEXT",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS modal_title VARCHAR DEFAULT 'Rejoignez la Communauté'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS modal_subtitle TEXT DEFAULT 'Dites-nous en un peu plus sur vous pour débloquer votre réduction.'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS modal_promo_text VARCHAR DEFAULT 'Rejoignez notre communauté de passionnés et profitez d''une réduction immédiate sur votre prochain cours !'",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS modal_discount_percent INTEGER DEFAULT 15",
            "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS modal_image_filename VARCHAR DEFAULT NULL"
        ]
        
        for m in migrations:
            try:
                db.execute(text(m))
            except Exception:
                pass # Souvent l'erreur est que la colonne existe déjà
        
        db.commit()
        print("Migrations terminées.")

        # 3. Seeding
        admin_user = db.query(models.User).filter_by(username="Administrateur").first()
        if not admin_user:
            print("Création de l'utilisateur Admin...")
            db.add(models.User(username="Administrateur", hashed_password=get_password_hash("WebSite@dmin2026")))
            db.commit()

        site_config = db.query(models.SiteConfig).first()
        if not site_config:
            print("Création de la configuration par défaut...")
            db.add(models.SiteConfig())
            db.commit()

        print("Migration vers PostgreSQL réussie !")
        db.close()

    except Exception as e:
        print(f"ERREUR lors de la migration : {e}")

if __name__ == "__main__":
    migrate()
