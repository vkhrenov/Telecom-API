from sqlalchemy.orm import Mapped, mapped_column, declarative_base
from sqlalchemy import text, DateTime

Base = declarative_base()

# User Profiles Table Model ---------------------------------------------------
class UserProfilesModel(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str]
    name: Mapped[str]
    login: Mapped[str] = mapped_column(unique=True, index=True)
    password: Mapped[str]  = mapped_column(index=True)
    email: Mapped[str]
    isactive: Mapped[bool]
    issuperuser: Mapped[bool]
    datecreated: Mapped[str] = mapped_column(DateTime, nullable=False, server_default=text("now()"))
    datedeactivated: Mapped[str] = mapped_column(DateTime, nullable=False, server_default=text("'2222-01-01 00:00:00'::timestamp without time zone"))

# Deleted User Profiles Table Model ---------------------------------------------    
class UserProfilesDelModel(Base):
    __tablename__ = "user_profiles_del"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str]
    name: Mapped[str]
    login: Mapped[str] = mapped_column(unique=True, index=True)
    password: Mapped[str]  = mapped_column(index=True)
    email: Mapped[str]
    isactive: Mapped[bool]
    issuperuser: Mapped[bool]
    datecreated: Mapped[str] = mapped_column(DateTime, nullable=False)
    datedeactivated: Mapped[str] = mapped_column(DateTime, nullable=False)
    datedeleted: Mapped[str] = mapped_column(DateTime, nullable=False, server_default=text("now()"))    

# User Settings Table Model ---------------------------------------------------
class UserSettingsModel(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    userid: Mapped[int] = mapped_column(unique=True ,index=True)
    productid: Mapped[int]
    note: Mapped[str]
    ratio: Mapped[float]
    productpriority: Mapped[int]
    dateeff: Mapped[str] = mapped_column(DateTime, nullable=False, index=True, server_default=text("now()") )
    dateexp: Mapped[str] = mapped_column(DateTime, nullable=False, index=True, server_default=text("'2222-01-01 00:00:00'::timestamp without time zone"))

# User Rates Table Model ---------------------------------------------------
class RatesModel(Base):
    __tablename__ = "rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    productid: Mapped[int]
    endpointid: Mapped[int]
    rate: Mapped[float]
    dateeff: Mapped[str] = mapped_column(DateTime, nullable=False, index=True, server_default=text("now()") )
    dateexp: Mapped[str] = mapped_column(DateTime, nullable=False, index=True, server_default=text("'2222-01-01 00:00:00'::timestamp without time zone"))

# Products Table Model ---------------------------------------------------
class ProductsModel(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    productname: Mapped[str] = mapped_column(unique=True, index=True)
    description: Mapped[str]

# Endpoints Table Model ---------------------------------------------------
class EndpointsModel(Base):
    __tablename__ = "endpoints"

    id: Mapped[int] = mapped_column(primary_key=True)
    endpoint: Mapped[str] = mapped_column(unique=True, index=True)
    description: Mapped[str]

# User Endpoint Table Model ---------------------------------------------------
class EndpointStatsModel(Base):
    __tablename__ = "endpoint_stats"

    calldate: Mapped[str] = mapped_column(primary_key=True, index=True, server_default=text("now()"))
    userid: Mapped[int] = mapped_column(primary_key=True, index=True)
    endpointid: Mapped[int] = mapped_column(primary_key=True)
    count: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    amount: Mapped[float] = mapped_column(nullable=False, server_default=text("0.0"))

