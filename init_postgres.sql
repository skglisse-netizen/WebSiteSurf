-- SCRIPT SQL POUR POSTGRESQL - Moroccan Wave Vibes

-- Table: services
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    description TEXT,
    price NUMERIC(10, 2),
    discount_percent NUMERIC(5, 2) DEFAULT 0,
    image_url VARCHAR(255),
    level VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE
);

-- Table: site_config
CREATE TABLE IF NOT EXISTS site_config (
    id SERIAL PRIMARY KEY,
    hero_title VARCHAR(255) DEFAULT 'Domptez les Vagues avec WaveRider',
    hero_subtitle TEXT,
    hero_button_text VARCHAR(255) DEFAULT 'Découvrir nos Formules',
    contact_button_text VARCHAR(255) DEFAULT 'Contactez-nous',
    school_name VARCHAR(255) DEFAULT 'WaveRider',
    contact_address VARCHAR(255) DEFAULT '123 Plage des Vagues, 64200 Biarritz',
    contact_phone VARCHAR(255) DEFAULT '+33 6 12 34 56 78',
    contact_email VARCHAR(255) DEFAULT 'allo@waverider.fr',
    navbar_bg_color VARCHAR(50) DEFAULT '#ffffff',
    navbar_text_color VARCHAR(50) DEFAULT '#1f2937',
    footer_bg_color VARCHAR(50) DEFAULT '#111827',
    footer_text_color VARCHAR(50) DEFAULT '#ffffff',
    logo_filename VARCHAR(255) DEFAULT NULL,
    why_title VARCHAR(255) DEFAULT 'Pourquoi rider avec nous ?',
    why_description TEXT,
    why_image_filename VARCHAR(255) DEFAULT NULL,
    why_feature1_icon VARCHAR(50) DEFAULT '👨‍🏫',
    why_feature1_title VARCHAR(255) DEFAULT 'Moniteurs Diplômés d''État',
    why_feature1_desc VARCHAR(255),
    why_feature2_icon VARCHAR(50) DEFAULT '🏄',
    why_feature2_title VARCHAR(255) DEFAULT 'Matériel Premium',
    why_feature2_desc VARCHAR(255),
    why_feature3_icon VARCHAR(50) DEFAULT '🌊',
    why_feature3_title VARCHAR(255) DEFAULT 'Choix des Spots',
    why_feature3_desc VARCHAR(255),
    modal_title VARCHAR(255) DEFAULT 'Rejoignez la Communauté',
    modal_subtitle TEXT,
    modal_promo_text VARCHAR(255),
    modal_discount_percent INTEGER DEFAULT 15,
    modal_image_filename VARCHAR(255) DEFAULT NULL
);

-- Table: inquiries
CREATE TABLE IF NOT EXISTS inquiries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(255),
    message TEXT,
    service_id INTEGER REFERENCES services(id),
    booking_date VARCHAR(255),
    people_count INTEGER,
    level VARCHAR(255),
    status VARCHAR(50) DEFAULT 'en_attente',
    is_processed BOOLEAN DEFAULT FALSE
);

-- Table: users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE,
    hashed_password VARCHAR(255),
    contact_email VARCHAR(255) DEFAULT 'allo@waverider.fr',
    mfa_secret VARCHAR(255),
    mfa_enabled BOOLEAN DEFAULT FALSE
);

-- Table: hero_images
CREATE TABLE IF NOT EXISTS hero_images (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255),
    config_id INTEGER REFERENCES site_config(id) ON DELETE CASCADE
);

-- Table: daily_visits
CREATE TABLE IF NOT EXISTS daily_visits (
    id SERIAL PRIMARY KEY,
    date VARCHAR(255) UNIQUE,
    count INTEGER DEFAULT 1
);

-- Table: course_schedules
CREATE TABLE IF NOT EXISTS course_schedules (
    id SERIAL PRIMARY KEY,
    date_text VARCHAR(255),
    time_text VARCHAR(255),
    course_title VARCHAR(255),
    description TEXT,
    spots_available INTEGER DEFAULT 10,
    level VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE
);

-- Insertion de la configuration initiale
INSERT INTO site_config (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
