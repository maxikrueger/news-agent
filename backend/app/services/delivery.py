"""Delivery service for sending digests to Discord and Email"""

import json
import logging
from datetime import UTC, datetime

import requests

logger = logging.getLogger(__name__)


class DeliveryService:
    @staticmethod
    def deliver_via_discord(webhook_url: str, content: str, username: str = "News Agent") -> bool:
        """Send digest to Discord via webhook

        Discord has a 2000 character limit per message, so content is chunked intelligently.
        """
        if not webhook_url:
            logger.error("Discord webhook URL is empty")
            return False

        try:
            # Split content into chunks at line breaks
            chunks = []
            current_chunk = ""

            for line in content.split("\n"):
                # Leave 50 chars buffer for safety
                if len(current_chunk) + len(line) + 1 > 1950:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = line
                else:
                    current_chunk += "\n" + line if current_chunk else line

            if current_chunk:
                chunks.append(current_chunk)

            # Send each chunk
            for i, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue

                payload = {
                    "content": chunk,
                    "username": username,
                }

                response = requests.post(webhook_url, json=payload, timeout=10)

                if response.status_code == 204:
                    logger.info(f"Discord message {i+1}/{len(chunks)} sent successfully")
                elif response.status_code == 429:
                    logger.error(f"Discord rate limit hit: {response.text}")
                    return False
                elif response.status_code == 404:
                    logger.error("Discord webhook not found (invalid URL)")
                    return False
                else:
                    logger.error(f"Discord error {response.status_code}: {response.text}")
                    return False

            return True

        except requests.Timeout:
            logger.error("Discord webhook request timeout")
            return False
        except Exception as e:
            logger.error(f"Error sending to Discord: {e}")
            return False

    @staticmethod
    def deliver_file_via_discord(
        webhook_url: str,
        filename: str,
        data: bytes,
        content: str = "",
        username: str = "News Agent",
        max_bytes: int = 8 * 1024 * 1024,
    ) -> bool:
        """Upload a file (the audio digest) to Discord as a webhook attachment.

        Webhook uploads are capped by Discord; anything larger is rejected with a
        413, so the size is checked before the request rather than after.
        """
        if not webhook_url:
            logger.error("Discord webhook URL is empty")
            return False

        if not data:
            logger.error("Refusing to upload an empty file to Discord")
            return False

        if len(data) > max_bytes:
            logger.error(
                "Attachment is %d KB, above the %d KB webhook limit - skipping upload",
                len(data) // 1024,
                max_bytes // 1024,
            )
            return False

        try:
            response = requests.post(
                webhook_url,
                data={"payload_json": json.dumps({"content": content, "username": username})},
                files={"file": (filename, data, "audio/mpeg")},
                timeout=60,
            )
        except requests.Timeout:
            logger.error("Discord file upload timed out")
            return False
        except Exception as e:
            logger.error(f"Error uploading file to Discord: {e}")
            return False

        # 204 without ?wait=true, 200 when Discord echoes the created message
        if response.status_code in (200, 204):
            logger.info(f"Discord attachment {filename} ({len(data) // 1024} KB) sent successfully")
            return True

        logger.error(f"Discord file upload error {response.status_code}: {response.text}")
        return False

    @staticmethod
    def deliver_via_email(
        email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
        sendgrid_api_key: str | None = None,
    ) -> bool:
        """Send digest via email using SendGrid

        Requires SENDGRID_API_KEY (or the parameter) and SENDGRID_FROM_EMAIL, a sender
        address verified in the SendGrid account.
        """
        import os

        api_key = sendgrid_api_key or os.environ.get("SENDGRID_API_KEY")
        sender = os.environ.get("SENDGRID_FROM_EMAIL")

        if not api_key:
            logger.error("SendGrid API key not configured")
            return False

        if not sender:
            logger.error("SENDGRID_FROM_EMAIL not configured")
            return False

        if not email:
            logger.error("Email address is empty")
            return False

        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Email, Mail, To

            # Create email object
            from_email = Email(sender)
            to_email = To(email)

            mail = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                plain_text_content=text_content or html_content,
                html_content=html_content,
            )

            # Send via SendGrid
            sg = SendGridAPIClient(api_key)
            response = sg.send(mail)

            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent to {email} successfully")
                return True
            else:
                logger.error(f"SendGrid error {response.status_code}: {response.body}")
                return False

        except ImportError:
            logger.error("sendgrid package not installed")
            return False
        except Exception as e:
            logger.error(f"Error sending email to {email}: {e}")
            return False

    @staticmethod
    def format_digest_for_email(
        digest_content: str, user_email: str, schedule_name: str = "Daily Digest"
    ) -> tuple[str, str]:
        """Format digest content for email delivery

        Returns (html_content, text_content)
        """
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                        line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;
                           padding: 20px; border-radius: 8px; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header p {{ margin: 5px 0 0 0; font-size: 14px; opacity: 0.9; }}
                .content {{ margin: 20px 0; }}
                .article {{ border-left: 4px solid #667eea; padding-left: 15px; margin: 15px 0; }}
                .article h3 {{ margin: 0 0 5px 0; color: #667eea; }}
                .article p {{ margin: 5px 0; color: #666; }}
                .footer {{ border-top: 1px solid #eee; margin-top: 20px; padding-top: 20px;
                           font-size: 12px; color: #999; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{schedule_name}</h1>
                    <p>{today}</p>
                </div>
                <div class="content">
                    {digest_content}
                </div>
                <div class="footer">
                    <p>This is an automated digest from News Agent. <a href="#">Manage preferences</a></p>
                </div>
            </div>
        </body>
        </html>
        """

        return html_template, digest_content

    @staticmethod
    def validate_discord_webhook(webhook_url: str) -> bool:
        """Validate Discord webhook URL"""
        if not webhook_url or not webhook_url.startswith("https://discord.com/api/webhooks/"):
            return False

        try:
            # Try to post an empty message
            response = requests.post(webhook_url, json={"content": ""}, timeout=5)
            return response.status_code in [204, 400]  # 400 means webhook exists but empty content
        except Exception:
            return False

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address format"""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))
