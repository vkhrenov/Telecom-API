from sqlalchemy.orm import Mapped, mapped_column, declarative_base
from sqlalchemy import Column, String

Base = declarative_base()

# LERG6 Table Model ----------------------------------------------------
class Lerg6Model(Base):
    __tablename__ = "lerg6"

    npanxxx: Mapped[str] = mapped_column(primary_key=True, index=True)
    lata: Mapped[str]
    npanxx: Mapped[str]
    blockid: Mapped[str] 
    ocn: Mapped[str]
    line_fr: Mapped[str]
    line_to: Mapped[str]
    lata3: Mapped[str]
    switch: Mapped[str]
    state: Mapped[str]
    rc: Mapped[str]
    ocnname: Mapped[str]
    category: Mapped[str]
    co_spec_name: Mapped[str]
    lataname: Mapped[str]
    locality: Mapped[str]

# Local Table Model ---------------------------------------------------
class LocalModel(Base):    
    __tablename__ = "local"

    from_rc_abbrev: Mapped[str] = mapped_column(primary_key=True, index=True)
    from_state: Mapped[str] = mapped_column(primary_key=True, index=True)
    from_lata: Mapped[str] = mapped_column(primary_key=True, index=True)
    to_rc_abbrev: Mapped[str] = mapped_column(primary_key=True, index=True)
    to_state: Mapped[str] = mapped_column(primary_key=True, index=True)
    to_lata: Mapped[str] = mapped_column(primary_key=True, index=True)

# Numberpoolblock Table Model ------------------------------------------
class Numberpoolblock(Base):
    __tablename__ = "numberpoolblock"

    mibcreatetime: Mapped[str]
    mibupdatetime: Mapped[str]
    objectclass: Mapped[str]
    namebinding: Mapped[str]
    numberpoolblockid: Mapped[int]
    npanxxx: Mapped[str] = mapped_column(primary_key=True, index=True)
    spid: Mapped[str]
    activationtimestamp: Mapped[str]
    lrn: Mapped[str]
    class_dpc: Mapped[str]
    class_ssn: Mapped[str]
    lidb_dpc: Mapped[str]
    lidb_ssn: Mapped[str]
    cnam_dpc: Mapped[str]
    cnam_ssn: Mapped[str]
    isvm_dpc: Mapped[str]
    isvm_ssn: Mapped[str]
    wsmsc_dpc: Mapped[str]
    wsmsc_ssn: Mapped[str]
    blocksvtype: Mapped[str]
    downloadreason: Mapped[str]
    altspid: Mapped[str]
    alteult: Mapped[str]
    alteulv: Mapped[str]
    altbid: Mapped[str]
    voiceuri: Mapped[str]
    mmsuri: Mapped[str]
    smsuri: Mapped[str]

# TN2LRNXXX Table Dynamic Model -------------------------------------
_dynamic_model_cache = {}
def create_dynamic_model(table_name: str):
    if table_name in _dynamic_model_cache:
        return _dynamic_model_cache[table_name]
     
    class_attrs = {
        '__tablename__': table_name,
        'tn': Column(String, primary_key=True, index=True),
        'mibcreatetime': Column(String),
        'mibupdatetime': Column(String),
        'lrn': Column(String),
        'spid': Column(String),
        'activationtimestamp': Column(String),
        'class_dpc': Column(String),
        'class_ssn': Column(String),
        'lidb_dpc': Column(String),
        'lidb_ssn': Column(String),
        'cnam_dpc': Column(String),
        'cnam_ssn': Column(String),
        'isvm_dpc': Column(String),
        'isvm_ssn': Column(String),
        'wsmsc_dpc': Column(String),
        'wsmsc_ssn': Column(String),
        'enduserlocationvalue': Column(String),
        'enduserlocationtype': Column(String),
        'billingid': Column(String),
        'lnptype': Column(String),
        'downloadreason': Column(String),
        'svtype': Column(String),
        'altspid': Column(String),
        'alteult': Column(String),
        'alteulv': Column(String),
        'altbid': Column(String),
        'voiceuri': Column(String),
        'mmsuri': Column(String),
        'smsuri': Column(String)
    }
    model = type(f"{table_name.capitalize()}Model", (Base,), class_attrs)
    _dynamic_model_cache[table_name] = model  
    return model

# SPIDNames Table Model -----------------------------------
class SPIDNamesModel(Base):
    __tablename__ = "spidnames"

    spid: Mapped[str] = mapped_column(primary_key=True, index=True)
    spidname: Mapped[str]

# SimpleCarrierNames Table Model ---------------------------
class SimpleCarrierNamesModel(Base):
    __tablename__ = "simple_carrier_names"

    co_spec_name: Mapped[str] = mapped_column(primary_key=True, index=True)
    simplified_name: Mapped[str]

# NNMP Table Model ------------------------------------------
class NNMPModel(Base):
    __tablename__ = "nnmp"

    co_spec_name: Mapped[str] = mapped_column(primary_key=True, index=True)
    nnmp: Mapped[int]
