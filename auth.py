from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from pymongo.errors import DuplicateKeyError
import os
import re

# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv()

# ✅ Required environment variables (no hardcoding)
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
MONGO_URI = os.getenv("MONGO_URI")

# Fail fast if missing any .env values
if os.getenv("GITHUB_ACTIONS") == "true":
    print("⚠️ Running in GitHub Actions CI — skipping env var enforcement.")
    SECRET_KEY = SECRET_KEY or "dummy_secret"
    ALGORITHM = ALGORITHM or "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = ACCESS_TOKEN_EXPIRE_MINUTES or "60"
    MONGO_URI = MONGO_URI or "mongodb://localhost:27017/testdb"
    
required_env_vars = {
    "SECRET_KEY": SECRET_KEY,
    "ALGORITHM": ALGORITHM,
    "ACCESS_TOKEN_EXPIRE_MINUTES": ACCESS_TOKEN_EXPIRE_MINUTES,
    "MONGO_URI": MONGO_URI,
}

missing = [k for k, v in required_env_vars.items() if not v]
if missing:
    raise ValueError(f"❌ Missing required environment variables: {', '.join(missing)}")

# Convert token expiry to integer safely
try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(ACCESS_TOKEN_EXPIRE_MINUTES)
except ValueError:
    raise ValueError("❌ ACCESS_TOKEN_EXPIRE_MINUTES must be an integer")

# ---------------------------
# Database connection (MongoDB)
# ---------------------------
client = MongoClient(MONGO_URI)
db = client["cloudassets"]
users_collection = db["users"]

if os.getenv("GITHUB_ACTIONS") == "true":
    print("⚠️ Running in GitHub Actions CI — skipping MongoDB connection.")
    client = None
    db = None
    users_collection = None
else:
    try:
        client = MongoClient(MONGO_URI)
        db = client["cloudassets"]
        users_collection = db["users"]
        client.admin.command("ping")
        users_collection.create_index("username", unique=True)
        print("✅ Connected to MongoDB and ensured unique index on username")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise
# ---------------------------
# Security Configuration
# ---------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = HTTPBearer()

# ---------------------------
# FastAPI Router
# ---------------------------
router = APIRouter(prefix="/auth", tags=["Authentication"])

# ---------------------------
# Helper Functions
# ---------------------------
def get_password_hash(password: str) -> str:
    """Hash a plain text password safely within bcrypt limits."""
    if len(password.encode("utf-8")) > 72:
        password = password[:72]  # bcrypt truncates past 72 bytes
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password safely within bcrypt limits."""
    if len(plain_password.encode("utf-8")) > 72:
        plain_password = plain_password[:72]
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Generate a new JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def validate_username(username: str):
    """Allow alphanumeric usernames with limited special characters."""
    pattern = r"^[A-Za-z0-9_.@-]+$"
    if not re.match(pattern, username):
        raise HTTPException(
            status_code=400,
            detail="Username can only include letters, numbers, and _ . @ - characters."
        )
    return username

def validate_password(password: str):
    """Enforce password complexity."""
    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$"
    if not re.match(pattern, password):
        raise HTTPException(
            status_code=400,
            detail=(
                "Password must be at least 8 characters long, include one uppercase letter, "
                "one lowercase letter, one number, and one special character."
            )
        )
    return password

# ---------------------------
# API Routes
# ---------------------------
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(form_data: OAuth2PasswordRequestForm = Depends()):
    """Register a new user securely with validation."""
    username = validate_username(form_data.username)
    password = validate_password(form_data.password)

    hashed_pw = get_password_hash(password)

    try:
        users_collection.insert_one({"username": username, "password": hashed_pw})
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Username already exists")

    return {"message": f"✅ User '{username}' registered successfully"}

@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate and return a JWT token."""
    username = validate_username(form_data.username)
    user = users_collection.find_one({"username": username})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    """Decode and verify JWT to identify the current user."""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
