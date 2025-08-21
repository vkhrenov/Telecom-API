from sqlalchemy.orm import Mapped, mapped_column, declarative_base

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
    datecreated: Mapped[str] = mapped_column(nullable=True)
    datedeactivated: Mapped[str] = mapped_column(nullable=True)

# User Settings Table Model ---------------------------------------------------
class UserSettingsModel(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    userid: Mapped[int] = mapped_column(unique=True ,index=True)
    productid: Mapped[int]
    ratio: Mapped[float]
    productpriority: Mapped[int]
    dateeff: Mapped[str] = mapped_column(nullable=True, index=True)
    dateexp: Mapped[str] = mapped_column(nullable=True, index=True)

# User Rates Table Model ---------------------------------------------------
class RatesModel(Base):
    __tablename__ = "rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    productid: Mapped[int]
    endpointid: Mapped[int]
    rate: Mapped[float]
    dateeff: Mapped[str] = mapped_column(nullable=True, index=True)
    dateexp: Mapped[str] = mapped_column(nullable=True, index=True)

# Endpoints Table Model ---------------------------------------------------
class EndpointsModel(Base):
    __tablename__ = "endpoints"

    id: Mapped[int] = mapped_column(primary_key=True)
    endpoint: Mapped[str] = mapped_column(unique=True, index=True)
    description: Mapped[str]

# User Endpoint Model ---------------------------------------------------
class EndpointStats(Base):
    __tablename__ = "endpoint_stats"

    calldate: Mapped[str] = mapped_column(primary_key=True, index=True)
    userid: Mapped[int] = mapped_column(primary_key=True, index=True)
    endpointid: Mapped[int] = mapped_column(primary_key=True)
    count: Mapped[int]
