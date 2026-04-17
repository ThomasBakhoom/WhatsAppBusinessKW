"""CSV import tasks for contacts."""

import asyncio
import csv
import io

import structlog
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()

COLUMN_MAP = {
    "phone": ["phone", "phone_number", "mobile", "whatsapp"],
    "email": ["email", "email_address"],
    "first_name": ["first_name", "firstname", "first", "name"],
    "last_name": ["last_name", "lastname", "last", "surname"],
    "notes": ["notes", "note", "comment"],
}


def _match_column(header: str) -> str | None:
    normalized = header.strip().lower().replace(" ", "_")
    for field, aliases in COLUMN_MAP.items():
        if normalized in aliases:
            return field
    return None


@celery_app.task(
    name="app.tasks.import_tasks.process_csv_import",
    bind=True,
    queue="imports",
    max_retries=0,
)
def process_csv_import(self, csv_data: str, company_id: str, user_id: str):
    """Process a CSV import."""
    return asyncio.run(_async_import(csv_data, company_id, user_id))


async def _async_import(csv_data: str, company_id: str, user_id: str) -> dict:
    from uuid import UUID
    from sqlalchemy import select
    from app.core.database import tenant_session
    from app.models.contact import Contact

    reader = csv.DictReader(io.StringIO(csv_data))

    if not reader.fieldnames:
        return {"total": 0, "created": 0, "updated": 0, "errors": 0, "error_details": []}

    col_mapping = {}
    for header in reader.fieldnames:
        field = _match_column(header)
        if field:
            col_mapping[header] = field

    if "phone" not in col_mapping.values():
        return {"total": 0, "created": 0, "updated": 0, "errors": 1,
                "error_details": [{"row": 0, "error": "No phone column found"}]}

    field_to_header = {v: k for k, v in col_mapping.items()}
    company_uuid = UUID(company_id)
    total = created = updated = errors = 0
    error_details: list[dict] = []

    # Buffer rows so we can chunk per transaction (the SET LOCAL GUC only
    # lasts for the current transaction, so each chunk reopens it).
    chunk_size = 500
    rows = list(reader)
    total_rows = len(rows)

    for chunk_start in range(0, total_rows, chunk_size):
        chunk = rows[chunk_start:chunk_start + chunk_size]
        async with tenant_session(company_uuid) as db:
            for offset, row in enumerate(chunk):
                row_num = chunk_start + offset + 2  # +2: header + 1-indexed
                total += 1
                try:
                    phone = row.get(field_to_header.get("phone", ""), "").strip()
                    if not phone:
                        errors += 1
                        error_details.append({"row": row_num, "error": "Empty phone"})
                        continue

                    existing = await db.execute(
                        select(Contact).where(
                            Contact.phone == phone,
                            Contact.deleted_at.is_(None),
                        )
                    )
                    contact = existing.scalar_one_or_none()

                    if contact:
                        for field in ["email", "first_name", "last_name", "notes"]:
                            header = field_to_header.get(field)
                            if header and row.get(header, "").strip():
                                setattr(contact, field, row[header].strip())
                        updated += 1
                    else:
                        contact = Contact(
                            company_id=company_uuid, phone=phone,
                            email=row.get(field_to_header.get("email", ""), "").strip() or None,
                            first_name=row.get(field_to_header.get("first_name", ""), "").strip(),
                            last_name=row.get(field_to_header.get("last_name", ""), "").strip(),
                            notes=row.get(field_to_header.get("notes", ""), "").strip() or None,
                            source="import",
                        )
                        db.add(contact)
                        created += 1
                except Exception as e:
                    errors += 1
                    error_details.append({"row": row_num, "error": str(e)})

    logger.info("csv_import_complete", total=total, created=created, updated=updated, errors=errors)
    return {"total": total, "created": created, "updated": updated, "errors": errors,
            "error_details": error_details[:50]}
