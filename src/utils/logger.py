import logging
import os
import asyncio
import hashlib

from logging import Logger
from src.schemas.auth.users   import UserEndpointSchema
from datetime import datetime
from sqlalchemy import text

interval = int(os.environ.get("BILLING_LOGGER_INTERVAL", 300))
log = logging.getLogger("app")

# Billing logger class to handle periodic log rotation and logging ----------------------------------------------------
class BillingLogger:
    """
    A class to encapsulate billing logging functionality.
    """
    hostname: str
    log_dir = "logs"
    logger: Logger
    log_filename: str = ""
    interval: int = 300  
    worker_id: int
    counter: int = 0

    def __init__(self, interval: int = 300):
        self.interval = interval
        self.hostname = os.environ.get("HOSTNAME","routeapi")
        os.makedirs(self.log_dir, exist_ok = True)  # Ensure logs directory exists
        self.set_new_handler()

    def rotate_handler_periodically(self):
        asyncio.create_task(self._rotate_handler_task())
 
    async def _rotate_handler_task(self):
        while True:
           self.set_new_handler()
           await asyncio.sleep(self.interval)

    # Set a new logging handler with a unique filename     
    def set_new_handler(self):
        self.logger = logging.getLogger("billing") 
        self.worker_id = os.getpid()
        date_str = datetime.now().strftime("%Y%m%d%H%M%S")
        old_log_filename = self.log_filename 
        self.log_filename = f".billing-{date_str}-{self.hostname}-{self.worker_id}.log"
        handler = logging.FileHandler(f"{self.log_dir}/{self.log_filename}")
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        # Remove old handlers
        for h in self.logger.handlers[:]:
            self.logger.removeHandler(h)
            h.close()
        self.logger.addHandler(handler)
        if old_log_filename != "":
            old_path = os.path.join(self.log_dir, old_log_filename)
            new_log_filename = old_log_filename.lstrip(".")
            new_path = os.path.join(self.log_dir, new_log_filename)

            if os.path.exists(old_path):
                if os.path.getsize(old_path) == 0:
                    os.remove(old_path)
                else:          
                    os.rename(old_path, new_path)

    # Log billing information for a user endpoint call
    def log_billing(self, userinfo: UserEndpointSchema, retvar: str, dn: str, tn: str):
        """
        Logs billing information for a user endpoint call.
        """        
        self.counter += 1
        log = f"BILL\tIP={userinfo.ip_address}\tID={userinfo.username}\tEP={userinfo.endpoint}\treturn=[{retvar}]\t{dn}\t{tn}"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        eventid = hashlib.sha256((log + str(self.counter) + timestamp).encode()).hexdigest()
        self.logger.info(f"{log}\t{eventid}")

#---------------------------------------------------------
billing_logger = BillingLogger(interval)
#---------------------------------------------------------

# Utility function for logging access events ----------------------------------------------------
def access_logger (logger: Logger, user: str, ip_address: str, infostr:str):
    logger.info(f"AUTH,IP={ip_address},USER={user},{infostr}")

# Utility function to extract IP address from request headers -----------------------------------
def getIPAddress(request) -> str:
    """
    Extracts the IP address from the request headers or client information.
    """

    ip_address = request.headers.get("X-Real-IP")
    if not ip_address:
        ip_address = request.headers.get("X-Forwarded-For")
    if not ip_address:
        ip_address = request.headers.get("X-Cluster-Client-Ip")
    if not ip_address:
        ip_address = request.client.host    
    return ip_address if ip_address else "unknown"
