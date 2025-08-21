import logging

from fastapi import APIRouter, HTTPException, Response, Depends, Request, status
from src.schemas.auth.users import UserLoginSchema, UserPasswordChangeSchema
from src.auth.jwt import security, config
from src.auth.credentials import check_credentials, update_user_password
from sqlalchemy.ext.asyncio import AsyncSession
from authx.schema import RequestToken
from fastapi.security.utils import get_authorization_scheme_param
from src.utils.logger import access_logger, getIPAddress
from src.databases.database_session import get_async_session

logger = logging.getLogger(__name__)

router = APIRouter()

# Endpoint for user login ------------------------------------------------------------------------------------------ 
@router.post("/login", summary="User login")
async def login(creds: UserLoginSchema, request: Request, response: Response, session: AsyncSession = Depends(get_async_session)):

    """
    Endpoint for user login
    """
    ip_address = getIPAddress(request)
    user = await check_credentials(creds, session)
    if user is not None:
        if user.isactive is False:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="User is inactive")

    # Create access token and set it in the response cookie
        userid=str(user.id)          
        access_token  = security.create_access_token(uid=userid, data={"uname": user.username}, fresh=True)
        refresh_token = security.create_refresh_token(uid=userid, data={"uname": user.username})

        security.set_access_cookies(response=response,  token=access_token)
        security.set_refresh_cookies(response=response, token=refresh_token)
 
        response.set_cookie(config.JWT_ACCESS_COOKIE_NAME, access_token)
        response.set_cookie(config.JWT_REFRESH_COOKIE_NAME, refresh_token)  

        access_logger(logger, userid, ip_address, f"User {user.username} logged in successfully")
        return {"access_token": access_token , "token_type": "bearer", "expires_in": config.JWT_ACCESS_TOKEN_EXPIRES.total_seconds(),
                "refresh_token": refresh_token  }
    access_logger(logger, creds.login, ip_address, f"User failed to log in")
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

# Endpoint to change user password -----------------------------------------------------------------------------
@router.post("/change_password", summary="Change user password")
async def change_password(creds: UserPasswordChangeSchema, request: Request, response: Response, session: AsyncSession = Depends(get_async_session),):
    """
    Endpoint to change user password
    """
    ip_address = getIPAddress(request)
    user = await check_credentials(UserLoginSchema(login=creds.login, password=creds.password), session)
    if user is not None:
        if user.isactive is False:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="User is inactive")

    # Update the user's password in the database
        userid = str(user.id)
        state = await update_user_password(creds.login, creds.new_password, session)
        if state is False:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Failed to change password")
        access_logger(logger, userid, ip_address, f"User {user.username} changed password successfully")
        return {"detail": "Password changed successfully"}
    access_logger(logger, creds.login, ip_address, f"User failed to change password")
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")  

# Endpoint for refreshing access token ---------------------------------------------------------------------------
@router.post("/refresh", summary="Refresh access token")
async def refresh_token(request: Request, response: Response):

    """
    Endpoint to refresh the access token
    """
    ip_address = getIPAddress(request)
    auth_header = request.headers.get("Authorization")
    if auth_header:
        scheme, refresh_token = get_authorization_scheme_param(auth_header)
        if refresh_token == '':
            refresh_token, x = get_authorization_scheme_param(auth_header)

    try:
        try:
            refresh_payload = await security.refresh_token_required(request)
        
        except Exception as header_error:

            if not refresh_token:
                raise header_error

            # Manually decode and verify the refresh token
            token =  RequestToken (
                token = refresh_token,
                type = 'refresh',
                location = 'headers'              
            )
            refresh_payload = security.verify_token(token, verify_csrf=False)

        # Create a new access and refresh token
        userid = refresh_payload.sub
        uname = refresh_payload.uname

        access_token  = security.create_access_token(uid=userid, data={"uname": uname}, fresh=False)
        refresh_token = security.create_refresh_token(uid=userid, data={"uname": uname} )

        response.set_cookie(config.JWT_ACCESS_COOKIE_NAME, access_token)
        response.set_cookie(config.JWT_REFRESH_COOKIE_NAME, refresh_token) 

        security.set_access_cookies (response=response, token=access_token)
        security.set_refresh_cookies(response=response, token=refresh_token)

        access_logger(logger, userid, ip_address, f"User {uname} refreshed access token successfully")
        return {"access_token": access_token , "token_type": "bearer", "expires_in": config.JWT_ACCESS_TOKEN_EXPIRES.total_seconds(),
                "refresh_token": refresh_token}
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
