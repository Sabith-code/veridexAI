import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def create_tech_stack_document():
    doc = Document()

    # Margins (1.0 inch)
    for s in doc.sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)

    # Palette
    COLOR_PRIMARY = RGBColor(27, 54, 93)      # Deep Navy #1B365D
    COLOR_TEAL = RGBColor(13, 148, 136)       # Teal #0D9488
    COLOR_EMERALD = RGBColor(5, 150, 105)     # Emerald #059669
    COLOR_TEXT = RGBColor(45, 55, 72)         # Slate Charcoal #2D3748
    COLOR_MUTED = RGBColor(113, 128, 150)     # Gray #718096
    HEX_PRIMARY = "1B365D"
    HEX_BG_LIGHT = "F8FAFC"
    HEX_BORDER = "E2E8F0"
    HEX_CALLOUT_BG = "F0FDF4"
    HEX_CALLOUT_BORDER = "10B981"
    HEX_WHY_BG = "EFF6FF"
    HEX_WHY_BORDER = "3B82F6"

    # Base Style
    normal = doc.styles['Normal']
    normal.font.name = 'Calibri'
    normal.font.size = Pt(11)
    normal.font.color.rgb = COLOR_TEXT
    normal.paragraph_format.line_spacing = 1.2
    normal.paragraph_format.space_after = Pt(6)

    def add_title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(20)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(text)
        run.font.size = Pt(26)
        run.font.bold = True
        run.font.color.rgb = COLOR_PRIMARY
        return p

    def add_subtitle(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(20)
        run = p.add_run(text)
        run.font.size = Pt(13)
        run.font.italic = True
        run.font.color.rgb = COLOR_TEAL
        return p

    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.size = Pt(16)
        run.font.bold = True
        run.font.color.rgb = COLOR_PRIMARY
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = COLOR_TEAL
        return p

    def add_h3(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.size = Pt(11.5)
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

    def add_why_box(why_text, alternatives_text):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.cell(0, 0)
        cell.width = Inches(6.5)

        tcPr = cell._tc.get_or_add_tcPr()
        tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{HEX_WHY_BG}"/>'))
        tcPr.append(parse_xml(f'''
            <w:tcBorders {nsdecls("w")}>
                <w:top w:val="none"/>
                <w:left w:val="single" w:sz="24" w:space="0" w:color="{HEX_WHY_BORDER}"/>
                <w:bottom w:val="none"/>
                <w:right w:val="none"/>
            </w:tcBorders>
        '''))

        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(5)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.left_indent = Inches(0.12)
        p.paragraph_format.right_indent = Inches(0.12)

        r_wb = p.add_run("WHY WE CHOSE IT: ")
        r_wb.font.bold = True
        r_wb.font.size = Pt(10)
        r_wb.font.color.rgb = RGBColor(37, 99, 235)

        r_wt = p.add_run(why_text + "\n")
        r_wt.font.size = Pt(10)
        r_wt.font.color.rgb = COLOR_TEXT

        r_ab = p.add_run("ALTERNATIVES REJECTED: ")
        r_ab.font.bold = True
        r_ab.font.size = Pt(9.5)
        r_ab.font.color.rgb = COLOR_MUTED

        r_at = p.add_run(alternatives_text)
        r_at.font.size = Pt(9.5)
        r_at.font.italic = True
        r_at.font.color.rgb = COLOR_TEXT

        p_sp = doc.add_paragraph()
        p_sp.paragraph_format.space_before = Pt(3)
        p_sp.paragraph_format.space_after = Pt(3)

    def style_table(tbl, col_widths, headers, data):
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_cells = tbl.rows[0].cells
        for i, header_text in enumerate(headers):
            hdr_cells[i].text = header_text
            hdr_cells[i].width = Inches(col_widths[i])
            hp = hdr_cells[i].paragraphs[0]
            hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            hp.paragraph_format.space_before = Pt(5)
            hp.paragraph_format.space_after = Pt(5)
            for run in hp.runs:
                run.font.bold = True
                run.font.size = Pt(9.5)
                run.font.color.rgb = RGBColor(255, 255, 255)
            tcPr = hdr_cells[i]._tc.get_or_add_tcPr()
            tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{HEX_PRIMARY}"/>'))

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
                    run.font.size = Pt(9)
                    run.font.color.rgb = COLOR_TEXT
                tcPr = row_cells[c_idx]._tc.get_or_add_tcPr()
                tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_color}"/>'))
                tcPr.append(parse_xml(f'''
                    <w:tcBorders {nsdecls("w")}>
                        <w:top w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>
                        <w:left w:val="none"/><w:right w:val="none"/>
                        <w:bottom w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>
                    </w:tcBorders>
                '''))

        p_sp = doc.add_paragraph()
        p_sp.paragraph_format.space_before = Pt(4)
        p_sp.paragraph_format.space_after = Pt(4)

    # =========================================================================
    # COVER / HEADER
    # =========================================================================
    add_title("VERIDEX TECH STACK & TOOLS DEEP DIVE")
    add_subtitle("Comprehensive Architectural Rationale, Design Decisions & Trade-Off Analysis\nOctober 2026")

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.paragraph_format.space_after = Pt(20)
    r_m = p_meta.add_run("A complete, layer-by-layer breakdown of every language, framework, database, scraper, and AI model selected for Veridex, explaining why each tool was chosen over industry alternatives.")
    r_m.font.size = Pt(10.5)
    r_m.font.italic = True
    r_m.font.color.rgb = COLOR_MUTED

    doc.add_page_break()

    # =========================================================================
    # SECTION 1: ARCHITECTURAL OVERVIEW
    # =========================================================================
    add_h1("1. Architectural Overview & Design Philosophy")
    doc.add_paragraph(
        "Veridex is architected as a decoupled, multi-tier system engineered around three core operational tenets: "
        "(1) Local-first privacy, ensuring that user research intents and search queries are never logged, profiled, or sold; "
        "(2) Adversarial verification, ensuring that the model authoring an answer is never permitted to validate its own claims; "
        "and (3) Real-time sub-second latency, achieved by deploying non-autoregressive neural encoders instead of slow, expensive generative LLM judges."
    )
    doc.add_paragraph(
        "To achieve these goals, Veridex divides its technical responsibilities across two decoupled runtime environments: "
        "a Node.js / Next.js reactive frontend and orchestration layer, paired with a specialized Python 3.12 deep learning and deterministic mathematical verification engine."
    )

    # =========================================================================
    # SECTION 2: LAYER 1 - FRONTEND & USER INTERFACE
    # =========================================================================
    add_h1("2. Layer 1: Frontend & User Experience Engineering")
    doc.add_paragraph(
        "The frontend of Veridex is designed to provide immediate streaming feedback, transparent citation attribution, and interactive claim auditing."
    )

    add_h2("2.1. Next.js 16 (App Router) & React 19")
    doc.add_paragraph(
        "Veridex utilizes Next.js 16 with the modern App Router paradigm (`src/app/`) running React 19."
    )
    add_why_box(
        "Next.js App Router provides native support for React Server Components (RSC) and HTTP streaming route handlers (`src/app/api/chat/route.ts`). "
        "This allows Veridex to stream synthesized text chunks character-by-character to the client while running intensive background research rounds asynchronously. "
        "React 19 brings concurrent rendering and optimized hydration, preventing UI freezes during heavy streaming.",
        "Traditional SPA (Vite + React) was rejected because it requires separate Express/Fastify server infrastructure, complicating local desktop bundling and SSR routing. "
        "Remix was evaluated but rejected due to smaller ecosystem support for Electron desktop bundling."
    )

    add_h2("2.2. Server-Sent Events (SSE) & RFC 6902 JSON Patching")
    doc.add_paragraph(
        "Rather than polling or waiting for a complete response, Veridex communicates state over a continuous `text/event-stream` using the RFC 6902 JSON Patch standard."
    )
    add_why_box(
        "SSE operates over standard HTTP/1.1 and HTTP/2, eliminating the protocol upgrade overhead, proxy complications, and firewall blocking associated with WebSockets. "
        "By applying RFC 6902 JSON Patch operations in `useChat.tsx`, the backend can surgically update specific blocks in the message tree—such as adding a discovered source, updating a research step, or streaming a word—without re-rendering or serializing the entire conversation state.",
        "WebSockets were rejected because bi-directional communication is unnecessary (the user sends a prompt once; the server streams multiple updates). "
        "Long polling was rejected due to catastrophic latency and excessive HTTP connection churn."
    )

    add_h2("2.3. Tailwind CSS & Tailwind Typography")
    doc.add_paragraph(
        "Styling is managed entirely via Tailwind CSS with the `@tailwindcss/typography` plugin."
    )
    add_why_box(
        "Tailwind generates a minimal, purged CSS bundle at build time with zero runtime CSS-in-JS overhead. "
        "The typography plugin provides pre-built, elegant styling for complex markdown structures—including nested bullet points, code fences, blockquotes, and tables—rendered via `markdown-to-jsx`. "
        "CSS variables (`var(--background)`, `var(--card)`) allow instant, flicker-free dark and light mode switching.",
        "Styled-components and Emotion were rejected because runtime CSS-in-JS severely degrades streaming performance and causes layout thrashing during fast token generation."
    )

    add_h2("2.4. Lucide React & Simple Icons")
    doc.add_paragraph(
        "Icons are powered by `lucide-react` paired with `@icons-pack/react-simple-icons`."
    )
    add_why_box(
        "Lucide provides clean, consistent, tree-shakeable SVG icons for UI navigation and status indicators. "
        "Simple Icons supplies accurate, official brand SVGs (NVIDIA, Google, Anthropic, OpenRouter, GitHub) used in the provider picker and Model Council blocks.",
        "FontAwesome was rejected due to heavy font file bloat and lack of modern brand icon tree-shaking."
    )

    # =========================================================================
    # SECTION 3: LAYER 2 - BACKEND, DESKTOP & DATA PERSISTENCE
    # =========================================================================
    add_h1("3. Layer 2: Backend, Desktop & Data Persistence")

    add_h2("3.1. Node.js Asynchronous Runtime")
    doc.add_paragraph(
        "The server runtime executes on Node.js (v20+ LTS)."
    )
    add_why_box(
        "Node's non-blocking, event-driven I/O model is uniquely suited for orchestrating simultaneous network tasks. "
        "During Model Council execution, Node coordinates parallel API calls to 3 separate cloud LLMs while streaming live results and running local embedding vector searches without thread contention.",
        "Python (FastAPI) for the web orchestrator was considered, but rejected because the React/Next.js frontend requires a Node.js server environment for SSR and bundling, making Node the natural orchestrator."
    )

    add_h2("3.2. SQLite via `better-sqlite3` & Drizzle ORM")
    doc.add_paragraph(
        "Local application state—including conversation histories, user settings, and message blocks—is persisted in a local SQLite database managed by Drizzle ORM."
    )
    add_why_box(
        "SQLite is a serverless, zero-configuration, embedded database that stores all data in a single file on the user's local disk. "
        "`better-sqlite3` is the fastest SQLite driver for Node.js, executing queries synchronously with direct C++ V8 bindings (bypassing asynchronous overhead). "
        "Drizzle ORM provides complete TypeScript type-safety with zero runtime bloat, auto-generating clean migrations without heavy query engines.",
        "PostgreSQL and MySQL were rejected because they require installing and managing an external background database server, making simple desktop distribution impossible. "
        "Prisma was rejected due to its heavy Rust engine binary, slow cold starts, and excessive memory footprint on desktop systems."
    )

    add_h2("3.3. Electron 34 Desktop Packaging")
    doc.add_paragraph(
        "For desktop distribution (`yarn app`), Veridex wraps the application in Electron 34 (`desktop/main.mjs`)."
    )
    add_why_box(
        "Electron allows packaging the entire Next.js application, SearXNG search engine, and local runtime into a single, native executable for Windows and macOS. "
        "It provides deep OS integration: native window controls, system tray menus, offline application lifecycle management, and secure local file access.",
        "Tauri was evaluated, but rejected due to the complexity of embedding the existing Next.js dynamic Node.js server and bundled SearXNG Python subprocesses inside a Rust shell."
    )

    add_h2("3.4. Webpack Compiler (`--webpack`) vs. Turbopack")
    doc.add_paragraph(
        "Veridex explicitly configures Next.js to build and compile using Webpack (`next build --webpack`)."
    )
    add_why_box(
        "While Turbopack is Next.js's newer Rust-based compiler, it currently suffers from severe path-resolution and junction bugs on Windows (as seen in the `Next.js package not found` panic during on-demand compilation). "
        "Webpack provides battle-tested stability, flawless module resolution across Windows short paths (`C:\\Users\\MUHAMM~1`), and support for custom Node native addons (`better-sqlite3`).",
        "Turbopack in development was disabled on critical paths to eliminate unexpected Rust engine panics."
    )

    # =========================================================================
    # SECTION 4: LAYER 3 - SEARCH, RETRIEVAL & WEB SCRAPING
    # =========================================================================
    add_h1("4. Layer 3: Search, Retrieval & Web Scraping Infrastructure")

    add_h2("4.1. Bundled Local SearXNG Instance")
    doc.add_paragraph(
        "At the heart of Veridex's retrieval pipeline is a bundled, locally-managed SearXNG instance (`desktop/searxng.mjs`, `src/lib/searxng.ts`)."
    )
    add_why_box(
        "SearXNG is an open-source, privacy-respecting metasearch engine that aggregates queries across 70+ search engines (Google, DuckDuckGo, Bing, ArXiv, Reddit, Wikipedia, GitHub) into a single unified JSON API. "
        "It strips all tracking cookies, IP addresses, and user identifiers, guaranteeing complete research anonymity. "
        "Crucially, SearXNG costs $0.00 in API fees, freeing Veridex from metered commercial search APIs (like Bing Search API at $10-$25 per 1,000 queries).",
        "Google Custom Search API was rejected due to restrictive daily query quotas (100 free/day) and aggressive user tracking. "
        "Tavily and Brave Search were rejected because they introduce recurring subscription costs and centralized query logging."
    )

    add_h2("4.2. Headless Playwright (Chromium) & Mozilla Readability")
    doc.add_paragraph(
        "In Quality and Deep Research modes, top search results are scraped using headless Playwright (`src/lib/agents/search/researcher/actions/scrapeURL.ts`) and distilled via Mozilla Readability."
    )
    add_why_box(
        "Modern websites are heavily dynamic Single Page Applications (SPAs) built with React, Vue, or Angular. Plain HTTP requests (like Axios or Fetch) receive empty HTML shells without content. "
        "Playwright spins up an actual headless Chromium browser, executes JavaScript, waits for the DOM to hydrate, and captures the true rendered content. "
        "Mozilla Readability (the exact engine powering Firefox Reader View) then strips all navigation bars, sidebars, cookie banners, advertisements, and footer links, leaving pure, distraction-free article text for the factual extraction pipeline.",
        "Cheerio and Beautiful Soup were rejected because they cannot execute JavaScript, failing to scrape up to 60% of modern dynamic web pages. "
        "Puppeteer was rejected in favor of Playwright due to Playwright's superior auto-waiting and browser lifecycle stability."
    )

    add_h2("4.3. Tiktoken (`js-tiktoken`) Context Budgeter")
    doc.add_paragraph(
        "Before feeding retrieved search findings to the writer LLM, chunks are budgeted using `js-tiktoken` (`src/lib/agents/search/contextBudget.ts`)."
    )
    add_why_box(
        "LLMs have finite context windows and experience 'lost-in-the-middle' attention degradation when flooded with excessive text. "
        "`js-tiktoken` is a pure JavaScript port of OpenAI's official BPE tokenizer. It computes exact token counts without requiring native Python or C++ bindings, enforcing strict token caps (16,000 tokens for search; 32,000 tokens for deep research) and preventing context window overflow.",
        "Character-based heuristics (e.g. dividing length by 4) were rejected because token lengths vary wildly across code, multilingual text, and special symbols, risking prompt overflow crashes."
    )

    # =========================================================================
    # SECTION 5: LAYER 4 - GENERATIVE FOUNDATION MODELS
    # =========================================================================
    add_h1("5. Layer 4: Generative Foundation Models & Provider Adapters")

    add_h2("5.1. OpenRouter Integration (NVIDIA Nemotron Free Tier)")
    doc.add_paragraph(
        "Veridex implements a dedicated provider for OpenRouter (`src/lib/models/providers/openrouter/`)."
    )
    add_why_box(
        "OpenRouter provides a unified OpenAI-compatible interface to over 100+ state-of-the-art foundation models with a single API key. "
        "Crucially, it hosts **NVIDIA Nemotron-4 340B and Nemotron 70B/120B on free tiers** (`:free`), allowing users to run frontier-grade reasoning without any personal credit card or API expenses.",
        "Connecting directly to NVIDIA NIM was rejected because OpenRouter automatically handles model routing, failover, and rate-limit retries across distributed inference clusters."
    )

    add_h2("5.2. Google Gemini API Adapter with Resilient Fallback Cascade")
    doc.add_paragraph(
        "Gemini integration is provided via `GeminiLLM` (`src/lib/models/providers/gemini/geminiLLM.ts`)."
    )
    add_why_box(
        "Google Gemini Flash offers extreme generation speed (~150 tokens/sec) and a generous free tier. "
        "To insulate users against Google's frequent transient 503 (High Demand) and 429 (Rate Limit) errors, Veridex built a custom intelligent adapter with: "
        "(1) Automated exponential backoff retries (1.5s, 3.0s); "
        "(2) Deprecated model aliasing (`models/gemini-2.5-pro` -> `models/gemini-flash-latest`); and "
        "(3) Model fallback cascading across sibling models (`gemini-flash-latest` -> `gemini-flash-lite-latest` -> `gemini-3.8-flash`).",
        "Direct Google GenAI SDK was wrapped in OpenAI-compatible abstractions so that all models in the system share identical streaming, tool-calling, and pricing interfaces."
    )

    add_h2("5.3. Local Ollama Runtime")
    doc.add_paragraph(
        "For offline, private, and internal utility tasks, Veridex natively connects to Ollama (`localhost:11434`)."
    )
    add_why_box(
        "Ollama is the premier local LLM runtime, providing automated GPU layer offloading (CUDA / Apple Metal / ROCm) and GGUF model quantization. "
        "It executes internal agent tasks (intent classification, query planning, and claim decomposition) with **zero latency overhead from cloud networks, zero API cost, and 100% data privacy**.",
        "vLLM and LM Studio were rejected because Ollama provides the cleanest, simplest single-binary distribution for non-technical desktop users."
    )

    # =========================================================================
    # SECTION 6: LAYER 5 - ADVERSARIAL VERIFICATION (LAYA)
    # =========================================================================
    add_h1("6. Layer 5: Adversarial Verification & Deep Learning (LAYA)")

    add_h2("6.1. Python 3.12 Deep Learning Environment")
    doc.add_paragraph(
        "The Verification Engine is built in Python 3.12 (`verification/`)."
    )
    add_why_box(
        "Python is the undisputed standard for modern machine learning, supported by PyTorch, Hugging Face Transformers, and scientific computing packages. "
        "Running the verification engine as a decoupled Python subprocess ensures that heavy PyTorch tensors and GPU memory allocations never interfere with the Node.js web server event loop.",
        "JavaScript/Wasm-based machine learning (ONNX.js / Transformers.js) was evaluated but rejected because browser-grade runtimes cannot reliably utilize discrete NVIDIA GPUs for 400M+ parameter bidirectional encoders at scale."
    )

    add_h2("6.2. LAYA (ModernBERT-large / mmBERT) Non-Autoregressive Scorer")
    doc.add_paragraph(
        "Claim validation is powered by LAYA (`verification/laya_scorer.py`), developed by Nandha Kishor."
    )
    add_why_box(
        "LAYA is a non-autoregressive System 1 decision engine. While traditional LLMs generate text token-by-token (taking ~3-5 seconds per claim), "
        "LAYA processes the entire claim-evidence pair in a single encoder forward pass, completing entailment classification in **~35ms on GPU and ~200ms on CPU**. "
        "Furthermore, LAYA features three specialized heads: "
        "(1) `choice` (SUPPORTED / CONTRADICTED / UNCERTAIN); "
        "(2) `score` (ordinal strength 0–4); and "
        "(3) `noul` (calibrated probability trained via Brier score and log score). "
        "Its probabilities are statistically calibrated, meaning a 90% confidence score represents true 90% empirical precision.",
        "Using GPT-4o or Claude as a claim judge was rejected because verifying 6 claims would take 30+ seconds and cost $0.05 per query, making real-time verification completely unusable."
    )

    add_h2("6.3. Ollama `qwen2.5:3b` for Claim Decomposition")
    doc.add_paragraph(
        "Atomic claim isolation is handled by Ollama running `qwen2.5:3b` (`verification/claim_decomposer.py`)."
    )
    add_why_box(
        "`qwen2.5:3b` is arguably the best compact open-weights model in the world for structured JSON adherence and instruction following. "
        "It reliably extracts atomic factual propositions from complex prose while ignoring opinions, advice, and conversational greetings. "
        "At 3B parameters, it loads in under 2GB of VRAM and executes fast on consumer hardware.",
        "Llama 3.2 1B and Gemma 2B were evaluated but rejected because smaller 1B/2B models frequently choke on grammar-constrained JSON schemas, emitting empty responses or malformed markdown fences."
    )

    add_h2("6.4. Inter-Process Communication (JSON Stdin/Stdout Bridge)")
    doc.add_paragraph(
        "The bridge between Node.js and Python is implemented via `child_process.spawn` piping JSON over standard I/O (`src/app/api/verify/route.ts`, `verification/bridge.py`)."
    )
    add_why_box(
        "JSON over stdin/stdout provides a clean, dependency-free, cross-platform boundary that requires zero extra networking ports, zero firewall configurations, and zero external daemon management. "
        "Node serializes `{answer, sources, backend}` to child stdin, and reads the resulting `{claims, trust}` JSON from child stdout upon exit.",
        "gRPC and HTTP microservices were considered, but standard I/O IPC was chosen for desktop simplicity to avoid port collision issues on user PCs."
    )

    # =========================================================================
    # SECTION 7: LAYER 6 - DETERMINISTIC TRUST ENGINE
    # =========================================================================
    add_h1("7. Layer 6: Deterministic Mathematical Trust Engine")

    add_h2("7.1. Pure Closed-Form Python Mathematics (Zero-LLM)")
    doc.add_paragraph(
        "The final aggregation of verification scores is performed by `verification/trust_engine.py`."
    )
    add_why_box(
        "Every existing commercial AI system uses an LLM to generate qualitative trust summaries ('I am fairly confident...'), which introduces secondary hallucination. "
        "Veridex's Trust Engine completely eliminates LLMs from the scoring loop: it uses pure closed-form directional signed confidence mathematics: "
        "`s_i = +c_i` for Supported, `-c_i` for Contradicted, and `0.0` for Uncertain. "
        "The resulting aggregate score is projected monotonically: `Trust = (S + 1.0) / 2.0`. "
        "This guarantees that the trust score is **deterministic, tamper-proof, auditable, and mathematically bounded between 0% and 100%**.",
        "LLM-as-a-judge for score aggregation was rejected because probabilistic models can yield different trust numbers for identical verification inputs, destroying scientific reproducibility."
    )

    # =========================================================================
    # SECTION 8: COMPREHENSIVE SUMMARY MATRIX
    # =========================================================================
    add_h1("8. Comprehensive Tech Stack Summary Matrix")
    doc.add_paragraph(
        "The following master reference table summarizes every technology, its functional tier, alternatives considered, and the core justification for its inclusion in Veridex:"
    )

    tbl = doc.add_table(rows=1, cols=4)
    style_table(
        tbl,
        [1.3, 1.4, 1.8, 2.0],
        ["Tool / Technology", "Category / Layer", "Alternatives Rejected", "Core Reason for Selection"],
        [
            ["Next.js 16 (App Router)", "Web Framework", "Vite + React, Remix, Nuxt", "Native streaming route handlers, React Server Components, unified API + UI"],
            ["React 19", "UI Library", "Vue 3, Svelte 5", "Concurrent rendering, optimized streaming hydration, massive ecosystem"],
            ["Tailwind CSS", "Styling & Typography", "Styled-Components, Emotion", "Zero runtime overhead, purged utility classes, seamless dark mode tokens"],
            ["SSE + RFC 6902", "Network Streaming", "WebSockets, Long Polling", "Unidirectional HTTP/2 stream, granular JSON Patch DOM mutations"],
            ["SQLite (better-sqlite3)", "Embedded Database", "PostgreSQL, MongoDB, Prisma", "Zero-config serverless local file database, fastest synchronous C++ driver"],
            ["Drizzle ORM", "Database ORM", "Prisma, TypeORM", "Pure TypeScript type-safety, zero binary bloat, clean migration control"],
            ["Electron 34", "Desktop Packaging", "Tauri, Neutralino", "Proven multi-process support, native Chromium windowing, node child process IPC"],
            ["Webpack (--webpack)", "Module Bundler", "Turbopack (dev)", "Avoids Turbopack Windows path-resolution panics, rock-solid stability"],
            ["SearXNG (Bundled)", "Search Aggregator", "Google API, Bing API, Tavily", "100% private, zero query tracking, 70+ engines, zero per-query API fees"],
            ["Playwright Chromium", "Web Scraper", "Puppeteer, Cheerio, Axios", "Full JavaScript hydration for modern dynamic SPAs, auto-waiting stability"],
            ["Mozilla Readability", "Article Extractor", "Beautiful Soup, JSDOM solo", "Official Firefox Reader View algorithm, strips ads and nav bars perfectly"],
            ["Tiktoken (js-tiktoken)", "Token Budgeter", "Character-count heuristics", "Precise BPE token counting, prevents context window overflow and cost bloat"],
            ["OpenRouter API", "Cloud Model Gateway", "Direct NVIDIA NIM, Groq solo", "Unified multi-vendor gateway, access to free NVIDIA Nemotron models"],
            ["Google Gemini Flash", "Generative Model", "GPT-3.5, Claude Haiku solo", "Ultra-fast generation (~150 tok/s), generous free tier, multimodal ready"],
            ["Ollama Runtime", "Local LLM Server", "vLLM, LM Studio, llama.cpp", "Automated GPU offload, simple binary distribution, clean REST endpoints"],
            ["Python 3.12", "Verification Runtime", "Node.js ML, Rust ML", "Universal standard for deep learning, PyTorch and Transformers ecosystem"],
            ["LAYA (ModernBERT)", "Claim Scorer", "GPT-4o, Claude Judge, Cross-Encoder", "Non-autoregressive ~35ms GPU forward pass, calibrated proper-scoring rules"],
            ["Qwen 2.5:3b", "Utility Agent Model", "Gemma 2B, Llama 3.2 1B", "Best-in-class compact model for structured JSON schema without formatting errors"],
            ["Deterministic Trust Math", "Scoring Engine", "LLM-as-a-Judge, heuristic rules", "Pure closed-form mathematics, auditable, deterministic, zero hallucination"],
        ]
    )

    return doc

if __name__ == '__main__':
    doc = create_tech_stack_document()

    dest1 = r"C:\Users\Muhammed Sabith\Desktop\Veridex_Tech_Stack_and_Tools_Deep_Dive.docx"
    dest2 = r"C:\Users\Muhammed Sabith\Desktop\veridex\docs\Veridex_Tech_Stack_and_Tools_Deep_Dive.docx"

    doc.save(dest1)
    print(f"Saved primary to: {dest1}")
    try:
        os.makedirs(os.path.dirname(dest2), exist_ok=True)
        doc.save(dest2)
        print(f"Saved replica to: {dest2}")
    except Exception as e:
        print("Could not save replica:", e)
