"""Candidate evidence manifest builder implementing the paper-mandated extraction pipeline."""

import re
from typing import Any

from cci.domain.contracts import CandidateManifest
from cci.intake.canonicalizer import classify_url, deduplicate_urls, is_false_positive_link, normalize_url
from cci.intake.parsers import ParsedDocument


def extract_url_contexts(text: str) -> dict[str, str]:
    """Extracts contextual category labels for URLs appearing in resume text.

    Detects candidate declarations like 'Portfolio:', 'Personal Website:', 'Website:', etc.
    """
    contexts: dict[str, str] = {}
    if not text:
        return contexts

    portfolio_label_pattern = re.compile(
        r'(?i)\b(?:portfolio(?:\s*website|\s*link|\s*page)?|personal\s*website|personal\s*site|personal\s*page|website|web|site)\b[:\s|-]+'
    )

    for line in text.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue
        if portfolio_label_pattern.search(line_clean):
            from cci.intake.parsers.pdf import URL_REGEX
            for m in URL_REGEX.finditer(line_clean):
                norm = normalize_url(m.group(0))
                if norm and not is_false_positive_link(norm):
                    contexts[norm] = 'portfolio'

    return contexts

EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Standard resume section headers
SECTION_PATTERNS = {
    "skills": re.compile(
        r"^(?:(?:technical|key|core|professional|relevant|hard|software|it|computer|domain)\s+)?skills?(?:\s+(?:&|and)\s+(?:expertise|tools|abilities|competencies))?\b"
        r"|^(?:core|key|technical)\s+competencies\b"
        r"|^competencies\b"
        r"|^(?:core|key|technical|emerging)\s+technologies\b"
        r"|^technologies(?:\s+(?:&|and)\s+(?:tools|frameworks))?\b"
        r"|^(?:tools\s+(?:&|and)\s+technologies|technologies\s+(?:&|and)\s+tools)\b"
        r"|^(?:programming\s+)?languages(?:\s+(?:&|and)\s+(?:frameworks|technologies|tools|libraries))?\b"
        r"|^(?:tech(?:nical)?\s+)?(?:stack|toolkit)\b"
        r"|^(?:technical\s+)?proficiencies\b"
        r"|^skill\s*sets?\b"
        r"|^(?:areas\s+of\s+)?expertise\b",
        re.IGNORECASE,
    ),
    "projects": re.compile(
        r"^(?:personal\s+|academic\s+|selected\s+)?projects\b", re.IGNORECASE
    ),
    "experience": re.compile(
        r"^(?:work\s+|professional\s+)?experience\b|^employment\b|^history\b",
        re.IGNORECASE,
    ),
    "education": re.compile(r"^education\b|^academics\b", re.IGNORECASE),
    "summary": re.compile(r"^(?:(?:professional|personal|career)\s+)?(?:summary|profile|objective)\b", re.IGNORECASE),
    "certifications": re.compile(r"^(?:certifications?|certificates?|credentials|licenses)(?:\s|$)", re.IGNORECASE),
    "achievements": re.compile(r"^(?:achievements?|awards?|honors?|publications?|volunteering|languages|interests)(?:\s|$)", re.IGNORECASE),
}


def extract_candidate_name(text: str) -> str:
    """Extracts candidate display name from top header lines of CV."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return "Unknown Candidate"

    # Take first non-empty line that does not look like an email, phone, or URL
    for line in lines[:15]:
        if any(pattern.match(line) for pattern in SECTION_PATTERNS.values()):
            # Do not use section content as a person's identity.
            break
        if EMAIL_REGEX.search(line):
            continue
        if re.search(r"https?://|www\.|\+?\d[\d\s-]{7,}", line):
            continue
        # Clean potential title or label noise
        clean_name = re.sub(
            r"^(resume|curriculum vitae|cv)[:\s-]*", "", line, flags=re.IGNORECASE
        ).strip()
        if len(clean_name) > 1 and len(clean_name.split()) <= 5:
            return clean_name

    return 'Unknown Candidate'


def extract_candidate_email(text: str) -> str | None:
    """Extracts primary contact email."""
    match = EMAIL_REGEX.search(text)
    if match:
        return match.group(0).lower()
    return None


# Subcategories commonly found inside a skills section that shouldn't break out of skills
SKILLS_SUBCATEGORY_PATTERN = re.compile(
    r"^(?:[•\-\*·●▪■◦‣⁃\s]*)(?:(?:programming\s+)?languages?|frameworks?(?:\s+(?:&|and)\s+libraries)?|developer\s+tools|databases?|cloud(?:\s+(?:&|and)\s+devops)?|platforms?|technologies|tools|libraries|devops|backend|frontend|fullstack|methodologies|web\s+technologies|version\s+control|operating\s+systems|core|others?)\s*:\s*(.+)$",
    re.IGNORECASE,
)

INLINE_SKILLS_PATTERN = re.compile(
    r"^(?:[•\-\*·●▪■◦‣⁃#|~0-9.\s]*)(?:technical\s+|key\s+|core\s+|software\s+)?(?:skills?|technologies|tools?|tech\s+stack|competencies|proficiencies|languages)\s*:\s*(.+)$",
    re.IGNORECASE,
)

COMMON_TECH_CANONICAL = [
    ('Python', r'\bpython\b'),
    ('TypeScript', r'\btypescript\b'),
    ('JavaScript', r'\bjavascript\b'),
    ('Go', r'\b(?:golang|go)\b(?!\s+(?:to|ahead|back|on|for))'),
    ('Rust', r'\brust\b'),
    ('Java', r'\bjava\b(?!script)'),
    ('C++', r'\bc\+\+\b'),
    ('C#', r'\bc#\b'),
    ('SQL', r'\bsql\b'),
    ('PostgreSQL', r'\b(?:postgresql|postgres)\b'),
    ('MySQL', r'\bmysql\b'),
    ('MongoDB', r'\bmongodb\b'),
    ('Redis', r'\bredis\b'),
    ('React', r'\breact(?:\.js)?\b'),
    ('Next.js', r'\bnext(?:\.js)?\b'),
    ('Node.js', r'\bnode(?:\.js)?\b'),
    ('Vue.js', r'\bvue(?:\.js)?\b'),
    ('Angular', r'\bangular\b'),
    ('FastAPI', r'\bfastapi\b'),
    ('Flask', r'\bflask\b'),
    ('Django', r'\bdjango\b'),
    ('Spring Boot', r'\bspring\s+boot\b'),
    ('Docker', r'\bdocker\b'),
    ('Kubernetes', r'\b(?:kubernetes|k8s)\b'),
    ('AWS', r'\baws\b|\bamazon\s+web\s+services\b'),
    ('GCP', r'\bgcp\b|\bgoogle\s+cloud\b'),
    ('Azure', r'\bazure\b'),
    ('Git', r'\bgit\b(?!hub|lab)'),
    ('GraphQL', r'\bgraphql\b'),
    ('Kafka', r'\bkafka\b'),
    ('Terraform', r'\bterraform\b'),
    ('PyTorch', r'\bpytorch\b'),
    ('TensorFlow', r'\btensorflow\b'),
    ('Linux', r'\blinux\b'),
    ('Tailwind CSS', r'\btailwind(?:\s+css)?\b'),
    ('HTML', r'\bhtml5?\b'),
    ('CSS', r'\bcss3?\b'),
]


def fallback_extract_tech(text: str) -> list[str]:
    """Fallback extractor for technical skills from narrative CV text when no skills section exists."""
    found: list[str] = []
    for name, pattern in COMMON_TECH_CANONICAL:
        if re.search(pattern, text, re.IGNORECASE):
            found.append(name)
    return found


def segment_sections(text: str) -> dict[str, list[str]]:
    """Segments resume text into standard sections based on detected headings."""
    sections: dict[str, list[str]] = {
        "header": [],
        "skills": [],
        "projects": [],
        "experience": [],
        "education": [],
        "other": [],
        "summary": [],
        "certifications": [],
        "achievements": [],
    }

    current_section = "header"
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    for line in lines:
        clean_header = re.sub(r"^[•\-\*·●▪■◦‣⁃#|>~0-9.\s]+", "", line).strip()
        clean_title = re.sub(r"[:\-\–\—\s|]+$", "", clean_header).strip()

        # Retain subcategory lines inside skills (e.g. "Languages: Python, Go")
        if current_section == "skills" and SKILLS_SUBCATEGORY_PATTERN.match(line):
            sections["skills"].append(line)
            continue

        matched_section = None
        has_inline_content = ":" in clean_header and len(clean_header.split(":", 1)[1].strip()) > 0

        if clean_title and not has_inline_content:
            words = clean_title.split()
            if len(words) <= 5:
                for sec_name, pattern in SECTION_PATTERNS.items():
                    if pattern.match(clean_title):
                        matched_section = sec_name
                        break

        if matched_section:
            current_section = matched_section
        else:
            inline_match = INLINE_SKILLS_PATTERN.match(line)
            if inline_match and current_section != "skills":
                current_section = "skills"
                sections["skills"].append(line)
            else:
                sections[current_section].append(line)

    return sections


def extract_skills_from_section(skill_lines: list[str]) -> list[str]:
    """Extracts normalized technical skill tokens from skills section."""
    skills = []
    category_pattern = re.compile(
        r'^(?:[•\-\*·●▪■◦‣⁃\s]*)(?:(?:programming\s+)?languages?|frameworks?(?:\s+(?:&|and)\s+libraries)?|developer\s+tools|databases?|cloud(?:\s+(?:&|and)\s+devops)?|platforms?|technologies|tools|libraries|devops|backend|frontend|fullstack|methodologies|web\s+technologies|version\s+control|operating\s+systems|core|others?)\s*:\s*',
        re.IGNORECASE,
    )

    for line in skill_lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        line_clean = re.sub(r'^[•\-\*·●▪■◦‣⁃\s]+', '', line_clean)
        line_clean = category_pattern.sub('', line_clean)
        line_clean = re.sub(r'^[A-Za-z &/+-]+:\s*', '', line_clean)

        parts = re.split(r'(?:[,•·●▪■◦‣⁃|;\t]+|\s+[/]\s+)(?![^()]*\))', line_clean)
        for part in parts:
            clean = part.strip()
            clean = re.sub(r'^[•\-\*·●▪■◦‣⁃\s]+', '', clean)
            clean = re.sub(r'[;,.]+$', '', clean).strip()
            clean = re.sub(r'^[A-Za-z\s]+:\s*', '', clean).strip()

            if clean.lower() in {'etc', 'etc.', 'and', '&', 'various', 'others', 'proficient in', 'experience with'}:
                continue

            if 1 <= len(clean) <= 80 and not re.match(r'^\d+$', clean) and len(clean.split()) <= 6:
                if clean not in skills:
                    skills.append(clean)
    return skills


def extract_project_claims(project_lines: list[str]) -> list[dict[str, Any]]:
    """Groups project lines into structured project claim records."""
    claims: list[dict[str, Any]] = []
    current_proj: dict[str, Any] | None = None

    for line in project_lines:
        # Project titles are typically short or contain bullet indicators
        has_date = bool(re.search(r'\b(?:19|20)\d{2}\b|\bPresent\b', line))
        title = not re.search(r'https?://|github\.com|\s\|\s|^(?:Founder|Role|Contributor)\b', line, re.I) and not line.startswith(('-', '*', '•'))
        if title and (('\t' in line and has_date) or (len(line.split()) <= 6 and not line.endswith('.'))):
            if current_proj:
                claims.append(current_proj)
            current_proj = {
                "title": line,
                "description": "",
                "technologies": [],
            }
        else:
            if current_proj is not None:
                if current_proj["description"]:
                    current_proj["description"] += " " + line
                else:
                    current_proj["description"] = line

    if current_proj:
        claims.append(current_proj)

    return claims


def build_candidate_manifest(
    document: ParsedDocument,
    display_name_override: str | None = None,
) -> CandidateManifest:
    """Builds a verified CandidateManifest following the paper-mandated order:

    1. Embedded hyperlinks
    2. Visible URLs
    3. Deterministic URL/platform classification
    4. Structured extraction & normalization
    5. Validation
    6. Canonicalization / deduplication
    """
    # 1 & 2. Gather URLs: embedded first, then visible, filtering out degree false positives
    raw_urls = [u for u in (list(document.embedded_urls) + list(document.visible_urls)) if not is_false_positive_link(u)]

    # 3 & 6. Canonicalize and deduplicate
    canonical_urls = deduplicate_urls(raw_urls)
    url_contexts = extract_url_contexts(document.raw_text)

    # Classify URLs strictly by platform
    github_urls: list[str] = []
    linkedin_urls: list[str] = []
    coding_profile_urls: list[str] = []
    credential_urls: list[str] = []
    deployment_urls: list[str] = []
    portfolio_urls: list[str] = []
    shared_document_urls: list[str] = []
    project_links: list[str] = []
    public_links: list[str] = []

    for url in canonical_urls:
        if is_false_positive_link(url):
            continue
        ctx = url_contexts.get(url)
        cat = classify_url(url, context=ctx)
        if cat == "github":
            github_urls.append(url)
        elif cat == "linkedin":
            linkedin_urls.append(url)
        elif cat == "coding_profile":
            coding_profile_urls.append(url)
        elif cat == "credential":
            credential_urls.append(url)
        elif cat == "deployment":
            deployment_urls.append(url)
            if ctx == "portfolio" and url not in portfolio_urls:
                portfolio_urls.append(url)
        elif cat == "portfolio":
            portfolio_urls.append(url)
        elif cat == "cloud_storage":
            shared_document_urls.append(url)
        elif cat == "project":
            project_links.append(url)
        else:
            if ctx == "portfolio":
                portfolio_urls.append(url)
            else:
                public_links.append(url)

    # 4. Structured extraction from parsed text
    name = display_name_override or extract_candidate_name(document.raw_text)
    email = extract_candidate_email(document.raw_text)

    sections = segment_sections(document.raw_text)
    claimed_skills = extract_skills_from_section(sections.get("skills", []))

    # Fallback 1: If skills section yielded nothing, scan for subcategory lines across all text
    if not claimed_skills:
        fallback_lines = []
        for line in document.raw_text.splitlines():
            clean_l = line.strip()
            if not clean_l:
                continue
            if SKILLS_SUBCATEGORY_PATTERN.match(clean_l) or INLINE_SKILLS_PATTERN.match(clean_l):
                fallback_lines.append(clean_l)
        if fallback_lines:
            claimed_skills = extract_skills_from_section(fallback_lines)

    # Fallback 2: Narrative/paragraph resume without explicit skills headers
    if not claimed_skills:
        claimed_skills = fallback_extract_tech(document.raw_text)

    project_claims = extract_project_claims(sections.get("projects", []))
    experience_claims = [{"text": line} for line in sections.get("experience", [])[:10]]

    # 5. Build and validate against frozen domain contract
    return CandidateManifest(
        display_name=name,
        email=email,
        picture=document.picture,
        github_urls=github_urls,
        project_links=project_links,
        deployment_urls=deployment_urls,
        portfolio_urls=portfolio_urls,
        coding_profile_urls=coding_profile_urls,
        credential_urls=credential_urls,
        linkedin_urls=linkedin_urls,
        shared_document_urls=shared_document_urls,
        public_links=public_links,
        claimed_skills=claimed_skills,
        project_claims=project_claims,
        experience_claims=experience_claims,
    )
