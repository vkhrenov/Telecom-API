from typing import Optional, List, Any
from pydantic import BaseModel

# Schema for handling request parameters for customer list endpoint -------------------------
class RequestCustomerListSchema(BaseModel):
    filter: Optional[str] = None  
    range: Optional[str] = None
    sort: Optional[str] = None