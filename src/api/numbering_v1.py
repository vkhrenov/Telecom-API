import logging

from fastapi import APIRouter, Depends, Query, Response
from src.api import deps

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from src.databases.database_session import get_async_session

from src.logic.numbering_v1   import get_Lerg6_by_NPANXX, get_NPANXX, get_Local
from src.logic.numbering_v1   import get_LRN_Info, get_SPID_Name, get_Simple_Name
from src.schemas.numbering_v1 import PhoneCodes_TypeParamsSchema, PhoneNumber_TypeParamsSchema
from src.schemas.numbering_v1 import FullDataSchema, FullDataCoSpecSchema
from src.schemas.auth.users   import UserEndpointSchema
from src.utils.logger         import billing_logger
from fastapi_redis_cache      import cache

logger = logging.getLogger(__name__)
TN_PREFIXES= ('1', '+1')

router = APIRouter()

# Endpoint to get call jurisdiction information ------------------------------------------------
@cache(expire=120)
@router.get("/jurisdiction/", summary="Get call jurisdiction information")
async def get_jurisdiction(
    params: Annotated[PhoneCodes_TypeParamsSchema, Query()],
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserEndpointSchema = Depends(deps.require_endpoint_access())
):

    """
    Endpoint to retrieve call jurisdiction information

    Returns jurisdictions: Local, Intrastate, Interstate, or Unknown based on the provided phone numbers.
   
    The `dialing_code` is the number from which the call is made, and `dial_code` is the number to which the call is made.
    The `dialing_code` and `dial_code` should be in E.164 format, NPANXX, or 10-digit number.
    """

    lerg6_from = await get_Lerg6_by_NPANXX(get_NPANXX(params.dialing_code), session)
    
    if lerg6_from is None:
        billing_logger(logger,userinfo,"Unknown",params.dialing_code,params.dial_code)
        return return_by_type(params.type, "Jurisdiction", "Unknown")        
    
    lerg6_to   = await get_Lerg6_by_NPANXX(get_NPANXX(params.dial_code), session)
    
    if lerg6_to is None:
        billing_logger(logger,userinfo,"Unknown",params.dialing_code,params.dial_code)
        return return_by_type(params.type, "Jurisdiction", "Unknown")
    
    if (
        lerg6_from.state == lerg6_to.state and
        lerg6_from.lata == lerg6_to.lata and 
        lerg6_from.rc == lerg6_to.rc):

        billing_logger(logger,userinfo,"Local",params.dialing_code,params.dial_code)
        return return_by_type(params.type, "Jurisdiction", "Local")
    
    local = await get_Local(lerg6_from, lerg6_to, session)
    if local is not None:
        billing_logger(logger,userinfo,"Local",params.dialing_code,params.dial_code)
        return return_by_type(params.type, "Jurisdiction", "Local")

    if lerg6_from.state == lerg6_to.state:
        billing_logger(logger,userinfo,"Intrastate",params.dialing_code,params.dial_code)
        return return_by_type(params.type, "Jurisdiction", "Intrastate")

    billing_logger(logger,userinfo,"Interstate",params.dialing_code,params.dial_code)
    return return_by_type(params.type, "Jurisdiction", "Interstate")

# Endpoint to get LRN by TN ----------------------------------------------------------------------
@router.get("/LRN/", summary="Get LRN by TN") 
async def get_lrn(params: Annotated[PhoneNumber_TypeParamsSchema, Query()],
                  session: AsyncSession = Depends(get_async_session),
                  userinfo: UserEndpointSchema = Depends(deps.require_endpoint_access())
):
    """
    Endpoint to retrieve Local Routing Number (LRN) by Telephone Number (TN).
    The `tn` should be in E.164 format, or 10-digit number.
    If the LRN is not found, it will return an empty LRN.    
    """
    prefix = getPrefix(params.tn)
    lrn_record = await get_LRN_Info(params.tn, session)

    if lrn_record is not None:
        lrn_record.lrn = setPrefix(lrn_record.lrn, prefix)
        billing_logger(logger, userinfo, lrn_record.lrn, "", params.tn)
        return return_by_type(params.type, "LRN", lrn_record.lrn)
     
    billing_logger(logger, userinfo, "", "", params.tn)
    return return_by_type(params.type, "LRN", "")

# Endpoint to get Full Data with CoSpec by TN ------------------------------------------------------
@router.get("/FullDataCoSpec/", summary="Get All available portability data with CoSpec")
async def get_full_dataCoSpec(
    params: Annotated[PhoneNumber_TypeParamsSchema, Query()],
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserEndpointSchema = Depends(deps.require_endpoint_access())
):
    """
    Endpoint to retrieve major data for a given telephone number (TN).
    The `tn` should be in E.164 format, or 10-digit number.
    """
    fullDataCoSpec = await procFullDataCoSpec(params, session)

    if fullDataCoSpec.co_spec_name == "USE VARIES BY COMPANY":
        fullDataCoSpec.co_spec_name_or_ocn_name = fullDataCoSpec.ocn_name
    else:
        if len(fullDataCoSpec.co_spec_name) > 3:
            fullDataCoSpec.co_spec_name_or_ocn_name = fullDataCoSpec.co_spec_name
        else:
            fullDataCoSpec.co_spec_name_or_ocn_name = fullDataCoSpec.ocn_name

    billing_logger(logger, userinfo, fullDataCoSpec, "", params.tn)

    if params.type == 'raw':
        return f"{fullDataCoSpec.tn}|{fullDataCoSpec.lrn}|{fullDataCoSpec.spid}|{fullDataCoSpec.ocn}|{fullDataCoSpec.ocn_name}|{fullDataCoSpec.category}|{fullDataCoSpec.co_spec_name}|{fullDataCoSpec.spid_name}|{fullDataCoSpec.co_spec_name_or_ocn_name}"
    elif params.type == 'json':
        return fullDataCoSpec
    elif params.type == 'xml':
        response = Response(
            content=f"<fullDataCoSpec><tn>{fullDataCoSpec.tn}</tn><lrn>{fullDataCoSpec.lrn}</lrn><spid>{fullDataCoSpec.spid}</spid><ocn>{fullDataCoSpec.ocn}</ocn><ocn_name>{fullDataCoSpec.ocn_name}</ocn_name>" + 
                    f"<category>{fullDataCoSpec.category}</category><co_spec_name>{fullDataCoSpec.co_spec_name}</co_spec_name><spid_name>{fullDataCoSpec.spid_name}</spid_name>" +
                    f"<co_spec_name_or_ocn_name>{fullDataCoSpec.co_spec_name_or_ocn_name}</co_spec_name_or_ocn_name></fullDataCoSpec>",
            media_type="application/xml"
        )
        return response
        
# Endpoint to get Full Data without CoSpec by TN ------------------------------------------------------
@router.get("/FullData/", summary="Get portability Data")
async def get_full_data(   
    params: Annotated[PhoneNumber_TypeParamsSchema, Query()],
#    session: AsyncSession = Depends(deps.get_session),
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserEndpointSchema = Depends(deps.require_endpoint_access())
):
    """
    Endpoint to retrieve portability data for a given telephone number (TN).
    The `tn` should be in E.164 format, or 10-digit number.
    """

    fullDataCoSpec = await procFullDataCoSpec(params, session)

    fields = {k: v for k, v in fullDataCoSpec.model_dump().items() if k in FullDataSchema.model_fields}
    fullData = FullDataSchema(**fields)

    billing_logger(logger, userinfo, fullData, "", params.tn)

    if params.type == 'raw':
        return f"{fullData.tn}|{fullData.lrn}|{fullData.spid}|{fullData.ocn}|{fullData.ocn_name}|{fullData.category}|{fullData.spid_name}"
    elif params.type == 'json':
        return fullData
    elif params.type == 'xml':
        response = Response(
            content=f"<FullData><tn>{fullData.tn}</tn><lrn>{fullData.lrn}</lrn><spid>{fullData.spid}</spid><ocn>{fullData.ocn}</ocn><ocn_name>{fullData.ocn_name}</ocn_name>" + 
                    f"<category>{fullData.category}</category><spid_name>{fullData.spid_name}</spid_name></FullData>",
            media_type="application/xml"
        )
        return response
    
#-----------------------------------------------------------------------------------------------------
def return_by_type(type, field, data):
    """
    Helper function to return data based on the requested type.
    """
    if type == 'raw':
        return data
    elif type == 'json':
        return {field: data}
    elif type == 'xml':
        response = Response(content=f"<{field}>{data}</{field}>", media_type="application/xml")
        return response
    else:
        raise ValueError("Invalid type parameter. Must be 'raw', 'json', or 'xml'.")
#-----------------------------------------------------------------------------------------------------    
async def procFullDataCoSpec(params, session) -> FullDataCoSpecSchema:

    npanxxx = get_NPANXX(params.tn)

    fullData = FullDataCoSpecSchema(
        tn=params.tn,
        lrn="",
        spid="",
        ocn="",
        ocn_name="",
        category="",
        co_spec_name="",
        spid_name="",
        co_spec_name_or_ocn_name="",
        simplified_name=""
    )
    prefix = getPrefix(params.tn)
    lrn_record = await get_LRN_Info(params.tn, session)
    if lrn_record is not None:
        npanxxx = get_NPANXX(lrn_record.lrn)
        fullData.spid = lrn_record.spid
        fullData.lrn = setPrefix(lrn_record.lrn, prefix)

    lerg6 = await get_Lerg6_by_NPANXX(npanxxx, session)

    if lerg6 is not None:
        fullData.ocn = lerg6.ocn
        fullData.ocn_name = lerg6.ocnname
        fullData.category = lerg6.category
        fullData.co_spec_name = lerg6.co_spec_name

    if fullData.spid:
        fullData.spid_name = await get_SPID_Name(fullData.spid, session)

    fullData.simplified_name = await get_Simple_Name(fullData.co_spec_name, session)

    return fullData
#-----------------------------------------------------------------------------------------------------  
def getPrefix(tn: str) -> str:
    """
    Get the prefix for the TN based on the defined prefixes.
    """
    if tn.startswith(TN_PREFIXES):
        for prefix in TN_PREFIXES:
            if tn.startswith(prefix):
                return prefix
    return ""
#----------------------------------------------------------------------------------------------------- 
def setPrefix(tn: str, prefix: str) -> str:
    """
    Set the prefix for the TN if it is not already set.
    """
    return prefix + tn
    