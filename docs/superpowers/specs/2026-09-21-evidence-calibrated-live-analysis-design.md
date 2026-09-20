# Evidence-Calibrated Live Analysis Design

## Goal

Make the upload-to-result workflow more accurate and sensible by improving
resume extraction, separating shallow declarations from hands-on evidence,
discounting correlated observations, smoothing small ownership samples, and
showing explicit job-requirement matches and gaps.

## User outcome

After a resume is uploaded and the candidate-selected sources are inspected,
the result should answer four separate questions:

1. What did the resume actually declare?
2. What was observed in the supplied public artifacts?
3. How much of each observation can reasonably be attributed to the candidate?
4. Which job requirements are evidenced, only indirectly supported, or still
   unknown?

The system must remain decision support for a human interviewer. It must not
turn missing evidence into a negative capability score or present a numeric
score as a hiring decision.

## Constraints and invariants

- Candidate code is never executed, built, installed, or tested.
- Only resume-supplied or explicitly user-selected public sources are fetched.
- Uploaded documents and live analysis remain request-scoped.
- Missing, unavailable, uncredited, and unresolved evidence remains UNKNOWN.
- Existing RCI, evidence coverage, provenance, and functional-rescore behavior
  remain backward compatible.
- No external LLM call is added. All new decisions are deterministic and
  inspectable from source text, artifact paths, revisions, and confidence
  factors.
- Existing response fields remain valid; new result fields are additive.

## Design

### 1. Resume normalization

Extend deterministic intake with normalized line handling and a controlled
technology matcher:

- accept common numbered, colon-terminated, and aliased section headings;
- reject obvious job-title and document-label lines as candidate names;
- preserve the candidate's display spelling while deduplicating equivalent
  skills such as `React.js` and `React`;
- use the same exact-token technology matcher for resume skills, public-page
  mentions, and JD terms, preventing false positives such as `Java` matching
  `JavaScript` and allowing punctuation-heavy terms such as `C++` and `CI/CD`.

The parser will not infer a skill from ordinary prose. Skills remain declared
claims until artifact evidence is observed.

### 2. Evidence calibration

Add a deterministic calibration layer at live repository registration:

- classify each observation as a dependency declaration, source usage, test
  artifact, infrastructure artifact, documentation artifact, or structural
  signal;
- use conservative verification/depth factors for shallow signals and retain
  stronger factors for implementation and test evidence;
- apply a diminishing-return factor to repeated signals from the same
  repository/capability/category so ten similar files do not look like ten
  independent projects;
- preserve the original signal and add calibration metadata to provenance.

Ownership from the recent-commit sample will use an explicit small-sample
shrinkage factor. A supplied username with one matching commit will receive
some evidence of attribution, but not the same confidence as a sustained
matching history. A missing or non-matching identity remains zero attribution,
so the current unknown-capability invariant is preserved.

### 3. Requirement-level role fit

Add additive dossier models for requirement matches and a role-fit summary.
Each normalized JD requirement is classified as:

- `observed`: a positive evidence record matches the requested technology or
  capability;
- `related`: the capability is evidenced, but the exact requested technology
  was not observed;
- `unknown`: no usable evidence supports the requirement;
- `unresolved`: the JD line could not be mapped to the controlled ontology.

The summary will count mandatory/preferred requirements, list mandatory gaps,
and preserve the evidence IDs and explanation for every match. It will not
change the formal RCI denominator; it gives the interviewer a direct,
requirement-oriented interpretation alongside RCI and coverage.

### 4. Result integration

The live dossier will include `role_fit` and each live response will retain the
existing receipt, evidence, graph, and limitation data. The live report will
also expose the role-fit summary so the existing result page can surface
critical gaps without a second analysis pass.

## Error handling

- Malformed resume text continues to return a clear intake 422.
- A malformed or unsafe external URL remains a visible source receipt and does
  not abort analysis of other sources.
- Evidence calibration is fail-closed: if an observation cannot be classified,
  it receives the conservative structural-signal profile and remains visible.
- Requirement matching never manufactures a capability mapping for an
  unresolved JD line.

## Testing strategy

Add regression tests for:

- section aliases, job-title name rejection, and exact technology boundaries;
- small-sample ownership shrinkage and non-matching identity behavior;
- evidence-tier factors and diminishing returns within one repository;
- requirement statuses, mandatory-gap summaries, and additive dossier output;
- existing live upload, source failure, provenance, missingness, and graph
  invariants.

The full backend suite and the web typecheck/build will be run after the
changes. If the bundled runtime lacks a dependency, the verification report
will state the exact blocked command rather than infer success.
