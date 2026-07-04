# CADVerify AI Backend

This folder contains the FastAPI backend foundation for the CADVerify AI platform.

## What is included
- FastAPI application entry point
- CORS middleware configuration
- Environment variable loading with `.env`
- Basic logging setup
- Health and root API routes
- Placeholder structure for future backend modules

## Run locally

1. Change into the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. Open the API docs:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API endpoints
- `GET /` returns a welcome message
- `GET /health` returns the service health status

## Notes
This backend foundation intentionally excludes OCR, DXF parsing, file uploads, and comparison logic so it remains ready for future implementation.
