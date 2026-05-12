from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    raw_password = password.encode('utf-8')
    if len(raw_password) > 72:
        raise ValueError("Password is too long. Bcrypt supports a maximum of 72 bytes.")
    return pwd_context.hash(raw_password)

def verify_password(plain: str, hashed: str) -> bool:
    safe_plain = plain.encode('utf-8')[:72]
    return pwd_context.verify(safe_plain, hashed)