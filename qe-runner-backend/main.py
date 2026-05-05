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
import subprocess
import uuid
import time
import psutil
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
QE_TIMEOUT_SECONDS = 60
MAX_MEMORY_PERCENT = 97
MAX_CPU_PERCENT = 97
RESOURCE_CHECK_INTERVAL_SECONDS = 1


MAX_ATOMS_FOR_QE_CHECK = 30
MAX_UPLOADED_PSEUDO_FILES = 10
MAX_PSEUDO_FILE_SIZE_MB = 20
MAX_PSEUDO_FILE_SIZE_BYTES = MAX_PSEUDO_FILE_SIZE_MB * 1024 * 1024

def safe_filename(filename: str) -> str:
    """
    Keep only the file name, not any path.
    This prevents unsafe paths like ../../file.
    """
    return Path(filename).name


def extract_required_pseudos(input_text: str) -> list[str]:
    """
    Extract pseudopotential filenames from the ATOMIC_SPECIES card.

    Expected ATOMIC_SPECIES format:
        Element  AtomicMass  PseudoFile

    Example:
        Ba 137.327 Ba.upf
        Ti 47.867 Ti.upf
        O 15.999 O.upf
    """
    required_pseudos = []
    lines = input_text.splitlines()

    inside_atomic_species = False

    section_starters = (
        "&CONTROL",
        "&SYSTEM",
        "&ELECTRONS",
        "&IONS",
        "&CELL",
        "ATOMIC_POSITIONS",
        "CELL_PARAMETERS",
        "K_POINTS",
    )

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if inside_atomic_species:
                continue
            continue

        if stripped.startswith("ATOMIC_SPECIES"):
            inside_atomic_species = True
            continue

        if inside_atomic_species:
            if stripped.startswith(section_starters):
                break

            parts = stripped.split()

            if len(parts) >= 3:
                pseudo_file = parts[2]
                required_pseudos.append(pseudo_file)

    return required_pseudos


def extract_nat(input_text: str) -> int | None:
    """
    Extract nat from the &SYSTEM namelist.

    Example:
        nat = 10
    """
    for line in input_text.splitlines():
        stripped = line.strip()

        if stripped.lower().startswith("nat"):
            if "=" not in stripped:
                continue

            value = stripped.split("=", 1)[1]
            value = value.replace(",", "").strip()

            try:
                return int(float(value))
            except ValueError:
                return None

    return None

def make_text(value) -> str:
    """
    Convert subprocess output to text safely.
    TimeoutExpired can return bytes, str, or None.
    """
    if value is None:
        return ""

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    return str(value)

def extract_calculation(input_text: str) -> str | None:
    """
    Extract calculation type from &CONTROL.
    Example:
        calculation = 'scf'
    """
    for line in input_text.splitlines():
        stripped = line.strip()

        if stripped.lower().startswith("calculation"):
            if "=" not in stripped:
                continue

            value = stripped.split("=", 1)[1]
            value = value.replace(",", "").strip()
            value = value.strip("'").strip('"')
            return value.lower()

    return None

def classify_qe_output(output_text: str) -> str:
    """
    Classify QE output based on common markers.
    """
    lower_output = output_text.lower()

    if "job done" in lower_output:
        return "completed"

    if "convergence has been achieved" in lower_output:
        return "converged"

    if "error" in lower_output or "%%%%%%" in lower_output:
        return "error"

    if "program pwscf" in lower_output:
        return "started"

    if "reading input from" in lower_output:
        return "started"

    if "number of atoms/cell" in lower_output:
        return "started"

    return "unknown"


def make_text(value) -> str:
    """
    Convert subprocess output to text safely.
    TimeoutExpired can return bytes, str, or None.
    """
    if value is None:
        return ""

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    return str(value)


def classify_qe_output(output_text: str) -> str:
    """
    Classify QE output based on common Quantum ESPRESSO markers.
    """
    lower_output = output_text.lower()

    if "job done" in lower_output:
        return "completed"

    if "convergence has been achieved" in lower_output:
        return "converged"

    if "error" in lower_output or "%%%%%%" in lower_output:
        return "error"

    if "program pwscf" in lower_output:
        return "started"

    if "reading input from" in lower_output:
        return "started"

    if "number of atoms/cell" in lower_output:
        return "started"

    return "unknown"


def run_qe_smoke_check(job_dir: Path, timeout_seconds: int = QE_TIMEOUT_SECONDS) -> dict:
    """
    Run Quantum ESPRESSO for a short monitored smoke check.

    The goal is not to finish the simulation.
    The goal is to confirm that pw.x can start reading/running the generated input.
    """
    pwx_path = shutil.which("pw.x")

    if pwx_path is None:
        return {
            "qe_run_status": "qe_not_available",
            "qe_run_message": "pw.x was not found on this backend.",
            "qe_output_excerpt": "",
        }

    input_path = job_dir / "input.pwi"
    output_path = job_dir / "qe_check.out"

    output_chunks = []
    start_time = time.time()
    stop_reason = None
    max_memory_seen = 0.0
    max_cpu_seen = 0.0

    process = subprocess.Popen(
        [pwx_path, "-inp", input_path.name],
        cwd=job_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    ps_process = psutil.Process(process.pid)

    try:
        while True:
            elapsed = time.time() - start_time

            # Read available output line by line if possible
            if process.stdout is not None:
                line = process.stdout.readline()
                if line:
                    output_chunks.append(line)

            # Check whether QE finished
            return_code = process.poll()
            if return_code is not None:
                # Read remaining output
                if process.stdout is not None:
                    remaining_output = process.stdout.read()
                    if remaining_output:
                        output_chunks.append(remaining_output)

                output_text = "".join(output_chunks)
                output_path.write_text(output_text, encoding="utf-8", errors="replace")

                output_class = classify_qe_output(output_text)

                if return_code == 0:
                    return {
                        "qe_run_status": "qe_completed",
                        "qe_run_message": "pw.x completed successfully within the online smoke-check limit.",
                        "qe_output_excerpt": output_text[-3000:],
                        "resource_summary": {
                            "max_memory_percent": max_memory_seen,
                            "max_cpu_percent": max_cpu_seen,
                            "elapsed_seconds": round(elapsed, 2),
                        },
                    }

                return {
                    "qe_run_status": "qe_failed",
                    "qe_run_message": f"pw.x stopped with exit code {return_code}.",
                    "qe_output_excerpt": output_text[-3000:],
                    "resource_summary": {
                        "max_memory_percent": max_memory_seen,
                        "max_cpu_percent": max_cpu_seen,
                        "elapsed_seconds": round(elapsed, 2),
                        "output_class": output_class,
                    },
                }

            # Resource usage
            memory_percent = psutil.virtual_memory().percent
            cpu_percent = psutil.cpu_percent(interval=0.1)

            max_memory_seen = max(max_memory_seen, memory_percent)
            max_cpu_seen = max(max_cpu_seen, cpu_percent)

            if memory_percent >= MAX_MEMORY_PERCENT:
                stop_reason = (
                    f"Memory usage reached {memory_percent:.1f}% "
                    f"and exceeded the safety limit of {MAX_MEMORY_PERCENT}%."
                )
                process.terminate()
                break

            if cpu_percent >= MAX_CPU_PERCENT:
                stop_reason = (
                    f"CPU usage reached {cpu_percent:.1f}% "
                    f"and exceeded the safety limit of {MAX_CPU_PERCENT}%."
                )
                process.terminate()
                break

            if elapsed >= timeout_seconds:
                stop_reason = (
                    f"pw.x exceeded the {timeout_seconds}-second online smoke-check limit."
                )
                process.terminate()
                break

            time.sleep(RESOURCE_CHECK_INTERVAL_SECONDS)

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

        if process.stdout is not None:
            remaining_output = process.stdout.read()
            if remaining_output:
                output_chunks.append(remaining_output)

        output_text = "".join(output_chunks)
        output_path.write_text(output_text, encoding="utf-8", errors="replace")

        output_class = classify_qe_output(output_text)

        if output_class in ["started", "converged", "completed"]:
            status = "qe_started_but_stopped"
            message = (
                "pw.x started successfully and produced valid Quantum ESPRESSO output. "
                f"The online check stopped early: {stop_reason}"
            )
        else:
            status = "qe_stopped"
            message = (
                "pw.x was stopped during the online smoke check. "
                f"Reason: {stop_reason}"
            )

        return {
            "qe_run_status": status,
            "qe_run_message": message,
            "qe_output_excerpt": output_text[-3000:],
            "resource_summary": {
                "max_memory_percent": max_memory_seen,
                "max_cpu_percent": max_cpu_seen,
                "elapsed_seconds": round(time.time() - start_time, 2),
                "output_class": output_class,
                "stop_reason": stop_reason,
            },
        }

    except Exception as error:
        try:
            process.kill()
        except Exception:
            pass

        output_text = "".join(output_chunks)

        return {
            "qe_run_status": "qe_failed",
            "qe_run_message": f"Backend error while monitoring pw.x: {type(error).__name__}: {error}",
            "qe_output_excerpt": output_text[-3000:],
            "resource_summary": {
                "max_memory_percent": max_memory_seen,
                "max_cpu_percent": max_cpu_seen,
                "elapsed_seconds": round(time.time() - start_time, 2),
            },
        }    

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
    run_qe: bool = Form(False),
    pseudo_files: list[UploadFile] = File(default=[]),
):
    """
    Receive QE input text and uploaded pseudopotential files.

    Files are saved in a temporary job folder and scheduled
    for automatic deletion after 10 minutes.
    """
    
    if len(pseudo_files) > MAX_UPLOADED_PSEUDO_FILES:
        return {
            "status": "too_many_files",
            "message": (
                f"Too many pseudopotential files uploaded. "
                f"Maximum allowed is {MAX_UPLOADED_PSEUDO_FILES}."
            ),
            "max_uploaded_pseudo_files": MAX_UPLOADED_PSEUDO_FILES,
        }

    nat = extract_nat(input_text)

    if run_qe and nat is not None and nat > MAX_ATOMS_FOR_QE_CHECK:
        return {
            "status": "too_many_atoms_for_qe_check",
            "message": (
                f"This input has nat = {nat}. "
                f"The online QE smoke check is limited to nat <= {MAX_ATOMS_FOR_QE_CHECK}. "
                "You can still download the input file and run it locally, in Docker, or on an HPC cluster."
            ),
            "nat": nat,
            "max_atoms_for_qe_check": MAX_ATOMS_FOR_QE_CHECK,
        }
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

        if len(content) > MAX_PSEUDO_FILE_SIZE_BYTES:
            remove_job_dir(job_dir)

            return {
                "status": "file_too_large",
                "job_id": job_id,
                "message": (
                    f"Uploaded file '{filename}' is too large. "
                    f"Maximum allowed size is {MAX_PSEUDO_FILE_SIZE_MB} MB."
                ),
                "file": filename,
                "max_file_size_mb": MAX_PSEUDO_FILE_SIZE_MB,
            }

        file_path.write_bytes(content)

        saved_files.append(filename)

    required_pseudos = extract_required_pseudos(input_text)
    missing_pseudos = [
        pseudo for pseudo in required_pseudos if pseudo not in saved_files
    ]

    background_tasks.add_task(
        remove_job_dir_later,
        job_dir,
        AUTO_DELETE_SECONDS,
    )

    if missing_pseudos:
        return {
            "status": "missing_pseudopotentials",
            "job_id": job_id,
            "message": "Some pseudopotential files listed in ATOMIC_SPECIES were not uploaded.",
            "input_file": "input.pwi",
            "required_pseudopotentials": required_pseudos,
            "uploaded_pseudopotentials": saved_files,
            "missing_pseudopotentials": missing_pseudos,
            "auto_delete_seconds": AUTO_DELETE_SECONDS,
        }
    
    calculation_type = extract_calculation(input_text)

    heavy_calculations = ["relax", "vc-relax", "md", "vc-md"]

    if run_qe and calculation_type in heavy_calculations:
        return {
            "status": "ready_for_qe_check",
            "job_id": job_id,
            "message": (
                f"calculation = '{calculation_type}' is structurally valid, "
                "but full relaxation/MD calculations are too heavy for the online smoke check."
            ),
            "input_file": "input.pwi",
            "required_pseudopotentials": required_pseudos,
            "uploaded_pseudopotentials": saved_files,
            "missing_pseudopotentials": [],
            "auto_delete_seconds": AUTO_DELETE_SECONDS,
            "qe_run_status": "qe_too_large_for_online_check",
            "qe_run_message": (
                f"The online smoke check does not run '{calculation_type}' jobs. "
                "Use 'scf' for the online smoke check, or download this input and run it locally, in Docker, or on HPC."
            ),
            "qe_output_excerpt": "",
        }

    qe_result = {
        "qe_run_status": "not_requested",
        "qe_run_message": "QE smoke check was not requested.",
        "qe_output_excerpt": "",
    }

    if run_qe:
        qe_result = run_qe_smoke_check(job_dir=job_dir, timeout_seconds=QE_TIMEOUT_SECONDS)

    return {
        "status": "ready_for_qe_check",
        "job_id": job_id,
        "message": "All required pseudopotential files were uploaded. Temporary files will be deleted automatically after 10 minutes.",
        "input_file": "input.pwi",
        "required_pseudopotentials": required_pseudos,
        "uploaded_pseudopotentials": saved_files,
        "missing_pseudopotentials": [],
        "auto_delete_seconds": AUTO_DELETE_SECONDS,
        **qe_result,
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