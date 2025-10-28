import os
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional, List
from dotenv import load_dotenv
from auth import create_access_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta



app = FastAPI(
    title="Cloud Asset Metadata API",
    description="Manage cloud asset metadata (EC2, S3, etc.) with REST API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
load_dotenv()

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set")

try:
    client = MongoClient(MONGO_URI)
    db = client["cloudassets"]
    assets_collection = db["assets"]
    client.admin.command('ping')
    print("Successfully connected to MongoDB Atlas")
except PyMongoError as e:
    print(f"Error connecting to MongoDB: {e}")
    raise


class AssetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Asset name")
    owner: str = Field(..., min_length=1, max_length=100, description="Asset owner")
    type: str = Field(..., min_length=1, max_length=50, description="Asset type (e.g., EC2, S3)")
    region: str = Field(..., min_length=1, max_length=50, description="Cloud region")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "production-web-server",
                "owner": "engineering-team",
                "type": "EC2",
                "region": "us-east-1"
            }
        }


class AssetResponse(BaseModel):
    id: str = Field(..., description="Asset unique identifier")
    name: str
    owner: str
    type: str
    region: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "name": "production-web-server",
                "owner": "engineering-team",
                "type": "EC2",
                "region": "us-east-1"
            }
        }


def convert_objectid(asset: dict) -> dict:
    if asset and "_id" in asset:
        asset["id"] = str(asset["_id"])
        del asset["_id"]
    return asset



@app.get("/")
def root():
    return {
        "message": "Cloud Asset Metadata API",
        "endpoints": {
            "create": "POST /assets",
            "list": "GET /assets",
            "get": "GET /assets/{id}",
            "delete": "DELETE /assets/{id}"
        }
    }


@app.post("/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(asset: AssetCreate):
    try:
        asset_dict = asset.model_dump()
        result = assets_collection.insert_one(asset_dict)

        created_asset = assets_collection.find_one({"_id": result.inserted_id})
        return convert_objectid(created_asset)
    except PyMongoError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/assets", response_model=List[AssetResponse])
def list_assets():
    try:
        assets = list(assets_collection.find())
        return [convert_objectid(asset) for asset in assets]
    except PyMongoError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/assets/{id}", response_model=AssetResponse)
def get_asset(id: str):
    try:
        if not ObjectId.is_valid(id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid asset ID format"
            )

        asset = assets_collection.find_one({"_id": ObjectId(id)})

        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset with id '{id}' not found"
            )

        return convert_objectid(asset)
    except HTTPException:
        raise
    except PyMongoError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.delete("/assets/{id}", status_code=status.HTTP_200_OK)
def delete_asset(id: str):
    try:
        if not ObjectId.is_valid(id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid asset ID format"
            )

        result = assets_collection.delete_one({"_id": ObjectId(id)})

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset with id '{id}' not found"
            )

        return {"message": f"Asset with id '{id}' deleted successfully"}
    except HTTPException:
        raise
    except PyMongoError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
