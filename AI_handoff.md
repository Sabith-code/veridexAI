You are taking over an existing research/project codebase.

IMPORTANT:
Before changing anything, inspect the repository thoroughly and understand the existing architecture. Do not rewrite or replace existing functionality unnecessarily.

==================================================
PROJECT CONTEXT
==================================================

I am building an Explainable/Trustworthy AI system focused on verifying factual claims made by an LLM.

The overall idea is:

USER QUERY
   ↓
LLM / ANSWER GENERATOR
   ↓
GENERATED ANSWER
   ↓
CLAIM DECOMPOSER
   ↓
INDIVIDUAL CLAIMS
   ↓
EVIDENCE RETRIEVAL / MAPPING
   ↓
CLAIM + EVIDENCE
   ↓
VALIDATOR LLM / ENSEMBLE
   ↓
SUPPORTED / CONTRADICTED / UNCERTAIN
   ↓
TRUST ENGINE
   ↓
CLAIM-LEVEL TRUST SCORES
   ↓
EXPLAINABLE HUMAN-REVIEW UI


The important research contribution is NOT simply building another chatbot or search engine.

Simplicity is being used as the underlying:
- answer generator
- web retrieval system
- source retrieval layer

My actual contribution is a separate claim-level verification/trust engine sitting on top of it.

The intended novelty is around claim-level verification, evidence mapping, and potentially ensemble agreement between validators, rather than whole-answer verification.

Do NOT assume that modifying Simplicity itself is the research contribution.

==================================================
CURRENT ARCHITECTURE
==================================================

The current architecture is approximately:

                ┌───────────────────────────┐
                │       Simplicity          │
                │                           │
User Query ────►│ Answer Generation         │
                │ + Web Search              │
                │ + Source Retrieval        │
                └─────────────┬─────────────┘
                              │
                              ▼
                    Answer + Sources
                              │
                              ▼
                  MY VERIFICATION SYSTEM
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              Claim Decomposer    Evidence Mapper
                    │                   │
                    └─────────┬─────────┘
                              ▼
                       Validator LLM
                              │
                              ▼
                         Trust Engine
                              │
                              ▼
                       Review / UI


==================================================
WHAT IS ALREADY IMPLEMENTED
==================================================

PHASE 0 — SCOPING / ARCHITECTURE
---------------------------------

Completed.

The architecture decision has been made:

- Use Simplicity as the generator + retrieval layer.
- Keep the verification/trust engine separate.
- Treat claim-level ensemble verification as a potential point of novelty.
- Do not confuse Simplicity's existing whole-answer Council mechanism with my intended claim-level verification system.

The verification system should operate on individual claims, not simply assign one confidence score to an entire generated answer.


==================================================
PHASE 1 — GENERATOR / SIMPLICITY FOUNDATION
==================================================

Completed enough for integration.

Simplicity has been cloned and successfully run as a normal web application using:

    yarn dev

The Electron desktop shell is NOT the intended integration target.

The plain web/server version is preferred because I need to integrate its output into my own Python/backend verification pipeline.

The application is generating answers successfully using a local Ollama model.

CURRENT LOCAL LLM:

    Ollama
    qwen2.5:7b

Machine:

    Windows
    16 GB RAM
    Intel Core Ultra 7
    No dedicated GPU

Ollama has been verified independently:

    ollama --version
    Ollama 0.33.2

    ollama list

shows:

    qwen2.5:7b
    4.7 GB

The model successfully responds to prompts.

The reason for moving to Ollama is that OpenRouter's free quota was being exhausted.

Do not assume OpenRouter is required.


==================================================
SIMPLICITY INTERNAL WIRE FORMAT
==================================================

I have already investigated Simplicity's output format.

IMPORTANT:

The application does NOT use ordinary JSON for the complete streamed response.

The response is newline-delimited JSON (NDJSON).

Different blocks are streamed separately.

Relevant conceptual structure:

    text blocks
        ↓
    generated answer text

    source blocks
        ↓
    evidence/source metadata


The source data includes information such as:
- title
- URL
- content
- metadata

The frontend already uses these source blocks to render citations.

This means the integration layer needs to consume the NDJSON stream and reconstruct:

    answer text
    +
    source list

The intended wrapper interface is:

    get_answer_and_sources(query)
        ->
    (text, [sources])


==================================================
IMPORTANT EXISTING SIMPLICITY KNOWLEDGE
==================================================

Relevant parts of the existing Simplicity architecture have already been inspected.

Search flow roughly involves:

    SearchAgent
       ↓
    classifier
       ↓
    query planner
       ↓
    researcher
       ↓
    SearXNG/web search
       ↓
    source findings
       ↓
    writer
       ↓
    final answer


Search findings preserve source metadata, including URLs.

The frontend has a citation pipeline that associates answer citations with source blocks.

Therefore, do not unnecessarily rebuild web retrieval or citation/source extraction from scratch.

The goal is to expose the useful backend output to my verification pipeline.


==================================================
KNOWN SIMPLICITY PROVIDER ISSUES
==================================================

There were previous issues involving:

1. Claude Code being automatically selected despite not being logged in.

Errors included:

    Claude Code error: Not logged in · Please run /login

2. OpenRouter model discovery returning HTML instead of JSON.

Error:

    Unexpected token '<', "<!DOCTYPE "... is not valid JSON

3. Provider/model persistence problems.

4. SearXNG dynamic localhost port/lifecycle problems.

Some of these have already been investigated.

DO NOT spend time fixing unrelated Electron/SearXNG/provider issues unless they prevent the current integration from working.

The immediate research goal is to get a reliable programmatic interface to:

    answer + sources


==================================================
PREVIOUS CONFIGURATION FIX
==================================================

A previous Next.js production build problem was caused by concurrent config writes.

In:

    src/lib/config/index.ts

initializeFromEnv() previously called:

    this.saveConfig();

This was changed to:

    if (process.env.NEXT_PHASE !== 'phase-production-build') {
        this.saveConfig();
    }

This fixed the production build.

DO NOT revert this change unless you have a concrete reason and can prove it is incorrect.


==================================================
WHAT IS NOT IMPLEMENTED YET
==================================================

The following research pipeline is still largely unimplemented.

PHASE 1 REMAINING PIECE:
---------------------------------

A wrapper around Simplicity.

Required interface:

    get_answer_and_sources(query)
        ->
    {
        answer: string,
        sources: [...]
    }

The wrapper needs to:

1. Send a query to the running Simplicity instance.
2. Consume the NDJSON stream.
3. Parse individual JSON lines.
4. Reconstruct streamed text blocks into the final answer.
5. Extract source blocks.
6. Preserve source metadata.
7. Return a clean Python-friendly structure.

This wrapper is the immediate next milestone.

Do NOT start building the claim verifier before this interface works.


==================================================
PHASE 2 — CLAIM DECOMPOSITION
==================================================

NOT IMPLEMENTED.

Goal:

Take the generated answer and split it into independently verifiable factual claims.

Example:

Answer:

    "The Eiffel Tower was completed in 1889 and is located in Paris.
     It was designed by Gustave Eiffel."

Should become approximately:

    Claim 1:
    The Eiffel Tower was completed in 1889.

    Claim 2:
    The Eiffel Tower is located in Paris.

    Claim 3:
    The Eiffel Tower was designed by Gustave Eiffel.

The decomposition should avoid creating meaningless fragments.

Each claim should ideally have:
- claim ID
- claim text
- location/span in original answer if useful
- optional claim type/category

Potential output:

    [
        {
            "id": "C1",
            "text": "...",
            "span": ...
        },
        ...
    ]

Keep this modular.


==================================================
PHASE 3 — EVIDENCE MAPPING
==================================================

NOT IMPLEMENTED.

Simplicity already retrieves sources for the answer.

Initially, use those sources rather than rebuilding the entire retrieval system.

The evidence mapper should determine:

    Claim
       ↓
    Relevant source(s)

Potential structure:

    {
        claim_id: "C1",
        evidence: [
            {
                source_id: "...",
                title: "...",
                url: "...",
                content: "..."
            }
        ]
    }


IMPORTANT:

Whole-answer sources are not automatically claim-specific evidence.

A source may be irrelevant to a particular claim.

Therefore, evidence mapping should eventually score/filter source relevance per claim.

A future enhancement can re-run retrieval for individual claims when the original sources are insufficient.

Do NOT over-engineer this initially.

First make a working version using the existing Simplicity sources.


==================================================
PHASE 4 — VALIDATOR LLM
==================================================

NOT IMPLEMENTED.

THIS IS THE CORE RESEARCH COMPONENT.

The validator should receive:

    CLAIM
    +
    EVIDENCE

and determine whether the evidence supports the claim.

Possible labels:

    SUPPORTED
    CONTRADICTED
    UNCERTAIN

The validator should also provide an explanation/rationale.

Example:

    Claim:
    "The Eiffel Tower was completed in 1889."

    Evidence:
    "...the Eiffel Tower was completed in 1889..."

    Result:
    SUPPORTED

    Explanation:
    The evidence explicitly states that the Eiffel Tower was completed in 1889.


==================================================
VALIDATOR ENSEMBLE / MINI-COUNCIL
==================================================

A possible research extension is claim-level validator agreement.

Instead of asking one LLM:

    "Is this answer trustworthy?"

the system can ask multiple validator models/prompts to independently evaluate:

    claim + evidence

Example:

    Validator A → SUPPORTED
    Validator B → SUPPORTED
    Validator C → UNCERTAIN

Then aggregate their judgments.

This is different from simply using Simplicity's existing whole-answer Council mechanism.

The intended contribution is:

    CLAIM-LEVEL
    +
    EVIDENCE-AWARE
    +
    ENSEMBLE VERIFICATION

Do not implement a huge multi-agent system unless it is justified.

Start with a minimal validator ensemble abstraction that can later support multiple models.


==================================================
PHASE 5 — TRUST ENGINE
==================================================

NOT IMPLEMENTED.

The Trust Engine converts validation results into claim-level trust/confidence scores.

Possible factors include:

- validator agreement
- evidence relevance
- evidence strength
- contradiction signals
- source quality
- number of independent supporting sources
- number of contradicting sources

Conceptually:

    Claim
       ↓
    Evidence
       ↓
    Validator Results
       ↓
    Agreement / Evidence Signals
       ↓
    Trust Score


The exact mathematical scoring formula has NOT been finalized.

Do not pretend that a particular formula has already been decided.

Design the Trust Engine so the scoring strategy can be changed easily.


==================================================
PHASE 6 — HUMAN REVIEW / EXPLAINABLE UI
==================================================

NOT IMPLEMENTED.

The eventual UI should make the system explainable.

Conceptually:

    Generated Answer

    ┌─────────────────────────────────────┐
    │ The Eiffel Tower was completed...   │
    │                                     │
    │ [Claim 1] ✓ Supported               │
    │                                     │
    │ Evidence:                            │
    │ Source A                             │
    │ Source B                             │
    │                                     │
    │ Validator agreement: 3/3            │
    │ Trust score: 0.94                    │
    └─────────────────────────────────────┘


The user should be able to inspect:

- individual claims
- supporting evidence
- contradicting evidence
- validator decisions
- explanations
- trust score
- source URLs

A graph visualization may eventually be useful:

    Claim
      │
      ├── Evidence A
      ├── Evidence B
      └── Evidence C

But do not build the graph first.

Get the underlying data model working first.


==================================================
PHASE 7 — EVALUATION
==================================================

NOT IMPLEMENTED.

This is important and must not be postponed indefinitely.

Need a labeled evaluation dataset/test set containing factual claims and their verification labels.

Possible metrics:

- claim decomposition quality
- evidence retrieval precision/recall
- validation accuracy
- precision
- recall
- F1
- calibration/trust-score quality
- agreement between validators

The evaluation should compare the proposed claim-level system against meaningful baselines.

Do not fabricate evaluation results.

Build the evaluation infrastructure so results can be generated reproducibly.


==================================================
CURRENT PROJECT STATUS
==================================================

Completed:

    ✓ Architecture/scoping
    ✓ Simplicity running
    ✓ Local Ollama running
    ✓ qwen2.5:7b working
    ✓ Understanding Simplicity's NDJSON response
    ✓ Understanding text blocks vs source blocks
    ✓ Understanding citation/source structure
    ✓ Understanding that Simplicity can provide answer + sources

Not completed:

    ✗ Simplicity integration wrapper
    ✗ Claim decomposition
    ✗ Claim-level evidence mapping
    ✗ Validator LLM
    ✗ Validator ensemble
    ✗ Trust Engine
    ✗ Human review UI
    ✗ Evaluation dataset
    ✗ Evaluation metrics/experiments


==================================================
PRIORITY ORDER
==================================================

DO NOT implement everything at once.

The recommended development order is:

STEP 1
Build and test:

    get_answer_and_sources(query)

STEP 2
Build minimal:

    answer
      ↓
    claims

STEP 3
Build:

    claims
      +
    existing sources
      ↓
    claim-specific evidence

STEP 4
Build a single validator:

    claim + evidence
      ↓
    supported / contradicted / uncertain

STEP 5
Build the Trust Engine.

STEP 6
Create a minimal end-to-end pipeline:

    Query
      ↓
    Simplicity
      ↓
    Answer + Sources
      ↓
    Claims
      ↓
    Evidence
      ↓
    Validator
      ↓
    Trust Scores


ONLY AFTER THIS WORKS:

STEP 7
Add validator ensemble.

STEP 8
Add human review UI.

STEP 9
Build evaluation framework.


==================================================
MOST IMPORTANT DEVELOPMENT PRINCIPLE
==================================================

Build a MINIMAL END-TO-END SLICE before building sophisticated components.

The first meaningful milestone should be:

    query
      ↓
    Simplicity
      ↓
    answer + sources
      ↓
    claim decomposition
      ↓
    evidence mapping
      ↓
    one validator
      ↓
    trust score


If this works, the project has a demonstrable research prototype.

Then improve each component independently.


==================================================
WHAT I EXPECT FROM YOU
==================================================

You are acting as a senior engineer/research prototype developer.

Before changing code:

1. Inspect the repository.
2. Understand the existing architecture.
3. Locate the Simplicity API/stream endpoint.
4. Verify the NDJSON response format from actual code.
5. Identify the correct integration boundary.
6. Determine where the new verification modules should live.

Do NOT immediately rewrite Simplicity.

Do NOT duplicate functionality that Simplicity already provides.

Do NOT start with UI.

Do NOT implement an enormous multi-agent architecture.

FIRST TASK:

Implement only the Simplicity wrapper:

    get_answer_and_sources(query)

It should reliably return:

    answer
    sources

with clean structured data.

Create a small test/demo that proves:

    query
      ↓
    Simplicity
      ↓
    parsed answer
      +
    parsed sources

Once that works, stop and report:

- files created/modified
- API endpoint used
- NDJSON structure observed
- answer parsing logic
- source parsing logic
- sample output
- how the next claim-decomposition module can consume the wrapper

Do not proceed to claim decomposition until the wrapper is verified.

==================================================
RESEARCH DIRECTION
==================================================

The final system is intended to be an Explainable AI / Trustworthy AI research prototype.

The core question is roughly:

"Given an LLM-generated answer and its retrieved evidence, can we decompose the answer into atomic claims and independently verify each claim, producing transparent evidence-backed trust scores rather than treating the entire answer as one indivisible response?"

The system should therefore prioritize:

- claim-level verification
- evidence grounding
- transparency
- explainability
- validator agreement
- reproducible evaluation
īī
The generated answer itself is NOT the research contribution.

The verification/trust layer is.

Keep this distinction in mind throughout development.