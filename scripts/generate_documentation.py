import os
import sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def create_document():
    doc = Document()

    # Set page margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Palette
    COLOR_PRIMARY = RGBColor(27, 54, 93)     # Deep Navy #1B365D
    COLOR_SECONDARY = RGBColor(13, 148, 136) # Vibrant Teal #0D9488
    COLOR_TEXT = RGBColor(45, 55, 72)        # Slate Charcoal #2D3748
    COLOR_MUTED = RGBColor(113, 128, 150)    # Gray #718096
    HEX_BG_LIGHT = "F7FAFC"
    HEX_BORDER = "E2E8F0"
    HEX_PRIMARY = "1B365D"
    HEX_TEAL = "0D9488"
    HEX_CALLOUT_BG = "F0FDF4"
    HEX_CALLOUT_BORDER = "10B981"

    # Base Normal Style
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = COLOR_TEXT
    normal_style.paragraph_format.line_spacing = 1.2
    normal_style.paragraph_format.space_after = Pt(6)

    def add_title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(30)
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(28)
        run.font.bold = True
        run.font.color.rgb = COLOR_PRIMARY
        return p

    def add_subtitle(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(24)
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(14)
        run.font.italic = True
        run.font.color.rgb = COLOR_SECONDARY
        return p

    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(18)
        run.font.bold = True
        run.font.color.rgb = COLOR_PRIMARY
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = COLOR_SECONDARY
        return p

    def add_h3(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = COLOR_TEXT
        return p

    def add_bullet(p, bold_prefix, text):
        p.style = 'List Bullet'
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        run_b = p.add_run(bold_prefix)
        run_b.font.bold = True
        run_b.font.color.rgb = COLOR_TEXT
        run_t = p.add_run(text)
        run_t.font.color.rgb = COLOR_TEXT

    def add_callout(text, prefix="KEY TAKEAWAY: "):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.cell(0, 0)
        cell.width = Inches(6.5)
        
        # XML styling for cell background and left border
        tcPr = cell._tc.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{HEX_CALLOUT_BG}"/>')
        tcPr.append(shd)
        
        borders = parse_xml(f'''
            <w:tcBorders {nsdecls("w")}>
                <w:top w:val="none"/>
                <w:left w:val="single" w:sz="24" w:space="0" w:color="{HEX_CALLOUT_BORDER}"/>
                <w:bottom w:val="none"/>
                <w:right w:val="none"/>
            </w:tcBorders>
        ''')
        tcPr.append(borders)
        
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.left_indent = Inches(0.1)
        p.paragraph_format.right_indent = Inches(0.1)
        
        run_p = p.add_run(prefix)
        run_p.font.bold = True
        run_p.font.size = Pt(10.5)
        run_p.font.color.rgb = RGBColor(16, 185, 129)
        
        run_t = p.add_run(text)
        run_t.font.size = Pt(10.5)
        run_t.font.italic = True
        run_t.font.color.rgb = COLOR_TEXT
        
        # Add space after table
        empty_p = doc.add_paragraph()
        empty_p.paragraph_format.space_before = Pt(4)
        empty_p.paragraph_format.space_after = Pt(4)

    def style_table(tbl, col_widths, headers, data):
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        
        # Header Row
        hdr_cells = tbl.rows[0].cells
        for i, header_text in enumerate(headers):
            hdr_cells[i].text = header_text
            hdr_cells[i].width = Inches(col_widths[i])
            hdr_p = hdr_cells[i].paragraphs[0]
            hdr_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            hdr_p.paragraph_format.space_before = Pt(6)
            hdr_p.paragraph_format.space_after = Pt(6)
            for run in hdr_p.runs:
                run.font.bold = True
                run.font.size = Pt(10)
                run.font.color.rgb = RGBColor(255, 255, 255)
            
            # Header cell background
            tcPr = hdr_cells[i]._tc.get_or_add_tcPr()
            shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{HEX_PRIMARY}"/>')
            tcPr.append(shd)
            
        # Data Rows
        for r_idx, row_data in enumerate(data):
            row_cells = tbl.add_row().cells
            bg_color = HEX_BG_LIGHT if r_idx % 2 == 1 else "FFFFFF"
            for c_idx, cell_value in enumerate(row_data):
                row_cells[c_idx].text = cell_value
                row_cells[c_idx].width = Inches(col_widths[c_idx])
                cell_p = row_cells[c_idx].paragraphs[0]
                cell_p.paragraph_format.space_before = Pt(4)
                cell_p.paragraph_format.space_after = Pt(4)
                for run in cell_p.runs:
                    run.font.size = Pt(9.5)
                    run.font.color.rgb = COLOR_TEXT
                
                # Alternate row shading & light borders
                tcPr = row_cells[c_idx]._tc.get_or_add_tcPr()
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_color}"/>')
                tcPr.append(shd)
                
                borders = parse_xml(f'''
                    <w:tcBorders {nsdecls("w")}>
                        <w:top w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>
                        <w:left w:val="none"/>
                        <w:bottom w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>
                        <w:right w:val="none"/>
                    </w:tcBorders>
                ''')
                tcPr.append(borders)

        # Space after table
        p_sp = doc.add_paragraph()
        p_sp.paragraph_format.space_before = Pt(4)
        p_sp.paragraph_format.space_after = Pt(4)

    # ==========================================
    # COVER / HEADER
    # ==========================================
    add_title("VERIDEX")
    add_subtitle("Next-Generation Autonomous Search & Adversarial Claim Verification Engine\nSystem Architecture, Theoretical Foundations & Comprehensive Engineering Specification")

    # Metadata Block
    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.paragraph_format.space_after = Pt(24)
    run_m = p_meta.add_run("Author: Veridex Core Engineering Team   |   Version: 2.1 (Production)   |   Date: October 2026")
    run_m.font.size = Pt(10)
    run_m.font.bold = True
    run_m.font.color.rgb = COLOR_MUTED

    doc.add_page_break()

    # ==========================================
    # SECTION 1: EXECUTIVE SUMMARY
    # ==========================================
    add_h1("1. Executive Summary")
    doc.add_paragraph(
        "Modern artificial intelligence applications face a fundamental crisis of trust: Large Language Models (LLMs) "
        "suffer from hallucination, confabulation, and sycophancy. While Retrieval-Augmented Generation (RAG) and AI search engines "
        "(such as Perplexity and SearchGPT) have emerged to address this by grounding responses in web search snippets, "
        "they exhibit a profound systemic vulnerability: the model generating the answer is also entrusted with determining "
        "whether its own answer is truthful. This circular validation creates an unmitigated confirmation bias, where models "
        "routinely cite sources that actually contradict their generated claims."
    )
    doc.add_paragraph(
        "Veridex (formerly Simplicity) is a clean-sheet, production-grade search and verification platform engineered to solve "
        "this epistemic failure. Veridex introduces an adversarial, decoupled architecture that strictly enforces the principle: "
        "'Never let an LLM grade its own homework.' Operating as a dual-engine platform, Veridex pairs an autonomous multi-round "
        "search orchestrator with an independent Python verification pipeline powered by LAYA (a sub-50ms non-autoregressive "
        "decision engine) and a deterministic mathematical Trust Engine."
    )
    add_callout(
        "Veridex guarantees that every factual assertion in a generated answer is atomized, mapped to verbatim retrieved web passages, "
        "evaluated through calibrated non-autoregressive entailment classifiers, and aggregated into a transparent, reproducible 0–100% trust score.",
        prefix="CORE MISSION: "
    )

    # ==========================================
    # SECTION 2: THE PROBLEM STATEMENT
    # ==========================================
    add_h1("2. The Problem Statement: Why Standard AI Search Fails")
    doc.add_paragraph(
        "To appreciate the necessity of Veridex, one must examine the critical limitations of contemporary AI search and RAG platforms:"
    )
    
    p = doc.add_paragraph()
    add_bullet(p, "Circular Self-Verification: ", "When a single LLM retrieves search results, synthesizes an answer, and formats inline citations, it frequently hallucinates facts and fabricates citations. If prompted 'Are you sure?', the model exhibits sycophancy—doubling down on its initial falsehoods rather than correcting them.")
    
    p = doc.add_paragraph()
    add_bullet(p, "Single-Vendor Model Monoculture: ", "Standard search products tie the user to a single model provider (e.g., OpenAI or Anthropic). If that specific foundation model has a knowledge blind spot, an ideological bias, or an unannounced alignment update, the user has no mechanism to detect the distortion.")

    p = doc.add_paragraph()
    add_bullet(p, "Prohibitive Verification Latency: ", "Prior attempts at post-generation claim verification have relied on secondary LLM calls. For an answer containing 6 atomic claims, invoking secondary generative LLMs to evaluate each claim adds 25–40 seconds of latency and substantial API costs, making real-time verification completely impractical.")

    p = doc.add_paragraph()
    add_bullet(p, "Privacy Degradation & Tracking: ", "Commercial search engines index, profile, and monetize user query streams. Standard AI search APIs leak sensitive research intents directly to centralized third-party ad networks.")

    # ==========================================
    # SECTION 3: SYSTEM ARCHITECTURE & DUAL-ENGINE PARADIGM
    # ==========================================
    add_h1("3. System Architecture & The Dual-Engine Paradigm")
    doc.add_paragraph(
        "Veridex addresses these challenges through a strict separation of concerns, dividing the system into two independent, "
        "asynchronously operating engines:"
    )

    add_h2("3.1. Engine A: The Generation Engine (Next.js / Node.js / Electron)")
    doc.add_paragraph(
        "The Generation Engine owns user interaction, autonomous search planning, metasearch retrieval, web scraping, and answer "
        "synthesis. It supports three distinct operational modes:"
    )
    p = doc.add_paragraph()
    add_bullet(p, "Standard Search (Speed Mode): ", "Executes a single fast retrieval round, applies embedding-based cosine similarity reranking, and streams a journalistic, citation-annotated answer in under 3 seconds.")
    
    p = doc.add_paragraph()
    add_bullet(p, "Deep Research Mode: ", "An autonomous investigation loop capable of running up to 6 iterative rounds, executing up to 20 targeted SearXNG queries, scraping full HTML web pages via Mozilla Readability and headless Playwright, and extracting telegram-style atomic facts before authoring a comprehensive analytical report.")

    p = doc.add_paragraph()
    add_bullet(p, "Model Council Mode: ", "A revolutionary multi-vendor architecture. Instead of relying on a single AI model, Veridex executes the search phase once, then fans out the identical factual search context simultaneously to 2 to 3 distinct frontier LLMs from competing vendors (e.g., Claude, GPT-4o, NVIDIA Nemotron, Gemini). A designated Chair Model compares all member answers, explicitly mapping out areas of Convergence, Divergence, and Unique Insights.")

    add_h2("3.2. Engine B: The Adversarial Verification Engine (Python / LAYA)")
    doc.add_paragraph(
        "The Verification Engine is completely isolated from the generation layer. Written in Python 3.12, it consumes the final "
        "synthesized text and raw source snippets via a JSON standard I/O bridge. It executes four sequential verification phases:"
    )
    p = doc.add_paragraph()
    add_bullet(p, "Phase 1 - Atomic Claim Decomposition: ", "Splits the generated answer into isolated, checkable atomic propositions (C1, C2, C3...), stripping away opinions, rhetorical statements, and conversational filler.")
    
    p = doc.add_paragraph()
    add_bullet(p, "Phase 2 - Sentence-Segment Evidence Mapping: ", "Slices raw web sources into individual sentence passages (P1, P2...), calculates lexical overlap, and maps each atomic claim to its most relevant candidate evidence snippets.")

    p = doc.add_paragraph()
    add_bullet(p, "Phase 3 - Non-Autoregressive Entailment Scoring (LAYA): ", "Evaluates the strict logical entailment between claim and evidence in ~35ms per forward pass using LAYA's ModernBERT encoder, outputting calibrated probabilities for SUPPORTED, CONTRADICTED, or UNCERTAIN.")

    p = doc.add_paragraph()
    add_bullet(p, "Phase 4 - Deterministic Mathematical Trust Aggregation: ", "Aggregates all claim verdicts into transparent signed scores and computes an overall 0–100% Trust Metric using closed-form mathematics with zero LLM hallucination.")

    # Table of Dual Engine Architecture
    tbl1 = doc.add_table(rows=1, cols=4)
    style_table(
        tbl1,
        [1.3, 1.6, 1.8, 1.8],
        ["Component", "Technology", "Primary Responsibility", "Key Characteristic"],
        [
            ["Generation Engine", "Next.js 16, TypeScript, Node.js", "User UI, query routing, SSE streaming, SQLite persistence", "Reactive, asynchronous, real-time token streaming via rfc6902"],
            ["Search Backend", "SearXNG, Playwright, Readability", "Anonymous metasearch aggregation, HTML scraping, fact extraction", "Zero query logging, 70+ engines, automated vertical routing"],
            ["Model Council", "OpenRouter, Anthropic, Gemini, Ollama", "Multi-vendor parallel generation, divergence & consensus synthesis", "Apples-to-apples comparison over identical search context"],
            ["Verification Engine", "Python 3.12, PyTorch, LAYA, Ollama", "Claim decomposition, passage mapping, entailment, trust scoring", "Adversarial, non-autoregressive, calibrated probabilities"],
        ]
    )

    # ==========================================
    # SECTION 4: UNPRECEDENTED NOVELTY & COMPETITIVE ADVANTAGES
    # ==========================================
    add_h1("4. Technical Novelty & Competitive Advantages")
    doc.add_paragraph(
        "Veridex is not another wrapper around an LLM API. It introduces four architectural innovations that fundamentally distinguish "
        "it from existing commercial and open-source platforms:"
    )

    add_h2("4.1. Non-Autoregressive Entailment with LAYA (Sub-50ms Latency)")
    doc.add_paragraph(
        "Traditional automated fact-checking systems use generative LLMs (like GPT-4 or Qwen-7B) to determine entailment. "
        "Generative LLMs are autoregressive: they predict text token-by-token, requiring hundreds of decoding steps per claim. "
        "This makes multi-claim validation prohibitively slow."
    )
    doc.add_paragraph(
        "Veridex integrates LAYA, a non-autoregressive System 1 decision engine built on ModernBERT-large (421M parameters) and "
        "mmBERT (322M parameters). LAYA processes the entire claim-evidence pair in a single encoder forward pass, taking only "
        "~35ms on GPU and ~200ms on CPU. Furthermore, LAYA's classification heads are trained using reinforcement learning "
        "against strictly proper scoring rules (Brier score and log score), meaning its output probabilities are mathematically calibrated: "
        "a 90% confidence score accurately reflects a 90% statistical probability of empirical truth."
    )

    add_h2("4.2. Two-Tier Cascade Hybrid Architecture")
    doc.add_paragraph(
        "To balance extreme speed with explainability, Veridex deploys an intelligent two-tier hybrid cascade:"
    )
    p = doc.add_paragraph()
    add_bullet(p, "Tier 1 (LAYA Fast Path - 90% of Claims): ", "High-confidence claims (confidence >= 0.65) are resolved in ~35ms. LAYA delivers immediate verdict labels, calibrated confidence metrics, and ordinal support strength (0–4 scale).")
    
    p = doc.add_paragraph()
    add_bullet(p, "Tier 2 (Ollama Fallback / Escalation): ", "If LAYA flags a claim as borderline or low-confidence (< 0.65), the system automatically escalates only that specific claim to a local Ollama model (Qwen 2.5) to generate an extended natural-language chain-of-thought rationale.")

    add_h2("4.3. The Deterministic Trust Engine (Zero Hallucinated Metrics)")
    doc.add_paragraph(
        "Most AI benchmarks score answers subjectively using an 'LLM-as-a-Judge'. Veridex firmly rejects this practice. "
        "Its Trust Engine is written in pure Python mathematics without any generative LLM in the aggregation loop. "
        "Every claim contributes a transparent, deterministic signed value to the final score, guaranteeing that verification results "
        "are auditable, deterministic, and scientifically reproducible."
    )

    add_h2("4.4. Multi-Vendor Model Council (Consensus Over Authority)")
    doc.add_paragraph(
        "Rather than forcing the user to trust a single AI provider, Veridex's Model Council queries multiple distinct foundation models "
        "simultaneously over the exact same retrieved evidence context. The Chair model synthesizes the findings by categorizing them into:"
    )
    p = doc.add_paragraph()
    add_bullet(p, "Convergence: ", "Facts verified independently by every foundation model.")
    p = doc.add_paragraph()
    add_bullet(p, "Divergence: ", "Direct conflicts where models disagree on interpretations, dates, or numbers.")
    p = doc.add_paragraph()
    add_bullet(p, "Unique Insights: ", "Specialized nuances uncovered by only one model.")

    # ==========================================
    # SECTION 5: STEP-BY-STEP PROMPT-TO-VERIFICATION WORKFLOW
    # ==========================================
    add_h1("5. The Complete Prompt-to-Verification Lifecycle")
    doc.add_paragraph(
        "The following walkthrough details the exact operational sequence when a user submits a prompt to Veridex:"
    )

    add_h2("Step 1: User Submission & Client Dispatch")
    doc.add_paragraph(
        "The user enters a research prompt via MessageInput.tsx, selecting an optimization mode (Speed, Balanced, Quality), "
        "target verticals (Web, Academic, Discussions), and a search mode (Search, Deep Research, or Council). The useChat.tsx "
        "hook serializes the state and dispatches an HTTP POST request to /api/chat, establishing a persistent Server-Sent Events (SSE) stream."
    )

    add_h2("Step 2: Intent Classification & Query Reformulation")
    doc.add_paragraph(
        "Before searching, the request enters classifier.ts. A lightweight local Utility LLM (Ollama Qwen 2.5) analyzes the conversation "
        "history and the prompt. It reformulates the user prompt into a context-free standalone inquiry, detects if search should be skipped "
        "(e.g., pure math calculations or greetings), and identifies appropriate search verticals (e.g., ArXiv for academic queries, "
        "Reddit for discussions)."
    )

    add_h2("Step 3: Autonomous Multi-Round Search & Scraping")
    doc.add_paragraph(
        "The Researcher module (researcher/index.ts) initiates iterative search rounds:"
    )
    p = doc.add_paragraph()
    add_bullet(p, "Query Planning: ", "queryPlanner.ts generates 3 diverse, keyword-optimized queries for the first round.")
    p = doc.add_paragraph()
    add_bullet(p, "Metasearch Execution: ", "Queries are dispatched to SearXNG via searxng.ts, aggregating raw results from Google, DuckDuckGo, Bing, ArXiv, and Reddit without user tracking.")
    p = doc.add_paragraph()
    add_bullet(p, "Reranking & Scraping: ", "In Speed mode, results are vector-embedded and filtered by cosine similarity (> 0.5). In Quality/Deep Research mode, top pages are scraped via Playwright and Mozilla Readability, and a fact extractor extracts atomic bullet points.")
    p = doc.add_paragraph()
    add_bullet(p, "Gap Refinement: ", "The query planner inspects gathered findings against the original goal. If gaps remain, it refines queries for subsequent rounds (up to 6 rounds in Deep Research).")
    p = doc.add_paragraph()
    add_bullet(p, "Context Budgeting: ", "contextBudget.ts enforces strict token caps (16,000 tokens for standard search; 32,000 for deep research) and compiles the deduplicated sources into structured XML context: <search_results>.")

    add_h2("Step 4: Answer Synthesis & Real-Time Streaming")
    doc.add_paragraph(
        "In Single-Model mode, writer.ts injects the XML context into the prompt of the user's selected model (e.g., OpenRouter NVIDIA Nemotron, "
        "Gemini Flash, or Claude), enforcing mandatory inline citations in [number] format. Tokens stream in real time to the UI via SSE. "
        "In Council mode, the context is sent to 2–3 vendor models in parallel, followed by Chair synthesis."
    )

    add_h2("Step 5: Adversarial Verification Bridge")
    doc.add_paragraph(
        "Once the answer is rendered, the user clicks 'Verify answer' in VerificationPanel.tsx. Node.js spawns a Python subprocess "
        "(verification.bridge) and pipes the generated text along with the retrieved source snippets into stdin JSON:"
    )
    p = doc.add_paragraph()
    add_bullet(p, "Claim Decomposition: ", "claim_decomposer.py invokes Ollama with schema enforcement to isolate every factual proposition into atomic claims (C1, C2, C3...).")
    p = doc.add_paragraph()
    add_bullet(p, "Evidence Mapping: ", "evidence_mapper.py segments source documents into individual sentences (P1, P2...), calculates token-level lexical overlap, and maps each claim to candidate evidence segments.")
    p = doc.add_paragraph()
    add_bullet(p, "Claim Validation: ", "claim_validator.py routes claims to laya_scorer.py. LAYA processes the pairs in ~35ms, scoring verdict, confidence, and support strength.")
    p = doc.add_paragraph()
    add_bullet(p, "Trust Engine: ", "trust_engine.py computes signed confidence values and generates a comprehensive TrustReport containing the mathematical trust score, supported/uncertain/contradicted tallies, and human-readable natural language explanations.")

    add_h2("Step 6: Interactive Verification Panel Display")
    doc.add_paragraph(
        "The bridge stdout returns JSON to /api/verify, and the frontend dynamically updates. The user is presented with a 0–100% "
        "Overall Trust badge, claim category badges, and expandable accordion cards showing the exact rationale and verbatim "
        "evidence snippets with direct hyperlinks to the original web sources."
    )

    # ==========================================
    # SECTION 6: THE MATHEMATICAL FOUNDATIONS OF THE TRUST ENGINE
    # ==========================================
    add_h1("6. Mathematical Foundations of the Trust Engine")
    doc.add_paragraph(
        "The Veridex Trust Engine (verification/trust_engine.py) implements a mathematically rigorous, transparent scoring baseline. "
        "It deliberately excludes LLM judgment from the score computation, ensuring full auditability."
    )

    add_h2("6.1. Signed Confidence Mapping")
    doc.add_paragraph(
        "Let C = {c_1, c_2, ..., c_N} be the set of atomic claims decomposed from the answer. For each claim c_i, the validator produces "
        "a classification label L_i in {SUPPORTED, CONTRADICTED, UNCERTAIN} and a calibrated confidence value conf_i in [0, 1]. "
        "The directional signed confidence score s_i is defined as:"
    )
    
    # Equation callout
    add_callout(
        "s_i = +conf_i  if L_i = SUPPORTED\n"
        "s_i = -conf_i  if L_i = CONTRADICTED\n"
        "s_i =  0.0     if L_i = UNCERTAIN",
        prefix="SIGNED CONFIDENCE FORMULA:\n"
    )

    doc.add_paragraph(
        "This mapping ensures that contradictory claims penalize trust symmetrically, while uncertain claims (claims with insufficient "
        "or ambiguous evidence) contribute 0 to the directional score—neither falsely boosting trust nor unfairly penalizing the answer "
        "as a direct falsehood."
    )

    add_h2("6.2. Weighted Aggregation & Normalization")
    doc.add_paragraph(
        "Each claim possesses an optional priority weight w_i > 0 (defaulting to 1.0 in the baseline equal-weight setting). "
        "The raw aggregate signed score S is computed as the weighted average across all N claims:"
    )
    add_callout(
        "S = ( sum_{i=1}^N w_i * s_i ) / ( sum_{i=1}^N w_i )     where S in [-1.0, +1.0]",
        prefix="RAW AGGREGATE SCORE:\n"
    )

    doc.add_paragraph(
        "To present an intuitive percentage metric to end users, the signed range [-1, +1] is mapped monotonically to the interval [0, 1]:"
    )
    add_callout(
        "Overall Trust = (S + 1.0) / 2.0     where Overall Trust in [0.0, 1.0] (0% to 100%)",
        prefix="NORMALIZED OVERALL TRUST:\n"
    )

    add_h2("6.3. Evidence Certainty & Coverage Metrics")
    doc.add_paragraph(
        "In addition to directional trust, Veridex computes the Evidence Certainty Rate, which quantifies the proportion of claims "
        "that received an unambiguous, evidence-bounded verdict:"
    )
    add_callout(
        "Certainty Rate = ( sum_{i in Non-Uncertain} w_i * conf_i ) / ( sum_{i=1}^N w_i )",
        prefix="CERTAINTY COVERAGE FORMULA:\n"
    )

    # ==========================================
    # SECTION 7: EXHAUSTIVE TECH STACK & TOOLS BREAKDOWN
    # ==========================================
    add_h1("7. Exhaustive Tech Stack & Tools Breakdown")
    doc.add_paragraph(
        "The Veridex architecture integrates best-of-breed open-source and proprietary technologies across its full vertical stack:"
    )

    tbl2 = doc.add_table(rows=1, cols=4)
    style_table(
        tbl2,
        [1.3, 1.5, 1.8, 1.9],
        ["Tier", "Tool / Library", "Role in Veridex", "Technical Rationale"],
        [
            ["Web Framework", "Next.js 16 (App Router)", "Core application framework, SSR, and API route routing", "High-performance React Server Components and native streaming endpoints"],
            ["Frontend UI", "React 19, Tailwind CSS", "Interactive chat interface, citation tooltips, verification cards", "Modern component lifecycle, reactive state, and dark/light theming"],
            ["Streaming", "Server-Sent Events (SSE), rfc6902", "Real-time block updates and patch streaming", "Enables live character-by-character text generation and research steps"],
            ["Database", "SQLite via better-sqlite3 & Drizzle ORM", "Local persistence of chat sessions, messages, and settings", "Zero-configuration local embedded database with full ACID compliance"],
            ["Desktop Container", "Electron 34", "Cross-platform desktop application packaging", "Native window integration, background service lifecycle management"],
            ["Search Aggregator", "SearXNG (Bundled)", "Anonymous metasearch querying Google, DDG, ArXiv, Reddit", "Zero query logging, 70+ engines, custom category and vertical filters"],
            ["Web Scraper", "Playwright & Mozilla Readability", "Headless browser scraping and DOM article distillation", "Bypasses client-side rendering; strips navigation and ads for fact extraction"],
            ["Context Budgeter", "Tiktoken (js-tiktoken)", "Token-bounding retrieved search snippets before LLM ingestion", "Prevents context window overflow and controls prompt token expenses"],
            ["Generative Models", "OpenRouter (Nemotron), Gemini, Claude", "Writer and Model Council answer synthesis", "Enables free-tier NVIDIA Nemotron models, fast Gemini Flash, and Claude"],
            ["Fast Claim Scorer", "LAYA (ModernBERT / mmBERT)", "Non-autoregressive System 1 claim entailment classifier", "Sub-50ms forward pass latency on GPU; calibrated proper-scoring probabilities"],
            ["Local Utility LLM", "Ollama (qwen2.5:3b)", "Intent classification, query planning, claim decomposition", "Zero-cost, private, local function calling and structured JSON output"],
            ["Machine Learning", "PyTorch 2.6, Transformers 4.49", "Deep learning runtime for LAYA encoder heads", "Hardware-accelerated tensor math (NVIDIA CUDA, Apple MPS, or CPU)"],
        ]
    )

    # ==========================================
    # SECTION 8: CONFIGURATION & RESILIENCY
    # ==========================================
    add_h1("8. Operational Resiliency & Fault-Tolerant Engineering")
    doc.add_paragraph(
        "Veridex has been hardened against the common failure modes of distributed AI and local machine learning systems:"
    )
    p = doc.add_paragraph()
    add_bullet(p, "Gemini Free-Tier Rate-Limit Handling: ", "Google's free Gemini API enforces strict 15 RPM limits and frequently throws transient 503 (High Demand) spikes. Veridex's GeminiLLM implements automated exponential backoff retries (1.5s, 3s) and an automatic model cascade across sibling models (gemini-flash-latest -> gemini-flash-lite-latest -> gemini-3.8-flash).")

    p = doc.add_paragraph()
    add_bullet(p, "Robust JSON Parser for Compact LLMs: ", "Smaller local models (e.g. 2B/3B parameters) frequently violate JSON schema constraints by outputting markdown code fences (```json) or conversational text. Veridex's claim decomposer includes a regex-based JSON extractor that strips code fences and trailing commas before parsing.")

    p = doc.add_paragraph()
    add_bullet(p, "Graceful LAYA Fallback: ", "If LAYA is not installed or Hugging Face weights fail to download, the HybridClaimValidator catches the exception and routes all verification tasks transparently to Ollama without throwing a fatal application error.")

    # ==========================================
    # SECTION 9: CONCLUSION & FUTURE ROADMAP
    # ==========================================
    add_h1("9. Conclusion & Strategic Roadmap")
    doc.add_paragraph(
        "Veridex demonstrates that high-speed web search and rigorous epistemic verification can coexist in a single, "
        "cohesive architecture. By replacing subjective self-checking with an adversarial, non-autoregressive verification "
        "pipeline and grounding claims in auditable mathematical trust metrics, Veridex establishes a new standard for trustworthy AI."
    )
    doc.add_paragraph(
        "Future engineering milestones on the Veridex roadmap include:"
    )
    p = doc.add_paragraph()
    add_bullet(p, "Persistent Verification Microservice: ", "Transitioning the Python bridge from a per-query subprocess to a persistent FastAPI HTTP/gRPC daemon, completely eliminating Python cold-start latency.")
    p = doc.add_paragraph()
    add_bullet(p, "Knowledge Graph Visualization: ", "Generating interactive 3D force-directed knowledge graphs showing claims, evidence nodes, and contradiction vectors directly in the frontend UI.")
    p = doc.add_paragraph()
    add_bullet(p, "Distributed P2P Council Consensus: ", "Enabling decentralized Model Councils across peer devices to reach consensus on controversial queries without centralized server coordination.")

    return doc

if __name__ == "__main__":
    doc = create_document()
    
    # Save destinations
    dest1 = r"C:\Users\Muhammed Sabith\Desktop\Veridex_Technical_Whitepaper.docx"
    dest2 = r"C:\Users\Muhammed Sabith\Desktop\veridex\docs\Veridex_Technical_Whitepaper.docx"
    
    doc.save(dest1)
    print(f"Saved primary to: {dest1}")
    
    try:
        os.makedirs(os.path.dirname(dest2), exist_ok=True)
        doc.save(dest2)
        print(f"Saved replica to: {dest2}")
    except Exception as e:
        print(f"Could not save replica: {e}")
