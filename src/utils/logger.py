
from logging import Logger
from src.schemas.auth.users   import UserEndpointSchema

# Utility functions for logging billling events
def billing_logger (logger: Logger, userinfo: UserEndpointSchema, retvar: str, dn: str,tn: str):
    logger.info(f"BILL,IP={userinfo.ip_address},UID={userinfo.uid},EP={userinfo.endpoint},return=[{retvar}],{dn},{tn}")

# Utility function for logging access events
def access_logger (logger: Logger, user: str, ip_address: str, infostr:str):
    logger.info(f"AUTH,IP={ip_address},USER={user},{infostr}")

# Utility function to extract IP address from request headers
def getIPAddress(request) -> str:
    """
    Extracts the IP address from the request headers or client information.
    """
    ip_address = (
        request.headers.get("X-Real-Ip")
        or request.headers.get("X-Forwarded-For")
        or (request.client.host if request.client else None)
    )
    return ip_address if ip_address else "unknown"