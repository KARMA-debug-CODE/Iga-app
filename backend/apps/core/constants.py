"""Curriculum-wide constants shared by every app."""

GRADES = [
    ("S1", "Senior 1"),
    ("S2", "Senior 2"),
    ("S3", "Senior 3"),
    ("S4", "Senior 4"),
    ("S5", "Senior 5"),
    ("S6", "Senior 6"),
]
GRADE_CODES = [code for code, _ in GRADES]

O_LEVEL_GRADES = ("S1", "S2", "S3")
A_LEVEL_GRADES = ("S4", "S5", "S6")

LEVELS = [("O", "O-Level (S1–S3)"), ("A", "A-Level (S4–S6)")]

LANGUAGES = [("en", "English"), ("fr", "Français")]
LANGUAGE_CODES = [code for code, _ in LANGUAGES]


def level_for_grade(grade):
    if grade in O_LEVEL_GRADES:
        return "O"
    if grade in A_LEVEL_GRADES:
        return "A"
    return None


class ContentStatus:
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"

    CHOICES = [
        (DRAFT, "Draft"),
        (REVIEW, "Awaiting review"),
        (PUBLISHED, "Published"),
        (ARCHIVED, "Archived"),
    ]
