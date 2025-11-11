import os, logging

logger = logging.getLogger(__name__)

from sqlalchemy import select, text
from src.models.users import UserProfilesModel, EndpointsModel, EndpointStatsModel
from sqlalchemy import func

from datetime import datetime, timedelta
from src.logic.utilities import normalize_date_for_pg, normalize_str_date, normalize_str_expdate

# Function to get a list of users with pagination -----------------------------------------------------------
async def get_users_statinfo(session, range_from=0, range_to=24, filter_dict={}, sort_list=[]):

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
   
    data = []
    for row in paginated_ret:
        (ld_dips, ld_amount) = await get_ld_totals(row[0].id, session)
        (dtd_dips,dtd_amount) = await get_dtd_count(row[0].id, session)
        (mtd_dips,mtd_amount) = await get_mtd_count(row[0].id, session)
        (lastm_dips,lastm_amount) = await get_lastm_count(row[0].id, session)
        data.append({
            "id": row[0].id,
            "name": row[0].name,
            "isactive": row[0].isactive,
            "ld_count": ld_dips,
            "ld_amount": ld_amount,
            "dtd_count": dtd_dips,
            "dtd_amount": dtd_amount,
            "mtd_count": mtd_dips,
            "mtd_amount": mtd_amount,
            "lastm_count": lastm_dips,
            "lastm_amount": lastm_amount
        })

    return {
        "data": data,
        "total": total_count
    }

# Function to get a specific statement by ID -----------------------------------------------------------
async def get_statement(session,user_id):

    result = await session.execute(
        select(UserProfilesModel)
        .where(UserProfilesModel.id == user_id)
    )
    ret = result.first()

    if not ret:
        return []

    user = ret[0]

    result = await session.execute(
        select(func.max(EndpointStatsModel.calldate))
        .where(EndpointStatsModel.userid == user_id)
    )
    last_call = result.scalar()
    if last_call:
        last_call_date = normalize_str_date(str(last_call))
    else:
         last_call_date = None

    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "email": user.email,
        "isactive": user.isactive,
        "issuperuser": user.issuperuser,
        "datecreated": normalize_str_date(str(user.datecreated)),
        "datedeactivated": normalize_str_expdate(str(user.datedeactivated)),
        "last_call_date": last_call_date
    }

# Function to get user summaries with pagination -----------------------------------------------------------
async def get_user_summaries(session, range_from=0, range_to=24, filter_dict={}):
    pg_timezone = os.getenv("PG_TIMEZONE", "UTC")
    # Set timezone for the session (PostgreSQL only)
    await session.execute(text(f"SET TIMEZONE = '{pg_timezone}'"))

    query = select(EndpointsModel.id, EndpointsModel.endpoint, EndpointsModel.description, func.sum(EndpointStatsModel.count), func.sum(EndpointStatsModel.amount)).join(EndpointStatsModel, EndpointsModel.id == EndpointStatsModel.endpointid)
           
    if filter_dict and isinstance(filter_dict, dict):
        for field_name, value in filter_dict.items():       
            if field_name ==  "id":
                 query = query.where(EndpointStatsModel.userid == int(value))
            if field_name ==  "summaryType":
                summary_type = value
                now = datetime.now()
                if summary_type == "mtd":
                    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    query = query.where(EndpointStatsModel.calldate >= start_date)
                elif summary_type == "lastm":
                    first_day_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    last_month_end = first_day_of_current_month - timedelta(seconds=1)
                    last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    query = query.where(EndpointStatsModel.calldate >= last_month_start, EndpointStatsModel.calldate <= last_month_end)
                elif summary_type == "dtd":
                    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    query = query.where(EndpointStatsModel.calldate >= start_date)
                elif summary_type == "ld":
                    start_date = now - timedelta(days=1)
                    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    query = query.where(EndpointStatsModel.calldate >= start_date, EndpointStatsModel.calldate < end_date)
                else:
                    # If summaryType is unrecognized, the type is from and to dates divided by |
                    try:
                        from_str, to_str = summary_type.split("|")
                        from_date = normalize_date_for_pg(from_str)
                        to_date = normalize_date_for_pg(to_str)
                        query = query.where(EndpointStatsModel.calldate >= from_date, EndpointStatsModel.calldate < to_date)
                    except Exception:
                        return {"data": [], "total": 0}
                        
    query = query.order_by(EndpointsModel.endpoint).group_by(EndpointsModel.id, EndpointsModel.endpoint, EndpointsModel.description)
    result = await session.execute(query)
    ret = result.all()
    total_count = len(ret)

    paginated_ret = ret[range_from:range_to + 1]
   
    data = [
        { 
            "id": row[0],
            "endpoint": row[1],
            "description": row[2],
            "dips": row[3] if row[3] is not None else 0,
            "amount": float(row[4]) if row[4] is not None else 0.0
        }
        for row in paginated_ret
    ]

    total_dips = 0
    total_amount = 0.0

    for row in ret:
        total_dips += row[3] if row[3] is not None else 0
        total_amount += float(row[4]) if row[4] is not None else 0.0

    data.append({
        "id": "",
        "endpoint": "",
        "description": "",
        "dips": total_dips,
        "amount": total_amount
    })    
    
    return {
        "data": data,
        "total": total_count
    }

# Function to get monthly (30 days back from today ) summaries excluding test users -----------------------------------------------------------
async def get_monthly_summaries(session):
    pg_timezone = os.getenv("PG_TIMEZONE", "UTC")
    # Set timezone for the session (PostgreSQL only)
    await session.execute(text(f"SET TIMEZONE = '{pg_timezone}'"))

    now = datetime.now()
    start_date = now - timedelta(days=30)

    query = (
        select(
            func.sum(EndpointStatsModel.count),
            func.sum(EndpointStatsModel.amount)
        )
        .select_from(UserProfilesModel)
        .join(EndpointStatsModel, UserProfilesModel.id == EndpointStatsModel.userid)
        .where(
            EndpointStatsModel.calldate >= start_date,
            ~UserProfilesModel.username.like('test%')
        )
    )

    result = await session.execute(query)
    ret = result.first()
    data = {
        "monthly_dips": ret[0] if ret[0] is not None else 0,
        "monthly_amount": round(float(ret[1]), 3) if ret[1] is not None else 0.0
    }

    return data

# Function to get monthly stats per day with pagination -----------------------------------------------------------
async def get_monthly_stats_pday(session, range_from=0, range_to=50, filter_dict={},sort_list=[]):
    pg_timezone = os.getenv("PG_TIMEZONE", "UTC")
    # Set timezone for the session (PostgreSQL only)
    await session.execute(text(f"SET TIMEZONE = '{pg_timezone}'"))

    query = select(
        func.date(EndpointStatsModel.calldate).label("day"),
        func.sum(EndpointStatsModel.count).label("total_count"),
        func.sum(EndpointStatsModel.amount).label("total_amount")
    ) .select_from(UserProfilesModel).join(EndpointStatsModel, UserProfilesModel.id == EndpointStatsModel.userid).where(
            ~UserProfilesModel.username.like('test%')
        )

    if filter_dict and isinstance(filter_dict, dict):
        for field_name, value in filter_dict.items():       
            if field_name ==  "userid":
                 query = query.where(EndpointStatsModel.userid == int(value))
            elif field_name ==  "endpointid":
                 query = query.where(EndpointStatsModel.endpointid == int(value))
            elif field_name ==  "from_date":
                 from_date = normalize_date_for_pg(value)
                 query = query.where(EndpointStatsModel.calldate >= from_date)
            elif field_name ==  "to_date":
                 to_date = normalize_date_for_pg(value)
                 query = query.where(EndpointStatsModel.calldate < to_date)
                  
    query = query.group_by(
        func.date(EndpointStatsModel.calldate)
    )

    query = query.order_by(func.date(EndpointStatsModel.calldate).asc())
    result = await session.execute(query)
    ret = result.all()
    total_count = len(ret)

    paginated_ret = ret[range_from:range_to + 1]
   
    data = [
        { 
            "id":  int(row[0].strftime("%Y%m%d")),
            "date": row[0],
            "dips": row[1] if row[1] is not None else 0,
            "amount": float(row[2]) if row[2] is not None else 0.0
        }
        for row in paginated_ret
    ]

    return {
        "data": data,
        "total": total_count
    }

# Function to get daily stats per 5 min with pagination -----------------------------------------------------------
async def get_daily_stats_p5(session, range_from=0, range_to=300, filter_dict={},sort_list=[]):
    pg_timezone = os.getenv("PG_TIMEZONE", "UTC")
    # Set timezone for the session (PostgreSQL only)
    await session.execute(text(f"SET TIMEZONE = '{pg_timezone}'"))

    time_bucket = func.date_trunc(
        "minute",
        func.date_trunc("hour", EndpointStatsModel.calldate)
        + func.floor(func.extract("minute", EndpointStatsModel.calldate) / 5 + 1)
        * text("interval '5 minutes'"),
    )

    query = select(
        time_bucket.label("time_interval"),
        func.sum(EndpointStatsModel.count).label("total_count"),
        func.sum(EndpointStatsModel.amount).label("total_amount")
    ).select_from(UserProfilesModel).join(EndpointStatsModel, UserProfilesModel.id == EndpointStatsModel.userid).where(
            ~UserProfilesModel.username.like('test%')
        )

    if filter_dict and isinstance(filter_dict, dict):
        for field_name, value in filter_dict.items():       
            if field_name ==  "userid":
                 query = query.where(EndpointStatsModel.userid == int(value))
            elif field_name ==  "endpointid":
                 query = query.where(EndpointStatsModel.endpointid == int(value))
            elif field_name ==  "from_date":
                 from_date = normalize_date_for_pg(value)
                 query = query.where(EndpointStatsModel.calldate >= from_date)
            elif field_name ==  "to_date":
                 to_date = normalize_date_for_pg(value)
                 query = query.where(EndpointStatsModel.calldate < to_date)
                  
    query = query.group_by(time_bucket)
    query = query.order_by(time_bucket.asc())
    result = await session.execute(query)
    ret = result.all()
    total_count = len(ret)

    paginated_ret = ret[range_from:range_to + 1]
   
    data = [
        { 
            "id":  int(row[0].strftime("%Y%m%d%H%M")),
            "date": row[0].strftime("%Y-%m-%d %H:%M:%S"),
            "dips": row[1] if row[1] is not None else 0,
            "amount": float(row[2]) if row[2] is not None else 0.0
        }
        for row in paginated_ret
    ]

    return {
        "data": data,
        "total": total_count
    }

# Function to get the latest dip information -----------------------------------------------------------
async def get_latest_information(session):

    query =  select(func.max(EndpointStatsModel.calldate))
    result = await session.execute(query)
       
    ret = result.first()

    if not ret:
        return {}
    
    query = select(
        func.sum(EndpointStatsModel.count).label("total_count"),
        func.sum(EndpointStatsModel.amount).label("total_amount")
    ) .select_from(UserProfilesModel).join(EndpointStatsModel, UserProfilesModel.id == EndpointStatsModel.userid).where(
            ~UserProfilesModel.username.like('test%')
        ).where(
            EndpointStatsModel.calldate >= datetime.now() - timedelta(days=1)
        )
    result = await session.execute(query)
    rettotal = result.first()
    
    return {
        "latest_dip": normalize_str_date(str(ret[0])) if ret[0] else None,
        "daily_dips": rettotal[0] if rettotal[0] is not None else 0,
        "daily_amount": round(float(rettotal[1]), 3) if rettotal[1] is not None else 0.0       
    }
# -------------------------------------------------------------------------------------------------------
# Helper function to get MTD count for a user -----------------------------------------------------------
async def get_mtd_count(user_id, session):

    pg_timezone = os.getenv("PG_TIMEZONE", "UTC")
    start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Set timezone for the session (PostgreSQL only)
    await session.execute(text(f"SET TIMEZONE = '{pg_timezone}'"))
    query = (
        select(func.sum(EndpointStatsModel.count), func.sum(EndpointStatsModel.amount))
        .where(
            EndpointStatsModel.userid == user_id,
            EndpointStatsModel.calldate >= start_date
        )
    )

    ret = await session.execute(query)
    result = ret.first()
    mtd_dips = result[0] if result[0] is not None else 0
    mtd_amount = float(result[1]) if result[1] is not None else 0.0
    return (mtd_dips, mtd_amount) 

# Helper function to get Last Month count for a user -----------------------------------------------------------
async def get_lastm_count(user_id, session):

    pg_timezone = os.getenv("PG_TIMEZONE", "UTC")
    now = datetime.now()
    first_day_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_end = first_day_of_current_month - timedelta(seconds=1)
    last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Set timezone for the session (PostgreSQL only)
    await session.execute(text(f"SET TIMEZONE = '{pg_timezone}'"))
    query = (
        select(func.sum(EndpointStatsModel.count), func.sum(EndpointStatsModel.amount))
        .where(
            EndpointStatsModel.userid == user_id,
            EndpointStatsModel.calldate >= last_month_start,
            EndpointStatsModel.calldate <= last_month_end
        )
    )

    ret = await session.execute(query)
    result = ret.first()
    lastm_dips = result[0] if result[0] is not None else 0
    lastm_amount = float(result[1]) if result[1] is not None else 0.0
    return (lastm_dips, lastm_amount) 
    
# Helper function to get DTD count for a user -----------------------------------------------------------
async def get_dtd_count(user_id, session):

    pg_timezone = os.getenv("PG_TIMEZONE", "UTC")
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Set timezone for the session (PostgreSQL only)
    await session.execute(text(f"SET TIMEZONE = '{pg_timezone}'"))
    query = (
        select(func.sum(EndpointStatsModel.count), func.sum(EndpointStatsModel.amount))
        .where(
            EndpointStatsModel.userid == user_id,
            EndpointStatsModel.calldate >= start_date
        )
    )

    ret = await session.execute(query)
    result = ret.first()
    dtd_dips = result[0] if result[0] is not None else 0
    dtd_amount = float(result[1]) if result[1] is not None else 0.0
    return (dtd_dips, dtd_amount) 

# Helper function to get Last Day count for a user -----------------------------------------------------------
async def get_ld_totals(user_id, session):
    pg_timezone = os.getenv("PG_TIMEZONE", "UTC")
    start_date = datetime.now() - timedelta(days=1)
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Set timezone for the session (PostgreSQL only)
    await session.execute(text(f"SET TIMEZONE = '{pg_timezone}'"))
    query = (
        select(func.sum(EndpointStatsModel.count), func.sum(EndpointStatsModel.amount))
        .where(
            EndpointStatsModel.userid == user_id,
            EndpointStatsModel.calldate >= start_date,
            EndpointStatsModel.calldate < end_date
        )
    )

    ret = await session.execute(query)
    result = ret.first()
    ld_dips = result[0] if result[0] is not None else 0
    ld_amount = float(result[1]) if result[1] is not None else 0.0
    return (ld_dips, ld_amount)