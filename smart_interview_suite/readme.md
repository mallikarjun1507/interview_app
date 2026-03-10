# Smart Interview Suite

**Complete pipeline**: PDF Resume → Email Extraction → Auto Screening → Mock Test → Real Email Notifications → Interview Scheduling

## Setup
1. Create `.env` with Gmail App Password
2. Create Virtual environment by `python -m venv venv` and activate the same `venv\Scripts\activate`
3. Install all dependencies`pip install -r requirements.txt`
4. Run the streamlit app `streamlit run app.py`
5. **Delete `smart_interview.db` first time**

## Demo Users
- Admin: `admin@test.com` / `admin`
- Interviewer: `int@test.com` / `test` (**ID=2**)
- Candidate: `cand@test.com` / `test`

## Flow
1. Candidate uploads PDF resume → Email extracted → Auto resume score
2. If passed → Take test → Auto score → **REAL EMAIL** "Test Passed"
3. Admin creates slots (Interviewer ID=2) → Auto schedule → **REAL EMAIL** "Interview at 10AM"
