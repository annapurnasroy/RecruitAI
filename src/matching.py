
import re


def normalize_text(text: str) -> str:
    """Normalize text for case-insensitive matching."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def match_skills(resume_text: str, required_skills: list[str]) -> dict:
    """
    Match required skills against resume text.

    A missing keyword means 'not found in the resume',
    not that the candidate lacks the skill.
    """
    normalized_resume = normalize_text(resume_text)

    matched = []
    not_found = []

    for skill in required_skills:
        skill = skill.strip()

        if not skill:
            continue

        pattern = r"(?<!\w)" + re.escape(skill.lower()) + r"(?!\w)"

        if re.search(pattern, normalized_resume):
            matched.append(skill)
        else:
            not_found.append(skill)

    total = len(matched) + len(not_found)
    percentage = round((len(matched) / total) * 100, 2) if total else 0.0

    return {
        "matched_skills": matched,
        "not_found_skills": not_found,
        "matched_count": len(matched),
        "required_count": total,
        "match_percentage": percentage,
    }
