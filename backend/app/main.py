import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CADVerify AI Backend",
    description="Backend foundation for CAD drawing verification workflows.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent
UPLOAD_DIR: Final[Path] = BASE_DIR / "uploads"
PDF_DIR: Final[Path] = UPLOAD_DIR / "pdf"
DXF_DIR: Final[Path] = UPLOAD_DIR / "dxf"


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "CADVerify AI Backend Running 🚀"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "CADVerify AI Backend",
    }


@app.post("/upload")
async def upload_files(
    pdf_file: UploadFile = File(..., description="PDF engineering drawing"),
    dxf_file: UploadFile = File(..., description="DXF CAD drawing"),
) -> dict[str, object]:
    try:
        PDF_DIR.mkdir(parents=True, exist_ok=True)
        DXF_DIR.mkdir(parents=True, exist_ok=True)

        pdf_extension = Path(pdf_file.filename or "").suffix.lower()
        dxf_extension = Path(dxf_file.filename or "").suffix.lower()

        if pdf_extension != ".pdf":
            raise HTTPException(status_code=400, detail="The PDF file must have a .pdf extension.")
        if dxf_extension != ".dxf":
            raise HTTPException(status_code=400, detail="The DXF file must have a .dxf extension.")

        unique_suffix = uuid.uuid4().hex[:8]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        pdf_target_name = f"{timestamp}_{unique_suffix}_{Path(pdf_file.filename or 'uploaded.pdf').stem}.pdf"
        dxf_target_name = f"{timestamp}_{unique_suffix}_{Path(dxf_file.filename or 'uploaded.dxf').stem}.dxf"

        pdf_target_path = PDF_DIR / pdf_target_name
        dxf_target_path = DXF_DIR / dxf_target_name

        with pdf_target_path.open("wb") as pdf_buffer:
            pdf_buffer.write(await pdf_file.read())

        with dxf_target_path.open("wb") as dxf_buffer:
            dxf_buffer.write(await dxf_file.read())

        return {
            "status": "uploaded",
            "original_filenames": [pdf_file.filename, dxf_file.filename],
            "stored_filenames": [pdf_target_name, dxf_target_name],
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive fallback for runtime errors
        logger.exception("Upload processing failed")
        raise HTTPException(status_code=500, detail="Failed to upload files.") from exc


@app.on_event("startup")
def startup_event() -> None:
    logger.info("CADVerify AI backend startup complete")
