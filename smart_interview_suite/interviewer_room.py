import streamlit as st
from streamlit_webrtc import webrtc_streamer, RTCConfiguration
import uuid

st.set_page_config(page_title="Live Interview Room")

st.title(" Live Interview Room")

# Generate room id if interviewer
if "room_id" not in st.session_state:
    st.session_state.room_id = str(uuid.uuid4())[:8]

room_id = st.query_params.get("room")

if room_id:
    st.success(f"Connected to Interview Room: {room_id}")
else:
    room_id = st.session_state.room_id
    st.info("Share this link with candidate:")
    st.code(f"http://localhost:8501/?room={room_id}")

RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

webrtc_streamer(
    key=room_id,
    rtc_configuration=RTC_CONFIGURATION,
    media_stream_constraints={"video": True, "audio": True},
)