from typing import Annotated, Any
from urllib.parse import urlsplit
from uuid import UUID, uuid4
import re

from pydantic import BaseModel, Field, field_validator, model_validator
from cci.domain.contracts import CandidateManifest
from cci.domain.enums import CanonicalRole

MAX_UPLOAD = 3 * 1024 * 1024
MAX_REPOSITORIES = 6
MAX_FILES = 100
MAX_RECENT_COMMITS = 30
MAX_ARTIFACT_ATTRIBUTION_PATHS = 24
MAX_FILE_BYTES = 128 * 1024
MAX_ARCHIVE_BYTES = 8 * 1024 * 1024
MAX_EXPANDED_BYTES = 24 * 1024 * 1024
MAX_SECONDS = 45
MAX_ANALYSIS_REQUEST_BYTES = 512 * 1024
MAX_LEAN_REQUEST_BYTES = 512 * 1024
ShortText = Annotated[str, Field(max_length=2048)]


def github_parts(url: str) -> tuple[str, str | None]:
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc.lower() not in {'github.com', 'www.github.com'} or parsed.query or parsed.fragment:
        raise ValueError('Use an HTTPS github.com profile or repository URL without query parameters.')
    parts = parsed.path.strip('/').split('/')
    if len(parts) not in (1, 2) or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})', parts[0]):
        raise ValueError('Expected a GitHub account or owner/repository URL.')
    if parts[0].lower() in {'search', 'topics', 'orgs', 'settings', 'login', 'marketplace', 'collections', 'features', 'explore'}:
        raise ValueError('Supply a candidate account or repository, not a GitHub navigation page.')
    repo = parts[1].removesuffix('.git') if len(parts) == 2 else None
    if repo is not None and (not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', repo) or repo in {'.', '..'}):
        raise ValueError('Invalid repository name.')
    return parts[0], repo


class ResumeReview(BaseModel):
    sections: dict[str, list[str]] = Field(default_factory=dict)
    learning_skills: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    extraction_method: str = 'deterministic_document_structure'


class ResumeIntake(BaseModel):
    analysis_run_id: UUID = Field(default_factory=uuid4)
    candidate_id: UUID = Field(default_factory=uuid4)
    manifest: CandidateManifest
    document_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    filename: str = Field(max_length=240)
    text_preview: str = Field(default='', max_length=12000)
    warnings: list[str] = Field(default_factory=list, max_length=20)
    storage: str = 'request_only'
    resume_review: ResumeReview = Field(default_factory=ResumeReview)


class LeanAnalysisRequest(BaseModel):
    analysis_run_id: UUID
    role: CanonicalRole = CanonicalRole.BACKEND
    jd_text: str = Field(default='', max_length=20000)
    jd_edits: str | None = Field(default=None, max_length=20000)
    github_urls: list[ShortText] = Field(default_factory=list, max_length=20)
    user_reviewed_urls: list[ShortText] | None = Field(default=None, max_length=100)
    external_urls: list[ShortText] | None = Field(default=None, max_length=100)
    github_identity: str = Field(default='', pattern=r'^(?:[A-Za-z0-9][A-Za-z0-9-]{0,38})?$')
    optional_settings: dict[str, Any] = Field(default_factory=dict)

    @field_validator('github_urls')
    @classmethod
    def validate_urls(cls, urls):
        result = []
        for url in urls:
            owner, repo = github_parts(url)
            normalized = f'https://github.com/{owner}' + (f'/{repo}' if repo else '')
            if normalized.lower() not in {s.lower() for s in result}:
                result.append(normalized)
        return result

    @model_validator(mode='after')
    def normalize_fields(self):
        if self.jd_edits and not self.jd_text:
            self.jd_text = self.jd_edits
        if self.user_reviewed_urls is not None and self.external_urls is None:
            self.external_urls = self.user_reviewed_urls
        return self


class LiveAnalysisRequest(BaseModel):
    intake: ResumeIntake | None = None
    analysis_run_id: UUID | None = None
    role: CanonicalRole = CanonicalRole.BACKEND
    jd_text: str = Field(default='', max_length=20000)
    jd_edits: str | None = Field(default=None, max_length=20000)
    github_urls: list[ShortText] = Field(default_factory=list, max_length=20)
    user_reviewed_urls: list[ShortText] | None = Field(default=None, max_length=100)
    external_urls: list[ShortText] | None = Field(default=None, max_length=100)
    github_identity: str = Field(default='', pattern=r'^(?:[A-Za-z0-9][A-Za-z0-9-]{0,38})?$')
    optional_settings: dict[str, Any] = Field(default_factory=dict)

    @field_validator('github_urls')
    @classmethod
    def validate_urls(cls, urls):
        result = []
        for url in urls:
            owner, repo = github_parts(url)
            normalized = f'https://github.com/{owner}' + (f'/{repo}' if repo else '')
            if normalized.lower() not in {s.lower() for s in result}:
                result.append(normalized)
        return result

    @model_validator(mode='after')
    def validate_and_normalize(self):
        if not self.intake and not self.analysis_run_id:
            raise ValueError('Either intake or analysis_run_id must be provided.')
        if self.jd_edits and not self.jd_text:
            self.jd_text = self.jd_edits
        if self.user_reviewed_urls is not None and self.external_urls is None:
            self.external_urls = self.user_reviewed_urls
        return self
