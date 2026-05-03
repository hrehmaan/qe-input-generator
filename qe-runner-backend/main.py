"""
QE Runner Backend

This backend receives a generated Quantum ESPRESSO input file
and uploaded pseudopotential files.

Stage 1:
- Save files temporarily
- Auto-delete files after 10 minutes
- Allow manual deletion using job_id

Stage 2 later:
- Run pw.x for a tiny online QE check
"""

import asyncio
import shutil
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="QE Runner Backend",
    description="Temporary backend for Quantum ESPRESSO input checks.",
    version="0.1.0",
)

# Allow Streamlit frontend to call this backend.
# During development, we allow all origins.
# Later, we can restrict this to your Streamlit app URL only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_JOB_DIR = Path("qe_jobs")
BASE_JOB_DIR.mkdir(parents=True, exist_ok=True)

AUTO_DELETE_SECONDS = 600  # 10 minutes


def safe_filename(filename: str) -> str:
    """
    Keep only the file name, not any path.
    This prevents unsafe paths like ../../file.
    """
    return Path(filename).name


def remove_job_dir(job_dir: Path) -> None:
    """
    Delete a temporary job directory.
    """
    shutil.rmtree(job_dir, ignore_errors=True)


async def remove_job_dir_later(job_dir: Path, delay_seconds: int) -> None:
    """
    Delete a temporary job directory after a delay.
    """
    await asyncio.sleep(delay_seconds)
    remove_job_dir(job_dir)


@app.get("/")
def root():
    """
    Health check endpoint.
    """
    return {
        "status": "ok",
        "message": "QE Runner Backend is running.",
    }


@app.post("/qe-check")
async def qe_check(
    background_tasks: BackgroundTasks,
    input_text: str = Form(...),
    pseudo_files: list[UploadFile] = File(default=[]),
):
    """
    Receive QE input text and uploaded pseudopotential files.

    Files are saved in a temporary job folder and scheduled
    for automatic deletion after 10 minutes.
    """
    job_id = uuid.uuid4().hex
    job_dir = BASE_JOB_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    input_path = job_dir / "input.pwi"
    input_path.write_text(input_text, encoding="utf-8")

    saved_files = []

    for uploaded_file in pseudo_files:
        filename = safe_filename(uploaded_file.filename)

        if not filename.lower().endswith(".upf"):
            return {
                "status": "error",
                "job_id": job_id,
                "message": f"Only .UPF/.upf pseudopotential files are allowed. Invalid file: {filename}",
            }

        file_path = job_dir / filename
        content = await uploaded_file.read()
        file_path.write_bytes(content)

        saved_files.append(filename)

    background_tasks.add_task(
        remove_job_dir_later,
        job_dir,
        AUTO_DELETE_SECONDS,
    )

    return {
        "status": "uploaded",
        "job_id": job_id,
        "message": "Files uploaded successfully. Temporary files will be deleted automatically after 10 minutes.",
        "input_file": "input.pwi",
        "uploaded_pseudopotentials": saved_files,
        "auto_delete_seconds": AUTO_DELETE_SECONDS,
    }


@app.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    """
    Manually delete a temporary job folder.
    """
    job_dir = BASE_JOB_DIR / job_id

    if not job_dir.exists():
        return {
            "status": "not_found",
            "job_id": job_id,
            "message": "No temporary files found for this job_id. They may already have been deleted.",
        }

    remove_job_dir(job_dir)

    return {
        "status": "deleted",
        "job_id": job_id,
        "message": "Temporary files deleted successfully.",
    }


@app.get("/jobs/{job_id}")
def check_job(job_id: str):
    """
    Check whether a temporary job folder still exists.
    """
    job_dir = BASE_JOB_DIR / job_id

    if not job_dir.exists():
        return {
            "status": "not_found",
            "job_id": job_id,
            "message": "Temporary job folder does not exist.",
        }

    files = [path.name for path in job_dir.iterdir() if path.is_file()]

    return {
        "status": "exists",
        "job_id": job_id,
        "files": files,
    }