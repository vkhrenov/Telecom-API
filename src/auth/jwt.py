from datetime import timedelta
from authx import AuthX, AuthXConfig
from src.configs.settings import get_settings

config = AuthXConfig()
config.JWT_ENCODE_ISSUER = get_settings().security.jwt_issuer
config.JWT_DECODE_ISSUER = get_settings().security.jwt_issuer
config.JWT_SECRET_KEY = get_settings().security.jwt_secret_key.get_secret_value()
config.JWT_COOKIE_SECURE = get_settings().security.jwt_cookie_secure
config.JWT_ACCESS_TOKEN_EXPIRES =  timedelta(seconds=get_settings().security.jwt_access_token_expire_secs)
config.JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=get_settings().security.jwt_refresh_token_expire_secs)
config.JWT_TOKEN_LOCATION = ["cookies", "headers"]
config.JWT_ACCESS_COOKIE_NAME = "access_token"
config.JWT_REFRESH_COOKIE_NAME = "refresh_token"
config.JWT_COOKIE_CSRF_PROTECT = False

security = AuthX(config=config)
