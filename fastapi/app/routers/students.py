import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from app.db import (
    create_student_record,
    fetch_students_data,
    fetch_student_by_id,
    update_student_record,
    delete_student_record,
    fetch_students_summary_stats,
    run_custom_sql_query,
)

logger = logging.getLogger("mcp_gateway.routers.students")
router = APIRouter(prefix="/api/db", tags=["SQL Server Database (wf) - CRUD"])


# ==============================================================================
# Pydantic Request & Response Models
# ==============================================================================
class StudentRecord(BaseModel):
    id: int
    student_name: str
    branch: str
    semester: int
    spi: Optional[float] = None
    cpi: Optional[float] = None
    exam_year: Optional[int] = None


class CreateStudentRequest(BaseModel):
    student_name: str = Field(..., description="Full name of the student", examples=["Rahul Verma"])
    branch: str = Field(..., description="Branch code (e.g. 'CE', 'IT', 'EC', 'ME')", examples=["CE"])
    semester: int = Field(..., description="Current semester (1 to 8)", ge=1, le=8, examples=[3])
    spi: float = Field(..., description="Semester Performance Index (0.0 to 10.0)", ge=0.0, le=10.0, examples=[8.75])
    cpi: float = Field(..., description="Cumulative Performance Index (0.0 to 10.0)", ge=0.0, le=10.0, examples=[8.60])
    exam_year: int = Field(..., description="Year of examination", ge=2000, le=2050, examples=[2024])
    custom_id: Optional[int] = Field(None, description="Optional custom ID. If omitted, auto-generates MAX(id) + 1")


class UpdateStudentRequest(BaseModel):
    student_name: Optional[str] = Field(None, description="Updated name")
    branch: Optional[str] = Field(None, description="Updated branch code")
    semester: Optional[int] = Field(None, description="Updated semester", ge=1, le=8)
    spi: Optional[float] = Field(None, description="Updated SPI score", ge=0.0, le=10.0)
    cpi: Optional[float] = Field(None, description="Updated CPI score", ge=0.0, le=10.0)
    exam_year: Optional[int] = Field(None, description="Updated exam year", ge=2000, le=2050)


class StudentsListResponse(BaseModel):
    success: bool
    database: str
    table: str
    total: int
    count: int
    offset: int
    limit: int
    students: List[StudentRecord]


class GenericSuccessResponse(BaseModel):
    success: bool
    message: str
    student: Optional[StudentRecord] = None
    deleted_id: Optional[int] = None


class SqlQueryRequest(BaseModel):
    query: str = Field(..., description="SQL Query to execute against the wf database", examples=["SELECT TOP 5 * FROM StudentsResult WHERE cpi > 8.5"])
    max_rows: Optional[int] = Field(default=100, description="Max rows to return", ge=1, le=500)


# ==============================================================================
# 1. CREATE ENDPOINT (POST /api/db/students)
# ==============================================================================
@router.post(
    "/students",
    response_model=GenericSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[1/4 CREATE] Add New Student Record",
)
async def create_student(payload: CreateStudentRequest):
    """
    Inserts a new student result record into the SQL Server database (`wf` -> `StudentsResult`).
    """
    try:
        result = create_student_record(
            student_name=payload.student_name,
            branch=payload.branch,
            semester=payload.semester,
            spi=payload.spi,
            cpi=payload.cpi,
            exam_year=payload.exam_year,
            custom_id=payload.custom_id,
        )
        return result
    except Exception as e:
        logger.exception("Failed to insert student record")
        raise HTTPException(status_code=500, detail=f"Create student failed: {str(e)}")


# ==============================================================================
# 2. READ ENDPOINTS (GET /api/db/students and GET /api/db/students/{id})
# ==============================================================================
@router.get(
    "/students",
    response_model=StudentsListResponse,
    summary="[2/4 READ] List & Filter Students",
)
async def list_students(
    branch: Optional[str] = Query(None, description="Filter by engineering branch (e.g. CE, IT, EC, ME)"),
    semester: Optional[int] = Query(None, description="Filter by semester (1 to 8)", ge=1, le=8),
    search: Optional[str] = Query(None, description="Search by student name or branch"),
    min_cpi: Optional[float] = Query(None, description="Minimum CPI threshold (e.g. 8.0)", ge=0.0, le=10.0),
    limit: int = Query(50, description="Number of records to return", ge=1, le=200),
    offset: int = Query(0, description="Pagination offset", ge=0),
):
    """
    Retrieves student records from Microsoft SQL Server (`wf` database -> `StudentsResult` table).
    """
    try:
        data = fetch_students_data(
            limit=limit,
            offset=offset,
            branch=branch,
            semester=semester,
            search=search,
            min_cpi=min_cpi,
        )
        return data
    except Exception as e:
        logger.exception("Failed to query student data from SQL Server")
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")


@router.get(
    "/students/{student_id}",
    response_model=StudentRecord,
    summary="[2/4 READ] Get Single Student by ID",
)
async def get_student_by_id(student_id: int):
    """
    Retrieves a single student record by their primary ID.
    """
    try:
        student = fetch_student_by_id(student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Student with ID {student_id} not found")
        return student
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching student {student_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# 3. UPDATE ENDPOINT (PUT /api/db/students/{id})
# ==============================================================================
@router.put(
    "/students/{student_id}",
    response_model=GenericSuccessResponse,
    summary="[3/4 UPDATE] Update Existing Student Record",
)
async def update_student(student_id: int, payload: UpdateStudentRequest):
    """
    Updates one or more fields of an existing student record in the `wf` database.
    """
    try:
        result = update_student_record(
            student_id=student_id,
            student_name=payload.student_name,
            branch=payload.branch,
            semester=payload.semester,
            spi=payload.spi,
            cpi=payload.cpi,
            exam_year=payload.exam_year,
        )
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Update failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating student {student_id}")
        raise HTTPException(status_code=500, detail=f"Update student failed: {str(e)}")


# ==============================================================================
# 4. DELETE ENDPOINT (DELETE /api/db/students/{id})
# ==============================================================================
@router.delete(
    "/students/{student_id}",
    response_model=GenericSuccessResponse,
    summary="[4/4 DELETE] Delete Student Record",
)
async def delete_student(student_id: int):
    """
    Deletes a student record from the `StudentsResult` table by ID.
    """
    try:
        result = delete_student_record(student_id)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Delete failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting student {student_id}")
        raise HTTPException(status_code=500, detail=f"Delete student failed: {str(e)}")


# ==============================================================================
# SUMMARY & CUSTOM QUERY
# ==============================================================================
@router.get("/students/stats/summary", summary="Get Aggregate Student Performance Metrics")
async def get_students_summary():
    """
    Calculates statistical summaries across branches, semesters, and overall CPI/SPI distributions.
    """
    try:
        return fetch_students_summary_stats()
    except Exception as e:
        logger.exception("Failed to calculate student statistics")
        raise HTTPException(status_code=500, detail=f"Database stats error: {str(e)}")


@router.post("/query", summary="Execute SQL Query on wf Database")
async def execute_sql(payload: SqlQueryRequest):
    """
    Execute a custom SQL query against the `wf` database.
    """
    try:
        result = run_custom_sql_query(payload.query, max_rows=payload.max_rows or 100)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("SQL execution failed")
        raise HTTPException(status_code=500, detail=f"SQL error: {str(e)}")
