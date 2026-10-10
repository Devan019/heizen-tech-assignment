import logging
from decimal import Decimal
from datetime import datetime, date
from typing import Any, Dict, List, Optional
import pyodbc
from app.config import get_settings

logger = logging.getLogger("mcp_gateway.db")


def serialize_db_value(val: Any) -> Any:
    """Helper to convert SQL Server types (Decimal, datetime, etc.) to JSON serializable objects."""
    if isinstance(val, Decimal):
        return float(val)
    elif isinstance(val, (datetime, date)):
        return val.isoformat()
    return val


def get_db_connection() -> pyodbc.Connection:
    """Establish and return a connection to Microsoft SQL Server."""
    settings = get_settings()
    driver = settings.SQL_SERVER_DRIVER
    server = settings.SQL_SERVER_HOST
    database = settings.SQL_SERVER_DATABASE

    candidate_servers = [server, "localhost", ".", "127.0.0.1"]
    candidate_drivers = [driver, "ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server"]

    last_error = None
    for d in candidate_drivers:
        for s in candidate_servers:
            if settings.SQL_SERVER_TRUSTED_CONNECTION:
                conn_str = f"DRIVER={{{d}}};SERVER={s};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes;"
            else:
                conn_str = f"DRIVER={{{d}}};SERVER={s};DATABASE={database};UID={settings.SQL_SERVER_USER};PWD={settings.SQL_SERVER_PASSWORD};TrustServerCertificate=yes;"

            try:
                conn = pyodbc.connect(conn_str, timeout=4)
                return conn
            except Exception as e:
                last_error = e

    logger.error(f"Failed to connect to SQL Server database '{database}': {last_error}")
    raise RuntimeError(f"SQL Server connection failed: {last_error}")


# ==============================================================================
# 1. CREATE (Insert student record)
# ==============================================================================
def create_student_record(
    student_name: str,
    branch: str,
    semester: int,
    spi: float,
    cpi: float,
    exam_year: int,
    custom_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Insert a new student record into StudentsResult table in wf database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Calculate ID if not provided
        if custom_id is None:
            cursor.execute("SELECT MAX(id) FROM [StudentsResult]")
            max_id = cursor.fetchone()[0] or 0
            new_id = max_id + 1
        else:
            new_id = custom_id

        insert_sql = """
            INSERT INTO [StudentsResult] (id, student_name, branch, semester, spi, cpi, exam_year)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(
            insert_sql,
            [new_id, student_name, branch.upper(), semester, spi, cpi, exam_year],
        )
        conn.commit()

        return {
            "success": True,
            "message": "Student record created successfully",
            "student": {
                "id": new_id,
                "student_name": student_name,
                "branch": branch.upper(),
                "semester": semester,
                "spi": float(spi),
                "cpi": float(cpi),
                "exam_year": exam_year,
            },
        }
    finally:
        conn.close()


# ==============================================================================
# 2. READ (Fetch students list or single student)
# ==============================================================================
def fetch_students_data(
    limit: int = 50,
    offset: int = 0,
    branch: Optional[str] = None,
    semester: Optional[int] = None,
    search: Optional[str] = None,
    min_cpi: Optional[float] = None,
) -> Dict[str, Any]:
    """Query student results from StudentsResult table in wf database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        where_clauses = []
        params: List[Any] = []

        if branch:
            where_clauses.append("branch = ?")
            params.append(branch.upper())

        if semester is not None:
            where_clauses.append("semester = ?")
            params.append(semester)

        if min_cpi is not None:
            where_clauses.append("cpi >= ?")
            params.append(min_cpi)

        if search:
            where_clauses.append("(student_name LIKE ? OR branch LIKE ?)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param])

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Count total
        count_sql = f"SELECT COUNT(*) FROM [StudentsResult] {where_sql}"
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()[0]

        # Fetch records
        query_sql = f"""
            SELECT id, student_name, branch, semester, spi, cpi, exam_year
            FROM [StudentsResult]
            {where_sql}
            ORDER BY id ASC
            OFFSET {offset} ROWS
            FETCH NEXT {limit} ROWS ONLY
        """
        cursor.execute(query_sql, params)
        columns = [column[0] for column in cursor.description]

        rows = cursor.fetchall()
        results = []
        for row in rows:
            row_dict = {col: serialize_db_value(val) for col, val in zip(columns, row)}
            results.append(row_dict)

        return {
            "success": True,
            "database": "wf",
            "table": "StudentsResult",
            "total": total_count,
            "count": len(results),
            "offset": offset,
            "limit": limit,
            "students": results,
        }
    finally:
        conn.close()


def fetch_student_by_id(student_id: int) -> Optional[Dict[str, Any]]:
    """Fetch single student record by ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, student_name, branch, semester, spi, cpi, exam_year FROM [StudentsResult] WHERE id = ?",
            [student_id],
        )
        row = cursor.fetchone()
        if not row:
            return None
        columns = [column[0] for column in cursor.description]
        return {col: serialize_db_value(val) for col, val in zip(columns, row)}
    finally:
        conn.close()


# ==============================================================================
# 3. UPDATE (Update student record)
# ==============================================================================
def update_student_record(
    student_id: int,
    student_name: Optional[str] = None,
    branch: Optional[str] = None,
    semester: Optional[int] = None,
    spi: Optional[float] = None,
    cpi: Optional[float] = None,
    exam_year: Optional[int] = None,
) -> Dict[str, Any]:
    """Update an existing student record in StudentsResult table."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Check existing record
        cursor.execute("SELECT id FROM [StudentsResult] WHERE id = ?", [student_id])
        if not cursor.fetchone():
            return {"success": False, "error": f"Student with ID {student_id} does not exist"}

        update_fields = []
        params: List[Any] = []

        if student_name is not None:
            update_fields.append("student_name = ?")
            params.append(student_name)
        if branch is not None:
            update_fields.append("branch = ?")
            params.append(branch.upper())
        if semester is not None:
            update_fields.append("semester = ?")
            params.append(semester)
        if spi is not None:
            update_fields.append("spi = ?")
            params.append(spi)
        if cpi is not None:
            update_fields.append("cpi = ?")
            params.append(cpi)
        if exam_year is not None:
            update_fields.append("exam_year = ?")
            params.append(exam_year)

        if not update_fields:
            return {"success": False, "error": "No fields provided to update"}

        params.append(student_id)
        update_sql = f"UPDATE [StudentsResult] SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(update_sql, params)
        conn.commit()

        # Fetch updated record
        updated_student = fetch_student_by_id(student_id)
        return {
            "success": True,
            "message": f"Student ID {student_id} updated successfully",
            "student": updated_student,
        }
    finally:
        conn.close()


# ==============================================================================
# 4. DELETE (Remove student record)
# ==============================================================================
def delete_student_record(student_id: int) -> Dict[str, Any]:
    """Delete a student record from StudentsResult table by ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Check if student exists
        cursor.execute("SELECT id, student_name, branch FROM [StudentsResult] WHERE id = ?", [student_id])
        row = cursor.fetchone()
        if not row:
            return {"success": False, "error": f"Student with ID {student_id} not found"}

        student_name = row[1]
        cursor.execute("DELETE FROM [StudentsResult] WHERE id = ?", [student_id])
        conn.commit()

        return {
            "success": True,
            "message": f"Student ID {student_id} ('{student_name}') deleted successfully",
            "deleted_id": student_id,
        }
    finally:
        conn.close()


# ==============================================================================
# SUMMARY & CUSTOM QUERY
# ==============================================================================
def fetch_students_summary_stats() -> Dict[str, Any]:
    """Calculate aggregate performance metrics by branch and semester."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*), AVG(CAST(cpi AS FLOAT)), AVG(CAST(spi AS FLOAT)), MAX(cpi), MIN(cpi) FROM [StudentsResult]")
        row = cursor.fetchone()
        overall = {
            "total_records": row[0],
            "average_cpi": round(row[1] or 0.0, 2),
            "average_spi": round(row[2] or 0.0, 2),
            "max_cpi": float(row[3] or 0.0),
            "min_cpi": float(row[4] or 0.0),
        }

        cursor.execute("""
            SELECT branch, COUNT(*) as count, AVG(CAST(cpi AS FLOAT)) as avg_cpi, AVG(CAST(spi AS FLOAT)) as avg_spi
            FROM [StudentsResult]
            GROUP BY branch
            ORDER BY avg_cpi DESC
        """)
        branches = [
            {
                "branch": r[0],
                "count": r[1],
                "avg_cpi": round(r[2] or 0.0, 2),
                "avg_spi": round(r[3] or 0.0, 2),
            }
            for r in cursor.fetchall()
        ]

        return {
            "overall": overall,
            "branches": branches,
        }
    finally:
        conn.close()


def run_custom_sql_query(sql_query: str, max_rows: int = 100) -> Dict[str, Any]:
    """Execute a read-only SELECT SQL query against the wf database."""
    forbidden = ["DROP", "TRUNCATE", "ALTER", "GRANT", "REVOKE"]
    for keyword in forbidden:
        if f" {keyword} " in f" {sql_query.upper()} ":
            raise ValueError(f"Dangerous query detected with keyword '{keyword}'. Query prohibited.")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql_query)
        if not cursor.description:
            conn.commit()
            return {"success": True, "rows": [], "rowcount": cursor.rowcount}

        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchmany(max_rows)
        data = [{col: serialize_db_value(val) for col, val in zip(columns, r)} for r in rows]

        return {
            "success": True,
            "database": "wf",
            "columns": columns,
            "row_count": len(data),
            "data": data,
        }
    finally:
        conn.close()
