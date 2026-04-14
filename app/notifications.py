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

async def send_n8n_notification(payload: Dict[str, Any]):
    """
    Sends a notification to the n8n webhook with the provided payload.
    This call is asynchronous and should be used with FastAPI's BackgroundTasks.
    """
    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    
    if not webhook_url:
        logger.error("N8N_WEBHOOK_URL not found in environment variables.")
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
            "type": "Reservation" if getattr(inquiry, 'service_id', None) else "Message",
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
