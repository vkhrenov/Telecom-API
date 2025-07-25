from fastapi import Depends, HTTPException, status, Request

from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.jwt import security
from src.logic.users import check_user_access, check_superuser_access
from src.schemas.auth.users import UserEndpointSchema, UserInfoSchema
from authx.schema import TokenPayload
from src.utils.logger import getIPAddress
from src.databases.database_session import get_async_session
import  src.databases.redis_cache


import logging

logger = logging.getLogger(__name__)

#async def get_session() -> AsyncGenerator[AsyncSession]:
#   async with database_session.get_async_session() as session:
#        yield session
#        # Ensure the session is closed after use
#        await session.close()
        
# Function to require user endpoint access -------------------------------------------------------------------------
def require_endpoint_access():
    async def inner_require_endpoint_access(payload: TokenPayload = Depends(security.access_token_required),
                                            session: AsyncSession = Depends(get_async_session),
                                            request: Request = None) -> UserEndpointSchema:
        
        endpoint = request.scope["endpoint"].__name__
        ip_address = getIPAddress(request)
               
        if (payload.sub is None or
            payload.sub == "" or
            payload.sub == "0"):
            raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is not authenticated"
            )
        uid = int(payload.sub) 

        user = await check_user_access(
            userid=uid, 
            endpoint=endpoint,
            session=session
        )
   
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to this endpoint is forbidden"
            )

        # Increment the endpoint call count in Redis
        redis_key = f"epcalls:{uid}"
        await src.databases.redis_cache.redis_client.hincrby(redis_key, user.endpointid, 1)
        
        return UserEndpointSchema(
            uid=uid,
            username=user.username,
            endpointid=user.endpointid,
            endpoint=endpoint,
            ip_address=ip_address
        )
        
    return inner_require_endpoint_access 

#  Function to require user info access -------------------------------------------------------------------------
def require_info_access():
    async def inner_require_info_access(payload: TokenPayload = Depends(security.access_token_required),
                                        session: AsyncSession = Depends(get_async_session),
                                        request: Request = None) -> UserInfoSchema:
        
       
        ip_address = getIPAddress(request)
               
        if (payload.sub is None or
            payload.sub == "" or
            payload.sub == "0"):
            raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is not authenticated"
            )
        uid = int(payload.sub)
        username = payload.uname 

        su = await check_superuser_access(userid=uid,session=session)

        return UserInfoSchema(
            uid=uid,
            username=username,
            is_superuser=su,
            ip_address=ip_address
        )
        
    return inner_require_info_access 