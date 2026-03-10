import streamlit as st
from models import SessionLocal, Job, InterviewSlot, Interview
from datetime import datetime


def admin_manage_slots():
    db = SessionLocal()

    st.subheader("Create Interview Slots")

    # Get active jobs
    jobs = db.query(Job).filter(Job.is_active == True).all()
    print(jobs, "jobs")

    job_map = {j.title: j.id for j in jobs}
    print(job_map, "job_map")

    job_title = st.selectbox("Job", list(job_map.keys())) if jobs else None
    print(job_title, "job title")

    # Fetch only INTERVIEWER users
    from models import User
    interviewers = db.query(User).filter(User.role == "INTERVIEWER").all()

    interviewer_map = {u.name: u.id for u in interviewers}

    interviewer_name = st.selectbox(
        "Select Interviewer",
        list(interviewer_map.keys())
    )

    interviewer_id = interviewer_map[interviewer_name]

    print(interviewer_id, "interviewer id")

    date = st.date_input("Date")
    print(date, "date")

    start_time = st.time_input("Start time")
    end_time = st.time_input("End time")

    print(start_time, end_time, "rnd time")

    if st.button("Create Slot") and job_title:

        slot = InterviewSlot(
            interviewer_id=interviewer_id,
            job_id=job_map[job_title],
            start_time=datetime.combine(date, start_time),
            end_time=datetime.combine(date, end_time),
        )

        print(slot, "slot")

        db.add(slot)

        print("slot added")

        db.commit()

        print("commit success")

        st.success("Slot created successfully")

    st.subheader("Existing Slots")

    slots = db.query(InterviewSlot).order_by(InterviewSlot.start_time.asc()).all()

    for s in slots:
        st.write(
            f"ID {s.id} | Job {s.job_id} | Interviewer {s.interviewer_id} | "
            f"{s.start_time} - {s.end_time} | Booked: {s.is_booked}"
        )

    db.close()

def interviewer_view_interviews(user_id: int):
    db = SessionLocal()
    st.subheader("My Interviews")
    interviews = (
    db.query(Interview)
    .join(InterviewSlot, Interview.slot_id == InterviewSlot.id)
    .filter(InterviewSlot.interviewer_id == user_id)
    .order_by(Interview.id.desc())
    .all()
)
    for i in interviews:
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
            i.feedback = feedback
            i.rating = rating
            db.commit()
            st.success("Feedback saved")
    db.close()
