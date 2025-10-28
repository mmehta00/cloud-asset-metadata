# Cloud Asset Metadata API

A FastAPI-based REST API for managing cloud asset metadata (EC2, S3, etc.) using MongoDB Atlas.

## Features

- **CRUD Operations**: Create, Read, List, and Delete cloud assets
- **MongoDB Atlas Integration**: Uses PyMongo for database operations
- **Pydantic Validation**: Request/response validation and serialization
- **CORS Enabled**: Ready for Postman and frontend integration
- **Error Handling**: Comprehensive error responses (404, 500, etc.)
- **OpenAPI Docs**: Interactive API documentation at `/docs`

## Prerequisites

- Python 3.8+
- MongoDB Atlas account with a cluster
- MongoDB connection string (MONGO_URI)

## Installation

### Local Setup

1. **Clone or download this project**

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variable**

   **Linux/Mac:**
   ```bash
   export MONGO_URI="mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority"
   ```

   **Windows (Command Prompt):**
   ```cmd
   set MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
   ```

   **Windows (PowerShell):**
   ```powershell
   $env:MONGO_URI="mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority"
   ```

   Alternatively, create a `.env` file:
   ```env
   MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
   ```

4. **Run the application**
   ```bash
   uvicorn main:app --reload
   ```

   The API will be available at: `http://localhost:8000`

### Replit Setup

1. Upload all files to your Replit project
2. Add `MONGO_URI` to Secrets (lock icon in sidebar)
3. Run: `uvicorn main:app --host 0.0.0.0 --port 8000`

## API Endpoints

### 1. Root
```http
GET /
```
Returns API information and available endpoints.

### 2. Create Asset
```http
POST /assets
Content-Type: application/json

{
  "name": "production-web-server",
  "owner": "engineering-team",
  "type": "EC2",
  "region": "us-east-1"
}
```

**Response (201 Created):**
```json
{
  "id": "507f1f77bcf86cd799439011",
  "name": "production-web-server",
  "owner": "engineering-team",
  "type": "EC2",
  "region": "us-east-1"
}
```

### 3. List All Assets
```http
GET /assets
```

**Response (200 OK):**
```json
[
  {
    "id": "507f1f77bcf86cd799439011",
    "name": "production-web-server",
    "owner": "engineering-team",
    "type": "EC2",
    "region": "us-east-1"
  }
]
```

### 4. Get Single Asset
```http
GET /assets/{id}
```

**Response (200 OK):**
```json
{
  "id": "507f1f77bcf86cd799439011",
  "name": "production-web-server",
  "owner": "engineering-team",
  "type": "EC2",
  "region": "us-east-1"
}
```

**Error (404 Not Found):**
```json
{
  "detail": "Asset with id '507f1f77bcf86cd799439011' not found"
}
```

### 5. Delete Asset
```http
DELETE /assets/{id}
```

**Response (200 OK):**
```json
{
  "message": "Asset with id '507f1f77bcf86cd799439011' deleted successfully"
}
```

**Error (404 Not Found):**
```json
{
  "detail": "Asset with id '507f1f77bcf86cd799439011' not found"
}
```

## Interactive API Documentation

Once the server is running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing with Postman

### Example POST Request

**URL:** `http://localhost:8000/assets`

**Method:** `POST`

**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
  "name": "production-database",
  "owner": "data-team",
  "type": "RDS",
  "region": "us-west-2"
}
```

### More Example Payloads

**S3 Bucket:**
```json
{
  "name": "company-backups-bucket",
  "owner": "devops-team",
  "type": "S3",
  "region": "eu-west-1"
}
```

**Lambda Function:**
```json
{
  "name": "image-processor",
  "owner": "ml-team",
  "type": "Lambda",
  "region": "ap-southeast-1"
}
```

**EKS Cluster:**
```json
{
  "name": "production-k8s",
  "owner": "platform-team",
  "type": "EKS",
  "region": "us-east-1"
}
```

## Database Structure

- **Database Name**: `cloudassets`
- **Collection Name**: `assets`
- **Document Schema**:
  ```json
  {
    "_id": ObjectId("..."),
    "name": "string",
    "owner": "string",
    "type": "string",
    "region": "string"
  }
  ```

## Error Handling

The API returns appropriate HTTP status codes:

- **200 OK**: Successful GET/DELETE
- **201 Created**: Successful POST
- **400 Bad Request**: Invalid asset ID format
- **404 Not Found**: Asset not found
- **500 Internal Server Error**: Database or server errors

## AWS Lambda Deployment (Zappa)

To deploy this API to AWS Lambda using Zappa:

1. **Install Zappa**
   ```bash
   pip install zappa
   ```

2. **Create `zappa_settings.json`**
   ```json
   {
     "production": {
       "app_function": "main.app",
       "aws_region": "us-east-1",
       "runtime": "python3.9",
       "environment_variables": {
         "MONGO_URI": "your-mongodb-atlas-connection-string"
       },
       "keep_warm": false,
       "memory_size": 512,
       "timeout_seconds": 30
     }
   }
   ```

3. **Deploy**
   ```bash
   zappa deploy production
   ```

4. **Update**
   ```bash
   zappa update production
   ```

5. **View logs**
   ```bash
   zappa tail production
   ```

**Note:** For production, use AWS Secrets Manager or Parameter Store instead of hardcoding credentials.

## Project Structure

```
.
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── .env                # Environment variables (optional)
```

## Environment Variables

- `MONGO_URI` (required): MongoDB Atlas connection string

Example:
```
mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
```

## Development

Run in development mode with auto-reload:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## License

MIT
