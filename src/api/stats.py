import logging

from fastapi import APIRouter, Depends, Query, Request, HTTPException, status
from typing  import Annotated
from src.schemas.stats import DateRange
from src.schemas.auth.users import UserInfoSchema
from sqlalchemy.ext.asyncio import AsyncSession
from src.api import deps
from src.logic.users import get_user_stats
from src.utils.logger import access_logger
from src.databases.database_session import get_async_session

logger = logging.getLogger(__name__)
SU_HEADER = "X-User-ID"
router = APIRouter()

# Endpoint to get usage statistics for a given date range --------------------------------------------------------------
@router.get("/endpointstats", summary="Get usage statistics") 
async def get_endpointstats(dates: Annotated[DateRange, Query(description="Date range for statistics")],
                    request: Request,
                    session: AsyncSession = Depends(get_async_session),
                    userinfo: UserInfoSchema = Depends(deps.require_info_access())):
    """
    Endpoint to get usage statistics for a given date range.
    """
    userid = int(userinfo.uid) if userinfo.uid else None
    if userinfo.is_superuser:
        uidsu = request.headers.get(SU_HEADER)
        if uidsu is not None and str(uidsu).isdigit():
            userid = int(uidsu)

    if userid is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Valid User ID is required for statistics")

    stats = await get_user_stats(userid, dates, session)
    access_logger(logger, userinfo.username, userinfo.ip_address, f"User requested statistics from {dates.start_date} to {dates.end_date}")
    if not stats:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No statistics found for the given date range")
    return stats
