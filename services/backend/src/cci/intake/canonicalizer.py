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

PLATFORM_PATTERNS = {
    "github": re.compile(r"^https?://(www\.)?github\.com(/.*)?$", re.IGNORECASE),
    "linkedin": re.compile(
        r"^https?://([a-z]{2,3}\.)?linkedin\.com/in(/.*)?$", re.IGNORECASE
    ),
    "credential": re.compile(
        r"^https?://(?:www\.)?(?:credly\.com|coursera\.org/(?:verify|account/accomplishments)|udacity\.com/certificate|badges\.parchment\.com|hackerrank\.com/certificates|freecodecamp\.org/certification|linkedin\.com/learning/certificates)(?:/.*)?$", re.IGNORECASE,
    ),
    "coding_profile": re.compile(
        r"^https?://(www\.)?(leetcode\.com|kaggle\.com|hackerrank\.com|codeforces\.com|topcoder\.com|codechef\.com)(/.*)?$",
        re.IGNORECASE,
    ),
    "deployment": re.compile(
        r"^https?://([a-zA-Z0-9-]+\.)*(vercel\.app|netlify\.app|herokuapp\.com|fly\.dev|railway\.app|render\.com|pages\.dev)(/.*)?$",
        re.IGNORECASE,
    ),
    "cloud_storage": re.compile(
        r"^https?://(?:www\.)?(?:drive\.google\.com|docs\.google\.com|dropbox\.com|dl\.dropboxusercontent\.com|onedrive\.live\.com|1drv\.ms|[a-zA-Z0-9-]+\.sharepoint\.com|box\.com|app\.box\.com|icloud\.com)(?:/.*)?$",
        re.IGNORECASE,
    ),
}


def normalize_url(raw_url: str) -> str | None:
    """Canonicalizes a URL by normalizing scheme, host, stripping tracking params, and formatting SSH git URLs."""
    if not raw_url or not isinstance(raw_url, str):
        return None

    cleaned = raw_url.strip()

    # Convert git SSH URLs (git@github.com:user/repo.git -> https://github.com/user/repo)
    ssh_match = re.match(r"^git@([a-zA-Z0-9.-]+):([a-zA-Z0-9._/-]+?)(\.git)?$", cleaned)
    if ssh_match:
        host, path, _ = ssh_match.groups()
        return f"https://{host.lower()}/{path.strip('/')}"

    # Add default https scheme if missing but looks like a web address
    if not re.match(r"^[a-zA-Z]+://", cleaned):
        if (
            cleaned.startswith("github.com")
            or cleaned.startswith("linkedin.com")
            or cleaned.startswith("www.")
            or re.match(r'^[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:com|org|net|io|dev|app|in|me|ai|edu)(?:[/?#]|$)', cleaned)
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

    # Clean path: strip .git suffix, reduce multiple slashes, strip trailing slash
    path = parsed.path
    path = path.removesuffix(".git")
    path = re.sub(r"/+", "/", path).rstrip("/")

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


def classify_url(url: str) -> str:
    """Classifies a canonical URL into one of:
    github, linkedin, coding_profile, credential, deployment, portfolio, cloud_storage, project, public_link
    """
    for category, pattern in PLATFORM_PATTERNS.items():
        if pattern.match(url):
            return category

    # Fallback heuristics
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()

    if re.search(r'/(?:certificates?|certifications?|credentials?|verify|badges)(?:[/. -]|$)', path, re.I):
        return 'credential'

    # Cloud storage or document sharing domains
    if any(storage in domain for storage in ("drive.google", "docs.google", "dropbox", "onedrive", "1drv.ms", "sharepoint", "box.com", "icloud")):
        return "cloud_storage"

    # Portfolio / personal domain indicator
    if any(term in domain for term in ("portfolio", "blog", "me.", "dev.", "site")):
        return "portfolio"

    # Git repository hostings
    if any(git_host in domain for git_host in ("gitlab.com", "bitbucket.org", "codeberg.org", "sourceforge.net")):
        return "project"

    # Specific code or project indicators in path
    if re.search(r'/(?:projects?|repos?|code|apps?)(?:[/. -]|$)', path, re.I):
        return "project"

    return "public_link"
