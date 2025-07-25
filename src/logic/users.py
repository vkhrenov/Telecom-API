import os
from sqlalchemy import select, func, text
from src.models.users import UserSettingsModel, RatesModel, EndpointsModel, UserProfilesModel, EndpointStats
from src.schemas.auth.users import UserEndpointSchema
from src.schemas.stats import DateRange
from datetime import datetime


# Function to check if the user has access to an endpoint -------------------------------------------------------------
async def check_user_access(
    userid: int, 
    endpoint: str,
    session
) -> UserEndpointSchema:
    """
    Check if the user has access to the system.
    
    Args:
        user_id (int): The ID of the user to check.
        session: The database session to use for the query.
    
    Returns:
        bool: True if the user has access, False otherwise.
    """
    pg_timezone = os.getenv("PG_TIMEZONE", "UTC")

    # Set timezone for the session (PostgreSQL only) 
    await session.execute(text(f"SET TIMEZONE = '{pg_timezone}'"))

    result = await session.execute(
        select(UserSettingsModel.productid, EndpointsModel.id, UserProfilesModel.username)
        .join(RatesModel, UserSettingsModel.productid == RatesModel.productid)
        .join(EndpointsModel, RatesModel.endpointid == EndpointsModel.id)
        .join(UserProfilesModel, UserSettingsModel.userid == UserProfilesModel.id)
        .where(
            UserSettingsModel.userid == userid,
            EndpointsModel.endpoint == endpoint,
            RatesModel.dateeff <= func.now(),
            RatesModel.dateexp > func.now(),
            UserSettingsModel.dateeff <= func.now(),
            UserSettingsModel.dateexp > func.now()
        )
        .order_by(UserSettingsModel.productpriority.desc())
    )
    
    ret = result.first()

    if ret:
        return UserEndpointSchema(
            uid=userid,
            username=ret[2],
            endpointid=ret[1],
            endpoint=endpoint,
            ip_address=""
        )
    return None

# Function to check if the user is a superuser  -----------------------------------------------------------  
async def check_superuser_access(
    userid: int,    
    session
) -> bool:
    """Check if the user is a superuser.
    Args:
        userid (int): The ID of the user to check.
        session: The database session to use for the query. 

    Returns:
        bool: True if the user is a superuser, False otherwise.
    """

    result = await session.execute(
        select(UserProfilesModel.username)
        .where(UserProfilesModel.id == userid,
               UserProfilesModel.issuperuser == True)
    )
    ret = result.first()
    if ret:
        return True
    return False

# Function to get username by user ID ----------------------------------------------------------------------
def get_username_by_id (
    userid: int, 
    session
) -> str:

    ret = session.scalar(select(UserProfilesModel.username).where(UserProfilesModel.id == userid))
    if ret is not None:
        return ret[0]
    return None  

# Function to get user statistics for a given date range ----------------------------------------------------
async def get_user_stats(userid: int,
                         dates: DateRange, 
                         session):
    
    pg_timezone = os.getenv("PG_TIMEZONE", "UTC")

    # Convert to datetime objects
    start_date = datetime.strptime(dates.start_date, "%Y-%m-%d %H:%M:%S")
    end_date = datetime.strptime(dates.end_date, "%Y-%m-%d %H:%M:%S")

    # Set timezone for the session (PostgreSQL only)
    await session.execute(text(f"SET TIMEZONE = '{pg_timezone}'"))

    result = await session.execute(
        select(EndpointsModel.endpoint, func.sum(EndpointStats.count))
        .join(EndpointStats, EndpointsModel.id == EndpointStats.endpointid)
        .where(
            EndpointStats.userid == userid,
            EndpointStats.calldate >= start_date,
            EndpointStats.calldate < end_date
        )
        .group_by(EndpointsModel.endpoint)
    )

    ret = result.all()

    return [{"endpoint": row[0], "count": row[1]} for row in ret]

