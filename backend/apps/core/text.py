"""Cleaning the text people type before it is stored.

Names, chat messages, shared notes, group and class names, questions teachers write, feedback, roster
imports and Santa questions are shown to other people, so before they are saved they are:

- normalised to Unicode NFC (an "é" typed as e + accent is stored like a typed "é", so search,
  duplicates and lengths behave);
- stripped of invisible and control characters: zero-width spaces and joiners, direction overrides
  (U+202E can make "gnp.exe" read "exe.png"), the byte order mark, soft hyphens, invisible "tag"
  letters that can hide instructions for Santa's model (Unicode category Cf), terminal escape codes and
  other control characters (Cc), and lone surrogates (Cs, which the database can't store);
- kept to one line where one line is expected (names, titles): line breaks and tabs become spaces;
- kept from piling accents: at most MAX_COMBINING combining marks after one letter, so a message
  can't spill over the rest of the chat;
- limited in length (the model field's max_length, or TEXT_MAX_CHARS for long text).

HTML or Markdown that people type is stored as the plain text it is, never rendered as HTML: React
escapes text, and the app's Markdown renderer ignores raw HTML and unsafe links
(frontend/src/components/Markdown.jsx).

The check runs in the API's serializers (so a message of only invisible characters is "blank", not
saved empty): every text field a ModelSerializer builds from a model CharField or TextField is a
CleanCharField (install()), and fields declared by hand use CleanCharField. Saving one of the models in
CLEANED_FIELDS cleans those fields again, which covers the Django admin, roster imports and scripts.
"""

import re
import unicodedata

from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save
from rest_framework import serializers
from rest_framework.fields import empty

MAX_COMBINING = 3
_LINE_BREAKS = re.compile(r"\r\n|[\r\n\x0b\x0c\x85\u2028\u2029]")
_ASCII_CONTROL = re.compile(r"[\x00-\x08\x0e-\x1f\x7f]")
_DROPPED = {"Cc", "Cf", "Cs"}
_COMBINING = {"Mn", "Me"}


def clean_text(value, multiline=False):
    """`value` normalised and stripped of invisible and control characters (see the module docstring).
    Line breaks become "\\n" in multiline text and spaces otherwise; tabs are kept only in multiline text."""
    if not isinstance(value, str) or not value:
        return value
    value = _LINE_BREAKS.sub("\n" if multiline else " ", unicodedata.normalize("NFC", value))
    if not multiline:
        value = value.replace("\t", " ")
    if value.isascii():
        return _ASCII_CONTROL.sub("", value)
    out, marks = [], 0
    for char in value:
        if char in "\n\t":
            out.append(char)
            marks = 0
            continue
        category = unicodedata.category(char)
        if category in _DROPPED:
            continue
        if category in _COMBINING:
            marks += 1
            if marks > MAX_COMBINING:
                continue
        else:
            marks = 0
        out.append(char)
    return "".join(out)


class CleanCharField(serializers.CharField):
    """A CharField whose text is cleaned (clean_text) before it is validated, so blank and length checks
    see what will be stored. multiline=True keeps line breaks and tabs; long text without a max_length
    gets TEXT_MAX_CHARS."""

    def __init__(self, *, multiline=False, **kwargs):
        self.multiline = multiline
        if multiline:
            kwargs.setdefault("max_length", settings.TEXT_MAX_CHARS)
        super().__init__(**kwargs)

    def run_validation(self, data=empty):
        if isinstance(data, str):
            data = clean_text(data, self.multiline)
        return super().run_validation(data)


class CleanTextField(CleanCharField):
    """CleanCharField for long text (a model TextField): several lines, Markdown."""

    def __init__(self, **kwargs):
        kwargs.setdefault("multiline", True)
        super().__init__(**kwargs)


# Models whose text is shown to other people, and the fields cleaned whenever they are saved.
CLEANED_FIELDS = {
    "accounts.User": ("first_name", "last_name", "school_name"),
    "community.StudyGroup": ("name", "description"),
    "community.Message": ("body",),
    "community.SharedNote": ("title", "body"),
    "community.MessageReport": ("reason",),
    "classroom.Classroom": ("name",),
    "classroom.Assignment": ("title", "instructions"),
    "assessments.Question": ("prompt", "explanation", "marking_guide"),
    "assessments.Choice": ("text",),
    "assessments.Quiz": ("title", "description"),
    "assessments.Answer": ("text_answer", "teacher_feedback"),
    "assessments.ExamPaper": ("title", "paper_code", "source_note"),
    "curriculum.Lesson": ("title", "summary", "body"),
    "curriculum.LessonTranslation": ("title", "summary", "body"),
    "curriculum.Resource": ("title", "description", "description_fr", "publisher", "licence"),
    "schools.School": ("name", "sector"),
    "tutor.TutorExchange": ("message",),
    "website.ContactMessage": ("name", "school", "message"),
}


def _clean_instance(sender, instance, **kwargs):
    for name in CLEANED_FIELDS.get(sender._meta.label, ()):
        field = sender._meta.get_field(name)
        value = getattr(instance, field.attname)
        cleaned = clean_text(value, multiline=isinstance(field, models.TextField))
        if isinstance(cleaned, str) and not isinstance(field, models.TextField):
            cleaned = cleaned.strip()
        if cleaned != value:
            setattr(instance, field.attname, cleaned)


def install():
    """Called once at start-up (CoreConfig.ready)."""
    mapping = serializers.ModelSerializer.serializer_field_mapping
    mapping[models.CharField] = CleanCharField
    mapping[models.TextField] = CleanTextField
    pre_save.connect(_clean_instance, dispatch_uid="iga-clean-text")
