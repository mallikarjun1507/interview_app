import re
import uuid
from sqlalchemy.orm import joinedload
from email_validator import validate_email, EmailNotValidError
from dotenv import load_dotenv
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
load_dotenv()

from models import SessionLocal, Question, Application, InterviewSlot, Interview, Answer, User
from pypdf import PdfReader
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logger_config import get_logger

logger = get_logger(__name__)


# -------------------- Utility Functions -------------------- #

def max_total_for_job(job):
    return sum(q.weight for q in job.questions)


def extract_text_from_pdf(uploaded_file):
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
        return text
    except Exception:
        return ""


def extract_email_from_resume(resume_text: str) -> str:
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, resume_text)

    for email in emails:
        try:
            validate_email(email)
            return email.lower()
        except EmailNotValidError:
            continue
    return None


# -------------------- Email Function -------------------- #
def send_real_email(to_email: str, subject: str, message: str):

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL", smtp_email)

    logger.info(f"Preparing to send email to {to_email}")
    logger.info(f"SMTP host={smtp_host} port={smtp_port}")

    if not smtp_email or not smtp_password:
        logger.error("SMTP credentials missing")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        logger.info("Connecting to SMTP server...")

        server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
        server.ehlo()

        if smtp_port == 587:
            server.starttls()
            server.ehlo()

        logger.info("Logging into SMTP server")

        server.login(smtp_email, smtp_password)

        server.send_message(msg)

        server.quit()

        logger.info(f"Email sent successfully to {to_email}")

        return True

    except socket.gaierror as e:
        logger.error(f"DNS error connecting to SMTP server: {e}")

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")

    except smtplib.SMTPException as e:
        logger.error(f"SMTP error occurred: {e}")

    except Exception as e:
        logger.error(f"Email sending failed for {to_email}: {e}")

    return False
# -------------------- Resume Scoring -------------------- #

def score_resume(text: str, required_keywords: list[str]) -> float:
    if not text:
        return 0.0

    text_low = text.lower()
    score = 0.0

    for kw in required_keywords:
        if kw.lower() in text_low:
            score += 1.0

    return score


def run_resume_screening(application_id: int, resume_text: str):
    db = SessionLocal()
    app = db.query(Application).get(application_id)

    if not app:
        db.close()
        return None

    required = []
    if app.job and app.job.skills_required:
        required = [s.strip() for s in app.job.skills_required.split(",") if s.strip()]

    rs = score_resume(resume_text, required)
    app.resume_score = rs

    needed = max(1, len(required) // 2) if required else 1

    if rs >= needed:
        app.status = "TEST_PENDING"
    else:
        app.status = "RESUME_REJECTED"

    db.commit()
    db.refresh(app)
    db.close()

    return app


# -------------------- Test Evaluation -------------------- #

def evaluate_screening(application_id: int):
    db = SessionLocal()

    app = (
        db.query(Application)
        .options(joinedload(Application.answers).joinedload(Answer.question))
        .get(application_id)
    )

    if not app:
        db.close()
        return None

    total = 0.0

    for ans in app.answers:
        q = ans.question

        if q.question_type == "MCQ" and ans.selected_option == q.correct_option:
            ans.score = q.weight
        else:
            ans.score = 0.0

        total += ans.score

    app.total_score = total
    max_total = max_total_for_job(app.job)
    threshold = 0.6 * max_total if max_total > 0 else 0.0

    if total >= threshold:
        app.status = "TEST_PASSED"
        notify_test_passed(app.id)
    else:
        app.status = "TEST_FAILED"

    db.commit()
    db.refresh(app)
    db.close()

    return app


# -------------------- Notifications -------------------- #
smtp_email = os.getenv('SMTP_EMAIL')
smtp_password = os.getenv('SMTP_PASSWORD')
def notify_test_passed(application_id: int):

    db = SessionLocal()

    logger.info("===== notify_test_passed START =====")
    logger.info(f"Application ID: {application_id}")

    app = db.query(Application).get(application_id)

    if not app:
        logger.error("Application not found")
        db.close()
        return

    logger.info(f"Application Status: {app.status}")

    if app.status == "TEST_PASSED":

        candidate = db.query(User).get(app.candidate_id)

        to_email = candidate.resume_email or candidate.email

        logger.info(f"Candidate Name: {candidate.name}")
        logger.info(f"Candidate Email: {to_email}")

        logger.debug(f"SMTP EMAIL configured: {bool(os.getenv('SMTP_EMAIL'))}")

        subject = f"🎉 Test Passed! {app.job.title}"

        message = (
            f"Dear {candidate.name},\n\n"
            f"You PASSED the screening test!\n"
            f"Score: {app.total_score:.1f}\n\n"
            f"Job: {app.job.title}\n"
            f"Application ID: {app.id}\n\n"
            f"Interview will be scheduled soon.\n\n"
            f"HR Team"
        )

        logger.info("Sending test passed email")

        send_real_email(to_email, subject, message)

    logger.info("===== notify_test_passed END =====")

    db.close()

# -------------------- UPDATED AUTO SCHEDULE (WebRTC) -------------------- #

def auto_schedule_interviews(job_id: int, round_type: str = "TECH1"):

    logger.info(f"Starting auto_schedule_interviews for job_id={job_id}")

    db = SessionLocal()

    apps = (
        db.query(Application)
        .filter(Application.job_id == job_id, Application.status == "TEST_PASSED")
        .order_by(Application.total_score.desc())
        .all()
    )

    slots = (
        db.query(InterviewSlot)
        .filter(
            InterviewSlot.job_id == job_id,
            InterviewSlot.is_booked == False
        )
        .order_by(InterviewSlot.start_time.asc())
        .all()
    )

    # ✅ ADD LOGGER HERE
    logger.info(f"Slots fetched: {len(slots)}")

    for s in slots:
        logger.info(
            f"Slot ID={s.id} job_id={s.job_id} start={s.start_time} booked={s.is_booked}"
        )

    logger.info(f"Passed Applications: {len(apps)}")

    BASE_URL = os.getenv("APP_URL", "https://interview-app-2-z4rm.onrender.com")

    for app, slot in zip(apps, slots):

        room_id = str(uuid.uuid4())[:8]
        room_link = f"{BASE_URL}/?room={room_id}"

        logger.info(f"Creating interview for application_id={app.id}")
        logger.info(f"Generated room link: {room_link}")

        interview = Interview(
            application_id=app.id,
            slot_id=slot.id,
            round_type=round_type,
            meet_link=room_link,
        )

        slot.is_booked = True
        app.status = "SCHEDULED"

        db.add(interview)

        db.commit()
        db.refresh(interview)

        logger.info(f"Interview created successfully with ID={interview.id}")

        notify_interview_scheduled(interview.id)

    db.close()

    logger.info("auto_schedule_interviews completed")

# -------------------- INTERVIEW EMAIL -------------------- #

def notify_interview_scheduled(interview_id: int):

    logger.info(f"notify_interview_scheduled START for interview_id={interview_id}")

    db = SessionLocal()

    interview = db.query(Interview).get(interview_id)

    if not interview:
        logger.error("Interview not found")
        db.close()
        return

    candidate = db.query(User).get(interview.application.candidate_id)
    interviewer = db.query(User).get(interview.slot.interviewer_id)

    logger.info(f"Candidate: {candidate.name}")
    logger.info(f"Interviewer: {interviewer.name}")

    to_email = candidate.resume_email or candidate.email

    subject = f"Interview Scheduled: {interview.application.job.title}"

    message = f"""
Dear {candidate.name},

Your interview has been scheduled.

Date & Time: {interview.slot.start_time}
Interviewer: {interviewer.name}

Join Link:
{interview.meet_link}

Best regards,
HR Team
"""

    # Candidate Email
    logger.info(f"Sending email to candidate: {to_email}")

    try:
        send_real_email(to_email, subject, message)
        logger.info("Candidate email sent successfully")
    except Exception as e:
        logger.error(f"Candidate email failed: {e}")

    # Interviewer Email
    logger.info(f"Sending email to interviewer: {interviewer.email}")

    try:
        send_real_email(interviewer.email, "New Interview Assigned", message)
        logger.info("Interviewer email sent successfully")
    except Exception as e:
        logger.error(f"Interviewer email failed: {e}")

    logger.info("Emails sending process completed")

    db.close()

    logger.info("notify_interview_scheduled END")