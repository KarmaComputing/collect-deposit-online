import logging
from email.message import EmailMessage
import time
import os
from dotenv import load_dotenv

load_dotenv(verbose=True)
log = logging.getLogger(__name__)

EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_QUEUE_FOLDER = os.getenv("EMAIL_QUEUE_FOLDER")


class EmailMessageQueue(EmailMessage):
    def queue(self):
        fileName = time.time_ns()
        try:
            email_queue_folder = EMAIL_QUEUE_FOLDER
            with open(f"{email_queue_folder}/{fileName}", "wb") as f:
                f.write(self.as_bytes())
                log.debug(
                    f"Written email to queue folder {email_queue_folder}"
                )  # noqa: E501
        except Exception as e:
            log.error(
                f"Error when writing EmailMessageQueue folder: {email_queue_folder}. {e}"  # noqa
            )


def send_deposit_collected_email(to):
    try:
        msg = EmailMessageQueue()
        msg["Subject"] = "Deposit collected"
        msg["From"] = EMAIL_FROM
        msg["To"] = to
        msg.set_content("Deposit collected")
        msg["Reply-To"] = EMAIL_FROM
        msg.queue()
    except Exception as e:
        log.error(f"Failed to send deposit collected email. {e}")


def send_booking_rescheduled_email(to, content="Booking has been rescheduled"):
    try:
        msg = EmailMessageQueue()
        msg["Subject"] = "Booking rescheduled"
        msg["From"] = EMAIL_FROM
        msg["To"] = to
        msg.set_content(content)
        msg["Reply-To"] = EMAIL_FROM
        msg.queue()
    except Exception as e:
        log.error(f"Failed to send booking rescheduled email. {e}")


def send_booking_cancelled_email(to, content="Booking has been cancelled"):
    try:
        msg = EmailMessageQueue()
        msg["Subject"] = "Booking cancelled"
        msg["From"] = EMAIL_FROM
        msg["To"] = to
        msg.set_content(content)
        msg["Reply-To"] = EMAIL_FROM
        msg.queue()
    except Exception as e:
        log.error(f"Failed to send booking cancelled email. {e}")
