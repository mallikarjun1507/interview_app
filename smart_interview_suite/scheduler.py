import streamlit as st
from models import SessionLocal, Job, InterviewSlot, Interview
from datetime import datetime
from logger_config import get_logger

logger = get_logger(__name__)


def admin_manage_slots():

    logger.info("Admin slot management page opened")

    db = SessionLocal()

    st.subheader("Create Interview Slots")

    # Get active jobs
    jobs = db.query(Job).filter(Job.is_active == True).all()

    logger.info(f"Active jobs fetched: {len(jobs)}")

    job_map = {j.title: j.id for j in jobs}

    logger.debug(f"Job map: {job_map}")

    job_title = st.selectbox("Job", list(job_map.keys())) if jobs else None

    logger.info(f"Selected job title: {job_title}")

    # Fetch only INTERVIEWER users
    from models import User

    interviewers = db.query(User).filter(User.role == "INTERVIEWER").all()

    logger.info(f"Interviewers fetched: {len(interviewers)}")

    interviewer_map = {u.name: u.id for u in interviewers}

    interviewer_name = st.selectbox(
        "Select Interviewer",
        list(interviewer_map.keys())
    )

    interviewer_id = interviewer_map[interviewer_name]

    logger.info(f"Selected interviewer id: {interviewer_id}")

    date = st.date_input("Date")
    start_time = st.time_input("Start time")
    end_time = st.time_input("End time")

    logger.info(f"Slot date: {date}")
    logger.info(f"Start time: {start_time} End time: {end_time}")

    if st.button("Create Slot") and job_title:

        slot = InterviewSlot(
            interviewer_id=interviewer_id,
            job_id=job_map[job_title],
            start_time=datetime.combine(date, start_time),
            end_time=datetime.combine(date, end_time),
        )

        logger.info(
            f"Creating slot job_id={job_map[job_title]} interviewer_id={interviewer_id}"
        )

        db.add(slot)

        logger.info("Slot added to session")

        db.commit()

        logger.info("Slot committed to database successfully")

        st.success("Slot created successfully")

    st.subheader("Existing Slots")

    slots = db.query(InterviewSlot).order_by(InterviewSlot.start_time.asc()).all()

    logger.info(f"Total slots fetched: {len(slots)}")

    for s in slots:

        logger.debug(
            f"Slot ID={s.id} job={s.job_id} interviewer={s.interviewer_id} "
            f"start={s.start_time} booked={s.is_booked}"
        )

        st.write(
            f"ID {s.id} | Job {s.job_id} | Interviewer {s.interviewer_id} | "
            f"{s.start_time} - {s.end_time} | Booked: {s.is_booked}"
        )

    db.close()

    logger.info("Admin slot management completed")


def interviewer_view_interviews(user_id: int):

    logger.info(f"Interviewer dashboard opened for user_id={user_id}")

    db = SessionLocal()

    st.subheader("My Interviews")

    interviews = (
        db.query(Interview)
        .join(InterviewSlot, Interview.slot_id == InterviewSlot.id)
        .filter(InterviewSlot.interviewer_id == user_id)
        .order_by(Interview.id.desc())
        .all()
    )

    logger.info(f"Total interviews fetched: {len(interviews)}")

    for i in interviews:

        logger.info(
            f"Interview ID={i.id} application_id={i.application_id} "
            f"job={i.application.job_id} time={i.slot.start_time}"
        )

        st.write(
            f"Interview {i.id} | Application {i.application_id} | Job {i.application.job_id} | "
            f"Round {i.round_type} | Time {i.slot.start_time}"
        )

        st.markdown(f"[Join Interview]({i.meet_link})")

        feedback = st.text_area(
            f"Feedback {i.id}", value=i.feedback or "", key=f"fb_{i.id}"
        )

        rating = st.slider(
            f"Rating {i.id}", 1, 10, value=i.rating or 5, key=f"rt_{i.id}"
        )

        if st.button(f"Save Feedback {i.id}"):

            logger.info(f"Saving feedback for interview_id={i.id}")

            i.feedback = feedback
            i.rating = rating

            db.commit()

            logger.info(f"Feedback saved successfully for interview_id={i.id}")

            st.success("Feedback saved")

    db.close()

    logger.info("Interviewer dashboard loaded successfully")