import streamlit as st
import json
import os
from datetime import datetime

from models import (
    init_db,
    SessionLocal,
    User,
    Job,
    Question,
    Application,
    Answer,
    Interview   # ✅ Added
)
from services import (
    evaluate_screening, 
    auto_schedule_interviews, 
    run_resume_screening,
    extract_text_from_pdf,
    extract_email_from_resume
)
from auth import login
from scheduler import admin_manage_slots, interviewer_view_interviews

#  NEW IMPORTS FOR WEBRTC
from streamlit_webrtc import webrtc_streamer, RTCConfiguration
import uuid

# laatest updates about the issues
# ------------------ NEW INTERVIEW ROOM FUNCTION ------------------ #
def interview_room(room_id):

    st.header("🎥 Live Interview Room")
    st.success(f"Room ID: {room_id}")
    st.info("Allow camera and microphone access to join the interview.")

    # initialize session state
    if "interview_started" not in st.session_state:
        st.session_state.interview_started = False

    col1, col2 = st.columns(2)

    with col1:
        if st.button("▶ Start Interview"):
            st.session_state.interview_started = True

    with col2:
        if st.button("⏹ Leave Interview"):
            st.session_state.interview_started = False
            st.warning("You left the interview")
            st.rerun()

    # only create webrtc when interview started
    if st.session_state.interview_started:

        RTC_CONFIGURATION = RTCConfiguration({
            "iceServers": [
                {"urls": ["stun:stun.l.google.com:19302"]},
                {"urls": ["stun:stun1.l.google.com:19302"]},
                {
                    "urls": [
                        "turn:openrelay.metered.ca:80",
                        "turn:openrelay.metered.ca:443",
                        "turn:openrelay.metered.ca:443?transport=tcp"
                    ],
                    "username": "openrelayproject",
                    "credential": "openrelayproject",
                },
            ]
        })

        ctx = webrtc_streamer(
            key=f"interview-{room_id}",   # stable key
            rtc_configuration=RTC_CONFIGURATION,
            media_stream_constraints={
                "video": True,
                "audio": True
            },
        )

        if ctx and ctx.state.playing:
            st.success("🟢 Connected to interview room")

    else:
        st.info("Click **Start Interview** to begin.")
        
def seed_demo_data():
    db = SessionLocal()
    if not db.query(User).first():
        admin = User(name="Admin", email="admin@test.com", role="ADMIN", password="admin")
        interviewer = User(name="Interviewer", email="int@test.com", role="INTERVIEWER", password="test")
        candidate = User(name="Candidate", email="cand@test.com", role="CANDIDATE", password="test")
        db.add_all([admin, interviewer, candidate])
        db.commit()

    if not db.query(Job).first():
        job = Job(
            title="Python Backend Developer",
            description="Final Year Demo Job",
            skills_required="Python, SQL, Streamlit, Django",
        )
        db.add(job)
        db.commit()
    db.close()


def load_questions_from_json():
    db = SessionLocal()
    file_path = os.path.join("data", "sample_questions.json")
    if not os.path.exists(file_path):
        db.close()
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for job_block in data:
        title = job_block["job_title"]
        job = db.query(Job).filter(Job.title == title).first()
        if not job:
            continue

        for q in job_block["questions"]:
            exists = (
                db.query(Question)
                .filter(Question.job_id == job.id, Question.text == q["text"])
                .first()
            )
            if exists:
                continue

            question = Question(
                job_id=job.id,
                text=q["text"],
                question_type=q["question_type"],
                options=q.get("options") or None,
                correct_option=q.get("correct_option") or None,
                weight=q.get("weight", 1.0),
            )
            db.add(question)

    db.commit()
    db.close()


def admin_dashboard():
    st.header("Admin / HR Dashboard")
    db = SessionLocal()

    st.subheader("Jobs")
    title = st.text_input("Job title")
    desc = st.text_area("Description")
    skills = st.text_area("Skills required (comma separated)")
    if st.button("Create Job"):
        job = Job(title=title, description=desc, skills_required=skills)
        db.add(job)
        db.commit()
        st.success("Job created")

    st.markdown("---")
    st.subheader("Manage Questions")
    jobs = db.query(Job).all()
    job_map = {j.title: j.id for j in jobs}
    job_title_q = st.selectbox("Select job", list(job_map.keys())) if jobs else None

    q_text = st.text_area("Question text")
    q_type = st.selectbox("Question type", ["MCQ", "TEXT"])
    options = []
    correct = None

    if q_type == "MCQ":
        opt_raw = st.text_input("Options (comma separated)")
        correct = st.text_input("Correct option (exact text)")
        if opt_raw:
            options = [o.strip() for o in opt_raw.split(",") if o.strip()]
    weight = st.number_input("Weight", min_value=0.5, max_value=10.0, step=0.5, value=1.0)

    if st.button("Add Question") and job_title_q and q_text:
        q = Question(
            job_id=job_map[job_title_q],
            text=q_text,
            question_type=q_type,
            options=options if options else None,
            correct_option=correct if correct else None,
            weight=weight,
        )
        db.add(q)
        db.commit()
        st.success("Question added")

    st.markdown("---")
    st.subheader("Applications Status")
    apps = db.query(Application).order_by(Application.created_at.desc()).all()
    for a in apps:
        st.write(
            f"App {a.id} | Cand {a.candidate_id} | Job {a.job_id} | "
            f"R={a.resume_score} T={a.total_score} | {a.status}"
        )

    st.markdown("---")
    admin_manage_slots()

    st.markdown("---")
    st.subheader("Auto-Schedule Interviews")
    job_id = st.number_input("Job ID", min_value=1, step=1)
    if st.button("Run auto-schedule"):
        auto_schedule_interviews(job_id)
        st.success("Auto scheduling completed!")
    db.close()


def candidate_dashboard(user):
    st.header("Candidate Dashboard")
    db = SessionLocal()

    st.subheader("My Applications")
    apps = db.query(Application).filter(Application.candidate_id == user["id"]).all()
    for app in apps:
        st.write(f"App {app.id} | {app.job.title} | R={app.resume_score} T={app.total_score} | {app.status}")
        if app.status == "TEST_PASSED":
            st.success("Test Passed - Waiting for interview")
        elif app.status == "SCHEDULED":
            st.success("Interview Scheduled!")

    st.markdown("---")
    st.subheader("Apply for Job (Resume Screening)")
    jobs = db.query(Job).filter(Job.is_active == True).all()
    job_map = {j.title: j.id for j in jobs}
    job_title = st.selectbox("Select job", list(job_map.keys())) if jobs else None
    resume_file = st.file_uploader("Upload resume (PDF)", type=["pdf"])

    if st.button("Apply") and job_title and resume_file is not None:
        resume_text = extract_text_from_pdf(resume_file)
        resume_email = extract_email_from_resume(resume_text)
        
        if not resume_text.strip():
            st.error("Could not read PDF.")
        elif not resume_email:
            st.error("No valid email found in resume.")
        else:
            candidate = db.query(User).get(user["id"])
            candidate.resume_email = resume_email
            db.commit()
            
            app = Application(
                candidate_id=user["id"],
                job_id=job_map[job_title],
                status="RESUME_PENDING",
            )
            db.add(app)
            db.commit()
            db.refresh(app)

            run_resume_screening(app.id, resume_text)
            st.success(f"Applied! Email: {resume_email} | App ID: {app.id}")

    st.markdown("---")
    st.subheader("Take Mock Test")
    app_id = st.number_input("Application ID", min_value=1, step=1)
    if st.button("Load Questions"):
        st.session_state["current_app_id"] = app_id

    current_app_id = st.session_state.get("current_app_id")
    if current_app_id:
        app = db.query(Application).get(current_app_id)
        if not app or app.candidate_id != user["id"]:
            st.error("Invalid application")
        elif app.status != "TEST_PENDING":
            st.warning(f"Status: {app.status}. Need TEST_PENDING.")
        else:
            questions = db.query(Question).filter(Question.job_id == app.job_id).all()
            answers_cache = {}
            for q in questions:
                st.write(f"**Q{q.id}:** {q.text}")
                if q.question_type == "MCQ":
                    choice = st.radio("", q.options, key=f"q_{q.id}")
                    answers_cache[q.id] = {"selected_option": choice}
                else:
                    txt = st.text_area("", key=f"q_{q.id}")
                    answers_cache[q.id] = {"response_text": txt}

            if st.button("Submit Test"):
                db.query(Answer).filter(Answer.application_id == app.id).delete()
                for qid, data in answers_cache.items():
                    ans = Answer(
                        application_id=app.id,
                        question_id=qid,
                        selected_option=data.get("selected_option"),
                        response_text=data.get("response_text"),
                    )
                    db.add(ans)
                db.commit()
                evaluate_screening(app.id)
                st.success("Test submitted & evaluated!")

                  # 🔥 Secure WebRTC Join
    room_param = st.query_params.get("room")
    if room_param:
        interview = db.query(Interview).filter(Interview.meet_link.contains(room_param)).first()

        if interview and interview.application.candidate_id == user["id"]:
            interview_room(room_param)
        else:
            st.error("Unauthorized access to interview room")
    db.close()


def interviewer_dashboard(user):
    st.header("Interviewer Dashboard")
    interviewer_view_interviews(user["id"])

    db = SessionLocal()

    #  Secure WebRTC Join
    room_param = st.query_params.get("room")
    if room_param:
        interview = db.query(Interview).filter(Interview.meet_link.contains(room_param)).first()

        if interview and interview.slot.interviewer_id == user["id"]:
            interview_room(room_param)
        else:
            st.error("Unauthorized access to interview room")

    db.close()


def main():
    st.set_page_config(page_title="Smart Screening And Interview Suite", layout="wide")
    init_db()
    seed_demo_data()
    load_questions_from_json()

  # 🔥 Check if interview room link opened
    query_params = st.query_params

    if "room" in query_params:
        room_id = query_params["room"]
        interview_room(room_id)
        st.stop()

    # Normal login flow
    login()
    
    user = st.session_state.get("user")
    if not user:
        st.info("Please login from sidebar.")
        return

    if user["role"] == "ADMIN":
        admin_dashboard()
    elif user["role"] == "CANDIDATE":
        candidate_dashboard(user)
    elif user["role"] == "INTERVIEWER":
        interviewer_dashboard(user)


if __name__ == "__main__":
    main()
