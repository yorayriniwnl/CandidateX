"""Deterministic URL normalization, deduplication, and platform classification."""

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "source",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
}

COMMON_TLDS = (
    r"com|org|net|edu|gov|io|ai|dev|app|in|me|co|tech|xyz|site|online|cloud|space|live|"
    r"design|pro|page|link|store|agency|digital|studio|info|biz|cc|tv|gg|sh|to|so|ee|ly|"
    r"im|eu|uk|us|ca|de|fr|jp|au|sg|ch|nl|se|no|es|it|co\.uk|org\.uk"
)

# Academic degree abbreviations, education acronyms, and common terms falsely matching TLDs
DEGREE_AND_ACADEMIC_TERMS = {
    "b.tech", "m.tech", "d.tech", "btech", "mtech",
    "b.e", "m.e",
    "b.com", "m.com",
    "b.sc", "m.sc", "d.sc",
    "b.ca", "m.ca",
    "b.arch", "m.arch",
    "b.des", "m.des",
    "b.ed", "m.ed",
    "b.pharm", "m.pharm", "d.pharm",
    "b.a", "m.a",
    "b.s", "m.s",
    "b.b.a", "m.b.a",
    "ph.d", "d.phil",
    "l.l.b", "l.l.m",
    "m.b.b.s", "m.d",
    "e.g", "i.e", "etc", "vs",
}


def is_false_positive_link(url: str) -> bool:
    """Detects academic degree abbreviations or common non-URL terms mistakenly extracted as links."""
    if not url or not isinstance(url, str):
        return True
    cleaned = url.strip().lower()
    cleaned = re.sub(r'^[a-z]+://', '', cleaned)
    cleaned = re.sub(r'^www\.', '', cleaned)
    # Strip port, path, query, and trailing dots/punctuation
    host_part = cleaned.split('/')[0].split('?')[0].split('#')[0].rstrip('.')
    if host_part in DEGREE_AND_ACADEMIC_TERMS:
        return True
    if re.match(r'^(?:b|m|d)\.(?:tech|com|sc|ca|e|arch|des|ed|pharm|a|s)$', host_part):
        return True
    return False


PLATFORM_PATTERNS = {
    "github": re.compile(r"^https?://(www\.)?github\.com(/.*)?$", re.IGNORECASE),
    "linkedin": re.compile(
        r"^https?://([a-z]{2,3}\.)?linkedin\.com/(?:in|pub|profile)(/.*)?$", re.IGNORECASE
    ),
    "credential": re.compile(
        r"^https?://(?:www\.)?(?:credly\.com|coursera\.org/(?:verify|account/accomplishments)|udacity\.com/certificate|badges\.parchment\.com|hackerrank\.com/certificates|freecodecamp\.org/certification|linkedin\.com/learning/certificates|udemy\.com/certificate|credential\.net|trailhead\.salesforce\.com|learn\.microsoft\.com)(?:/.*)?$", re.IGNORECASE,
    ),
    "coding_profile": re.compile(
        r"^https?://(www\.)?(leetcode\.com|kaggle\.com|hackerrank\.com|codeforces\.com|topcoder\.com|codechef\.com|geeksforgeeks\.org|hackerearth\.com|codewars\.com|spoj\.com|atcoder\.jp)(/.*)?$",
        re.IGNORECASE,
    ),
    "deployment": re.compile(
        r"^https?://([a-zA-Z0-9-]+\.)*(vercel\.app|netlify\.app|herokuapp\.com|fly\.dev|railway\.app|render\.com|pages\.dev|streamlit\.app|hf\.space|web\.app|firebaseapp\.com|surge\.sh|glitch\.me|workers\.dev|azurewebsites\.net|ngrok-free\.app|ngrok\.io)(/.*)?$",
        re.IGNORECASE,
    ),
    "cloud_storage": re.compile(
        r"^https?://(?:www\.)?(?:drive\.google\.com|docs\.google\.com|dropbox\.com|dl\.dropboxusercontent\.com|onedrive\.live\.com|1drv\.ms|[a-zA-Z0-9-]+\.sharepoint\.com|box\.com|app\.box\.com|icloud\.com|notion\.so|notion\.site)(?:/.*)?$",
        re.IGNORECASE,
    ),
    "portfolio": re.compile(
        r"^https?://(?:[a-zA-Z0-9-]+\.)*(?:bento\.me|linktr\.ee|peerlist\.io|polywork\.com|contra\.com|readcv\.com|dev\.to|medium\.com|hashnode\.dev|hashnode\.io|substack\.com|carrd\.co|about\.me|webflow\.io|framer\.website|framer\.app|framer\.ai|layers\.to|dribbble\.com|behance\.net)(?:/.*)?$|^https?://[a-zA-Z0-9-]+\.(?:github|gitlab)\.io(?:/.*)?$",
        re.IGNORECASE,
    ),
}


def normalize_url(raw_url: str) -> str | None:
    """Canonicalizes a URL by normalizing scheme, host, stripping tracking params, and formatting SSH git URLs."""
    if not raw_url or not isinstance(raw_url, str):
        return None

    cleaned = raw_url.strip()
    # Strip wrapping brackets and punctuation
    cleaned = re.sub(r'^[<(\[\'\"`]+', '', cleaned)
    cleaned = re.sub(r'[>)\],;:\'\"`.!?]+$', '', cleaned).strip()
    if not cleaned:
        return None

    # Immediate rejection of degree abbreviations or common non-URL terms
    if is_false_positive_link(cleaned):
        return None

    # Convert git SSH URLs (git@github.com:user/repo.git -> https://github.com/user/repo)
    ssh_match = re.match(r"^git@([a-zA-Z0-9.-]+):([a-zA-Z0-9._/-]+?)(\.git)?$", cleaned)
    if ssh_match:
        host, path, _ = ssh_match.groups()
        return f"https://{host.lower()}/{path.strip('/')}"

    # Add default https scheme if missing but looks like a web address.
    # Note: scheme-less URLs require at least 2 characters before the TLD to prevent degree false positives like B.Tech.
    if not re.match(r"^[a-zA-Z]+://", cleaned):
        if (
            cleaned.startswith("github.com")
            or cleaned.startswith("linkedin.com")
            or cleaned.startswith("www.")
            or re.match(rf'^[A-Za-z0-9][A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:{COMMON_TLDS})(?:[/?#]|$)', cleaned, re.IGNORECASE)
        ):
            cleaned = "https://" + cleaned
        else:
            return None

    try:
        parsed = urlparse(cleaned)
    except Exception:
        return None

    if parsed.scheme.lower() not in ("http", "https"):
        return None

    if not parsed.netloc:
        return None

    # Lowercase netloc and scheme
    netloc = parsed.netloc.lower()
    # Strip standard default ports
    if netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Verify netloc itself is not a false positive degree abbreviation
    if is_false_positive_link(netloc):
        return None

    # Clean path: strip .git suffix, reduce multiple slashes, strip trailing slash and residual punctuation
    path = parsed.path
    path = path.removesuffix(".git")
    path = re.sub(r"/+", "/", path).rstrip("/")
    path = re.sub(r'[>)\],;:\'\"`.!?]+$', '', path)

    # Strip marketing and tracking query parameters
    if parsed.query:
        query_pairs = parse_qsl(parsed.query, keep_blank_values=False)
        cleaned_pairs = [
            (k, v) for k, v in query_pairs if k.lower() not in TRACKING_PARAMS
        ]
        query = urlencode(cleaned_pairs)
    else:
        query = ""

    # Reconstruct canonical URL (strip fragment for deduplication)
    canonical = urlunparse((parsed.scheme.lower(), netloc, path, "", query, ""))
    return canonical


def deduplicate_urls(urls: list[str]) -> list[str]:
    """Normalizes and deduplicates a list of URLs, preserving order."""
    seen: set[str] = set()
    result: list[str] = []

    for u in urls:
        norm = normalize_url(u)
        if norm and norm not in seen:
            seen.add(norm)
            result.append(norm)

    return result


def classify_url(url: str, context: str | None = None) -> str:
    """Classifies a canonical URL into one of:
    github, linkedin, coding_profile, credential, deployment, portfolio, cloud_storage, project, public_link
    """
    if is_false_positive_link(url):
        return "public_link"

    for category, pattern in PLATFORM_PATTERNS.items():
        if pattern.match(url):
            return category

    # If context explicitly identified this as candidate portfolio/website
    if context == "portfolio":
        # Don't let portfolio context override recognized code hostings or certificates
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if not any(git_host in domain for git_host in ("gitlab.com", "bitbucket.org", "codeberg.org", "sourceforge.net")):
            return "portfolio"

    # Fallback heuristics
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()

    if re.search(r'/(?:certificates?|certifications?|credentials?|verify|badges)(?:[/. -]|$)', path, re.I):
        return 'credential'

    # Cloud storage or document sharing domains
    if any(storage in domain for storage in ("drive.google", "docs.google", "dropbox", "onedrive", "1drv.ms", "sharepoint", "box.com", "icloud", "notion.so", "notion.site")):
        return "cloud_storage"

    # Git repository & package hostings
    if any(git_host in domain for git_host in ("gitlab.com", "bitbucket.org", "codeberg.org", "sourceforge.net", "huggingface.co", "npmjs.com", "pypi.org", "crates.io", "hub.docker.com")):
        return "project"

    # Specific code or project indicators in path
    if re.search(r'/(?:projects?|repos?|code|apps?|models?|datasets?|packages?)(?:[/. -]|$)', path, re.I):
        return "project"

    # Developer portfolio pages (github.io, gitlab.io)
    if domain.endswith((".github.io", ".gitlab.io")):
        return "portfolio"

    # Portfolio / personal domain indicator
    if (
        any(term in domain for term in ("portfolio", "readcv", "bento.me", "linktr.ee", "substack", "medium.com", "dev.to", "hashnode", "carrd.co", "about.me"))
        or domain.endswith((".me", ".tech", ".bio", ".page", ".site", ".design", ".dev"))
        or domain.startswith(("portfolio.", "me.", "dev.", "blog."))
        or re.search(r'/(?:portfolio|work|showcase)(?:[/. -]|$)', path, re.I)
        or context == "portfolio"
    ):
        return "portfolio"

    return "public_link"
