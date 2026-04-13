import sys
import os

# To import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models, database, auth
from sqlalchemy.orm import Session

def update_admin():
    db = database.SessionLocal()
    try:
        new_username = "Administrateur"
        new_password = "WebSite@dmin2026"
        
        print(f"--- Migration de Sécurité Admin ---")
        
        # 1. Supprimer l'ancien admin s'il existe
        old_admin = db.query(models.User).filter_by(username="admin").first()
        if old_admin:
            db.delete(old_admin)
            print(f"[OK] Ancien compte 'admin' supprimé.")
        
        # 2. Vérifier si le nouveau existe déjà
        new_admin = db.query(models.User).filter_by(username=new_username).first()
        if new_admin:
            new_admin.hashed_password = auth.get_password_hash(new_password)
            print(f"[OK] Compte '{new_username}' déjà existant, mot de passe mis à jour.")
        else:
            db.add(models.User(
                username=new_username, 
                hashed_password=auth.get_password_hash(new_password)
            ))
            print(f"[OK] Nouveau compte '{new_username}' créé.")
            
        db.commit()
        print(f"-----------------------------------")
        print(f"Migration terminée avec succès !")
        
    except Exception as e:
        db.rollback()
        print(f"[ERREUR] Échec de la migration : {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_admin()
