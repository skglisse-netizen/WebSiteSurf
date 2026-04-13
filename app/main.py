from fastapi import FastAPI, Depends, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil
import pyotp

from . import models, schemas
from sqlalchemy import text
from .database import engine, get_db, SessionLocal
from .auth import get_current_user, verify_password, create_access_token, get_password_hash

# Ensure upload directories exist
UPLOAD_DIR = "static/uploads/hero"
LOGO_DIR = "static/uploads/logo"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(LOGO_DIR, exist_ok=True)

def secure_filename_lite(filename: str) -> str:
    import re
    # Remove path info and avoid path traversal
    base = os.path.basename(filename)
    name, ext = os.path.splitext(base)
    # Replace anything that isn't alphanumeric, dash or underscore with an underscore
    name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    return f"{name.lower()}{ext.lower()}"

def init_db():
    db = SessionLocal()
    try:
        # Tables creation
        models.Base.metadata.create_all(bind=engine)
        
        # Migrations and sync
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS school_name VARCHAR DEFAULT 'WaveRider'"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS contact_address VARCHAR DEFAULT '123 Plage des Vagues, 64200 Biarritz'"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS contact_phone VARCHAR DEFAULT '+33 6 12 34 56 78'"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS contact_email VARCHAR DEFAULT 'allo@waverider.fr'"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS contact_email VARCHAR DEFAULT 'allo@waverider.fr'"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS navbar_bg_color VARCHAR DEFAULT '#ffffff'"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS navbar_text_color VARCHAR DEFAULT '#1f2937'"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS footer_bg_color VARCHAR DEFAULT '#111827'"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS footer_text_color VARCHAR DEFAULT '#ffffff'"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret VARCHAR DEFAULT NULL"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN DEFAULT FALSE"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS logo_filename VARCHAR DEFAULT NULL"))
        db.execute(text("ALTER TABLE services ADD COLUMN IF NOT EXISTS discount_percent NUMERIC(5,2) DEFAULT 0"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_title VARCHAR DEFAULT 'Pourquoi rider avec nous ?'"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_description TEXT DEFAULT ''"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_image_filename VARCHAR DEFAULT NULL"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature1_icon VARCHAR DEFAULT '👨‍🏫'"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature1_title VARCHAR DEFAULT 'Moniteurs Diplômés d''État'"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature1_desc VARCHAR DEFAULT ''"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature2_icon VARCHAR DEFAULT '🏄'"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature2_title VARCHAR DEFAULT 'Matériel Premium'"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature2_desc VARCHAR DEFAULT ''"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature3_icon VARCHAR DEFAULT '🌊'"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature3_title VARCHAR DEFAULT 'Choix des Spots'"))
        db.execute(text("ALTER TABLE site_config ADD COLUMN IF NOT EXISTS why_feature3_desc VARCHAR DEFAULT ''"))
        
        # Reservation fields
        db.execute(text("ALTER TABLE inquiries ADD COLUMN IF NOT EXISTS service_id INTEGER REFERENCES services(id)"))
        db.execute(text("ALTER TABLE inquiries ADD COLUMN IF NOT EXISTS booking_date VARCHAR"))
        db.execute(text("ALTER TABLE inquiries ADD COLUMN IF NOT EXISTS people_count INTEGER"))
        db.execute(text("ALTER TABLE inquiries ADD COLUMN IF NOT EXISTS level VARCHAR"))
        
        db.commit()

        # Seed Admin user
        admin_user = db.query(models.User).filter_by(username="Administrateur").first()
        if not admin_user:
            db.add(models.User(username="Administrateur", hashed_password=get_password_hash("WebSite@dmin2026")))
            db.commit()

        # Seed initial config
        site_config = db.query(models.SiteConfig).first()
        if not site_config:
            db.add(models.SiteConfig())
            db.commit()
    except Exception as e:
        print(f"Database Init Notice: {e}")
        db.rollback()
    finally:
        db.close()

# Run initialization
init_db()

app = FastAPI(title="Surf Camp Web App")

# Mount static files (CSS, JS, Images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    # Fetch active services from the DB
    services = db.query(models.Service).filter(models.Service.is_active == True).all()
    config = db.query(models.SiteConfig).first()
    
    # If the database is empty, let's inject a dummy service for the first run
    if not services:
        dummy_service = models.Service(
            title="Stage de Surf - Débutant",
            description="Apprenez les bases du surf avec nos moniteurs diplômés. Sensations garanties dès la première vague !",
            price=150.00,
            image_url="https://images.unsplash.com/photo-1544551763-46a013bb70d5?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
        )
        db.add(dummy_service)
        db.commit()
        db.refresh(dummy_service)
        services = [dummy_service]

    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"request": request, "services": services, "config": config}
    )

@app.post("/reservation")
async def contact_form(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    message: str = Form(None),
    service_id: Optional[int] = Form(None),
    booking_date: Optional[str] = Form(None),
    people_count: Optional[int] = Form(None),
    level: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    # Save the reservation/inquiry to the database
    inquiry = models.Inquiry(
        name=name, 
        email=email, 
        phone=phone, 
        message=message,
        service_id=service_id,
        booking_date=booking_date,
        people_count=people_count,
        level=level
    )
    db.add(inquiry)
    db.commit()
    
    # Reload the page with a success message
    services = db.query(models.Service).filter(models.Service.is_active == True).all()
    config = db.query(models.SiteConfig).first()
    
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "request": request, 
            "services": services,
            "config": config,
            "success_message": "Merci ! Votre demande a été envoyée avec succès. Nous vous contacterons très vite."
        }
    )

@app.post("/footer-contact")
async def footer_contact(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
    db: Session = Depends(get_db)
):
    inquiry = models.Inquiry(
        name=f"{name} (Footer)", 
        email=email, 
        message=message
    )
    db.add(inquiry)
    db.commit()
    
    # Fetch data to re-render home page
    services = db.query(models.Service).filter(models.Service.is_active == True).all()
    config = db.query(models.SiteConfig).first()
    
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "request": request, 
            "services": services,
            "config": config,
            "success_message": "Merci ! Votre message a été envoyé depuis le pied de page."
        }
    )

@app.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    config = db.query(models.SiteConfig).first()
    return templates.TemplateResponse(request=request, name="admin/login.html", context={"request": request, "config": config})

@app.post("/admin/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    config = db.query(models.SiteConfig).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(request=request, name="admin/login.html", context={"request": request, "error": "Identifiants invalides", "config": config})
    
    # Check if MFA is enabled
    if user.mfa_enabled:
        # Create a temporary token for MFA verification (valid for 5 mins)
        temp_token = create_access_token(data={"sub": user.username, "mfa_pending": True}, expires_delta=timedelta(minutes=5))
        response = RedirectResponse(url="/admin/login/mfa", status_code=302)
        response.set_cookie(key="mfa_pending_token", value=temp_token, httponly=True)
        return response

    access_token = create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/admin/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@app.get("/admin/login/mfa", response_class=HTMLResponse)
async def login_mfa_page(request: Request, db: Session = Depends(get_db)):
    config = db.query(models.SiteConfig).first()
    return templates.TemplateResponse(request=request, name="admin/mfa_verify.html", context={"request": request, "config": config})

@app.post("/admin/login/mfa")
async def login_mfa_post(request: Request, code: str = Form(...), db: Session = Depends(get_db)):
    token = request.cookies.get("mfa_pending_token")
    if not token:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        from .auth import SECRET_KEY, ALGORITHM
        from jose import jwt
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except:
        return RedirectResponse(url="/admin/login", status_code=302)
        
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not user.mfa_secret:
        return RedirectResponse(url="/admin/login", status_code=302)
        
    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(code):
        config = db.query(models.SiteConfig).first()
        return templates.TemplateResponse(request=request, name="admin/mfa_verify.html", context={"request": request, "config": config, "error": "Code incorrect"})
    
    # Final JWT
    access_token = create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/admin/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    response.delete_cookie("mfa_pending_token")
    return response

# --- MFA SETUP ROUTES ---

@app.get("/admin/mfa/setup", response_class=HTMLResponse)
async def mfa_setup_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    config = db.query(models.SiteConfig).first()
    
    # Generate secret if not exists
    if not user.mfa_secret:
        user.mfa_secret = pyotp.random_base32()
        db.commit()
        
    totp = pyotp.TOTP(user.mfa_secret)
    provisioning_uri = totp.provisioning_uri(name=user.username, issuer_name=config.school_name)
    
    return templates.TemplateResponse(
        request=request, 
        name="admin/mfa_setup.html", 
        context={"request": request, "config": config, "user": user, "uri": provisioning_uri}
    )

@app.post("/admin/mfa/activate")
async def mfa_activate(request: Request, code: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not user.mfa_secret:
        return RedirectResponse(url="/admin/login", status_code=302)
        
    totp = pyotp.TOTP(user.mfa_secret)
    if totp.verify(code):
        user.mfa_enabled = True
        db.commit()
        return RedirectResponse(url="/admin/dashboard?mfa_success=1", status_code=302)
    else:
        config = db.query(models.SiteConfig).first()
        provisioning_uri = totp.provisioning_uri(name=user.username, issuer_name=config.school_name)
        return templates.TemplateResponse(
            request=request, 
            name="admin/mfa_setup.html", 
            context={"request": request, "config": config, "user": user, "uri": provisioning_uri, "error": "Code de vérification invalide"}
        )

@app.post("/admin/mfa/disable")
async def mfa_disable(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    user.mfa_enabled = False
    user.mfa_secret = None
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    config = db.query(models.SiteConfig).first()
    inquiries = db.query(models.Inquiry).order_by(models.Inquiry.id.desc()).all()
    hero_images = db.query(models.HeroImage).filter(models.HeroImage.config_id == config.id).all()
    services = db.query(models.Service).order_by(models.Service.id).all()
    
    return templates.TemplateResponse(
        request=request, 
        name="admin/dashboard.html", 
        context={
            "request": request, 
            "user": user, 
            "config": config, 
            "inquiries": inquiries,
            "hero_images": hero_images,
            "services": services
        }
    )

@app.post("/admin/hero-images/upload")
async def upload_hero_images(
    request: Request,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
        
    config = db.query(models.SiteConfig).first()
    
    for file in files:
        if not file.filename:
            continue
            
        # Use sanitized original filename
        new_filename = secure_filename_lite(file.filename)
        file_path = os.path.join(UPLOAD_DIR, new_filename)
        
        # Overwrite file on disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Add to DB only if it doesn't exist (to avoid duplicates in gallery)
        existing = db.query(models.HeroImage).filter(
            models.HeroImage.filename == new_filename,
            models.HeroImage.config_id == config.id
        ).first()
        
        if not existing:
            hero_img = models.HeroImage(filename=new_filename, config_id=config.id)
            db.add(hero_img)
    
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.post("/admin/hero-images/{image_id}/delete")
async def delete_hero_image(
    request: Request,
    image_id: int,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
        
    print(f"DEBUG: Attempting to delete hero image with ID {image_id}")
    img = db.query(models.HeroImage).filter(models.HeroImage.id == image_id).first()
    if img:
        print(f"DEBUG: Found image in DB: {img.filename}")
        # Delete file
        file_path = os.path.join(UPLOAD_DIR, img.filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"DEBUG: File deleted from disk: {file_path}")
            except Exception as e:
                print(f"DEBUG: Could not delete file from disk (might be in use): {e}")
        
        # Delete from DB
        db.delete(img)
        db.commit()
        print(f"DEBUG: Image deleted from DB and committed.")
    else:
        print(f"DEBUG: Image with ID {image_id} not found in DB.")
        
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.post("/admin/logo/upload")
async def upload_logo(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    config = db.query(models.SiteConfig).first()
    
    # Secure name
    new_filename = secure_filename_lite(file.filename)
    
    # Delete old logo if it has a BROADLY different name or just overwrite if it matches
    if config.logo_filename and config.logo_filename != new_filename:
        old_path = os.path.join(LOGO_DIR, config.logo_filename)
        if os.path.exists(old_path):
            os.remove(old_path)
            
    file_path = os.path.join(LOGO_DIR, new_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    config.logo_filename = new_filename
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.post("/admin/logo/delete")
async def delete_logo(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    config = db.query(models.SiteConfig).first()
    if config.logo_filename:
        file_path = os.path.join(LOGO_DIR, config.logo_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        config.logo_filename = None
        db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.post("/admin/dashboard")
async def dashboard_update(
    request: Request,
    hero_title: str = Form(...),
    hero_subtitle: str = Form(...),
    hero_button_text: str = Form(...),
    contact_button_text: str = Form(...),
    school_name: str = Form(...),
    contact_address: str = Form(...),
    contact_phone: str = Form(...),
    contact_email: str = Form(...),
    navbar_bg_color: str = Form(...),
    navbar_text_color: str = Form(...),
    footer_bg_color: str = Form(...),
    footer_text_color: str = Form(...),
    why_title: str = Form(...),
    why_description: str = Form(...),
    why_feature1_icon: str = Form(...),
    why_feature1_title: str = Form(...),
    why_feature1_desc: str = Form(...),
    why_feature2_icon: str = Form(...),
    why_feature2_title: str = Form(...),
    why_feature2_desc: str = Form(...),
    why_feature3_icon: str = Form(...),
    why_feature3_title: str = Form(...),
    why_feature3_desc: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
        
    config = db.query(models.SiteConfig).first()
    config.hero_title = hero_title
    config.hero_subtitle = hero_subtitle
    config.hero_button_text = hero_button_text
    config.contact_button_text = contact_button_text
    config.school_name = school_name
    config.contact_address = contact_address
    config.contact_phone = contact_phone
    config.contact_email = contact_email
    config.navbar_bg_color = navbar_bg_color
    config.navbar_text_color = navbar_text_color
    config.footer_bg_color = footer_bg_color
    config.footer_text_color = footer_text_color
    config.why_title = why_title
    config.why_description = why_description
    config.why_feature1_icon = why_feature1_icon
    config.why_feature1_title = why_feature1_title
    config.why_feature1_desc = why_feature1_desc
    config.why_feature2_icon = why_feature2_icon
    config.why_feature2_title = why_feature2_title
    config.why_feature2_desc = why_feature2_desc
    config.why_feature3_icon = why_feature3_icon
    config.why_feature3_title = why_feature3_title
    config.why_feature3_desc = why_feature3_desc
    db.commit()
    
    return RedirectResponse(url="/admin/dashboard", status_code=302)

# --- WHY SECTION IMAGE ---
WHY_IMG_DIR = "static/uploads/why"
os.makedirs(WHY_IMG_DIR, exist_ok=True)

@app.post("/admin/why-image/upload")
async def upload_why_image(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    config = db.query(models.SiteConfig).first()
    
    new_filename = secure_filename_lite(file.filename)
    
    if config.why_image_filename and config.why_image_filename != new_filename:
        old = os.path.join(WHY_IMG_DIR, config.why_image_filename)
        if os.path.exists(old):
            os.remove(old)
            
    file_path = os.path.join(WHY_IMG_DIR, new_filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    config.why_image_filename = new_filename
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.post("/admin/why-image/delete")
async def delete_why_image(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    config = db.query(models.SiteConfig).first()
    if config.why_image_filename:
        f = os.path.join(WHY_IMG_DIR, config.why_image_filename)
        if os.path.exists(f):
            os.remove(f)
        config.why_image_filename = None
        db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=302)

# --- SERVICES CRUD ---
SERVICE_IMG_DIR = "static/uploads/services"
os.makedirs(SERVICE_IMG_DIR, exist_ok=True)

@app.post("/admin/services/add")
async def service_add(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    discount_percent: float = Form(0),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    image_url = None
    if image and image.filename:
        fname = secure_filename_lite(image.filename)
        with open(os.path.join(SERVICE_IMG_DIR, fname), "wb") as f:
            shutil.copyfileobj(image.file, f)
        image_url = f"/static/uploads/services/{fname}"

    db.add(models.Service(title=title, description=description, price=price, discount_percent=discount_percent, image_url=image_url))
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.post("/admin/services/{service_id}/edit")
async def service_edit(
    request: Request,
    service_id: int,
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    discount_percent: float = Form(0),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    svc = db.query(models.Service).filter(models.Service.id == service_id).first()
    if svc:
        svc.title = title
        svc.description = description
        svc.price = price
        svc.discount_percent = discount_percent
        if image and image.filename:
            # Delete old image if it exists and is different
            if svc.image_url:
                old_fname = svc.image_url.split("/")[-1]
                new_fname = secure_filename_lite(image.filename)
                
                if old_fname != new_fname:
                    old_path = os.path.join(SERVICE_IMG_DIR, old_fname)
                    if os.path.exists(old_path):
                        os.remove(old_path)
            
            fname = secure_filename_lite(image.filename)
            with open(os.path.join(SERVICE_IMG_DIR, fname), "wb") as f:
                shutil.copyfileobj(image.file, f)
            svc.image_url = f"/static/uploads/services/{fname}"
        db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.post("/admin/services/{service_id}/delete")
async def service_delete(request: Request, service_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    svc = db.query(models.Service).filter(models.Service.id == service_id).first()
    if svc:
        # Delete image file
        if svc.image_url:
            fname = svc.image_url.split("/")[-1]
            file_path = os.path.join(SERVICE_IMG_DIR, fname)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
        db.delete(svc)
        db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.get("/admin/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("access_token")
    return response
