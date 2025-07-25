from sqlalchemy import select, func, update
from src.models.users import UserProfilesModel 
from src.schemas.auth.users import UserLoginSchema
import logging

logger = logging.getLogger(__name__)

# Check user credentials in the database --------------------------------------------------------------
async def check_credentials(creds: UserLoginSchema, session) -> UserProfilesModel:
    user = await session.scalar(select(UserProfilesModel).where(UserProfilesModel.login == creds.login))
    if user is not None:
        password = await session.scalar(select(func.crypt(creds.password, user.password)))

        # Check if the user exists and the password is correct
        user = await session.scalar(
            select(UserProfilesModel).where(
                UserProfilesModel.login == creds.login,
                UserProfilesModel.password == password
            )  
        )
    return user

# Update user password --------------------------------------------------------------------------------
async def update_user_password(login: str, new_password: str, session):
    password_hash = await session.scalar(select(func.crypt(new_password, func.gen_salt('md5'))))

    state = await session.execute(
        update(UserProfilesModel)
        .where(UserProfilesModel.login == login)
        .values(password=password_hash)
    )
    await session.commit()
    return state.rowcount > 0