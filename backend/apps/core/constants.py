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

# A-level combinations and their three principal subjects (subject codes). Computer Science is a principal
# subject only in MCE and MPC; students in the other combinations take ICT for general education.
COMBINATIONS = {
    "MCE": ("mathematics", "computer-science", "economics"),
    "MPC": ("mathematics", "physics", "computer-science"),
    "MEG": ("mathematics", "economics", "geography"),
    "MPG": ("mathematics", "physics", "geography"),
    "PCM": ("physics", "chemistry", "mathematics"),
    "PCB": ("physics", "chemistry", "biology"),
    "MCB": ("mathematics", "chemistry", "biology"),
    "HEG": ("history", "economics", "geography"),
    "LFK": ("literature", "french", "kinyarwanda"),
}
COMBINATION_CHOICES = [
    ("MCE", "MCE – Mathematics, Computer Science, Economics"),
    ("MPC", "MPC – Mathematics, Physics, Computer Science"),
    ("MEG", "MEG – Mathematics, Economics, Geography"),
    ("MPG", "MPG – Mathematics, Physics, Geography"),
    ("PCM", "PCM – Physics, Chemistry, Mathematics"),
    ("PCB", "PCB – Physics, Chemistry, Biology"),
    ("MCB", "MCB – Mathematics, Chemistry, Biology"),
    ("HEG", "HEG – History, Economics, Geography"),
    ("LFK", "LFK – Literature in English, French, Kinyarwanda"),
]

LANGUAGES = [("en", "English"), ("fr", "Français")]
LANGUAGE_CODES = [code for code, _ in LANGUAGES]
# Books and other study material can also be in Rwanda's other school languages.
RESOURCE_LANGUAGES = [*LANGUAGES, ("rw", "Kinyarwanda"), ("sw", "Kiswahili")]


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
