"""
Database repository for user management and document processing.
Uses raw parameterized SQL (%s) with PyMySQL connection context manager.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from backend.app.db import get_connection
from shared.contracts import Clause, ClauseGraph

logger = logging.getLogger(__name__)


def create_user(email: str, password_hash: str, full_name: str) -> int:
    """
    Insert a new user record into the users table using raw parameterized SQL.

    Args:
        email: Unique user email address.
        password_hash: Bcrypt password hash.
        full_name: Full name of the user.

    Returns:
        The auto-generated user_id (int).
    """
    sql = (
        "INSERT INTO users (email, password_hash, full_name) "
        "VALUES (%s, %s, %s)"
    )
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (email, password_hash, full_name))
            user_id = cursor.lastrowid
            logger.info("Successfully registered user ID %d (%s)", user_id, email)
            return int(user_id)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user record by email address using raw parameterized SQL.

    Args:
        email: Email address to search for.

    Returns:
        Dict of user row fields or None if not found.
    """
    sql = (
        "SELECT user_id, email, password_hash, full_name, created_at "
        "FROM users WHERE email = %s"
    )
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (email,))
            return cursor.fetchone()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve user record by user_id using raw parameterized SQL.

    Args:
        user_id: User identifier.

    Returns:
        Dict of user row fields or None if not found.
    """
    sql = (
        "SELECT user_id, email, password_hash, full_name, created_at "
        "FROM users WHERE user_id = %s"
    )
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (user_id,))
            return cursor.fetchone()


def create_document(
    file_name: str,
    document_type: str,
    stored_path: str,
    user_id: int,
) -> int:
    """
    Insert a new document record into documents table with status 'UPLOADED'.

    Args:
        file_name: Original contract filename.
        document_type: Contract type ('MSA', 'SOW', 'OTHER').
        stored_path: Path on filesystem where the file was saved.
        user_id: ID of the user uploading the document.

    Returns:
        Auto-generated document_id (int).
    """
    sql = (
        "INSERT INTO documents (file_name, document_type, stored_path, created_by, status) "
        "VALUES (%s, %s, %s, %s, 'UPLOADED')"
    )
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (file_name, document_type, stored_path, user_id))
            doc_id = cursor.lastrowid
            logger.info("Successfully created document ID %d (%s)", doc_id, file_name)
            return int(doc_id)


def update_document_status(
    document_id: int,
    status: str,
    page_count: Optional[int] = None,
    parser_version: Optional[str] = None,
) -> None:
    """
    Update document processing status and optional metadata.

    Args:
        document_id: ID of the target document.
        status: New DocumentStatus value ('UPLOADED', 'PARSED', 'ANALYZED', 'FAILED').
        page_count: Optional extracted total page count.
        parser_version: Optional parser engine version string.
    """
    if page_count is not None and parser_version is not None:
        sql = (
            "UPDATE documents "
            "SET status = %s, page_count = %s, parser_version = %s "
            "WHERE document_id = %s"
        )
        params = (status, page_count, parser_version, document_id)
    elif page_count is not None:
        sql = (
            "UPDATE documents "
            "SET status = %s, page_count = %s "
            "WHERE document_id = %s"
        )
        params = (status, page_count, document_id)
    elif parser_version is not None:
        sql = (
            "UPDATE documents "
            "SET status = %s, parser_version = %s "
            "WHERE document_id = %s"
        )
        params = (status, parser_version, document_id)
    else:
        sql = "UPDATE documents SET status = %s WHERE document_id = %s"
        params = (status, document_id)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            logger.info("Updated document %d status to %s", document_id, status)


def get_document(document_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve document record by document_id scoped strictly to created_by user_id.

    Args:
        document_id: ID of document.
        user_id: ID of requesting user.

    Returns:
        Dict of document row fields or None if not found or unauthorized.
    """
    sql = (
        "SELECT document_id, file_name, document_type, status, page_count, "
        "stored_path, parser_version, uploaded_at, created_by "
        "FROM documents "
        "WHERE document_id = %s AND created_by = %s"
    )
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (document_id, user_id))
            return cursor.fetchone()


def list_documents(user_id: int) -> List[Dict[str, Any]]:
    """
    List all documents uploaded by a user, ordered newest first.

    Args:
        user_id: ID of requesting user.

    Returns:
        List of document row dicts ordered by uploaded_at DESC, document_id DESC.
    """
    sql = (
        "SELECT document_id, file_name, document_type, status, page_count, "
        "stored_path, parser_version, uploaded_at, created_by "
        "FROM documents "
        "WHERE created_by = %s "
        "ORDER BY uploaded_at DESC, document_id DESC"
    )
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (user_id,))
            rows = cursor.fetchall()
            return list(rows) if rows else []


def insert_clauses(document_id: int, clauses: List[Clause]) -> None:
    """
    Batch insert parsed clauses into clauses table using executemany in ONE transaction.

    Args:
        document_id: ID of parent document.
        clauses: List of validated Clause contract instances.
    """
    if not clauses:
        return

    sql = (
        "INSERT INTO clauses ("
        "document_id, clause_id, title, text, page_number, section, parent_clause_id, references_json"
        ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    )
    rows = [
        (
            document_id,
            c.clause_id,
            c.title,
            c.text,
            c.page_number,
            c.section,
            c.parent_clause_id,
            json.dumps(c.references),
        )
        for c in clauses
    ]
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(sql, rows)
            logger.info("Successfully inserted %d clauses for document %d", len(clauses), document_id)


def get_clauses(document_id: int) -> List[Dict[str, Any]]:
    """
    Retrieve all parsed clauses for a document ordered by ascending id.

    Args:
        document_id: Document identifier.

    Returns:
        List of clause row dicts with references_json parsed as python list.
    """
    sql = (
        "SELECT id, document_id, clause_id, title, text, page_number, "
        "section, parent_clause_id, references_json, created_at "
        "FROM clauses "
        "WHERE document_id = %s "
        "ORDER BY id ASC"
    )
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (document_id,))
            rows = cursor.fetchall()
            result: List[Dict[str, Any]] = []
            for r in rows or []:
                row_dict = dict(r)
                if isinstance(row_dict.get("references_json"), str):
                    row_dict["references_json"] = json.loads(row_dict["references_json"])
                result.append(row_dict)
            return result


def save_graph(document_id: int, graph: ClauseGraph) -> None:
    """
    Persist or update clause dependency graph topology in clause_graphs table.

    Args:
        document_id: ID of document.
        graph: ClauseGraph contract model.
    """
    sql = (
        "INSERT INTO clause_graphs (document_id, graph_json, has_cycle) "
        "VALUES (%s, %s, %s) "
        "ON DUPLICATE KEY UPDATE "
        "graph_json = VALUES(graph_json), "
        "has_cycle = VALUES(has_cycle)"
    )
    graph_json_str = graph.model_dump_json()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (document_id, graph_json_str, bool(graph.has_cycle)))
            logger.info("Successfully saved clause graph for document %d (has_cycle=%s)", document_id, graph.has_cycle)


def get_graph(document_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve stored clause dependency graph record for a document.

    Args:
        document_id: Document identifier.

    Returns:
        Dict of graph record with graph_json parsed or None if not found.
    """
    sql = (
        "SELECT id, document_id, graph_json, has_cycle, created_at "
        "FROM clause_graphs "
        "WHERE document_id = %s"
    )
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (document_id,))
            row = cursor.fetchone()
            if row:
                row_dict = dict(row)
                if isinstance(row_dict.get("graph_json"), str):
                    row_dict["graph_json"] = json.loads(row_dict["graph_json"])
                return row_dict
            return None


def add_audit(
    document_id: int,
    user_id: Optional[int],
    action: str,
    details: Optional[str] = None,
) -> int:
    """
    Record an immutable lifecycle event in the audit_log table.

    Args:
        document_id: ID of document.
        user_id: Optional ID of user performing the action.
        action: Audit action name ('UPLOADED', 'PARSED', 'GRAPH_BUILT', 'FAILED', etc.).
        details: Optional detailed description or error traceback.

    Returns:
        Auto-generated event_id (int).
    """
    sql = (
        "INSERT INTO audit_log (document_id, user_id, action, details) "
        "VALUES (%s, %s, %s, %s)"
    )
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (document_id, user_id, action, details))
            event_id = cursor.lastrowid
            logger.info("Recorded audit event %d (%s) for document %d", event_id, action, document_id)
            return int(event_id)


def list_audit(document_id: int) -> List[Dict[str, Any]]:
    """
    List all audit events for a document in ascending chronological order.

    Args:
        document_id: Document identifier.

    Returns:
        List of audit event dict rows.
    """
    sql = (
        "SELECT event_id, document_id, user_id, action, details, created_at "
        "FROM audit_log "
        "WHERE document_id = %s "
        "ORDER BY event_id ASC"
    )
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (document_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows] if rows else []
