import os
import sys
import time
import requests
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | CANTARELLA | %(message)s")
logger = logging.getLogger(__name__)

# Load .env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".env"))
if not os.path.exists(env_path):
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(env_path)

MASTER_URL = os.getenv("MASTER_URL", "http://127.0.0.1:7777").rstrip('/')
HARVESTER_API_SECRET = os.getenv("HARVESTER_API_SECRET", "")
CANTARELLA_API_URL = "http://127.0.0.1:8742/cloudflare"
SITEKEY = "0x4AAAAAACHcU3E6UUbmv3p-"  # Primary Winna sitekey

def _api_headers():
    headers = {"Content-Type": "application/json"}
    if HARVESTER_API_SECRET:
        headers["Authorization"] = f"Bearer {HARVESTER_API_SECRET}"
    return headers

def check_pool_status():
    try:
        resp = requests.get(
            f"{MASTER_URL}/api/status",
            headers=_api_headers(),
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json()
        return {"need_more": True}
    except Exception as e:
        logger.warning("Master status check failed: %s", e)
        return {"need_more": True}

def push_token(token):
    try:
        resp = requests.post(
            f"{MASTER_URL}/api/push-token",
            json={"token": token},
            headers=_api_headers(),
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            logger.info("✅ Token pushed to master | Pool: %d/%d", data.get("pool", 0), data.get("cap", 0))
            return True
        else:
            logger.warning("Master rejected token: HTTP %d - %s", resp.status_code, resp.text)
            return False
    except Exception as e:
        logger.error("Failed to push token to master: %s", e)
        return False

def generate_cantarella_token():
    logger.info("🔄 Requesting token from CANTARELLA...")
    try:
        resp = requests.post(CANTARELLA_API_URL, json={
            "mode": "turnstile",
            "domain": "https://winna.com",
            "siteKey": SITEKEY
        }, timeout=45)
        
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token")
            if token:
                logger.info("🎉 Harvested token: %s...%s", token[:15], token[-15:])
                return token
        logger.warning("CANTARELLA failed: HTTP %d - %s", resp.status_code, resp.text)
        return None
    except Exception as e:
        logger.error("Could not reach CANTARELLA at %s: %s", CANTARELLA_API_URL, e)
        return None

def main():
    logger.info("=========================================")
    logger.info("CANTARELLA Remote Harvester Bridge Started")
    logger.info("Master API: %s", MASTER_URL)
    logger.info("CANTARELLA API: %s", CANTARELLA_API_URL)
    logger.info("=========================================")

    while True:
        status = check_pool_status()
        
        if status.get("need_more"):
            token = generate_cantarella_token()
            if token:
                push_token(token)
            else:
                logger.info("⏳ Waiting 5s before retrying CANTARELLA...")
                time.sleep(5)
        else:
            # Pool is full, sleep and check again
            time.sleep(3)

if __name__ == "__main__":
    main()
