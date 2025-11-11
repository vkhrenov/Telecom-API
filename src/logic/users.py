import os, logging

from sqlalchemy import select, func, text, delete
from src.models.users import UserSettingsModel, RatesModel, EndpointsModel, UserSettingsModel
from src.models.users import UserProfilesModel, EndpointStatsModel, UserProfilesDelModel
from src.schemas.auth.users import UserEndpointSchema
from src.schemas.stats import DateRange
from src.logic.utilities import normalize_date_for_pg, normalize_str_date, normalize_str_expdate
from datetime import datetime

logger = logging.getLogger(__name__)

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
        select(UserSettingsModel.productid, EndpointsModel.id, UserProfilesModel.username, UserSettingsModel.ratio, RatesModel.rate)
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
            ip_address="",
            productid=ret[0],
            ratio=ret[3],
            rate=ret[4]
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
        select(EndpointsModel.endpoint, func.sum(EndpointStatsModel.count))
        .join(EndpointStatsModel, EndpointsModel.id == EndpointStatsModel.endpointid)
        .where(
            EndpointStatsModel.userid == userid,
            EndpointStatsModel.calldate >= start_date,
            EndpointStatsModel.calldate < end_date
        )
        .group_by(EndpointsModel.endpoint)
    )

    ret = result.all()

    return [{"endpoint": row[0], "count": row[1]} for row in ret]

# Function to get a list of users with pagination -----------------------------------------------------------
async def get_users(session, range_from=0, range_to=24, filter_dict={}, sort_list=[]):

    query = select(UserProfilesModel)

    if sort_list and isinstance(sort_list, list) and len(sort_list) == 2:
        field_name, order = sort_list
        field = getattr(UserProfilesModel, field_name, None)
       
        if field is not None:
            if order.upper() == "ASC":
                query = query.order_by(field.asc())
            elif order.upper() == "DESC":
                query = query.order_by(field.desc())
   
    if filter_dict and isinstance(filter_dict, dict):
        for field_name, value in filter_dict.items():
            field = getattr(UserProfilesModel, field_name, None)
            
            if field == UserProfilesModel.id:
                ids = set()
                if isinstance(value, (list, tuple, set)):
                    candidates = value
                elif isinstance(value, str):
                    candidates = [v.strip() for v in value.split(",") if v.strip()]
                else:
                    candidates = [value]

                for v in candidates:
                    try:
                        ids.add(int(v))
                    except (ValueError, TypeError):
                        # skip non-integer candidates
                        continue

                if ids:
                    query = query.where(UserProfilesModel.id.in_(ids))
 
                continue
            else:    
                if field is not None and value:
                    query = query.where(field.ilike(f"%{value}%"))

    result = await session.execute(query)
    ret = result.all()
    total_count = len(ret)

    paginated_ret = ret[range_from:range_to + 1]
   
    data = [
        {
            "id": row[0].id,
            "username": row[0].username,
            "name": row[0].name,
            "login": row[0].login,
            "email": row[0].email,
            "isactive": row[0].isactive,
            "issuperuser": row[0].issuperuser,
            "datecreated": normalize_str_date(str(row[0].datecreated)),
            "datedeactivated": normalize_str_expdate(str(row[0].datedeactivated)),
        }
        for row in paginated_ret
    ]

    return {
        "data": data,
        "total": total_count
    }

# Function to create a new user -------------------------------------------------------------------------------
async def create_user(session, user_data):
    pg_timezone = os.getenv("PG_TIMEZONE", "UTC")

    # Hash the password using PostgreSQL crypt and gen_salt('md5')
    password_plain = user_data.get("password", "")
    result = await session.execute(
        text("SELECT crypt(:password, gen_salt('md5'))"),
        {"password": password_plain}
    )
    hashed_password = result.scalar()


    new_user = UserProfilesModel(
        username=user_data.get("username"),
        name=user_data.get("name"),
        login=user_data.get("login"),
        password=hashed_password,
        email=user_data.get("email"),
        isactive=user_data.get("isactive", True),
        issuperuser=user_data.get("issuperuser", False)
    )

    # Set timezone for the session (PostgreSQL only) 
    await session.execute(text(f"SET TIMEZONE = '{pg_timezone}'"))

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return {
        "id": new_user.id,
        "username": new_user.username,
        "name": new_user.name,
        "login": new_user.login,
        "email": new_user.email,
        "isactive": new_user.isactive,
        "issuperuser": new_user.issuperuser,
        "datecreated": normalize_str_date(str(new_user.datecreated)),
        "datedeactivated": normalize_str_expdate(str(new_user.datedeactivated)),
    }

# Function to update an existing user -------------------------------------------------------------------------------
async def update_user(session, user_id, user_data):
    pg_timezone = os.getenv("PG_TIMEZONE", "UTC")

    if user_data.get("datedeactivated"):
        user_data["datedeactivated"] = normalize_date_for_pg(user_data["datedeactivated"])
    else:
        user_data["datedeactivated"] = datetime(2222, 1, 1, 0, 0, 0)

    # Fetch the existing user
    existing_user = await session.get(UserProfilesModel, user_id)
    if not existing_user:
        raise ValueError("User not found")

    # Update fields if they are provided in user_data
    for field in ["username", "name", "login", "email", "isactive", "issuperuser", "datedeactivated"]:
        if field in user_data:
            setattr(existing_user, field, user_data[field])
    
    # If password is provided, hash it using PostgreSQL crypt and gen_salt('md5')
    if "password" in user_data and user_data["password"] :
        password_plain = user_data["password"]
        result = await session.execute(
            text("SELECT crypt(:password, gen_salt('md5'))"),
            {"password": password_plain}
        )
        hashed_password = result.scalar()
        existing_user.password = hashed_password

    # Update user settings if provided
    if "usersettings" in user_data:
        result = await session.execute(
            select(UserSettingsModel.id).where(UserSettingsModel.userid == user_id)
        )
        existing_ids = {row[0] for row in result.all()}
        incoming_ids = set()

        for us in user_data["usersettings"]:
            setting_id = us.get("id")
            us["dateeff"]=normalize_date_for_pg(us["dateeff"])
            if us["dateexp"] == "" or us["dateexp"] is None:
                us["dateexp"] = datetime(2222, 1, 1, 0, 0, 0)
            else:                           
                us["dateexp"]=normalize_date_for_pg(us["dateexp"])

            if setting_id:
                incoming_ids.add(setting_id)
                existing_setting = await session.get(UserSettingsModel, setting_id)
                if existing_setting:
                    for field in ["note", "ratio", "productpriority", "dateeff", "dateexp", "productid"]:
                        if field in us:
                            setattr(existing_setting, field, us[field])
            else:
                # Create new user setting
                new_setting = UserSettingsModel(
                    userid=user_id,
                    productid=us.get("productid"),
                    note=us.get("note"),
                    ratio=us.get("ratio"),
                    productpriority=us.get("productpriority"),
                    dateeff=us.get("dateeff"),
                    dateexp=us.get("dateexp")
                )
                session.add(new_setting)

        # Remove existing user settings that were not included in incoming payload
        
        ids_to_delete = list(existing_ids - incoming_ids)
        if ids_to_delete:
            await session.execute(
                delete(UserSettingsModel).where(UserSettingsModel.id.in_(ids_to_delete))
            )

    # Set timezone for the session (PostgreSQL only) 
    await session.execute(text(f"SET TIMEZONE = '{pg_timezone}'"))

    session.add(existing_user)
    await session.commit()
    await session.refresh(existing_user)
    
    return {
        "id": existing_user.id,
        "username": existing_user.username,
        "name": existing_user.name,
        "login": existing_user.login,
        "email": existing_user.email,
        "isactive": existing_user.isactive,
        "issuperuser": existing_user.issuperuser,
        "datecreated": normalize_str_date(str(existing_user.datecreated)),
        "datedeactivated": normalize_str_expdate(str(existing_user.datedeactivated)),
    }

# Function to get a single user by ID -------------------------------------------------------------------------------
async def get_user(session, user_id):

    result = await session.execute(
        select(UserProfilesModel)
        .where(UserProfilesModel.id == user_id)
    )
    ret = result.first()

    if not ret:
        return []

    user = ret[0]

    query = select(UserSettingsModel).where(UserSettingsModel.userid == user_id).order_by(UserSettingsModel.productpriority.desc())
    result = await session.execute(query)
    ret = result.all()
    usersettings = [
        {
            "id": row[0].id,
            "productid": row[0].productid,
            "note": row[0].note,
            "ratio": row[0].ratio,
            "productpriority": row[0].productpriority,
            "dateeff": normalize_str_date(str(row[0].dateeff)),
            "dateexp": normalize_str_expdate(str(row[0].dateexp)),
        }
        for row in ret
    ]

    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "login": user.login,
        "email": user.email,
        "isactive": user.isactive,
        "issuperuser": user.issuperuser,
        "datecreated": normalize_str_date(str(user.datecreated)),
        "datedeactivated": normalize_str_expdate(str(user.datedeactivated)),
        "usersettings": usersettings
    }

# Function to delete a user by ID -------------------------------------------------------------------------------
async def delete_user(session, user_id):
    pg_timezone = os.getenv("PG_TIMEZONE", "UTC")

    # Fetch the existing user
    existing_user = await session.get(UserProfilesModel, user_id)
    if not existing_user:
         return {"error": "User not found"}
    
    # Create a record in user_profiles_del before deleting
    deleted_user = UserProfilesDelModel(
        username=existing_user.username,
        name=existing_user.name,
        login=existing_user.login,
        password=existing_user.password,
        email=existing_user.email,
        isactive=existing_user.isactive,
        issuperuser=existing_user.issuperuser,
        datecreated=existing_user.datecreated,
        datedeactivated=existing_user.datedeactivated
    )

    # Set timezone for the session (PostgreSQL only) 
    await session.execute(text(f"SET TIMEZONE = '{pg_timezone}'"))
    session.add(deleted_user)
    await session.execute(delete(UserSettingsModel).where(UserSettingsModel.userid == user_id))
    await session.execute(delete(UserProfilesModel).where(UserProfilesModel.id == user_id))
    await session.commit()

    return {"id": existing_user.id, 
            "username": existing_user.username, 
            "name": existing_user.name,
            "login": existing_user.login,
            "email": existing_user.email,
            "isactive": existing_user.isactive,
            "issuperuser": existing_user.issuperuser,
            "datecreated": normalize_str_date(str(existing_user.datecreated)),
            "datedeactivated": normalize_str_expdate(str(existing_user.datedeactivated))
            }
