from fastapi import APIRouter, Depends, Request, Response, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.api import deps
from src.databases.database_session import get_async_session
from src.schemas.auth.users import UserInfoSchema
from typing import Annotated
from src.schemas.ui import RequestCustomerListSchema
from src.logic.users import get_users, create_user, update_user, get_user, delete_user
from src.logic.products import get_product_list, get_product, create_product, update_productid, delete_productid
from src.logic.endpoints import get_endpoint_list, get_endpoint, create_endpoint, update_endpointid, delete_endpointid
from src.logic.statements import get_users_statinfo, get_statement, get_user_summaries, get_monthly_summaries,get_monthly_stats_pday,get_daily_stats_p5, get_latest_information
from src.utils.logger import ui_logger

import json

router = APIRouter()

# Endpoint to get a list of customers (hidden from public documentation) --------------------------------------------------------------------
@router.get("/customers", summary="Get customer list", include_in_schema=False) 
async def get_customers(params: Annotated[RequestCustomerListSchema, Query()],
                        response: Response,
                        session: AsyncSession = Depends(get_async_session),
                        userinfo: UserInfoSchema = Depends(deps.require_info_access())):
  
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    filter_dict = json.loads(params.filter) if params.filter else {}
    sort_list = json.loads(params.sort) if params.sort else []
    range_list = json.loads(params.range) if params.range else [0, 24]
    range_from, range_to = range_list[0], range_list[1]

    custDict = await get_users(session,range_from=range_from, range_to=range_to, filter_dict=filter_dict, sort_list=sort_list)
    total_count = custDict["total"]

    response.headers["Content-Range"] = f"customers {range_from}-{range_to}/{total_count}"
    return custDict["data"]

# Endpoint to get a specific customer by ID (hidden from public documentation) --------------------------------------------------------------
@router.get("/customers/{id}", summary="Get customer info by id", include_in_schema=False)
async def get_customer_by_id(
    id: int,
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserInfoSchema = Depends(deps.require_info_access())
):
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    customer = await get_user(session, id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    return customer

# Endpoint to create a new customer (hidden from public documentation) -------------------------------------------------------------------
@router.post("/customers", summary="Create a customer", include_in_schema=False) 
async def set_customer(request: Request, 
                       session: AsyncSession = Depends(get_async_session),
                       userinfo: UserInfoSchema = Depends(deps.require_info_access())):
  
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    # Parse JSON body
    data = await request.json()
    
    new_customer = await create_user(session, data)
    ui_logger.log_event(userinfo, option="new_customer", data=new_customer)

    return new_customer

# Endpoint to update an existing customer (hidden from public documentation) --------------------------------------------------------------
@router.put("/customers/{id}", summary="Update a customer", include_in_schema=False) 
async def update_customer(
    id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserInfoSchema = Depends(deps.require_info_access())
):
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    # Parse JSON body
    data = await request.json()
    
    ui_logger.log_event(userinfo, option="upd_customer", data=data)
    update_customer = await update_user(session, id, data)
    
    return update_customer

# Endpoint to delete a customer (hidden from public documentation) -----------------------------------------------------------------------
@router.delete("/customers/{id}", summary="Delete a customer", include_in_schema=False)
async def delete_customer(
    id: int,
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserInfoSchema = Depends(deps.require_info_access())
):
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
        
    deleted_user = await delete_user(session, id)
    if "error" in deleted_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=deleted_user["error"])
    ui_logger.log_event(userinfo, option="del_customer", data=deleted_user)    
    return deleted_user

# Endpoint to get product names (hidden from public documentation) --------------------------------------------------------------------
@router.get("/products", summary="Get product list", include_in_schema=False) 
async def get_products(params: Annotated[RequestCustomerListSchema, Query()],
                        response: Response,
                        session: AsyncSession = Depends(get_async_session),
                        userinfo: UserInfoSchema = Depends(deps.require_info_access())):
  
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    filter_dict = json.loads(params.filter) if params.filter else {}
    sort_list = json.loads(params.sort) if params.sort else []
    range_list = json.loads(params.range) if params.range else [0, 24]
    range_from, range_to = range_list[0], range_list[1]

    prodDict = await get_product_list(session,range_from=range_from, range_to=range_to, filter_dict=filter_dict, sort_list=sort_list)
    total_count = prodDict["total"]

    response.headers["Content-Range"] = f"products {range_from}-{range_to}/{total_count}"
    return prodDict["data"]

# Endpoint to get a specific product by ID (hidden from public documentation) --------------------------------------------------------------
@router.get("/products/{id}", summary="Get a product info by id", include_in_schema=False)
async def get_product_by_id(
    id: int,
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserInfoSchema = Depends(deps.require_info_access())
):
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    product = await get_product(session, id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    return product

# Endpoint to create a new product (hidden from public documentation) -------------------------------------------------------------------
@router.post("/products", summary="Create a product", include_in_schema=False) 
async def set_product(request: Request, 
                       session: AsyncSession = Depends(get_async_session),
                       userinfo: UserInfoSchema = Depends(deps.require_info_access())):
  
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    # Parse JSON body
    data = await request.json()
    
    new_product = await create_product(session, data)
    ui_logger.log_event(userinfo, option="new_product", data=new_product) 
    return new_product

# Endpoint to update an existing product (hidden from public documentation) --------------------------------------------------------------
@router.put("/products/{id}", summary="Update a product", include_in_schema=False) 
async def update_product(
    id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserInfoSchema = Depends(deps.require_info_access())
):
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    # Parse JSON body
    data = await request.json()

    ui_logger.log_event(userinfo, option="upd_product", data=data)
    update_product = await update_productid(session, id, data)
    
    return update_product

# Endpoint to delete a customer (hidden from public documentation) -----------------------------------------------------------------------
@router.delete("/products/{id}", summary="Delete a product", include_in_schema=False)
async def delete_product(
    id: int,
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserInfoSchema = Depends(deps.require_info_access())
):
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
        
    deleted_product = await delete_productid(session, id)
    if "error" in deleted_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=deleted_product["error"])
    ui_logger.log_event(userinfo, option="del_product", data=deleted_product)
    return deleted_product

# Endpoint to get endpoint list (hidden from public documentation) --------------------------------------------------------------------
@router.get("/endpoints", summary="Get endpoint list", include_in_schema=False) 
async def get_endpoints(params: Annotated[RequestCustomerListSchema, Query()],
                        response: Response,
                        session: AsyncSession = Depends(get_async_session),
                        userinfo: UserInfoSchema = Depends(deps.require_info_access())):
  
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    filter_dict = json.loads(params.filter) if params.filter else {}
    sort_list = json.loads(params.sort) if params.sort else []
    range_list = json.loads(params.range) if params.range else [0, 24]
    range_from, range_to = range_list[0], range_list[1]

    epDict = await get_endpoint_list(session,range_from=range_from, range_to=range_to, filter_dict=filter_dict, sort_list=sort_list)
    total_count = epDict["total"]

    response.headers["Content-Range"] = f"endpoints {range_from}-{range_to}/{total_count}"
    return epDict["data"]

# Endpoint to get a specific endpoint by ID (hidden from public documentation) --------------------------------------------------------------
@router.get("/endpoints/{id}", summary="Get an endpoint info by id", include_in_schema=False)
async def get_endpoint_by_id(
    id: int,
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserInfoSchema = Depends(deps.require_info_access())
):
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    endpoint = await get_endpoint(session, id)
    if not endpoint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")
    
    return endpoint

# Endpoint to create a new endpoint (hidden from public documentation) -------------------------------------------------------------------
@router.post("/endpoints", summary="Create an endpoint", include_in_schema=False) 
async def set_endpoint(request: Request, 
                       session: AsyncSession = Depends(get_async_session),
                       userinfo: UserInfoSchema = Depends(deps.require_info_access())):
  
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    # Parse JSON body
    data = await request.json()
    
    new_endpoint = await create_endpoint(session, data)
    ui_logger.log_event(userinfo, option="new_endpoint", data=new_endpoint) 
    return new_endpoint

# Endpoint to update an existing endpoint (hidden from public documentation) --------------------------------------------------------------
@router.put("/endpoints/{id}", summary="Update an endpoint", include_in_schema=False) 
async def update_endpoint(
    id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserInfoSchema = Depends(deps.require_info_access())
):
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    # Parse JSON body
    data = await request.json()

    ui_logger.log_event(userinfo, option="upd_endpoint", data=data)
    update_endpoint = await update_endpointid(session, id, data)
    
    return update_endpoint

# Endpoint to delete an endpoint (hidden from public documentation) -----------------------------------------------------------------------
@router.delete("/endpoints/{id}", summary="Delete an endpoint", include_in_schema=False)
async def delete_endpoint(
    id: int,
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserInfoSchema = Depends(deps.require_info_access())
):
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
        
    deleted_endpoint = await delete_endpointid(session, id)
    if "error" in deleted_endpoint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=deleted_endpoint["error"])
    ui_logger.log_event(userinfo, option="del_endpoint", data=deleted_endpoint)
    return deleted_endpoint

# Endpoint to get statement list (hidden from public documentation) --------------------------------------------------------------------
@router.get("/statements", summary="Get statements", include_in_schema=False) 
async def get_statements(params: Annotated[RequestCustomerListSchema, Query()],
                        response: Response,
                        session: AsyncSession = Depends(get_async_session),
                        userinfo: UserInfoSchema = Depends(deps.require_info_access())):
  
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    filter_dict = json.loads(params.filter) if params.filter else {}
    sort_list = json.loads(params.sort) if params.sort else []
    range_list = json.loads(params.range) if params.range else [0, 24]
    range_from, range_to = range_list[0], range_list[1]

    summaryDict = await get_users_statinfo(session,range_from=range_from, range_to=range_to, filter_dict=filter_dict, sort_list=sort_list)
    total_count = summaryDict["total"]

    response.headers["Content-Range"] = f"statements {range_from}-{range_to}/{total_count}"
    return summaryDict["data"]

# Endpoint to get a specific statement by ID (hidden from public documentation) --------------------------------------------------------------
@router.get("/statements/{id}", summary="Get a statement by customer id", include_in_schema=False)
async def get_statement_by_id(
    id: int,
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserInfoSchema = Depends(deps.require_info_access())
):
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    statement = await get_statement(session, id)
    if not statement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    return statement

# Endpoint to get summaries (hidden from public documentation) --------------------------------------------------------------------
@router.get("/summaries", summary="Get summaries", include_in_schema=False) 
async def get_summaries(params: Annotated[RequestCustomerListSchema, Query()],
                        response: Response,
                        session: AsyncSession = Depends(get_async_session),
                        userinfo: UserInfoSchema = Depends(deps.require_info_access())):
  
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    filter_dict = json.loads(params.filter) if params.filter else {}

    range_list = json.loads(params.range) if params.range else [0, 24]
    range_from, range_to = range_list[0], range_list[1]

    summaryDict = await get_user_summaries(session,range_from=range_from, range_to=range_to, filter_dict=filter_dict)
    total_count = summaryDict["total"]

    response.headers["Content-Range"] = f"statements {range_from}-{range_to}/{total_count}"
    return summaryDict["data"]

# Endpoint to get total monthly dips and amounts (hidden from public documentation) --------------------------------------------------------------------
@router.get("/monthlystats", summary="Get monthly dips and amounts", include_in_schema=False) 
async def get_monthly_stats(
                        session: AsyncSession = Depends(get_async_session),
                        userinfo: UserInfoSchema = Depends(deps.require_info_access())):
  
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    stats = await get_monthly_summaries(session)

    return {
        "monthly_dips": stats["monthly_dips"],
        "monthly_amount": stats["monthly_amount"]
    }

# Endpoint to get monthly stats per day for the last 30 days --------------------------------------------------------------------
@router.get("/monthlystatsperday",  summary="Get monthly stats per day", include_in_schema=False)
async def get_monthly_stats_per_day(params: Annotated[RequestCustomerListSchema, Query()],
                        response: Response,
                        session: AsyncSession = Depends(get_async_session),
                        userinfo: UserInfoSchema = Depends(deps.require_info_access())):
  
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    filter_dict = json.loads(params.filter) if params.filter else {}

    range_list = json.loads(params.range) if params.range else [0, 50]
    range_from, range_to = range_list[0], range_list[1]

    summaryDict = await get_monthly_stats_pday(session,range_from=range_from, range_to=range_to, filter_dict=filter_dict)
    total_count = summaryDict["total"]

    response.headers["Content-Range"] = f"monthlystatsperday {range_from}-{range_to}/{total_count}"
    return summaryDict["data"]

# Endpoint to get daily stats per 5 min  ----------------------------------------------------------------------------------
@router.get("/dailystatsper5min",  summary="Get daily stats per 5 min", include_in_schema=False)
async def get_daily_stats_per_5min(params: Annotated[RequestCustomerListSchema, Query()],
                        response: Response,
                        session: AsyncSession = Depends(get_async_session),
                        userinfo: UserInfoSchema = Depends(deps.require_info_access())):
  
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    filter_dict = json.loads(params.filter) if params.filter else {}

    range_list = json.loads(params.range) if params.range else [0, 300]
    range_from, range_to = range_list[0], range_list[1]

    summaryDict = await get_daily_stats_p5(session,range_from=range_from, range_to=range_to, filter_dict=filter_dict)
    total_count = summaryDict["total"]

    response.headers["Content-Range"] = f"dailystatsper5miny {range_from}-{range_to}/{total_count}"
    return summaryDict["data"]

# Endpoint to get latest dip info (hidden from public documentation) --------------------------------------------------------------------
@router.get("/latestinfo", summary="Get latest dip info", include_in_schema=False)
async def get_latest_info(
                        session: AsyncSession = Depends(get_async_session),
                        userinfo: UserInfoSchema = Depends(deps.require_info_access())):
  
    if not userinfo.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    
    stats = await get_latest_information(session)

    return {
        "latest_dip": stats["latest_dip"],
        "daily_dips": stats["daily_dips"],
        "daily_amount": stats["daily_amount"]
    }