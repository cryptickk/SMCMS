
import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Delhi Municipal Corporation",
    page_icon="🏛️",
    layout="wide",
)

st.title("🏛️ Delhi Municipal Corporation")
st.subheader("Smart Municipal Complaint Management System")

st.info(
    "Submit a civic complaint. AI will automatically assign your complaint to the concerned department."
)

submit_tab, track_tab, dashboard_tab = st.tabs(
    ["Submit Complaint", "Track Complaint", "Recent Complaints"]
)

with submit_tab:
    with st.form("complaint_form"):
        ward = st.selectbox(
            "Select ward",
            ["Ward 1", "Ward 2", "Ward 3", "Ward 4", "Ward 5"],
        )

        complaint = st.text_area(
            "Describe your complaint",
            placeholder=(
                "Example: A large pothole near the government "
                "school is dangerous for children."
            ),
            max_chars=2000,
            height=150,
        )

        submitted = st.form_submit_button(
            "Submit Complaint",
            type="primary",
        )

    if submitted:
        if len(complaint.strip()) < 10:
            st.error("Please enter at least 10 characters.")
        else:
            try:
                response = requests.post(
                    f"{API_URL}/tickets",
                    json={
                        "ward": ward,
                        "complaint": complaint.strip(),
                    },
                    timeout=30,
                )
                response.raise_for_status()
                ticket = response.json()

                st.success("Complaint registered successfully!")
                st.code(ticket["ticket_id"], language=None)

                col1, col2 = st.columns(2)

                with col1:
                    st.metric(
                        "Predicted Department",
                        ticket["department"],
                    )
                    st.metric(
                        "Department Model Score",
                        f'{ticket["department_confidence"]:.1%}',
                    )

                with col2:
                    st.metric(
                        "Predicted Priority",
                        ticket["priority"],
                    )
                    st.metric(
                        "Priority Model Score",
                        f'{ticket["priority_confidence"]:.1%}',
                    )

                if ticket["manual_review"]:
                    st.warning(
                        "Flagged for manual review due to a low "
                        "model confidence score."
                    )

                st.write("Status:", ticket["status"])

            except requests.RequestException as exc:
                st.error(f"Could not submit complaint: {exc}")

with track_tab:
    st.write("Enter your ticket ID to retrieve a complaint.")

    ticket_id = st.text_input("Ticket ID")

    if st.button("Track Complaint"):
        if not ticket_id.strip():
            st.warning("Enter a ticket ID.")
        else:
            try:
                response = requests.get(
                    f"{API_URL}/tickets/{ticket_id.strip()}",
                    timeout=15,
                )

                if response.status_code == 404:
                    st.error("Ticket not found.")
                else:
                    response.raise_for_status()
                    ticket = response.json()

                    st.write("**Ticket:**", ticket["ticket_id"])
                    st.write("**Department:**", ticket["department"])
                    st.write("**Priority:**", ticket["priority"])
                    st.write("**Ward:**", ticket["ward"])
                    st.write("**Status:**", ticket["status"])
                    st.write("**Complaint:**", ticket["complaint"])

            except requests.RequestException as exc:
                st.error(f"Could not retrieve ticket: {exc}")

with dashboard_tab:
    st.write("Recent complaints")

    if st.button("Refresh Complaints"):
        try:
            response = requests.get(
                f"{API_URL}/tickets",
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            st.metric("Total complaints", data["count"])
            st.dataframe(
                data["tickets"],
                use_container_width=True,
                hide_index=True,
            )

        except requests.RequestException as exc:
            st.error(f"Could not load complaints: {exc}")
