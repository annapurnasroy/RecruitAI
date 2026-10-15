
from src.matching import match_skills


def evaluate_skill_matching(test_cases: list[dict]) -> dict:
    """
    Evaluate keyword matching against manually labelled examples.

    Each case should contain:
      - resume_text
      - required_skills
      - expected_matched_skills

    This measures keyword-matching behaviour, not candidate quality.
    """
    total = 0
    correct = 0
    results = []

    for case in test_cases:
        expected = {
            skill.lower()
            for skill in case["expected_matched_skills"]
        }

        actual_result = match_skills(
            case["resume_text"],
            case["required_skills"],
        )

        actual = {
            skill.lower()
            for skill in actual_result["matched_skills"]
        }

        case_correct = actual == expected
        total += 1
        correct += int(case_correct)

        results.append({
            "expected": sorted(expected),
            "actual": sorted(actual),
            "correct": case_correct,
        })

    return {
        "total_cases": total,
        "correct_cases": correct,
        "accuracy_percent": round(correct / total * 100, 2)
        if total else 0.0,
        "results": results,
    }
