
import re
from pathlib import Path
from pypdf import PdfReader


def generate_job_description(
    title: str,
    skills: list[str],
    experience: str,
) -> str:
    """Generate a mock job description for development and testing.

    This function does not call an external AI service.
    """

    skills_text = ", ".join(
        skills) if skills else "relevant professional skills"

    return (
        f"Job Title: {title}\n\n"
        f"About the Role:\n"
        f"We are looking for a {title} to join our team and contribute "
        f"to meaningful projects.\n\n"
        f"Responsibilities:\n"
        f"- Develop and maintain solutions related to {title}.\n"
        f"- Collaborate with team members and stakeholders.\n"
        f"- Write clear documentation and follow good practices.\n"
        f"- Troubleshoot issues and improve existing solutions.\n\n"
        f"Required Skills:\n"
        f"- {skills_text}\n\n"
        f"Experience:\n"
        f"{experience}\n\n"
        f"Note: This is a mock development response, not AI-generated content."
    )


def extract_resume_text(pdf_path: str | Path) -> str:
    """Extract readable text from a PDF while preserving line breaks."""
    import pdfplumber

    path = Path(pdf_path)

    if not path.is_file():
        raise FileNotFoundError("Resume PDF file was not found.")

    page_texts = []

    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(
                layout=True,
                x_tolerance=2,
                y_tolerance=3,
            ) or ""

            text = text.replace("\r\n", "\n").replace("\r", "\n")
            text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
            text = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text)
            text = text.strip()

            if text:
                page_texts.append(text)

    extracted_text = "\n\n".join(page_texts).strip()

    if not extracted_text:
        raise ValueError(
            "No readable text was found. The PDF may be scanned "
            "or contain only images."
        )

    return extracted_text


def structure_resume_text(text: str) -> dict:
    """
    Structure extracted resume text while preserving project details,
    course names, certification names, and links near their content.

    This is a rule-based parser. It does not invent missing details.
    """
    import re

    if not text or not text.strip():
        return {
            "contact": {},
            "sections": [],
            "unclassified": [],
        }

    # Normalize line endings without removing paragraph boundaries.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")

    raw_lines = [
        re.sub(r"[ \t]+", " ", line).strip()
        for line in text.split("\n")
    ]

    # Keep blank lines temporarily: they can separate projects.
    lines = []
    for line in raw_lines:
        if line or (lines and lines[-1] != ""):
            lines.append(line)

    while lines and not lines[0]:
        lines.pop(0)

    while lines and not lines[-1]:
        lines.pop()

    section_aliases = {
        "summary": "Professional Summary",
        "professional summary": "Professional Summary",
        "profile": "Professional Summary",
        "career objective": "Professional Summary",
        "objective": "Professional Summary",

        "experience": "Work Experience",
        "work experience": "Work Experience",
        "professional experience": "Work Experience",
        "employment history": "Work Experience",
        "work history": "Work Experience",
        "internship": "Internships",
        "internships": "Internships",

        "projects": "Projects",
        "project": "Projects",
        "academic projects": "Projects",
        "personal projects": "Projects",
        "key projects": "Projects",

        "technical skills": "Technical Skills",
        "technical expertise": "Technical Skills",
        "skills": "Skills",
        "core skills": "Skills",
        "key skills": "Skills",
        "programming skills": "Technical Skills",

        "education": "Education",
        "educational qualifications": "Education",
        "academic background": "Education",
        "academic qualifications": "Education",

        "certifications": "Certifications",
        "certificates": "Certifications",
        "licenses and certifications": "Certifications",
        "certifications and courses": "Certifications & Courses",
        "courses": "Courses",
        "relevant coursework": "Relevant Coursework",
        "coursework": "Relevant Coursework",
        "online courses": "Courses",
        "professional training": "Training",
        "training": "Training",

        "achievements": "Achievements",
        "awards": "Achievements",
        "publications": "Publications",
        "languages": "Languages",
        "interests": "Interests",
        "volunteering": "Volunteer Experience",
        "volunteer experience": "Volunteer Experience",
        "additional information": "Additional Information",
        "personal details": "Personal Details",
        "references": "References",
    }

    def normalize_heading(line):
        value = re.sub(r"^[#\s]+|[#\s:]+$", "", line).strip().lower()
        value = re.sub(r"\s+", " ", value)
        return section_aliases.get(value)

    email_pattern = (
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"
    )
    url_pattern = r"(?:https?://|www\.)[^\s<>]+"

    email_match = re.search(text, email_pattern, re.IGNORECASE)
    urls_in_document = re.findall(
        url_pattern, text, re.IGNORECASE
    )

    # Extract contact information from the resume header only.
    # Links in project/certification sections remain with those items.
    first_heading_index = next(
        (
            i for i, line in enumerate(lines)
            if line and normalize_heading(line)
        ),
        len(lines),
    )
    header_lines = [
        line for line in lines[:first_heading_index] if line
    ]
    header_text = "\n".join(header_lines)

    header_email = re.search(
        email_pattern, header_text, re.IGNORECASE
    )

    header_urls = list(dict.fromkeys(
        re.findall(url_pattern, header_text, re.IGNORECASE)
    ))

    phone_candidates = re.findall(
        r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)",
        header_text,
    )
    phone = next(
        (
            value.strip()
            for value in phone_candidates
            if len(re.sub(r"\D", "", value)) >= 8
        ),
        None,
    )

    name = None
    for line in header_lines[:8]:
        cleaned = line.strip()

        if (
            not normalize_heading(cleaned)
            and not re.search(email_pattern, cleaned, re.I)
            and not re.search(url_pattern, cleaned, re.I)
            and not re.search(r"\d{5,}", cleaned)
            and len(cleaned.split()) <= 6
            and not re.search(
                r"\b(resume|curriculum vitae|portfolio)\b",
                cleaned,
                re.I,
            )
        ):
            name = cleaned
            break

    contact = {
        "name": name,
        "email": (
            header_email.group(0)
            if header_email
            else None
        ),
        "phone": phone,
        "links": header_urls,
    }

    sections = []
    unclassified = []
    current_section = None
    current_item = ""

    def finish_item():
        nonlocal current_item, current_section

        value = re.sub(
            r"\s+", " ", current_item
        ).strip(" \t-•")

        if value:
            if current_section is not None:
                current_section["items"].append(value)
            else:
                unclassified.append(value)

        current_item = ""

    def looks_like_list_item(line):
        return bool(re.match(
            r"^\s*(?:[•●▪◦*-]\s+|\d+[.)]\s+)",
            line,
        ))

    def remove_list_marker(line):
        return re.sub(
            r"^\s*(?:[•●▪◦*-]\s+|\d+[.)]\s+)",
            "",
            line,
        ).strip()

    # Lines in these sections are likely to represent separate entries.
    entry_sections = {
        "Projects",
        "Certifications",
        "Certifications & Courses",
        "Courses",
        "Relevant Coursework",
        "Training",
        "Education",
        "Work Experience",
        "Internships",
        "Achievements",
        "Publications",
        "Volunteer Experience",
    }

    for line in lines:
        if not line:
            # A blank line can indicate a new project or entry.
            if current_section is not None:
                finish_item()
            continue

        heading = normalize_heading(line)

        if heading:
            finish_item()
            current_section = {
                "title": heading,
                "items": [],
            }
            sections.append(current_section)
            continue

        # Skip duplicate header contact lines only before the first
        # recognized section. Do not discard URLs in project details.
        if current_section is None:
            if (
                line == name
                or re.search(email_pattern, line, re.I)
                or re.fullmatch(url_pattern, line, re.I)
            ):
                continue

        # Explicit bullets/numbers should become separate entries.
        if looks_like_list_item(line):
            finish_item()
            current_item = remove_list_marker(line)
            continue

        # In entry-based sections, a short title-like line can mark
        # a new entry. Preserve its following description with it.
        if (
            current_section is not None
            and current_section["title"] in entry_sections
            and current_item
            and len(line.split()) <= 10
            and not line.endswith((",", ";", ":", "and", "or"))
            and not re.match(
                r"^(https?://|www\.|[-•])",
                line,
                re.I,
            )
        ):
            # Only split when the existing item looks like a completed
            # entry or a link. Avoid splitting ordinary wrapped text.
            previous = current_item.strip()
            previous_has_link = bool(
                re.search(url_pattern, previous, re.I)
            )
            previous_looks_titled = (
                len(previous.split()) <= 10
                and not previous.endswith((",", ";", ":", "and", "or"))
            )

            if previous_has_link or previous_looks_titled:
                finish_item()

        if (
            current_section is not None
            and current_section["title"] == "Projects"
            and current_item
        ):
            # Treat a short standalone line as a new project title
            # when the previous item already looks like a title.
            previous = current_item.strip()
            previous_is_title = (
                len(previous.split()) <= 10
                and not re.search(
                    r"https?://|www\.|GitHub:|Demo:|Certificate:",
                    previous,
                    re.IGNORECASE,
                )
                and not previous.endswith((".", ",", ";", ":"))
            )

            new_line_looks_like_title = (
                len(line.split()) <= 10
                and not line.endswith((".", ",", ";", ":"))
                and not re.search(
                    r"https?://|www\.|GitHub:|Demo:|Certificate:",
                    line,
                    re.IGNORECASE,
                )
                and not re.match(
                    r"^(built|developed|created|designed|implemented|using|responsible|worked|integrated|deployed)\b",
                    line,
                    re.IGNORECASE,
                )
            )

            if previous_is_title and new_line_looks_like_title:
                finish_item()

        if current_item:
            current_item += " " + line
        else:
            current_item = line

    finish_item()

    # Clean entries and group project titles with their descriptions and links.
    for section in sections:
        section["items"] = [
            item.strip()
            for item in section["items"]
            if item and item.strip()
        ]

    return {
        "contact": contact,
        "sections": sections,
        "unclassified": unclassified,
    }
