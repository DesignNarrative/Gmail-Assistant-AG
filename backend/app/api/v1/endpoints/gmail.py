from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update, delete, text
import os
import httpx
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.security import decrypt_value
from app.models.user import User
from app.models.email import Email
from app.models.thread import Thread
from app.models.attachment import Attachment
from app.models.sync_log import SyncLog
from app.models.document_chunk import DocumentChunk
from app.models.chat_message import ChatMessage
from app.models.processed_document import ProcessedDocument
from app.workers.sync_tasks import run_sync_gmail_label
from pydantic import BaseModel, Field
import uuid
import logging
import io
import csv
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import zipfile
import re
import urllib.request
import urllib.parse

router = APIRouter()
logger = logging.getLogger(__name__)

class LabelSettingsUpdate(BaseModel):
    gmail_label: str = Field(..., min_length=1, max_length=100)

class DisconnectGmailRequest(BaseModel):
    delete_synced_data: bool = False

@router.post("/sync/trigger")
async def trigger_gmail_sync(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.google_access_token:
        raise HTTPException(
            status_code=400, 
            detail="Gmail sync is not configured. Please authorize Google OAuth first."
        )
        
    try:
        # Check if user already has an active sync loop running
        from app.workers.sync_tasks import _active_sync_users
        if str(current_user.id) in _active_sync_users:
            stmt = (
                select(SyncLog)
                .where(SyncLog.user_id == current_user.id, SyncLog.status == "running")
                .order_by(desc(SyncLog.started_at))
                .limit(1)
            )
            active_log = (await db.execute(stmt)).scalars().first()
            return {
                "detail": "Gmail sync is already actively in progress in the background.",
                "sync_job_id": active_log.id if active_log else None,
                "status": "running",
                "started_at": active_log.started_at if active_log else None
            }

        # Create a new sync log entry
        sync_log = SyncLog(
            user_id=current_user.id,
            sync_type="manual",
            status="running"
        )
        db.add(sync_log)
        await db.commit()
        await db.refresh(sync_log)
        
        # Trigger background task directly inside FastAPI's event loop
        background_tasks.add_task(run_sync_gmail_label, str(current_user.id), str(sync_log.id))
        
        return {
            "detail": "Gmail sync job successfully started in background.",
            "sync_job_id": sync_log.id,
            "status": sync_log.status,
            "started_at": sync_log.started_at
        }
    except Exception as e:
        logger.error(f"Failed to trigger sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule sync job")

@router.get("/sync/status")
async def get_sync_status(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = (
            select(SyncLog)
            .where(SyncLog.user_id == current_user.id)
            .order_by(desc(SyncLog.started_at))
            .limit(limit)
        )
        result = await db.execute(stmt)
        logs = result.scalars().all()
        return logs
    except Exception as e:
        logger.error(f"Error fetching sync status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sync logs")

@router.get("/sync/stats")
async def get_sync_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Total emails for this user
        emails_count_stmt = select(func.count(Email.id)).where(Email.user_id == current_user.id)
        total_emails = (await db.execute(emails_count_stmt)).scalar() or 0
        
        # Undownloaded emails count for this user
        undownloaded_stmt = select(func.count(Email.id)).where(
            Email.user_id == current_user.id,
            Email.is_downloaded == False
        )
        undownloaded_emails = (await db.execute(undownloaded_stmt)).scalar() or 0

        # Total distinct threads for this user
        threads_count_stmt = select(func.count(func.distinct(Email.thread_id))).where(Email.user_id == current_user.id)
        total_threads = (await db.execute(threads_count_stmt)).scalar() or 0
        
        # Total attachments belonging to this user's emails
        att_count_stmt = (
            select(func.count(Attachment.id))
            .join(Email, Email.id == Attachment.email_id)
            .where(Email.user_id == current_user.id)
        )
        total_attachments = (await db.execute(att_count_stmt)).scalar() or 0
        
        # Total attachment size belonging to this user's emails
        att_size_stmt = (
            select(func.sum(Attachment.file_size))
            .join(Email, Email.id == Attachment.email_id)
            .where(Email.user_id == current_user.id)
        )
        total_size_bytes = (await db.execute(att_size_stmt)).scalar() or 0
        
        # Fetch latest sync run for this user
        latest_sync_stmt = (
            select(SyncLog)
            .where(SyncLog.user_id == current_user.id)
            .order_by(desc(SyncLog.started_at))
            .limit(1)
        )
        latest_sync = (await db.execute(latest_sync_stmt)).scalars().first()
        
        return {
            "total_emails": total_emails,
            "undownloaded_emails": undownloaded_emails,
            "total_threads": total_threads,
            "total_attachments": total_attachments,
            "total_size_bytes": total_size_bytes,
            "latest_sync": latest_sync
        }
    except Exception as e:
        logger.error(f"Error fetching sync stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sync statistics")

@router.put("/settings/label")
async def update_gmail_label(
    payload: LabelSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Fixed permanently to InboxIQ for all users
        stmt = update(User).where(User.id == current_user.id).values(gmail_label="InboxIQ")
        await db.execute(stmt)
        await db.commit()
        return {"detail": "Gmail sync label is fixed to InboxIQ.", "gmail_label": "InboxIQ"}
    except Exception as e:
        logger.error(f"Error updating Gmail sync label: {e}")
        raise HTTPException(status_code=500, detail="Failed to update sync label settings")

@router.post("/disconnect")
async def disconnect_gmail(
    payload: DisconnectGmailRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # 1. Attempt non-blocking token revocation with Google OAuth
        if current_user.google_access_token:
            try:
                raw_token = decrypt_value(current_user.google_access_token)
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(
                        'https://oauth2.googleapis.com/revoke',
                        params={'token': raw_token},
                        headers={'Content-Type': 'application/x-www-form-urlencoded'}
                    )
                logger.info(f"Google OAuth token revoked for user {current_user.email}")
            except Exception as rev_err:
                logger.warning(f"Could not revoke token via Google API (may already be expired): {rev_err}")

        # 2. Clear tokens on user model
        current_user.google_access_token = None
        current_user.google_refresh_token = None
        current_user.google_id = None
        db.add(current_user)

        # 3. If requested, permanently delete all synced emails, attachments, document chunks, and chat history
        if payload.delete_synced_data:
            # Clean up local disk attachment files if present
            try:
                att_stmt = select(Attachment.storage_path).join(Email, Attachment.email_id == Email.id).where(Email.user_id == current_user.id)
                att_res = await db.execute(att_stmt)
                for storage_path in att_res.scalars().all():
                    if storage_path and os.path.exists(storage_path):
                        try:
                            os.remove(storage_path)
                        except Exception:
                            pass
            except Exception as file_cleanup_err:
                logger.warning(f"Error during attachment file cleanup: {file_cleanup_err}")

            # Delete database records in clean dependency order
            try:
                await db.execute(text("DELETE FROM conversations WHERE user_id = :uid"), {"uid": current_user.id})
            except Exception as conv_err:
                logger.warning(f"Note on conversations cleanup: {conv_err}")

            await db.execute(delete(ChatMessage).where(ChatMessage.user_id == current_user.id))
            await db.execute(delete(DocumentChunk).where(DocumentChunk.user_id == current_user.id))
            await db.execute(delete(SyncLog).where(SyncLog.user_id == current_user.id))
            await db.execute(delete(Email).where(Email.user_id == current_user.id))
            logger.info(f"Purged all synced emails and AI data for user {current_user.email}")

        await db.commit()
        await db.refresh(current_user)

        return {
            "detail": "Gmail account disconnected successfully.",
            "data_deleted": payload.delete_synced_data
        }
    except Exception as e:
        logger.error(f"Error disconnecting Gmail for user {current_user.email}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to disconnect Gmail account: {str(e)}")



def set_cell_background(cell, fill_hex: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def format_size(size_bytes: int) -> str:
    if not size_bytes or size_bytes <= 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}" if unit != 'B' else f"{int(size_bytes)} B"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def format_recipients(recipients_data) -> str:
    if not recipients_data:
        return "(None)"
    if isinstance(recipients_data, list):
        items = []
        for r in recipients_data:
            if isinstance(r, dict):
                name = r.get("name", "").strip()
                email_addr = r.get("email", "").strip()
                if name and email_addr:
                    items.append(f"{name} <{email_addr}>")
                elif email_addr:
                    items.append(email_addr)
            elif isinstance(r, str):
                items.append(r)
        return ", ".join(items) if items else "(None)"
    return str(recipients_data)

def clean_email_body_for_export(body_raw: str) -> list[str]:
    if not body_raw:
        return ["(No content)"]

    # 1. Strip extracted hyperlinks block added by sync client
    body = re.sub(r'🔗 \*\*Extracted Hyperlinks:\*\*[\s\S]*$', '', body_raw)
    
    # 2. Strip tracking image tags: ![](https://...) or [![Alt](img_url)](link_url)
    body = re.sub(r'\[!\[(.*?)\]\(.*?\)\]\(.*?\)', r'\1', body)
    body = re.sub(r'!\[.*?\]\(.*?\)', '', body)
    
    # 3. Clean zero-width and invisible unicode characters
    body = re.sub(r'[\u200b-\u200d\ufeff\u034f\u200e\u200f]', '', body)
    
    # 4. Remove markdown table separator lines like ---|--- or |---|---|
    body = re.sub(r'^[\|\s\-:]+$', '', body, flags=re.MULTILINE)
    body = re.sub(r'\|\s*---\s*\|', '', body)
    
    # 5. Clean standalone horizontal rules * * * or --- or ___
    body = re.sub(r'^[ \t]*(\*|\-|_)[ \t]*(\*|\-|_)[ \t]*(\*|\-|_)[ \t\*\-_]*$', '', body, flags=re.MULTILINE)
    
    # 6. Simplify markdown links [Text](URL) -> Text
    def link_repl(match):
        text = match.group(1).strip()
        url = match.group(2).strip()
        if not text or text == url:
            return url
        return text
    body = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link_repl, body)
    
    # 7. Clean excessive newlines and leading pipe chars from markdown tables
    clean_lines = []
    prev_empty = False
    for line in body.split("\n"):
        line = line.strip()
        # Remove table pipe artifacts
        if line.startswith("|") and line.endswith("|"):
            line = line.strip("|").strip()
        elif line == "|":
            continue
            
        # Remove leading markdown headers syntax #, ##, ###
        line = re.sub(r'^#{1,6}\s*', '', line)
        
        # Remove markdown bold/italic asterisks around whole line
        line = re.sub(r'^\*\*(.*?)\*\*$', r'\1', line)
        
        if not line:
            if not prev_empty:
                clean_lines.append("")
                prev_empty = True
        else:
            clean_lines.append(line)
            prev_empty = False
            
    # Trim leading/trailing blank lines
    while clean_lines and not clean_lines[0]:
        clean_lines.pop(0)
    while clean_lines and not clean_lines[-1]:
        clean_lines.pop()
        
    return clean_lines if clean_lines else ["(No content)"]

def generate_email_docx(email_data: dict, attachments_data: list) -> bytes:
    doc = docx.Document()
    
    # Page Margins: 0.8 inch
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Header branding
    p_brand = doc.add_paragraph()
    r_brand = p_brand.add_run("📧 INBOXIQ — EXECUTIVE EMAIL BRIEFING")
    r_brand.font.name = "Calibri"
    r_brand.font.size = Pt(9)
    r_brand.font.bold = True
    r_brand.font.color.rgb = RGBColor(37, 99, 235)  # Blue-600
    p_brand.paragraph_format.space_after = Pt(2)

    # Subject Heading
    p_subj = doc.add_paragraph()
    r_subj = p_subj.add_run(email_data.get("subject") or "(No Subject)")
    r_subj.font.name = "Calibri"
    r_subj.font.size = Pt(16)
    r_subj.font.bold = True
    r_subj.font.color.rgb = RGBColor(15, 23, 42)  # Slate-900
    p_subj.paragraph_format.space_after = Pt(8)

    # Metadata Table Card
    meta_rows = [
        ("From:", f"{email_data.get('sender_name') or ''} <{email_data.get('sender_email', '')}>".strip()),
        ("Date:", email_data.get("date_formatted", "(No Date)")),
        ("To / Recipients:", email_data.get("recipients_formatted", "(None)")),
        ("Gmail Thread:", f"Thread ID: {email_data.get('thread_id', 'N/A')}  |  Label: {email_data.get('label', 'InboxIQ')}")
    ]
    
    table = doc.add_table(rows=len(meta_rows), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    for idx, (label, val) in enumerate(meta_rows):
        row = table.rows[idx]
        
        # Label cell
        cell_lbl = row.cells[0]
        cell_lbl.width = Inches(1.5)
        set_cell_background(cell_lbl, "F1F5F9")  # Slate-100
        p_lbl = cell_lbl.paragraphs[0]
        p_lbl.paragraph_format.space_before = Pt(2.5)
        p_lbl.paragraph_format.space_after = Pt(2.5)
        r_lbl = p_lbl.add_run(label)
        r_lbl.font.name = "Calibri"
        r_lbl.font.bold = True
        r_lbl.font.size = Pt(9)
        r_lbl.font.color.rgb = RGBColor(71, 85, 105)  # Slate-600
        
        # Value cell
        cell_val = row.cells[1]
        cell_val.width = Inches(5.3)
        set_cell_background(cell_val, "F8FAFC")  # Slate-50
        p_val = cell_val.paragraphs[0]
        p_val.paragraph_format.space_before = Pt(2.5)
        p_val.paragraph_format.space_after = Pt(2.5)
        r_val = p_val.add_run(val)
        r_val.font.name = "Calibri"
        r_val.font.size = Pt(9)
        r_val.font.color.rgb = RGBColor(15, 23, 42)

    # Spacing
    p_space = doc.add_paragraph()
    p_space.paragraph_format.space_before = Pt(6)
    p_space.paragraph_format.space_after = Pt(4)

    # Email Body Content Heading
    h_body = doc.add_heading("Email Content", level=2)
    h_body.paragraph_format.space_before = Pt(8)
    h_body.paragraph_format.space_after = Pt(6)
    for run in h_body.runs:
        run.font.name = "Calibri"
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = RGBColor(30, 58, 138)

    # Email Body Lines
    body_lines = clean_email_body_for_export(email_data.get("body_text", ""))
    for line in body_lines:
        p_line = doc.add_paragraph()
        p_line.paragraph_format.line_spacing = 1.15
        p_line.paragraph_format.space_after = Pt(3.5)
        if line:
            r_line = p_line.add_run(line)
            r_line.font.name = "Calibri"
            r_line.font.size = Pt(10)
            r_line.font.color.rgb = RGBColor(51, 65, 85)

    # Attachments Section (if any)
    if attachments_data:
        doc.add_paragraph()
        h_att = doc.add_heading(f"📎 Attached Files ({len(attachments_data)})", level=2)
        h_att.paragraph_format.space_before = Pt(14)
        h_att.paragraph_format.space_after = Pt(6)
        for run in h_att.runs:
            run.font.name = "Calibri"
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = RGBColor(30, 58, 138)

        # Attachment Metadata Table
        att_table = doc.add_table(rows=len(attachments_data) + 1, cols=4)
        att_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        att_headers = ["File Name", "Type", "Size", "OCR / Text Status"]
        col_widths = [Inches(2.8), Inches(1.5), Inches(1.0), Inches(1.5)]
        
        # Header row
        for i, h in enumerate(att_headers):
            cell = att_table.rows[0].cells[i]
            cell.width = col_widths[i]
            set_cell_background(cell, "E2E8F0")  # Slate-200
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)
            r = p.add_run(h)
            r.font.name = "Calibri"
            r.font.bold = True
            r.font.size = Pt(8.5)
            r.font.color.rgb = RGBColor(30, 41, 59)

        # Data rows
        for idx, att in enumerate(attachments_data):
            row = att_table.rows[idx + 1]
            status_text = "Extracted" if att.get("extracted_text") else ("Skipped" if att.get("is_processed") else "Pending")
            row_data = [
                att.get("filename", "Unknown"),
                att.get("mime_type", "application/octet-stream"),
                format_size(att.get("file_size", 0)),
                status_text
            ]
            for i, val in enumerate(row_data):
                cell = row.cells[i]
                cell.width = col_widths[i]
                set_cell_background(cell, "F8FAFC" if idx % 2 == 0 else "FFFFFF")
                p = cell.paragraphs[0]
                p.paragraph_format.space_before = Pt(2.5)
                p.paragraph_format.space_after = Pt(2.5)
                r = p.add_run(val)
                r.font.name = "Calibri"
                r.font.size = Pt(8.5)
                r.font.color.rgb = RGBColor(51, 65, 85)

        # Extracted Text Callout for each attachment that has text
        for att in attachments_data:
            ext_text = att.get("extracted_text")
            if ext_text and ext_text.strip():
                doc.add_paragraph()
                p_callout_hdr = doc.add_paragraph()
                p_callout_hdr.paragraph_format.space_before = Pt(8)
                p_callout_hdr.paragraph_format.space_after = Pt(2)
                r_callout_hdr = p_callout_hdr.add_run(f"📄 Extracted Text Content: {att.get('filename')}")
                r_callout_hdr.font.name = "Calibri"
                r_callout_hdr.font.bold = True
                r_callout_hdr.font.size = Pt(9.5)
                r_callout_hdr.font.color.rgb = RGBColor(30, 58, 138)

                # Indented text box
                snippet = ext_text[:3000].strip()
                p_ext = doc.add_paragraph()
                p_ext.paragraph_format.left_indent = Inches(0.2)
                p_ext.paragraph_format.space_after = Pt(4)
                r_ext = p_ext.add_run(snippet)
                r_ext.font.name = "Calibri"
                r_ext.font.size = Pt(9)
                r_ext.font.color.rgb = RGBColor(71, 85, 105)
                if len(ext_text) > 3000:
                    r_trunc = p_ext.add_run("\n... [Preview truncated. Full text available in attached file.]")
                    r_trunc.font.italic = True
                    r_trunc.font.size = Pt(8.5)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@router.get("/export")
async def export_synced_emails(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        from fastapi import Response
        # 1. Fetch up to 50 undownloaded emails for the user first (batch processing)
        stmt = select(Email).where(
            Email.user_id == current_user.id,
            Email.is_downloaded == False
        ).order_by(desc(Email.date_sent)).limit(50)
        result = await db.execute(stmt)
        emails = result.scalars().all()

        is_reexport = False
        # 2. If all emails are already downloaded, fall back to exporting up to 50 latest synced emails
        # so the user can re-export on demand at any time without getting blocked
        if not emails:
            stmt_all = select(Email).where(
                Email.user_id == current_user.id
            ).order_by(desc(Email.date_sent)).limit(50)
            result_all = await db.execute(stmt_all)
            emails = result_all.scalars().all()
            is_reexport = True

        if not emails:
            # Return 204 No Content only if user has no synced emails at all
            return Response(status_code=204)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for idx, e in enumerate(emails):
                # Query attachments for this email
                att_stmt = select(Attachment).where(Attachment.email_id == e.id)
                att_res = await db.execute(att_stmt)
                attachments = att_res.scalars().all()

                attachments_data = []
                for att in attachments:
                    doc_stmt = select(ProcessedDocument).where(ProcessedDocument.attachment_id == att.id)
                    doc_res = await db.execute(doc_stmt)
                    proc_doc = doc_res.scalars().first()

                    attachments_data.append({
                        "filename": att.filename,
                        "mime_type": att.mime_type,
                        "file_size": att.file_size,
                        "storage_path": att.storage_path,
                        "is_processed": att.is_processed,
                        "extracted_text": proc_doc.extracted_text if proc_doc else None
                    })

                # Format dates
                if e.date_sent:
                    date_formatted = e.date_sent.strftime("%B %d, %Y at %I:%M %p")
                elif e.date_received:
                    date_formatted = e.date_received.strftime("%B %d, %Y at %I:%M %p")
                else:
                    date_formatted = "(Date Unknown)"

                email_dict = {
                    "subject": e.subject or "(No Subject)",
                    "sender_name": e.sender_name or "",
                    "sender_email": e.sender_email or "",
                    "date_formatted": date_formatted,
                    "recipients_formatted": format_recipients(e.recipients),
                    "thread_id": e.thread_id or "N/A",
                    "label": ", ".join(e.labels) if e.labels else "InboxIQ",
                    "body_text": e.body_text or e.snippet or "(No body content)"
                }

                # Generate high-quality docx
                docx_bytes = generate_email_docx(email_dict, attachments_data)

                # Derive safe file / folder name
                safe_subject = re.sub(r'[^\w\s-]', '', e.subject or "No_Subject")
                safe_subject = re.sub(r'[-\s]+', '_', safe_subject).strip('_')[:45]
                if not safe_subject:
                    safe_subject = f"email_{idx+1}"

                # If email has attachments, organize into dedicated folder with original files
                if attachments_data:
                    folder_name = f"{idx+1:02d}_{safe_subject}"
                    zip_file.writestr(f"{folder_name}/Email_Summary.docx", docx_bytes)
                    used_filenames = set()
                    for att in attachments_data:
                        sp = att.get("storage_path")
                        if sp and os.path.exists(sp):
                            orig_name = att.get("filename") or "attachment"
                            fname = orig_name
                            counter = 1
                            base_n, ext_n = os.path.splitext(orig_name)
                            while fname in used_filenames:
                                counter += 1
                                fname = f"{base_n}_{counter}{ext_n}"
                            used_filenames.add(fname)
                            try:
                                with open(sp, "rb") as f:
                                    zip_file.writestr(f"{folder_name}/Attachments/{fname}", f.read())
                            except Exception as file_read_err:
                                logger.warning(f"Could not add physical attachment {sp} to zip: {file_read_err}")
                else:
                    # Clean single docx file in root
                    zip_file.writestr(f"{idx+1:02d}_{safe_subject}.docx", docx_bytes)

                # Mark as downloaded in DB if not already
                e.is_downloaded = True

        await db.commit()

        # Check how many undownloaded emails remain after this batch
        rem_stmt = select(func.count(Email.id)).where(
            Email.user_id == current_user.id,
            Email.is_downloaded == False
        )
        remaining_undownloaded = (await db.execute(rem_stmt)).scalar() or 0

        zip_buffer.seek(0)
        batch_count = len(emails)
        filename = f"emails_export_batch_{batch_count}.zip"

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Remaining-Undownloaded": str(remaining_undownloaded),
                "Access-Control-Expose-Headers": "X-Remaining-Undownloaded"
            }
        )
    except Exception as e:
        logger.error(f"Error exporting synced emails to zip: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to export synced emails: {str(e)}")


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        att_uuid = uuid.UUID(attachment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid attachment ID format")

    try:
        # Join Email to verify the attachment belongs to an email owned by current_user.id
        stmt = (
            select(Attachment, Email)
            .join(Email, Email.id == Attachment.email_id)
            .where(Attachment.id == att_uuid, Email.user_id == current_user.id)
        )
        row = (await db.execute(stmt)).first()

        if not row:
            raise HTTPException(status_code=404, detail="Attachment not found or access denied")

        attachment, email = row

        import os
        if not os.path.exists(attachment.storage_path):
            raise HTTPException(status_code=404, detail="Attachment file not found on disk")

        return FileResponse(
            path=attachment.storage_path,
            filename=attachment.filename,
            media_type=attachment.mime_type
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error downloading attachment {attachment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download attachment")

