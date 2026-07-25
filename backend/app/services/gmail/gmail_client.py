from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from app.core.config import get_settings
from app.core.security import decrypt_value, encrypt_value
from app.models.user import User
from app.models.email import Email
from app.models.thread import Thread
from app.models.attachment import Attachment
from app.models.sync_log import SyncLog
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
import os
import base64
import email
from datetime import datetime, timezone
import hashlib
import uuid
import logging
import html2text
import re

settings = get_settings()
logger = logging.getLogger(__name__)

class GmailSyncService:
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.creds = None
        self.service = None

    async def get_credentials(self) -> Credentials:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise ValueError("Google OAuth Client ID or Secret is not configured in server environment.")

        if not self.user.google_access_token:
            raise ValueError("Gmail account not connected. Please authenticate via OAuth.")

        access_token = decrypt_value(self.user.google_access_token)
        refresh_token = decrypt_value(self.user.google_refresh_token) if self.user.google_refresh_token else None

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )

        # Refresh access token if expired
        if creds.expired or not creds.valid:
            if not refresh_token:
                raise ValueError("Credentials expired and refresh token is missing. Please re-authenticate.")
            logger.info(f"Refreshing Google access token for user {self.user.id}")
            creds.refresh(Request())
            
            # Save new access token
            enc_access_token = encrypt_value(creds.token)
            stmt = update(User).where(User.id == self.user.id).values(google_access_token=enc_access_token)
            await self.db.execute(stmt)
            await self.db.commit()
            
            # Refresh self.user context
            await self.db.refresh(self.user)

        self.creds = creds
        self.service = build('gmail', 'v1', credentials=creds)
        return creds

    def _parse_headers(self, headers_list: list) -> dict:
        headers = {}
        for h in headers_list:
            headers[h['name'].lower()] = h['value']
        return headers

    def _get_body(self, payload: dict) -> tuple[str, str]:
        body_text = ""
        body_html = ""

        if 'parts' in payload:
            for part in payload['parts']:
                t, h = self._get_body(part)
                body_text += t
                body_html += h
        else:
            mime_type = payload.get('mimeType', '')
            data = payload.get('body', {}).get('data', '')
            if data:
                decoded = base64.urlsafe_b64decode(data.encode('utf-8')).decode('utf-8', errors='ignore')
                if mime_type == 'text/plain':
                    body_text = decoded
                elif mime_type == 'text/html':
                    body_html = decoded
        return body_text, body_html

    def _get_attachments_meta(self, payload: dict) -> list[dict]:
        attachments = []
        if 'parts' in payload:
            for part in payload['parts']:
                attachments.extend(self._get_attachments_meta(part))
        else:
            filename = payload.get('filename')
            body = payload.get('body', {})
            attachment_id = body.get('attachmentId')
            if filename and attachment_id:
                attachments.append({
                    "filename": filename,
                    "attachment_id": attachment_id,
                    "mime_type": payload.get('mimeType', 'application/octet-stream'),
                    "file_size": body.get('size', 0)
                })
        return attachments

    def _extract_links(self, html_content: str) -> list[str]:
        if not html_content:
            return []
        # Find all absolute URLs in href attributes
        links = re.findall(r'href=[\'"]?(https?://[^\'" >]+)', html_content)
        return list(set(links))

    async def sync_emails(self, sync_log: SyncLog) -> tuple[int, int]:
        await self.get_credentials()
        
        # Determine Gmail label to sync (user custom choice or system default env)
        label_name = getattr(self.user, 'gmail_label', None) or settings.GMAIL_LABEL or "Director's AI Assistant"
        query = f'label:"{label_name}"'
        logger.info(f"Querying Gmail messages for user {self.user.email} with label query: {query}")
        
        emails_count = 0
        attachments_count = 0
        
        try:
            # Fetch all messages using pagination
            messages = []
            page_token = None
            
            while True:
                results = self.service.users().messages().list(
                    userId='me', q=query, pageToken=page_token
                ).execute()
                
                messages.extend(results.get('messages', []))
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Total messages found in label '{label_name}' for {self.user.email}: {len(messages)}")
            os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

            for msg_meta in messages:
                msg_id = msg_meta['id']
                
                # Check if message already exists FOR THIS USER
                stmt = select(Email).where(Email.message_id == msg_id, Email.user_id == self.user.id)
                existing = (await self.db.execute(stmt)).scalars().first()
                if existing:
                    continue

                # Fetch full message payload
                msg = self.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
                payload = msg.get('payload', {})
                headers = self._parse_headers(payload.get('headers', []))
                
                subject = headers.get('subject', '(No Subject)')
                sender = headers.get('from', '')
                sender_name, sender_email = email.utils.parseaddr(sender)
                
                # Recipients parsing
                to_header = headers.get('to', '')
                recipients = [{"name": n, "email": e} for n, e in [email.utils.parseaddr(x) for x in to_header.split(',')]] if to_header else []
                cc_header = headers.get('cc', '')
                cc = [{"name": n, "email": e} for n, e in [email.utils.parseaddr(x) for x in cc_header.split(',')]] if cc_header else []
                bcc_header = headers.get('bcc', '')
                bcc = [{"name": n, "email": e} for n, e in [email.utils.parseaddr(x) for x in bcc_header.split(',')]] if bcc_header else []
                
                # Parsing dates
                date_str = headers.get('date')
                date_parsed = datetime.now(timezone.utc).replace(tzinfo=None)
                if date_str:
                    try:
                        date_parsed = email.utils.parsedate_to_datetime(date_str).replace(tzinfo=None)
                    except Exception:
                        pass
                
                body_text_raw, body_html = self._get_body(payload)
                attachments_meta = self._get_attachments_meta(payload)
                
                # Convert html to clean markdown text if html exists
                if body_html:
                    h2t = html2text.HTML2Text()
                    h2t.ignore_links = False
                    h2t.ignore_images = False
                    h2t.body_width = 0
                    cleaned_html_text = h2t.handle(body_html)
                    # Merge text bodies cleanly
                    body_text = cleaned_html_text.strip() if cleaned_html_text.strip() else body_text_raw
                else:
                    body_text = body_text_raw

                # Extract and format external links in the email body
                extracted_links = self._extract_links(body_html)
                if extracted_links:
                    links_summary = "\n\n🔗 **Extracted Hyperlinks:**\n" + "\n".join([f"- {link}" for link in extracted_links])
                    body_text += links_summary
                
                # Save Thread record
                thread_id = msg.get('threadId')
                stmt = select(Thread).where(Thread.thread_id == thread_id)
                thread = (await self.db.execute(stmt)).scalars().first()
                
                if thread:
                    thread.message_count += 1
                    if date_parsed > thread.last_message_at:
                        thread.last_message_at = date_parsed
                else:
                    thread = Thread(
                        thread_id=thread_id,
                        subject=subject,
                        message_count=1,
                        last_message_at=date_parsed
                    )
                    self.db.add(thread)
                
                # Save Email record with user_id mapping
                email_record = Email(
                    user_id=self.user.id,
                    message_id=msg_id,
                    thread_id=thread_id,
                    subject=subject,
                    body_text=body_text,
                    body_html=body_html,
                    sender_email=sender_email,
                    sender_name=sender_name,
                    recipients=recipients,
                    cc=cc,
                    bcc=bcc,
                    date_sent=date_parsed,
                    date_received=datetime.now(timezone.utc).replace(tzinfo=None),
                    labels=msg.get('labelIds', []),
                    snippet=msg.get('snippet', ''),
                    has_attachments=len(attachments_meta) > 0,
                    sync_status="completed"
                )
                self.db.add(email_record)
                await self.db.flush() # Yields email_record.id for foreign keys

                # NOTE: Email vector embeddings are generated after the sync completes,
                # directly in run_sync_gmail_label (see sync_tasks.py). We intentionally do
                # NOT enqueue a Celery task here: single-process mode runs no Celery worker,
                # so a .delay() call would only pile unconsumed tasks into Redis.

                # Process Attachments
                for att in attachments_meta:
                    size_mb = att['file_size'] / (1024 * 1024)
                    if size_mb > settings.MAX_ATTACHMENT_SIZE_MB:
                        logger.warning(f"Skipped attachment {att['filename']} - size {size_mb:.2f}MB exceeds limit of {settings.MAX_ATTACHMENT_SIZE_MB}MB")
                        continue
                        
                    try:
                        logger.info(f"Downloading attachment {att['filename']} ({size_mb:.2f} MB)")
                        raw_att = self.service.users().messages().attachments().get(
                            userId='me', messageId=msg_id, id=att['attachment_id']
                        ).execute()
                        
                        file_data = base64.urlsafe_b64decode(raw_att.get('data', '').encode('utf-8'))
                        content_hash = hashlib.sha256(file_data).hexdigest()
                        
                        file_ext = os.path.splitext(att['filename'])[1]
                        uuid_name = f"{uuid.uuid4()}{file_ext}"
                        storage_path = os.path.join(settings.UPLOAD_DIR, uuid_name)
                        
                        with open(storage_path, 'wb') as f:
                            f.write(file_data)
                            
                        att_record = Attachment(
                            email_id=email_record.id,
                            filename=att['filename'],
                            mime_type=att['mime_type'],
                            file_size=att['file_size'],
                            storage_path=storage_path,
                            content_hash=content_hash
                        )
                        self.db.add(att_record)
                        attachments_count += 1
                    except Exception as e:
                        logger.error(f"Failed to download attachment {att['filename']}: {e}")
                        
                emails_count += 1
                await self.db.commit()

        except Exception as e:
            logger.error(f"Gmail synchronization failed: {e}")
            raise e
            
        return emails_count, attachments_count
