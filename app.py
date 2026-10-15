
import csv
import io
import streamlit as st

from src.database import (
    init_db,
    create_job,
    get_jobs,
    save_screening,
    get_screenings,
    update_screening_status,
)
from src.pdf_utils import extract_text_from_pdf
from src.matching import match_skills
from src.screening import generate_candidate_summary
from src.evaluation import evaluate_skill_matching


# ---------------- Page setup ----------------
st.set_page_config(
    page_title="RecruitAI",
    page_icon="🧩",
    layout="wide",
)

init_db()

st.title("RecruitAI")
st.caption("Evidence-based recruitment assistance with human oversight.")

st.info(
    "RecruitAI supports human review; it does not make hiring decisions. "
    "A skill not found in a resume is not proof that the candidate lacks it."
)


# ---------------- Helpers ----------------
def make_csv(records):
    """Convert records to downloadable CSV without pandas."""
    output = io.StringIO()

    fields = [
        "candidate_name",
        "filename",
        "job_title",
        "matched_skills",
        "not_found_skills",
        "match_percentage",
        "ai_summary",
        "status",
        "created_at",
    ]

    writer = csv.DictWriter(
        output,
        fieldnames=fields,
        extrasaction="ignore",
    )
    writer.writeheader()

    for record in records:
        writer.writerow(record)

    return output.getvalue().encode("utf-8-sig")


def get_required_skills(job):
    return [
        skill.strip()
        for skill in job["required_skills"].splitlines()
        if skill.strip()
    ]


# ---------------- Navigation ----------------
tab_dashboard, tab_jobs, tab_screen, tab_records, tab_eval = st.tabs(
    [
        "Dashboard",
        "Create Job",
        "Screen Resumes",
        "Candidate Records",
        "Evaluation",
    ]
)


# ---------------- Dashboard ----------------
with tab_dashboard:
    jobs = get_jobs()
    records = get_screenings()

    col1, col2, col3 = st.columns(3)

    col1.metric("Jobs created", len(jobs))
    col2.metric("Resumes screened", len(records))
    col3.metric(
        "Pending human review",
        sum(
            record["status"] == "Pending human review"
            for record in records
        ),
    )

    st.subheader("Recent screening activity")

    if records:
        recent = [
            {
                "Candidate": record["candidate_name"],
                "Job": record["job_title"],
                "Keyword match (%)": record["match_percentage"],
                "Review status": record["status"],
            }
            for record in records[:10]
        ]

        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("No candidate records yet. Create a job to get started.")


# ---------------- Create Job ----------------
with tab_jobs:
    st.subheader("Create a job profile")

    with st.form("create_job_form"):
        job_title = st.text_input("Job title")

        job_description = st.text_area(
            "Job description",
            height=160,
            placeholder="Describe the role and its job-related requirements.",
        )

        skills_input = st.text_input(
            "Required skills (comma-separated)",
            placeholder="Python, SQL, Linux, Git",
        )

        job_submitted = st.form_submit_button("Save job")

    if job_submitted:
        skills = [
            skill.strip()
            for skill in skills_input.split(",")
            if skill.strip()
        ]

        if not job_title.strip() or not job_description.strip():
            st.error("Please enter both a job title and job description.")
        elif not skills:
            st.error("Please enter at least one required skill.")
        else:
            job_id = create_job(
                job_title,
                job_description,
                skills,
            )
            st.success(f"Job saved successfully. Job ID: {job_id}")

    st.subheader("Saved jobs")

    jobs = get_jobs()

    if jobs:
        for job in jobs:
            with st.expander(
                f'{job["title"]} — Job ID {job["id"]}'
            ):
                st.write(job["description"])
                st.write("**Required skills**")
                st.write(job["required_skills"])
    else:
        st.write("No jobs created yet.")


# ---------------- Screen Resumes ----------------
with tab_screen:
    st.subheader("Screen resumes against a selected job")

    jobs = get_jobs()

    if not jobs:
        st.warning("Create a job profile before uploading resumes.")
    else:
        job_options = {
            f'{job["title"]} (ID {job["id"]})': job
            for job in jobs
        }

        selected_label = st.selectbox(
            "Select job",
            list(job_options.keys()),
            key="selected_job",
        )
        selected_job = job_options[selected_label]
        required_skills = get_required_skills(selected_job)

        uploaded_files = st.file_uploader(
            "Upload PDF resumes",
            type=["pdf"],
            accept_multiple_files=True,
            help="Upload only resumes you are authorized to process.",
            key="resume_uploader",
        )

        if uploaded_files:
            st.caption(f"{len(uploaded_files)} PDF file(s) selected.")

        if st.button(
            "Analyze resumes",
            type="primary",
            disabled=not uploaded_files,
            key="analyze_resumes",
        ):
            prepared = []

            for uploaded_file in uploaded_files:
                try:
                    resume_text = extract_text_from_pdf(
                        uploaded_file.getvalue()
                    )

                    if not resume_text:
                        st.warning(
                            f"{uploaded_file.name}: no selectable text "
                            "was found. Scanned PDFs need OCR."
                        )
                        continue

                    matching = match_skills(
                        resume_text,
                        required_skills,
                    )

                    prepared.append(
                        {
                            "filename": uploaded_file.name,
                            "resume_text": resume_text,
                            "matching": matching,
                        }
                    )

                except Exception as exc:
                    st.error(
                        f"Could not process {uploaded_file.name}: {exc}"
                    )

            st.session_state["prepared_resumes"] = prepared
            st.session_state["prepared_job_id"] = selected_job["id"]

        # Keep analysis results available across Streamlit reruns.
        prepared_resumes = st.session_state.get(
            "prepared_resumes", []
        )

        if (
            prepared_resumes
            and st.session_state.get("prepared_job_id")
            == selected_job["id"]
        ):
            for index, item in enumerate(prepared_resumes):
                with st.expander(
                    f'Results: {item["filename"]}',
                    expanded=True,
                ):
                    candidate_name = st.text_input(
                        "Candidate name",
                        value=item["filename"].rsplit(".", 1)[0],
                        key=f"candidate_name_{index}",
                    )

                    matching = item["matching"]

                    st.metric(
                        "Keyword match percentage",
                        f'{matching["match_percentage"]:.2f}%',
                    )

                    st.write(
                        "**Skills found:**",
                        ", ".join(matching["matched_skills"]) or "None found",
                    )
                    st.write(
                        "**Skills not found in resume:**",
                        ", ".join(matching["not_found_skills"]) or "None",
                    )

                    summary_key = f"summary_{selected_job['id']}_{index}"
                    saved_key = f"saved_{selected_job['id']}_{index}"

                    if st.button(
                        "Generate AI summary",
                        key=f"generate_{selected_job['id']}_{index}",
                    ):
                        try:
                            with st.spinner(
                                "Generating evidence-based summary..."
                            ):
                                summary = generate_candidate_summary(
                                    job_title=selected_job["title"],
                                    job_description=selected_job["description"],
                                    required_skills=required_skills,
                                    resume_text=item["resume_text"],
                                    matched_skills=matching["matched_skills"],
                                    not_found_skills=matching["not_found_skills"],
                                )

                            st.session_state[summary_key] = summary

                        except Exception as exc:
                            st.error(
                                "AI analysis failed. Check the Groq "
                                "configuration and connection."
                            )
                            st.caption(str(exc))

                    summary = st.session_state.get(summary_key)

                    if summary:
                        st.markdown("#### AI-generated summary")
                        st.write(summary)

                        if st.button(
                            "Save candidate record",
                            key=f"save_{selected_job['id']}_{index}",
                            disabled=st.session_state.get(saved_key, False),
                        ):
                            if not candidate_name.strip():
                                st.error("Please enter a candidate name.")
                            else:
                                try:
                                    save_screening(
                                        job_id=selected_job["id"],
                                        candidate_name=candidate_name.strip(),
                                        filename=item["filename"],
                                        resume_text=item["resume_text"],
                                        matched_skills=matching["matched_skills"],
                                        not_found_skills=matching["not_found_skills"],
                                        match_percentage=matching["match_percentage"],
                                        ai_summary=summary,
                                    )

                                    st.session_state[saved_key] = True
                                    st.success(
                                        "Candidate record saved for human review."
                                    )
                                except Exception as exc:
                                    st.error(
                                        f"Could not save candidate record: {exc}"
                                    )

                        if st.session_state.get(saved_key, False):
                            st.caption("This candidate record has been saved.")


# ---------------- Candidate Records ----------------
with tab_records:
    st.subheader("Candidate records and human review")

    records = get_screenings()

    if not records:
        st.write("No saved candidate records yet.")
    else:
        for record in records:
            with st.expander(
                f'{record["candidate_name"]} — {record["job_title"]}'
            ):
                st.write(f'**File:** {record["filename"]}')
                st.write(
                    f'**Keyword match:** {record["match_percentage"]:.2f}%'
                )
                st.write(
                    f'**Skills found:** {record["matched_skills"] or "None"}'
                )
                st.write(
                    f'**Skills not found:** '
                    f'{record["not_found_skills"] or "None"}'
                )

                st.markdown("**AI summary**")
                st.write(record["ai_summary"] or "No summary saved.")

                statuses = [
                    "Pending human review",
                    "Reviewed",
                    "Shortlist for interview",
                    "Not proceeding",
                ]

                current_status = record["status"]
                status_index = (
                    statuses.index(current_status)
                    if current_status in statuses
                    else 0
                )

                new_status = st.selectbox(
                    "Human review status",
                    statuses,
                    index=status_index,
                    key=f"status_{record['id']}",
                )

                if st.button(
                    "Update review status",
                    key=f"update_{record['id']}",
                ):
                    update_screening_status(
                        record["id"],
                        new_status,
                    )
                    st.success("Review status updated.")
                    st.rerun()

        st.download_button(
            "Export candidate records as CSV",
            data=make_csv(records),
            file_name="recruitai_candidate_records.csv",
            mime="text/csv",
        )


# ---------------- Evaluation ----------------
with tab_eval:
    st.subheader("Keyword-matching evaluation")

    st.write(
        "These manually labelled examples test keyword-matching behaviour. "
        "A small demonstration does not establish real-world accuracy."
    )

    if st.button("Run demonstration evaluation"):
        test_cases = [
            {
                "resume_text": "Python and SQL experience",
                "required_skills": ["Python", "SQL", "Linux"],
                "expected_matched_skills": ["Python", "SQL"],
            },
            {
                "resume_text": "Java developer with Git experience",
                "required_skills": ["Java", "Python", "Git"],
                "expected_matched_skills": ["Java", "Git"],
            },
        ]

        result = evaluate_skill_matching(test_cases)

        col1, col2, col3 = st.columns(3)
        col1.metric("Test cases", result["total_cases"])
        col2.metric("Correct cases", result["correct_cases"])
        col3.metric("Accuracy (%)", result["accuracy_percent"])

        st.json(result["results"])
