import httpx
import logging
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def send_n8n_notification(payload: Dict[str, Any], webhook_type: str = "reservation"):
    """
    Sends a notification to the n8n webhook with the provided payload.
    This call is asynchronous and should be used with FastAPI's BackgroundTasks.
    webhook_type can be 'reservation' or 'contact'.
    """
    if webhook_type == "contact":
        webhook_url = os.getenv("N8N_CONTACT_WEBHOOK_URL") or os.getenv("N8N_WEBHOOK_URL")
    else:
        webhook_url = os.getenv("N8N_WEBHOOK_URL")
    
    if not webhook_url:
        logger.error(f"Webhook URL not found for type {webhook_type} in environment variables.")
        return False

    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"--- SENDING NOTIFICATION TO N8N ---")
            logger.info(f"URL: {webhook_url}")
            logger.info(f"PAYLOAD: {payload}")
            
            response = await client.post(webhook_url, json=payload, timeout=10.0)
            response.raise_for_status()
            
            logger.info(f"Notification sent successfully. Response: {response.text}")
            return True
    except httpx.HTTPStatusError as e:
        logger.error(f"Error response from n8n: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"Failed to send notification to n8n: {str(e)}")
    
    return False

def format_inquiry_payload(inquiry: Any, service_title: str = None) -> Dict[str, Any]:
    """
    Formats the SQLAlchemy Inquiry object into a dictionary for the webhook payload.
    We explicitly extract attributes to avoid lazy-loading issues.
    """
    try:
        # Extract data explicitly to be sure it's serialized
        data = {
            "id": getattr(inquiry, 'id', 0),
            "type": "Reservation" if (getattr(inquiry, 'service_id', None) or getattr(inquiry, 'booking_date', None)) else "Message",
            "name": str(getattr(inquiry, 'name', "Anonyme")),
            "email": str(getattr(inquiry, 'email', "N/A")),
            "phone": str(getattr(inquiry, 'phone', "N/A") or "N/A"),
            "message": str(getattr(inquiry, 'message', "") or "Pas de message"),
            "service": str(service_title or "Non spécifié"),
            "booking_date": str(getattr(inquiry, 'booking_date', "N/A") or "N/A"),
            "people_count": int(getattr(inquiry, 'people_count', 0) or 0),
            "level": str(getattr(inquiry, 'level', "N/A") or "N/A"),
            "admin_url": "http://mwv.sytes.net/admin/dashboard"
        }
        return data
    except Exception as e:
        logger.error(f"Error formatting inquiry payload: {e}")
        return {"error": str(e), "type": "Error"}

async def send_whatsapp_notification(payload: Dict[str, Any]):
    """
    Sends a WhatsApp notification using a service like UltraMsg.
    Expects WHATSAPP_API_URL, WHATSAPP_TOKEN, and WHATSAPP_TO_PHONE in .env
    """
    url = os.getenv("WHATSAPP_API_URL")
    token = os.getenv("WHATSAPP_TOKEN")
    to_phone = os.getenv("WHATSAPP_TO_PHONE")
    
    if not all([url, token, to_phone]):
        logger.debug("WhatsApp notification skipped: credentials missing in environment.")
        return False

    # Format a human-readable message for WhatsApp
    msg_type = payload.get("type", "Message")
    name = payload.get("name", "Anonyme")
    phone = payload.get("phone", "N/A")
    message = payload.get("message", "")
    service = payload.get("service", "Non spécifié")
    
    text = f"🔔 *Nouveau {msg_type}* 🌊\n\n"
    text += f"👤 *Nom:* {name}\n"
    text += f"📞 *Tel:* {phone}\n"
    text += f"🏄 *Service:* {service}\n"
    
    if payload.get("booking_date") and payload.get("booking_date") != "N/A":
        text += f"📅 *Date:* {payload.get('booking_date')}\n"
        
    if payload.get("people_count"):
        text += f"👥 *Personnes:* {payload.get('people_count')}\n"

    if message and message != "Pas de message":
        text += f"\n📝 *Message:* {message}\n"
        
    text += f"\n🔗 [Dashboard]({payload.get('admin_url')})"

    try:
        async with httpx.AsyncClient() as client:
            # UltraMsg style payload (token, to, body)
            # Most common APIs use these fields or can be adapted
            data = {
                "token": token,
                "to": to_phone,
                "body": text
            }
            # Some APIs might need JSON, others Form Data. UltraMsg uses Form Data (data=) or JSON.
            # We'll use JSON for better compatibility with modern APIs.
            response = await client.post(url, json=data, timeout=10.0)
            
            # If JSON fails, try Form Data (fallback for some older WhatsApp API wrappers)
            if response.status_code >= 400:
                response = await client.post(url, data=data, timeout=10.0)
                
            response.raise_for_status()
            logger.info(f"WhatsApp notification sent successfully.")
            return True
    except Exception as e:
        logger.error(f"Failed to send WhatsApp notification: {str(e)}")
    
    return False
async def send_telegram_notification(payload: Dict[str, Any]):
    """
    Sends a Telegram notification using the Telegram Bot API.
    Expects TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not all([token, chat_id]):
        logger.debug("Telegram notification skipped: credentials missing in environment.")
        return False

    # Format a human-readable message for Telegram (Markdown)
    msg_type = payload.get("type", "Message")
    name = payload.get("name", "Anonyme")
    phone = payload.get("phone", "N/A")
    message = payload.get("message", "")
    service = payload.get("service", "Non spécifié")
    
    text = f"🔔 *Nouveau {msg_type}* 🌊\n\n"
    text += f"👤 *Nom:* {name}\n"
    text += f"📞 *Tel:* {phone}\n"
    text += f"🏄 *Service:* {service}\n"
    
    if payload.get("booking_date") and payload.get("booking_date") != "N/A":
        text += f"📅 *Date:* {payload.get('booking_date')}\n"
        
    if payload.get("people_count"):
        text += f"👥 *Personnes:* {payload.get('people_count')}\n"

    if message and message != "Pas de message":
        text += f"\n📝 *Message:* {message}\n"
        
    text += f"\n[Ouvrir le Dashboard]({payload.get('admin_url')})"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    try:
        async with httpx.AsyncClient() as client:
            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            response = await client.post(url, json=data, timeout=10.0)
            response.raise_for_status()
            logger.info(f"Telegram notification sent successfully.")
            return True
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {str(e)}")
    
    return False
