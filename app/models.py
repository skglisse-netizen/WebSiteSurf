from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    price = Column(Numeric(10, 2))
    discount_percent = Column(Numeric(5, 2), default=0)  # 0-100
    image_url = Column(String)
    level = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

class Inquiry(Base):
    __tablename__ = "inquiries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    message = Column(Text)
    
    # New reservation fields
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    booking_date = Column(String, nullable=True)
    people_count = Column(Integer, nullable=True)
    level = Column(String, nullable=True)
    status = Column(String, default="en_attente") # en_attente, confirme, annule
    
    objective = Column(Text, nullable=True)
    source = Column(String, default="contact") # contact, lead, reservation
    
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    service = relationship("Service")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    contact_email = Column(String, default="allo@waverider.fr")
    mfa_secret = Column(String, nullable=True)
    mfa_enabled = Column(Boolean, default=False)

class SiteConfig(Base):
    __tablename__ = "site_config"

    id = Column(Integer, primary_key=True, index=True)
    hero_title = Column(String, default="Domptez les Vagues avec WaveRider")
    hero_subtitle = Column(Text, default="L'école de surf où la passion rencontre l'océan. Des cours pour tous les niveaux, du débutant au surfeur confirmé.")
    hero_button_text = Column(String, default="Découvrir nos Formules")
    contact_button_text = Column(String, default="Contactez-nous")
    
    school_name = Column(String, default="WaveRider")
    contact_address = Column(String, default="123 Plage des Vagues, 64200 Biarritz")
    contact_phone = Column(String, default="+33 6 12 34 56 78")
    contact_email = Column(String, default="allo@waverider.fr")

    # Apparence
    navbar_bg_color = Column(String, default="#ffffff")
    navbar_text_color = Column(String, default="#1f2937")
    footer_bg_color = Column(String, default="#111827")
    footer_text_color = Column(String, default="#ffffff")
    logo_filename = Column(String, default=None)

    # Section "Pourquoi nous ?"
    why_title = Column(String, default="Pourquoi rider avec nous ?")
    why_description = Column(Text, default="Notre école s'engage à vous offrir la meilleure expérience possible sur les vagues, alliant sécurité, progression et un maximum de fun.")
    why_image_filename = Column(String, default=None)
    why_feature1_icon = Column(String, default="👨‍🏫")
    why_feature1_title = Column(String, default="Moniteurs Diplômés d'État")
    why_feature1_desc = Column(String, default="Des experts passionnés pour vous guider en toute sécurité.")
    why_feature2_icon = Column(String, default="🏄")
    why_feature2_title = Column(String, default="Matériel Premium")
    why_feature2_desc = Column(String, default="Planches et combinaisons haut de gamme adaptées à chaque gabarit.")
    why_feature3_icon = Column(String, default="🌊")
    why_feature3_title = Column(String, default="Choix des Spots")
    why_feature3_desc = Column(String, default="Nous sélectionnons chaque jour la meilleure plage selon les conditions.")
 
    # Lead Capture Modal Configuration
    modal_title = Column(String, default="Rejoignez la Communauté")
    modal_subtitle = Column(Text, default="Dites-nous en un peu plus sur vous pour débloquer votre réduction.")
    modal_promo_text = Column(String, default="Rejoignez notre communauté de passionnés et profitez d'une réduction immédiate sur votre prochain cours !")
    modal_discount_percent = Column(Integer, default=15)
    modal_image_filename = Column(String, default=None)

    # Relationship to multiple hero images
    hero_images = relationship("HeroImage", back_populates="config", cascade="all, delete-orphan")

class HeroImage(Base):
    __tablename__ = "hero_images"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    config_id = Column(Integer, ForeignKey("site_config.id"))

    config = relationship("SiteConfig", back_populates="hero_images")

class DailyVisit(Base):
    __tablename__ = "daily_visits"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, unique=True, index=True)
    count = Column(Integer, default=1)

class CourseSchedule(Base):
    __tablename__ = "course_schedules"

    id = Column(Integer, primary_key=True, index=True)
    date_text = Column(String)
    time_text = Column(String)
    course_title = Column(String)
    description = Column(Text, nullable=True)
    spots_available = Column(Integer, default=10)
    level = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PopupEvent(Base):
    __tablename__ = "popup_events"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String) # 'view', 'close', 'fill'
    created_at = Column(String) # ISO date string
