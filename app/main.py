from fastapi import FastAPI, Depends, Request, Form, File, UploadFile, BackgroundTasks
from datetime import timedelta, datetime
import datetime as dt_module
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil
import pyotp

from . import models, schemas, notifications
from sqlalchemy import text
from .database import engine, get_db, SessionLocal
from .auth import get_current_user, verify_password, create_access_token, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES

# Ensure upload directories exist
UPLOAD_DIR = "static/uploads/hero"
LOGO_DIR = "static/uploads/logo"
SCHEDULE_IMG_DIR = "static/uploads/schedules"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(LOGO_DIR, exist_ok=True)
os.makedirs(SCHEDULE_IMG_DIR, exist_ok=True)

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
        models.Base.metadata.create_all(bind=engine)
    except: pass

    commands = [
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
        "ALTER TABLE inquiries ADD COLUMN IF NOT EXISTS schedule_id INTEGER REFERENCES course_schedules(id)",
        "ALTER TABLE course_schedules ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE course_schedules ADD COLUMN IF NOT EXISTS spots_available INTEGER DEFAULT 10",
        "ALTER TABLE course_schedules ADD COLUMN IF NOT EXISTS level TEXT",
        "ALTER TABLE course_schedules ADD COLUMN IF NOT EXISTS image_filename VARCHAR",
        "ALTER TABLE course_schedules ADD COLUMN IF NOT EXISTS discount_percent INTEGER DEFAULT 0",
        "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS modal_title VARCHAR DEFAULT 'Rejoignez la Communauté'",
        "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS modal_subtitle TEXT DEFAULT 'Dites-nous en un peu plus sur vous pour débloquer votre réduction.'",
        "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS modal_promo_text VARCHAR DEFAULT 'Rejoignez notre communauté de passionnés et profitez d''une réduction immédiate sur votre prochain cours !'",
        "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS modal_discount_percent INTEGER DEFAULT 15",
        "ALTER TABLE site_config ADD COLUMN IF NOT EXISTS modal_image_filename VARCHAR DEFAULT NULL",
        "ALTER TABLE inquiries ADD COLUMN IF NOT EXISTS objective TEXT",
        "ALTER TABLE inquiries ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'contact'",
        """
        CREATE TABLE IF NOT EXISTS popup_events (
            id SERIAL PRIMARY KEY,
            event_type VARCHAR,
            created_at VARCHAR
        )
        """
    ]

    for cmd in commands:
        try:
            db.execute(text(cmd))
            db.commit()
        except:
            db.rollback()

    try:
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
    except:
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
async def read_root(request: Request, success: Optional[str] = None, db: Session = Depends(get_db)):
    services = db.query(models.Service).filter(models.Service.is_active == True).all()
    
    # Track Daily Visit
    try:
        from datetime import date
        today_date = date.today().isoformat()
        daily_visit = db.query(models.DailyVisit).filter(models.DailyVisit.date == today_date).first()
        if daily_visit:
            daily_visit.count += 1
        else:
            daily_visit = models.DailyVisit(date=today_date, count=1)
            db.add(daily_visit)
        db.commit()
    except Exception as e:
        print(f"Tracking Error: {e}")
        db.rollback()
    
    # Process schedules to filter out expired ones
    raw_schedules = db.query(models.CourseSchedule).filter(models.CourseSchedule.is_active == True).all()
    from datetime import datetime, timedelta
    current_time = datetime.now()
    cutoff_time = current_time - timedelta(minutes=1)
    
    schedules = []
    has_deletions = False
    for sch in raw_schedules:
        try:
            sch_datetime = datetime.strptime(f"{sch.date_text} {sch.time_text}", "%Y-%m-%d %H:%M")
            if sch_datetime >= cutoff_time:
                schedules.append((sch, sch_datetime))
            else:
                sch.is_active = False
                has_deletions = True
        except ValueError:
            # Fallback if date/time format is non-parseable
            schedules.append((sch, None))
            
    if has_deletions:
        db.commit()
        
    # Sort active schedules chronologically
    schedules.sort(key=lambda x: x[1] if x[1] else datetime.max)
    sorted_schedules = [x[0] for x in schedules]

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

    success_message = None
    if success == "reservation":
        success_message = "Merci ! Votre demande a été envoyée avec succès. Nous vous contacterons très vite."
    elif success == "contact":
        success_message = "Merci ! Votre message a été envoyé depuis le pied de page."

    response = templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"request": request, "services": services, "config": config, "schedules": sorted_schedules, "success_message": success_message}
    )

    # Tracker la visite unique (Cookie 24h)
    if not request.cookies.get("visited_today"):
        import datetime
        today_str = datetime.date.today().isoformat()
        visit = db.query(models.DailyVisit).filter(models.DailyVisit.date == today_str).first()
        if visit:
            visit.count += 1
        else:
            visit = models.DailyVisit(date=today_str, count=1)
            db.add(visit)
        db.commit()
        response.set_cookie(key="visited_today", value="1", max_age=86400)
        
    return response

@app.post("/reservation")
async def contact_form(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    message: str = Form(None),
    service_id: Optional[int] = Form(None),
    booking_date: Optional[str] = Form(None),
    people_count: Optional[int] = Form(None),
    level: Optional[str] = Form(None),
    schedule_id: Optional[int] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
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
        level=level,
        schedule_id=schedule_id,
        source="reservation" if (service_id or booking_date) else "contact",
        created_at=dt_module.datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    
    # Deduct availability from CourseSchedule if this is a quick schedule booking
    if schedule_id:
        schedule = db.query(models.CourseSchedule).filter(models.CourseSchedule.id == schedule_id).first()
        if schedule and schedule.spots_available > 0:
            deduction = people_count if people_count else 1
            schedule.spots_available = max(0, schedule.spots_available - deduction)
            db.commit()
    
    # Reload the page with a success message
    services = db.query(models.Service).filter(models.Service.is_active == True).all()
    config = db.query(models.SiteConfig).first()
    
    # Send notification via n8n (Async)
    service = db.query(models.Service).filter(models.Service.id == service_id).first() if service_id else None
    service_title = service.title if service else ("Planning Rapide" if booking_date else "Formule Inconnue")
    webhook_target = "reservation" if (service_id or booking_date) else "contact"
    
    payload = notifications.format_inquiry_payload(inquiry, service_title)
    background_tasks.add_task(notifications.send_n8n_notification, payload, webhook_target)
    background_tasks.add_task(notifications.send_telegram_notification, payload)

    return RedirectResponse(url="/?success=reservation#accueil", status_code=303)

@app.post("/community-join")
async def community_join(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    level: str = Form(...),
    objective: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    # Save as an inquiry with a special message format
    message = f"[COMMUNITY JOIN] Objectif: {objective}"
    inquiry = models.Inquiry(
        name=name,
        email=email,
        phone=phone,
        objective=objective,
        level=level,
        status="en_attente",
        source="lead",
        created_at=dt_module.datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    
    # Send notification
    payload = notifications.format_inquiry_payload(inquiry, "Rejoint la Communauté")
    background_tasks.add_task(notifications.send_n8n_notification, payload, "contact")
    background_tasks.add_task(notifications.send_telegram_notification, payload)

    # Track fill event
    import datetime
    fill_event = models.PopupEvent(
        event_type="fill",
        created_at=datetime.datetime.now().isoformat()
    )
    db.add(fill_event)
    db.commit()

    return RedirectResponse(url="/?success=community#accueil", status_code=303)

@app.post("/admin/stats/popup/track")
async def track_popup(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        event_type = data.get("event")
        if event_type in ['view', 'close']:
            import datetime
            new_event = models.PopupEvent(
                event_type=event_type,
                created_at=datetime.datetime.now().isoformat()
            )
            db.add(new_event)
            db.commit()
        return {"status": "success"}
    except:
        return {"status": "error"}


@app.post("/footer-contact")
async def footer_contact(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    message: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    inquiry = models.Inquiry(
        name=f"{name} (Footer)", 
        email=email, 
        phone=phone,
        message=message,
        created_at=dt_module.datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    
    # Fetch data to re-render home page
    services = db.query(models.Service).filter(models.Service.is_active == True).all()
    config = db.query(models.SiteConfig).first()
    
    # Send notification via n8n (Async)
    payload = notifications.format_inquiry_payload(inquiry, "Contact Footer")
    background_tasks.add_task(notifications.send_n8n_notification, payload, "contact")
    background_tasks.add_task(notifications.send_telegram_notification, payload)

    return RedirectResponse(url="/?success=contact#accueil", status_code=303)

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
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
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
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
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
async def dashboard_page(
    request: Request, 
    db: Session = Depends(get_db),
    view: str = "month",
    month: int = None,
    year: int = None
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    config = db.query(models.SiteConfig).first()
    if not config:
        config = models.SiteConfig(school_name="Moroccan Wave Vibes")
        db.add(config)
        db.commit()
        db.refresh(config)

    inquiries = db.query(models.Inquiry).order_by(models.Inquiry.id.desc()).all()
    hero_images = db.query(models.HeroImage).filter(models.HeroImage.config_id == config.id).all()
    services = db.query(models.Service).all()
    schedules = db.query(models.CourseSchedule).all()
    recent_activities = db.query(models.Inquiry).order_by(models.Inquiry.id.desc()).limit(10).all()
    
    import datetime
    import json
    import calendar
    
    now = datetime.datetime.now()
    if year is None: year = now.year
    if month is None: month = now.month
    
    labels = []
    data_counts = []
    
    if view == "month":
        # Get number of days in selected month
        _, last_day = calendar.monthrange(year, month)
        
        # Query visits for this month
        month_prefix = f"{year:04d}-{month:02d}"
        visits = db.query(models.DailyVisit).filter(models.DailyVisit.date.like(f"{month_prefix}%")).all()
        visits_dict = {v.date: v.count for v in visits}
        
        for day in range(1, last_day + 1):
            day_str = f"{month_prefix}-{day:02d}"
            labels.append(f"{day:02d}")
            data_counts.append(visits_dict.get(day_str, 0))
            
    else: # View == "year"
        # Query visits for this year
        year_prefix = f"{year:04d}"
        visits = db.query(models.DailyVisit).filter(models.DailyVisit.date.like(f"{year_prefix}%")).all()
        
        month_totals = {m: 0 for m in range(1, 13)}
        for v in visits:
            # v.date is YYYY-MM-DD
            try:
                v_month = int(v.date.split("-")[1])
                month_totals[v_month] += v.count
            except: continue
            
        month_names = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
        for m in range(1, 13):
            labels.append(month_names[m-1])
            data_counts.append(month_totals[m])

    # Popup Stats for Time Chart
    popup_fills_data = []
    popup_closes_data = []
    popup_views_data = []

    try:
        if view == "month":
            prefix = f"{year:04d}-{month:02d}"
            all_events = db.query(models.PopupEvent).filter(models.PopupEvent.created_at.like(f"{prefix}%")).all()
            
            fills_dict = {}
            closes_dict = {}
            views_dict = {}
            
            for ev in all_events:
                d = ev.created_at[:10] # YYYY-MM-DD
                if ev.event_type == "fill": fills_dict[d] = fills_dict.get(d, 0) + 1
                elif ev.event_type == "close": closes_dict[d] = closes_dict.get(d, 0) + 1
                elif ev.event_type == "view": views_dict[d] = views_dict.get(d, 0) + 1
                
            for day in range(1, last_day + 1):
                day_str = f"{prefix}-{day:02d}"
                popup_fills_data.append(fills_dict.get(day_str, 0))
                popup_closes_data.append(closes_dict.get(day_str, 0))
                popup_views_data.append(views_dict.get(day_str, 0))
        else:
            prefix = f"{year:04d}"
            all_events = db.query(models.PopupEvent).filter(models.PopupEvent.created_at.like(f"{prefix}%")).all()
            
            fills_m = {m: 0 for m in range(1, 13)}
            closes_m = {m: 0 for m in range(1, 13)}
            views_m = {m: 0 for m in range(1, 13)}
            
            for ev in all_events:
                try:
                    m = int(ev.created_at.split("-")[1])
                    if ev.event_type == "fill": fills_m[m] += 1
                    elif ev.event_type == "close": closes_m[m] += 1
                    elif ev.event_type == "view": views_m[m] += 1
                except: continue
                
            for m in range(1, 13):
                popup_fills_data.append(fills_m[m])
                popup_closes_data.append(closes_m[m])
                popup_views_data.append(views_m[m])
    except:
        popup_fills_data = [0] * len(labels)
        popup_closes_data = [0] * len(labels)
        popup_views_data = [0] * len(labels)

    # Summary Stats
    popup_summary = {"fills": 0, "closes": 0, "views": 0}
    try:
        popup_summary["fills"] = db.query(models.PopupEvent).filter(models.PopupEvent.event_type == "fill").count()
        popup_summary["closes"] = db.query(models.PopupEvent).filter(models.PopupEvent.event_type == "close").count()
        popup_summary["views"] = db.query(models.PopupEvent).filter(models.PopupEvent.event_type == "view").count()
    except: pass

    return templates.TemplateResponse(
        request=request, 
        name="admin/dashboard.html", 
        context={
            "request": request, 
            "user": user, 
            "config": config, 
            "inquiries": inquiries,
            "hero_images": hero_images,
            "services": services,
            "schedules": schedules,
            "recent_activities": recent_activities,
            "chart_labels": json.dumps(labels),
            "chart_data": json.dumps(data_counts),
            "popup_fills_data": json.dumps(popup_fills_data),
            "popup_closes_data": json.dumps(popup_closes_data),
            "popup_views_data": json.dumps(popup_views_data),
            "current_view": view,
            "current_month": month,
            "current_year": year,
            "years_range": range(now.year - 2, now.year + 1),
            "popup_stats": popup_summary,
            "conversion_rate": (popup_summary["fills"] / popup_summary["views"] * 100) if popup_summary["views"] > 0 else 0,
            "popup_others": max(0, popup_summary["views"] - popup_summary["fills"] - popup_summary["closes"])
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
            
        new_filename = secure_filename_lite(file.filename)
        file_path = os.path.join(UPLOAD_DIR, new_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        existing = db.query(models.HeroImage).filter(
            models.HeroImage.filename == new_filename,
            models.HeroImage.config_id == config.id
        ).first()
        
        if not existing:
            hero_img = models.HeroImage(filename=new_filename, config_id=config.id)
            db.add(hero_img)
    
    try:
        db.commit()
    except:
        db.rollback()
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
        
    img = db.query(models.HeroImage).filter(models.HeroImage.id == image_id).first()
    if img:
        file_path = os.path.join(UPLOAD_DIR, img.filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        db.delete(img)
        try:
            db.commit()
        except:
            db.rollback()
        
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
    
    new_filename = secure_filename_lite(file.filename)
    
    if config.logo_filename and config.logo_filename != new_filename:
        old_path = os.path.join(LOGO_DIR, config.logo_filename)
        if os.path.exists(old_path):
            os.remove(old_path)
            
    file_path = os.path.join(LOGO_DIR, new_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    config.logo_filename = new_filename
    try:
        db.commit()
    except:
        db.rollback()
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
        try:
            db.commit()
        except:
            db.rollback()
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
    try:
        db.commit()
    except:
        db.rollback()
    
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
    try:
        db.commit()
    except:
        db.rollback()
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
        try:
            db.commit()
        except:
            db.rollback()
    return RedirectResponse(url="/admin/dashboard", status_code=302)

# --- MODAL SECTION ---
MODAL_IMG_DIR = "static/uploads/modal"
os.makedirs(MODAL_IMG_DIR, exist_ok=True)

@app.post("/admin/modal-config")
async def modal_config_update(
    request: Request,
    modal_title: str = Form(...),
    modal_subtitle: str = Form(...),
    modal_promo_text: str = Form(...),
    modal_discount_percent: int = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
        
    config = db.query(models.SiteConfig).first()
    config.modal_title = modal_title
    config.modal_subtitle = modal_subtitle
    config.modal_promo_text = modal_promo_text
    config.modal_discount_percent = modal_discount_percent
    try:
        db.commit()
    except:
        db.rollback()
    
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.post("/admin/modal-image/upload")
async def upload_modal_image(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    config = db.query(models.SiteConfig).first()
    
    new_filename = secure_filename_lite(file.filename)
    
    if config.modal_image_filename and config.modal_image_filename != new_filename:
        old = os.path.join(MODAL_IMG_DIR, config.modal_image_filename)
        if os.path.exists(old):
            os.remove(old)
            
    file_path = os.path.join(MODAL_IMG_DIR, new_filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    config.modal_image_filename = new_filename
    try:
        db.commit()
    except:
        db.rollback()
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.post("/admin/modal-image/delete")
async def delete_modal_image(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    config = db.query(models.SiteConfig).first()
    if config.modal_image_filename:
        f = os.path.join(MODAL_IMG_DIR, config.modal_image_filename)
        if os.path.exists(f):
            os.remove(f)
        config.modal_image_filename = None
        try:
            db.commit()
        except:
            db.rollback()
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
    level: List[str] = Form(None),
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

    level_str = ",".join(level) if level else None

    db.add(models.Service(
        title=title, 
        description=description, 
        price=price, 
        discount_percent=discount_percent, 
        image_url=image_url,
        level=level_str
    ))
    try:
        db.commit()
    except:
        db.rollback()
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
    level: List[str] = Form(None),
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
        svc.level = ",".join(level) if level else None
        if image and image.filename:
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
        try:
            db.commit()
        except:
            db.rollback()
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.post("/admin/services/{service_id}/delete")
async def service_delete(request: Request, service_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    svc = db.query(models.Service).filter(models.Service.id == service_id).first()
    if svc:
        if svc.image_url:
            fname = svc.image_url.split("/")[-1]
            file_path = os.path.join(SERVICE_IMG_DIR, fname)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
        db.delete(svc)
        try:
            db.commit()
        except:
            db.rollback()
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.get("/admin/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("access_token")
    return response

# --- MESSAGES CRUD ---
@app.post("/admin/messages/{inquiry_id}/read")
async def message_mark_read(request: Request, inquiry_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if inquiry:
        inquiry.is_processed = True
        db.commit()
    return RedirectResponse(url="/admin/dashboard#messages", status_code=302)

@app.post("/admin/leads/{inquiry_id}/validate")
async def lead_validate(request: Request, inquiry_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if inquiry:
        inquiry.is_processed = True
        db.commit()
    return RedirectResponse(url="/admin/dashboard#leads", status_code=302)

@app.post("/admin/leads/{inquiry_id}/unvalidate")
async def lead_unvalidate(request: Request, inquiry_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if inquiry:
        inquiry.is_processed = False
        db.commit()
    return RedirectResponse(url="/admin/dashboard#leads", status_code=302)

@app.post("/admin/messages/{inquiry_id}/unread")
async def message_mark_unread(request: Request, inquiry_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if inquiry:
        inquiry.is_processed = False
        db.commit()
    return RedirectResponse(url="/admin/dashboard#messages", status_code=302)

@app.post("/admin/messages/{inquiry_id}/delete")
async def message_delete(request: Request, inquiry_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if inquiry:
        db.delete(inquiry)
        db.commit()
    return RedirectResponse(url="/admin/dashboard#messages", status_code=302)

@app.post("/admin/leads/{inquiry_id}/delete")
async def lead_delete(request: Request, inquiry_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if inquiry:
        db.delete(inquiry)
        db.commit()
    return RedirectResponse(url="/admin/dashboard#leads", status_code=302)

@app.post("/admin/leads/{inquiry_id}/edit")
async def lead_edit(
    request: Request, 
    inquiry_id: int,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    level: str = Form(None),
    objective: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if inquiry:
        inquiry.name = name
        inquiry.email = email
        inquiry.phone = phone
        inquiry.level = level
        inquiry.objective = objective
        db.commit()
    return RedirectResponse(url="/admin/dashboard#leads", status_code=302)

@app.post("/admin/inquiries/{inquiry_id}/status")
async def inquiry_update_status(
    request: Request, 
    inquiry_id: int, 
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if inquiry:
        old_status = inquiry.status
        inquiry.status = status
        
        # Adjust CourseSchedule spots if applicable
        if inquiry.schedule_id:
            schedule = db.query(models.CourseSchedule).filter(models.CourseSchedule.id == inquiry.schedule_id).first()
            if schedule:
                deduction = inquiry.people_count if inquiry.people_count else 1
                if status == "annule" and old_status != "annule":
                    # Re-add spots on cancellation
                    schedule.spots_available += deduction
                elif old_status == "annule" and status != "annule":
                    # Re-deduct spots if moved back from cancelled
                    schedule.spots_available = max(0, schedule.spots_available - deduction)

        # Update is_processed based on status for backward compatibility
        if status in ["confirme", "annule"]:
            inquiry.is_processed = True
        else:
            inquiry.is_processed = False
        db.commit()
    
    target = "#reservations" if inquiry and inquiry.booking_date else "#messages"
    return RedirectResponse(url=f"/admin/dashboard{target}?success=status_updated", status_code=302)

# --- RESERVATIONS CRUD ---
@app.post("/admin/reservations/{inquiry_id}/validate")
async def reservation_validate(request: Request, inquiry_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if inquiry:
        inquiry.is_processed = True
        db.commit()
    return RedirectResponse(url="/admin/dashboard#reservations", status_code=302)

@app.post("/admin/reservations/{inquiry_id}/unvalidate")
async def reservation_unvalidate(request: Request, inquiry_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if inquiry:
        inquiry.is_processed = False
        db.commit()
    return RedirectResponse(url="/admin/dashboard#reservations", status_code=302)

@app.post("/admin/reservations/{inquiry_id}/delete")
async def reservation_delete(request: Request, inquiry_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if inquiry:
        # Re-add spots if not already cancelled and it's a schedule reservation
        if inquiry.schedule_id and inquiry.status != "annule":
            schedule = db.query(models.CourseSchedule).filter(models.CourseSchedule.id == inquiry.schedule_id).first()
            if schedule:
                deduction = inquiry.people_count if inquiry.people_count else 1
                schedule.spots_available += deduction
        
        db.delete(inquiry)
        db.commit()
    return RedirectResponse(url="/admin/dashboard#reservations", status_code=302)

@app.post("/admin/reservations/{inquiry_id}/edit")
async def reservation_edit(
    request: Request, 
    inquiry_id: int,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    service_id: int = Form(...),
    booking_date: str = Form(None),
    people_count: int = Form(None),
    level: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if inquiry:
        inquiry.name = name
        inquiry.email = email
        inquiry.phone = phone
        inquiry.service_id = service_id
        inquiry.booking_date = booking_date
        inquiry.people_count = people_count
        inquiry.level = level
        db.commit()
    return RedirectResponse(url="/admin/dashboard#reservations", status_code=302)

# --- SCHEDULES CRUD ---
@app.post("/admin/schedules/add")
async def schedule_add(
    request: Request,
    date_text: str = Form(...),
    time_text: str = Form(...),
    course_title: str = Form(...),
    description: str = Form(None),
    spots_available: int = Form(10),
    level: List[str] = Form(None),
    discount_percent: int = Form(0),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    level_str = ",".join(level) if level else None
    
    image_filename = None
    if image and image.filename:
        safe_name = secure_filename_lite(image.filename)
        unique_name = f"{uuid.uuid4().hex}_{safe_name}"
        file_path = os.path.join(SCHEDULE_IMG_DIR, unique_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_filename = unique_name

    db.add(models.CourseSchedule(
        date_text=date_text, 
        time_text=time_text, 
        course_title=course_title,
        description=description,
        spots_available=spots_available,
        level=level_str,
        discount_percent=discount_percent,
        image_filename=image_filename
    ))
    db.commit()
    return RedirectResponse(url="/admin/dashboard#planning-config", status_code=302)

@app.post("/admin/schedules/{schedule_id}/edit")
async def schedule_edit(
    request: Request,
    schedule_id: int,
    date_text: str = Form(...),
    time_text: str = Form(...),
    course_title: str = Form(...),
    description: str = Form(None),
    spots_available: int = Form(10),
    level: List[str] = Form(None),
    discount_percent: int = Form(0),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    sch = db.query(models.CourseSchedule).filter(models.CourseSchedule.id == schedule_id).first()
    if sch:
        sch.date_text = date_text
        sch.time_text = time_text
        sch.course_title = course_title
        sch.description = description
        sch.spots_available = spots_available
        sch.level = ",".join(level) if level else None
        sch.discount_percent = discount_percent
        
        if image and image.filename:
            # Delete old image if exists
            if sch.image_filename:
                old_path = os.path.join(SCHEDULE_IMG_DIR, sch.image_filename)
                if os.path.exists(old_path):
                    try: os.remove(old_path)
                    except: pass
            
            safe_name = secure_filename_lite(image.filename)
            unique_name = f"{uuid.uuid4().hex}_{safe_name}"
            file_path = os.path.join(SCHEDULE_IMG_DIR, unique_name)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            sch.image_filename = unique_name
            
        db.commit()
    return RedirectResponse(url="/admin/dashboard#planning-config", status_code=302)

@app.post("/admin/schedules/{schedule_id}/toggle")
async def schedule_toggle(request: Request, schedule_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    sch = db.query(models.CourseSchedule).filter(models.CourseSchedule.id == schedule_id).first()
    if sch:
        sch.is_active = not sch.is_active
        db.commit()
    return RedirectResponse(url="/admin/dashboard#planning-config", status_code=302)

@app.post("/admin/schedules/{schedule_id}/delete")
async def schedule_delete(request: Request, schedule_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    sch = db.query(models.CourseSchedule).filter(models.CourseSchedule.id == schedule_id).first()
    if sch:
        db.delete(sch)
        db.commit()
    return RedirectResponse(url="/admin/dashboard#planning-config", status_code=302)

