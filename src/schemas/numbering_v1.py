from pydantic import BaseModel, field_validator, Field
from typing import Optional, Literal
import re

# Schema for validating type parameter
class TypeParamsSchema(BaseModel):
    type: Optional[Literal['json', 'raw', 'xml']] = Field(
        default='json',
        description="Response format: 'json', 'raw', or 'xml'. Default is 'json'."
    )

    @field_validator("type")
    def validate_type(cls, v):
        if v not in ['json', 'raw', 'xml']:
            raise ValueError("Type must be one of: 'json', 'raw', or 'xml'.")
        return v

# Schema for validating phone numbers and dial codes
class DialCode_TypeParamsSchema(TypeParamsSchema):
    dial_code: str = Field(...,description="Dial code in 6-10 digit format. 1 or +1 prefix is allowed")

    @field_validator("dial_code")
    def validate_dial_code_e164_format(cls, v):
        v0 = v
        if v0.startswith("+"):
            v0 = v0[1:]
        if not re.fullmatch(r'^\d{6,11}$', v0):
            raise ValueError("Dial code must be in 6-10 digit format. 1 or +1 prefix is allowed.")
        return v
    
# Schema for validating phone codes    
class PhoneCodes_TypeParamsSchema(DialCode_TypeParamsSchema):
    dialing_code: str = Field(
        ..., 
        description="Dialing code in 6-10 digit format. 1 or +1 prefix is allowed"
    )

    @field_validator("dialing_code")
    def validate_dialing_code_e164_format(cls, v):
        v0 = v.lstrip("+")
        if not re.fullmatch(r'^\d{6,11}$', v0):
            raise ValueError("Dialing code must be in 6-10 digit format. 1 or +1 prefix is allowed.")
        return v

# Schema for validating a phone number with type parameters
class PhoneNumber_TypeParamsSchema(TypeParamsSchema):
    tn: str = Field(...,description="Telephone Number in E.164 format, 10-digit number, or 1 followed by a 10-digit number")

    @field_validator("tn")
    def validate_tn_e164_format(cls, v):
        v0 = v
        if v0.startswith("+"):
            v0 = v0[1:]
        if not re.fullmatch(r'^[1-9]\d{9,14}$', v0):
            raise ValueError("Telephone number must be in E.164 format (e.g. +12345678900),a 10-digit number, or a 1 followed by a 10-digit number")
        return v

# Schema for validating multiple phone numbers
class PhoneNumbers_TypeParamsSchema(PhoneNumber_TypeParamsSchema):
    cn: str = Field(...,description="Calling Number in E.164 format, 10-digit number, or 1 followed by a 10-digit number")

    @field_validator("cn")
    def validate_cn_e164_format(cls, v):
        v0 = v
        if v0.startswith("+"):
            v0 = v0[1:]
        if not re.fullmatch(r'^[1-9]\d{9,14}$', v0):
            raise ValueError("Calling number must be in E.164 format (e.g. +12345678900),a 10-digit number, or a 1 followed by a 10-digit number.")
        return v

# Schema for Local Routing Number (LRN) information
class LRNInfoSchema(BaseModel):
    tn: str
    lrn: str
    spid: str
    altspid: str
    activationtimestamp: str
    lnptype: str
    svtype: str
    alteult: str
    alteulv: str
    altbid: str
    billingid: str 
    voiceuri: str
    mmsuri: str
    smsuri: str

# Schema for Full Data information
class FullDataSchema(BaseModel):
    tn: str
    lrn: str
    spid: str
    ocn: str
    ocn_name: str
    category: str
    spid_name: str
    
# Schema for Full Data information with CoSpec 
class FullDataCoSpecSchema(FullDataSchema):
    co_spec_name: str
    co_spec_name_or_ocn_name: str
    simplified_name: str


