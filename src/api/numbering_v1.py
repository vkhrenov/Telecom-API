import logging
import requests
import os

from fastapi import APIRouter, Depends, Query, Response
from src.utils.logger import billing_logger
from src.api import deps
from datetime import datetime

from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from src.databases.database_session import get_async_session

from src.logic.numbering_v1    import get_Lerg6_by_NPANXX, get_NPANXX, get_Local
from src.logic.numbering_v1    import get_LRN_Info, get_SPID_Name, get_Simple_Name, get_NNMP
from src.schemas.numbering_v1  import PhoneCodes_TypeParamsSchema, PhoneNumber_TypeParamsSchema, PhoneNumbers_TypeParamsSchema
from src.schemas.numbering_v1  import FullDataSchema, FullDataCoSpecSchema, NNMPInfoSchema, LRNwithJurisdictionSchema
from src.schemas.auth.users    import UserEndpointSchema
from src.databases.redis_cache import get_cache, set_cache

TN_PREFIXES= ('1', '+1')

router = APIRouter()

# Endpoint to get call jurisdiction information ------------------------------------------------
@router.get("/jurisdiction/", summary="Get call jurisdiction information")
async def get_jurisdiction(
    params: Annotated[PhoneCodes_TypeParamsSchema, Query()],
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserEndpointSchema = Depends(deps.require_endpoint_access())
):
    jurisdiction = await getJurisdiction(params.dialing_code, params.dial_code, session)
    billing_logger.log_billing(userinfo, jurisdiction, params.dialing_code, params.dial_code)
    
    return return_by_type(params.type, "jurisdiction", jurisdiction)
    
# Endpoint to get LRN and call jurisdiction information -------------------------------------------
@router.get("/LRNjurisdiction/", summary="Get call jurisdiction and LRN information")
async def get_lrn_jurisdiction( 
    params: Annotated[PhoneNumbers_TypeParamsSchema, Query()],
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserEndpointSchema = Depends(deps.require_endpoint_access())
):
    """
    Endpoint to retrieve call jurisdiction and LRN information.
    The `tn` should be in E.164 format, or 10-digit number, or 1 followed by a 10-digit number.
    The `cn` should be in E.164 format, 10-digit number, or 1 followed by a 10-digit number.
    If the LRN is not found, it will return an empty LRN.
    """

    lrnjur = await procLRNjur(params, session)
    jurisdiction = await getJurisdiction(params.cn, params.tn, session)
    lrnjur.jurisdiction = jurisdiction
    billing_logger.log_billing(userinfo, lrnjur, params.cn, params.tn)

    if params.type == 'raw':
        return f"{lrnjur.lrn}|{lrnjur.ocn}|{lrnjur.lata}|{lrnjur.jurisdiction}|{lrnjur.state}|{lrnjur.rc}|{lrnjur.lec}|{lrnjur.lecType}"
    elif params.type == 'json':
        return lrnjur
    elif params.type == 'xml':
        response = Response(
            content=f"<LRNJurisdiction><lrn>{lrnjur.lrn}</lrn><ocn>{lrnjur.ocn}</ocn><lata>{lrnjur.lata}</lata><jurisdiction>{lrnjur.jurisdiction}</jurisdiction>" + 
                    f"<state>{lrnjur.state}</state><rc>{lrnjur.rc}</rc><lec>{lrnjur.lec}</lec><lecType>{lrnjur.lecType}</lecType></LRNJurisdiction>",
            media_type="application/xml"
        )
        return response
    return lrnjur

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
        billing_logger.log_billing(userinfo, lrn_record.lrn, "", params.tn)
        return return_by_type(params.type, "LRN", lrn_record.lrn)
     
    billing_logger.log_billing(userinfo, "", "", params.tn)
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

    billing_logger.log_billing(userinfo, fullDataCoSpec, "", params.tn)

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

    billing_logger.log_billing(userinfo, fullData, "", params.tn)

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

# Endpoint to get NNMP information by TN ----------------------------------------------------------    
@router.get("/NNMP/", summary="Get NetNumber Messaging Probability by TN")
async def get_nnmp(
    params: Annotated[PhoneNumber_TypeParamsSchema, Query()],
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserEndpointSchema = Depends(deps.require_endpoint_access())
):
    """
    Endpoint to retrieve NNMP information for a given telephone number (TN).
    The `tn` should be in E.164 format, or 10-digit number.
    """
    nnmp = 0
    fullDataCoSpec = await procFullDataCoSpec(params, session)
    if fullDataCoSpec.category == "CLEC":
        nnmp = await get_NNMP(fullDataCoSpec.co_spec_name, session)

    nnmpData = NNMPInfoSchema(
        nnmp = nnmp,
        ocn = fullDataCoSpec.ocn,
        ocn_name = fullDataCoSpec.ocn_name,
        category = fullDataCoSpec.category
    )

    billing_logger.log_billing(userinfo, nnmpData, "", params.tn)

    if params.type == 'raw':
        return f"{nnmpData.nnmp}|{nnmpData.ocn}|{nnmpData.ocn_name}|{nnmpData.category}"
    elif params.type == 'json':
        return nnmpData
    elif params.type == 'xml':
        response = Response(
            content=f"<NNMPInfo><nnmp>{nnmpData.nnmp}</nnmp><ocn>{nnmpData.ocn}</ocn><ocn_name>{nnmpData.ocn_name}</ocn_name>" + 
                    f"<category>{nnmpData.category}</category></NNMPInfo>",
            media_type="application/xml"
        )
        return response
    
# Endpoint to get Operating Company Number (OCN) by TN -------------------------------------------   
@router.get("/OCN/", summary="Get Operating Company Number by TN")    
async def get_ocn(
    params: Annotated[PhoneNumber_TypeParamsSchema, Query()],
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserEndpointSchema = Depends(deps.require_endpoint_access())
):
    """
    Endpoint to retrieve Operating Company Number (OCN) for a given telephone number (TN).
    The `tn` should be in E.164 format, or 10-digit number.
    """
    fullDataCoSpec = await procFullDataCoSpec(params, session)

    billing_logger.log_billing(userinfo, fullDataCoSpec.ocn, "", params.tn)

    if params.type == 'raw':
        return fullDataCoSpec.ocn
    elif params.type == 'json':
        return {"ocn": fullDataCoSpec.ocn}
    elif params.type == 'xml':
        response = Response(
            content=f"<OCN>{fullDataCoSpec.ocn}</OCN>",
            media_type="application/xml"
        )
        return response
    
# Endpoint to get Operating Company Name (OCN Name) by TN --------------------------------------------
@router.get("/OCNName/", summary="Get Operating Company Name by TN")
async def get_ocn_name(
    params: Annotated[PhoneNumber_TypeParamsSchema, Query()],
    session: AsyncSession = Depends(get_async_session), 
    userinfo: UserEndpointSchema = Depends(deps.require_endpoint_access())
):
    """
    Endpoint to retrieve Operating Company Name (OCN Name) for a given telephone number (TN).
    The `tn` should be in E.164 format, or 10-digit number.
    """
    fullDataCoSpec = await procFullDataCoSpec(params, session)

    billing_logger.log_billing(userinfo, fullDataCoSpec.ocn_name, "", params.tn)

    if params.type == 'raw':
        return fullDataCoSpec.ocn_name
    elif params.type == 'json':
        return {"ocn_name": fullDataCoSpec.ocn_name}
    elif params.type == 'xml':
        response = Response(
            content=f"<OCNName>{fullDataCoSpec.ocn_name}</OCNName>",
            media_type="application/xml"
        )
        return response
    
# Endpoint to get SPID Name by TN --------------------------------------------------------------------    
@router.get("/SPID/", summary="Get SPID by TN")
async def get_spid(
    params: Annotated[PhoneNumber_TypeParamsSchema, Query()],
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserEndpointSchema = Depends(deps.require_endpoint_access())
):
    """
    Endpoint to retrieve SPID for a given telephone number (TN).
    The `tn` should be in E.164 format, or 10-digit number.
    """
    fullDataCoSpec = await procFullDataCoSpec(params, session)

    spid = fullDataCoSpec.spid

    billing_logger.log_billing(userinfo, spid, "", params.tn)

    if params.type == 'raw':
        return spid
    elif params.type == 'json':
        return {"spid_name": spid}
    elif params.type == 'xml':
        response = Response(
            content=f"<SPIDName>{spid}</SPIDName>",
            media_type="application/xml"
        )
        return response

# Endpoint to get Category by TN --------------------------------------------------------------------    
@router.get("/category/", summary="Get Category by TN")
async def get_category(
    params: Annotated[PhoneNumber_TypeParamsSchema, Query()],
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserEndpointSchema = Depends(deps.require_endpoint_access())
):
    """
    Endpoint to retrieve Category for a given telephone number (TN).
    The `tn` should be in E.164 format, or 10-digit number.
    """
    fullDataCoSpec = await procFullDataCoSpec(params, session)

    billing_logger.log_billing(userinfo, fullDataCoSpec.category, "", params.tn)

    if params.type == 'raw':
        return fullDataCoSpec.category
    elif params.type == 'json':
        return {"category": fullDataCoSpec.category}
    elif params.type == 'xml':
        response = Response(
            content=f"<Category>{fullDataCoSpec.category}</Category>",
            media_type="application/xml"
        )
        return response

# Endpoint to get CNAM by TN --------------------------------------------------------------------
@router.get("/CNAM/", summary="Get CNAM by TN")
async def get_cnam(
    params: Annotated[PhoneNumber_TypeParamsSchema, Query()],
    session: AsyncSession = Depends(get_async_session),
    userinfo: UserEndpointSchema = Depends(deps.require_endpoint_access())
):
    """
    Endpoint to retrieve CNAM for a given telephone number (TN).
    The `tn` should be in E.164 format, or 10-digit number.
    
    Returns the CNAM as a string.
    """
    lookup_type = ""
    cache_key = f"cnam:{params.tn}"
    cached_cnam = await get_cache(cache_key)
    if cached_cnam:
        cnam = cached_cnam
        lookup_type = "cache"
    else:
        cnam = getCNAMFull(params.tn)
        await set_cache(cache_key, cnam, expire=604800)  # Cache for 7 days
        lookup_type = "vendor"

    billing_logger.log_billing(userinfo, f"{cnam}|{lookup_type}", "", params.tn)

    return return_by_type(params.type, "CNAM", cnam)

#-----------------------------------------------------------------------------------------------------
# Helper functions
#-----------------------------------------------------------------------------------------------------
def return_by_type(type, field, data):
    """
    Helper function to return data based on the requested type.
    """
    if type == 'raw':
        return str(data)
    elif type == 'json':
        return {field: data}
    elif type == 'xml':
        return f"<{field}>{data}</{field}>"
    else:
        raise ValueError("Invalid type parameter. Must be 'raw', 'json', or 'xml'.")
#-----------------------------------------------------------------------------------------------------    
async def procFullDataCoSpec(params, session) -> FullDataCoSpecSchema:

    npanxxx = get_NPANXX(params.tn)
    onpanxxx = npanxxx

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
        simplified_name="",
        ported_date="",
        osimplified_name=""
    )
    prefix = getPrefix(params.tn)
    lrn_record = await get_LRN_Info(params.tn, session)
    if lrn_record is not None:
        npanxxx = get_NPANXX(lrn_record.lrn)
        fullData.spid = lrn_record.spid
        fullData.lrn = setPrefix(lrn_record.lrn, prefix)
        fullData.ported_date = lrn_record.activationtimestamp
        olerg6 = await get_Lerg6_by_NPANXX(onpanxxx, session)
        if olerg6 is not None:
            fullData.osimplified_name = await get_Simple_Name(olerg6.co_spec_name, session)

    lerg6 = await get_Lerg6_by_NPANXX(npanxxx, session)
    
    if lerg6 is not None:
        fullData.ocn = lerg6.ocn
        fullData.ocn_name = lerg6.ocnname
        fullData.category = lerg6.category
        fullData.co_spec_name = lerg6.co_spec_name

    if fullData.spid:
        fullData.spid_name = await get_SPID_Name(fullData.spid, session)

    fullData.simplified_name = await get_Simple_Name(fullData.co_spec_name, session)

    if fullData.osimplified_name == "":
        fullData.osimplified_name = fullData.simplified_name

    return fullData
#-----------------------------------------------------------------------------------------------------    
async def procLRNjur(params, session) -> LRNwithJurisdictionSchema:

    npanxxx = get_NPANXX(params.tn)

    LRNJurData = LRNwithJurisdictionSchema(
        lrn="",
        ocn="",
        lata="",
        jurisdiction="",
        state="",
        rc="",
        lec="",
        lecType=""
    )
    prefix = getPrefix(params.tn)
    lrn_record = await get_LRN_Info(params.tn, session)
    if lrn_record is not None:
        npanxxx = get_NPANXX(lrn_record.lrn)
        LRNJurData.lrn = setPrefix(lrn_record.lrn, prefix)

    lerg6 = await get_Lerg6_by_NPANXX(npanxxx, session)

    if lerg6 is not None:
        LRNJurData.ocn = lerg6.ocn
        LRNJurData.lata = lerg6.lata
        LRNJurData.state = lerg6.state
        LRNJurData.rc = lerg6.rc
        LRNJurData.lec = lerg6.ocnname
        LRNJurData.lecType = lerg6.category

    return LRNJurData
#-----------------------------------------------------------------------------------------------------  
async def getJurisdiction(dialing_code: str, dial_code: str, session: AsyncSession) -> str:
    """
    Get the jurisdiction for the given dialing code and dial code.
    """
    lerg6_from = await get_Lerg6_by_NPANXX(get_NPANXX(dialing_code), session)
    
    if lerg6_from is None:
        return "Unknown"        
    
    lerg6_to   = await get_Lerg6_by_NPANXX(get_NPANXX(dial_code), session)
    
    if lerg6_to is None:
        return "Unknown"
    
    if (
        lerg6_from.state == lerg6_to.state and
        lerg6_from.lata == lerg6_to.lata and 
        lerg6_from.rc == lerg6_to.rc):
        return "Local"
    
    local = await get_Local(lerg6_from, lerg6_to, session)
    if local is not None:
        return "Local"

    if lerg6_from.state == lerg6_to.state:
        return "Intrastate"

    return "Interstate"
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
#-----------------------------------------------------------------------------------------------------
def getCNAMFull (tn: str) -> str:
    """
    Get the full CNAM for the given TN.
    
    """
    
    try:
        url = f"http://cnam.infoserv.net:30035/{tn}"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return response.text.strip()
        else:
            return f"Error: Unable to fetch CNAM (status code {response.status_code})"
    except Exception as e:
        return f"Error: {str(e)}"
