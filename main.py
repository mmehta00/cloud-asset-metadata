import os
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv

# Import authentication utilities and router
from auth import router as auth_router, get_current_user
from auth import MONGO_URI

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()

app = FastAPI(
    title="Cloud Asset Metadata API",
    description="Manage cloud asset metadata (EC2, S3, etc.) with REST API and JWT authentication",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Database Connection
# ----------------------------
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is not set")

try:
    client = MongoClient(MONGO_URI)
    db = client["cloudassets"]
    assets_collection = db["assets"]
    client.admin.command("ping")
    print("✅ Successfully connected to MongoDB Atlas")
except PyMongoError as e:
    print(f"❌ Error connecting to MongoDB: {e}")
    raise

# ----------------------------
# Models
# ----------------------------
class AssetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Asset name")
    type: str = Field(..., min_length=1, max_length=50, description="Asset type (e.g., EC2, S3)")
    region: str = Field(..., min_length=1, max_length=50, description="Cloud region")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "production-web-server",
                "type": "EC2",
                "region": "us-east-1"
            }
        }


class AssetResponse(BaseModel):
    asset_id: str = Field(..., alias="id")
    name: str
    owner: str
    type: str
    region: str

# ----------------------------
# Helper Function
# ----------------------------
def convert_objectid(asset: dict) -> dict:
    if asset and "_id" in asset:
        asset["id"] = str(asset["_id"])
        del asset["_id"]
    return asset

# ----------------------------
# Routes
# ----------------------------
@app.get("/")
def root():
    return {
        "message": "Cloud Asset Metadata API with Authentication",
        "auth_routes": {
            "register": "POST /auth/register",
            "login": "POST /auth/token"
        },
        "asset_routes": {
            "create": "POST /assets (requires JWT)",
            "list": "GET /assets (requires JWT)",
            "get": "GET /assets/{id} (requires JWT)",
            "delete": "DELETE /assets/{id} (requires JWT)"
        }
    }

# Register the authentication router
app.include_router(auth_router)

# ----------------------------
# Protected Asset Endpoints
# ----------------------------
@app.post("/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(asset: AssetCreate, current_user: str = Depends(get_current_user)):
    try:
        asset_dict = asset.dict()
        asset_dict["owner"] = current_user  # Assign owner dynamically
        result = assets_collection.insert_one(asset_dict)

        created_asset = assets_collection.find_one({"_id": result.inserted_id})
        return convert_objectid(created_asset)
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/assets", response_model=List[AssetResponse])
def list_assets(current_user: str = Depends(get_current_user)):
    try:
        assets = list(assets_collection.find({"owner": current_user}))
        return [convert_objectid(asset) for asset in assets]
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/assets/{id}", response_model=AssetResponse)
def get_asset(id: str, current_user: str = Depends(get_current_user)):
    try:
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="Invalid asset ID format")

        asset = assets_collection.find_one({"_id": ObjectId(id), "owner": current_user})
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found or unauthorized access")

        return convert_objectid(asset)
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.delete("/assets/{id}")
def delete_asset(id: str, current_user: str = Depends(get_current_user)):
    try:
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="Invalid asset ID format")

        result = assets_collection.delete_one({"_id": ObjectId(id), "owner": current_user})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Asset not found or unauthorized deletion")

        return {"message": f"✅ Asset '{id}' deleted successfully"}
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ----------------------------
# Run App (Local)
# ----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
