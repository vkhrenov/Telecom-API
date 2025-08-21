from sqlalchemy import select, func
from src.models.numbering_v1  import Lerg6Model,LocalModel, SPIDNamesModel, SimpleCarrierNamesModel   
from src.models.numbering_v1  import Numberpoolblock, NNMPModel
from src.models.numbering_v1  import create_dynamic_model
from src.schemas.numbering_v1 import LRNInfoSchema

# Function to get Lerg6 record by NPANXX -------------------------------------------------
async def get_Lerg6_by_NPANXX(dial_code: str, session):
    ret = await session.scalar(select(Lerg6Model).where(Lerg6Model.npanxxx == dial_code))
    return ret 

# Function to get Local jurisdiction information -----------------------------------------
async def get_Local(lerg6_from: Lerg6Model, lerg6_to: Lerg6Model, session):
    ret = await session.scalar(
        select(LocalModel).where(
            LocalModel.from_rc_abbrev == lerg6_from.rc,
            LocalModel.from_state == lerg6_from.state,
            LocalModel.from_lata == lerg6_from.lata,
            LocalModel.to_rc_abbrev == lerg6_to.rc,
            LocalModel.to_state == lerg6_to.state,
            LocalModel.to_lata == lerg6_to.lata
        )
    )
    return ret

# Function to get Local Routing Number (LRN) Information by Telephone Number (TN) ---------
async def get_LRN_Info_by_TN(tn: str, session):
    """
    Retrieves the Local Routing Number (LRN) information for a given telephone number (TN).
    
    Args:
        tn (str): The telephone number in E.164 format.
        session: The database session to execute the query.
    
    Returns:
        TN2LRNxxx: The LRN record associated with the TN, or None if not found.
    """
    ten_digit = get_10digitNumber(tn)
    npa = ten_digit[:3]
    TN2LRNDynamicModel = create_dynamic_model("tn2lrn" + npa)
    ret = await session.scalar(
        select(TN2LRNDynamicModel).where(TN2LRNDynamicModel.tn == ten_digit)
    )
    return ret

# Function to get Local Routing Number (LRN) Information by NPANXX -------------------------
async def get_LRN_NumberPool_by_TN(tn: str, session):
    """ Retrieves the Local Routing Number (LRN) information for a given NPANXX.
    Args:
        npanxxx (str): The NPANXX.
        session: The database session to execute the query.
    Returns:
        Numberpoolblock: The LRN record associated with the NPANXX, or None if not found.
    """ 
    ten_digit = get_10digitNumber(tn)
    npanxxx = ten_digit[:7]
    ret = await session.scalar(
        select(Numberpoolblock).where(Numberpoolblock.npanxxx == npanxxx)
    )
    return ret

#  Function to get LRN information by telephone number (TN) ---------------------------------
async def get_LRN_Info(tn: str, session)-> LRNInfoSchema:
    """Retrieves the Local Routing Number (LRN) information for a given telephone number (TN).
    
    Args:
        tn (str): The telephone number in E.164 format.
        session: The database session to execute the query.
    
    Returns:
        LRN record associated with the TN, or None if not found.
    """
    lrn_record = await get_LRN_Info_by_TN(tn, session)
    if lrn_record is None:
        lrn_record = await get_LRN_NumberPool_by_TN(tn, session)
        if lrn_record is not None:
            return LRNInfoSchema (
                tn=tn,
                lrn=lrn_record.lrn,
                spid=lrn_record.spid,
                altspid=lrn_record.altspid,
                activationtimestamp=lrn_record.activationtimestamp,
                lnptype='pool',
                svtype=lrn_record.blocksvtype,
                alteult=lrn_record.alteult,
                alteulv=lrn_record.alteulv,
                altbid=lrn_record.altbid,
                voiceuri=lrn_record.voiceuri,
                mmsuri=lrn_record.mmsuri,
                billingid="",  
                smsuri=lrn_record.smsuri            )
        
    else:
        return LRNInfoSchema (
            tn=tn,
            lrn=lrn_record.lrn,
            spid=lrn_record.spid,
            altspid=lrn_record.altspid,
            activationtimestamp=lrn_record.activationtimestamp,
            lnptype=lrn_record.lnptype,
            svtype=lrn_record.svtype,
            alteult=lrn_record.alteult,
            alteulv=lrn_record.alteulv,
            altbid=lrn_record.altbid,
            voiceuri=lrn_record.voiceuri,
            mmsuri=lrn_record.mmsuri,
            billingid=lrn_record.billingid,
            smsuri=lrn_record.smsuri
        )
    return None

# Function to get SPID name by SPID ----------------------------------------------------
async def get_SPID_Name(spid: str, session):
    """Retrieves the SPID name for a given SPID.
    
    Args:
        spid (str): The Service Provider ID.
        session: The database session to execute the query.
    
    Returns:
        str: The name of the service provider, or None if not found.
    """
    spid_name = await session.scalar(
        select(SPIDNamesModel.spidname).where(SPIDNamesModel.spid == spid)
    )
    return spid_name if spid_name else ""

# Function to get CoSpec name by co_spec_name -------------------------------------------
async def get_NNMP(co_spec_name: str, session):
    """Retrieves the NNMP (National Numbering Plan) for a given co_spec_name.
    
    Args:
        co_spec_name (str): The co_spec_name to retrieve the NNMP for.
        session: The database session to execute the query.
    
    Returns:
        str: The NNMP, or None if not found.
    """
    nnmp = await session.scalar(
        select(NNMPModel.nnmp).where(func.upper(NNMPModel.co_spec_name) == co_spec_name.upper())
    )
    return nnmp if nnmp else 0

# Function to get simplified name by co_spec_name --------------------------------------
async def get_Simple_Name(co_spec_name: str, session):
    """Retrieves the simplified name for a given co_spec_name.
    Args:
        co_spec_name (str): The co_spec_name to simplify.
        session: The database session to execute the query.
    Returns:
        str: The simplified name, or None if not found.
    """
    sn_name = await session.scalar(
        select(SimpleCarrierNamesModel.simplified_name).where(SimpleCarrierNamesModel.co_spec_name == co_spec_name)
    )
    return sn_name if sn_name else ""

# Function to extract 10 digit number and NPANXX ---------------------------------------
def get_10digitNumber(tn: str) -> str:
    """Extracts the last 10 digits of a phone number."""
    return tn[-10:] if len(tn) > 10 else tn

# Function to extract NPANXX -----------------------------------------------------------
def get_NPANXX(tn: str) -> str:
    """Extracts the NPANXX (first 6 digits of the last 10 digits) from a phone number."""
    ten_digit = get_10digitNumber(tn)
    return ten_digit[:6]


