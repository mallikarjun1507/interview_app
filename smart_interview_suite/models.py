from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Boolean, ForeignKey, DateTime, Text, JSON
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

DB_URL = os.getenv("DB_URL", "sqlite:///smart_interview.db")
engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    resume_email = Column(String(120), nullable=True)
    role = Column(String(20), nullable=False)
    password = Column(String(128), nullable=False)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    skills_required = Column(Text)
    is_active = Column(Boolean, default=True)

    questions = relationship("Question", backref="job")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    text = Column(Text, nullable=False)
    question_type = Column(String(10), nullable=False)
    options = Column(JSON, nullable=True)
    correct_option = Column(String(255), nullable=True)
    weight = Column(Float, default=1.0)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("users.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"))
    status = Column(String(30), default="RESUME_PENDING")
    resume_score = Column(Float, default=0.0)
    total_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("User")
    job = relationship("Job")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    response_text = Column(Text, nullable=True)
    selected_option = Column(String(255), nullable=True)
    score = Column(Float, default=0.0)

    application = relationship("Application", backref="answers")
    question = relationship("Question")


class InterviewSlot(Base):
    __tablename__ = "interview_slots"

    id = Column(Integer, primary_key=True, index=True)
    interviewer_id = Column(Integer, ForeignKey("users.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_booked = Column(Boolean, default=False)

    interviewer = relationship("User")


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"))
    slot_id = Column(Integer, ForeignKey("interview_slots.id"))
    round_type = Column(String(10), default="TECH1")
    meet_link = Column(String(255), nullable=True)  # Now stores WebRTC room link
    feedback = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)

    application = relationship("Application")
    slot = relationship("InterviewSlot")


def init_db():
    Base.metadata.create_all(bind=engine)