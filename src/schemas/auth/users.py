from pydantic import BaseModel

# Schema for validating user login credentials
class UserLoginSchema(BaseModel):
    login: str
    password: str

# Schema for changing user password
class UserPasswordChangeSchema(UserLoginSchema):
    new_password: str

# Schema for validating user endpoint access    
class UserEndpointSchema(BaseModel):
    uid: int
    username: str
    endpointid: int
    endpoint : str
    ip_address : str   

# Schema for user information
class UserInfoSchema(BaseModel):
    uid: int
    username: str
    is_superuser: bool
    ip_address : str
    
