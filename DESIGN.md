# Design System (`DESIGN.md`) — Agentic Ontology Starter

- **Scope**: All web surfaces in `src/web/static/` — Starter Studio `v6.14.0` (`studio.html`, `studio.js`, `studio.css`, `studio_i18n.json`, `flows_v5.js`), Reference Wizard `/wizard` (`index.html`, `app.js`, `app.css`, `i18n.json`, `flows.js`), and the shared flow renderer `aolflow.js` / `aolflow.css`.
- **Visual alignment**: Shares the unified **Studio v6** light visual grammar across the **Starter Notebook Lab**, **Starter Studio**, and the **Production Reference Studio** (`0. Overview`).
- **Core principle**: Single light theme — crisp white cards, hairline borders, high-contrast charcoal/slate typography, and accurate information rendered through layered diagrams, tables, and live execution logs.
- **Default locale**: **English (`en`) by default** on all routes (`/`, `/wizard`, `/admin`) with instant client-side **`EN | KO`** toggle and 100% key parity.

---

## 1. Design Tokens

| Category | Values |
| :--- | :--- |
| Typography | `"Pretendard Variable", "Pretendard", -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Segoe UI", Roboto, sans-serif` · Monospace `ui-monospace, SFMono-Regular, Menlo, monospace` |
| Text | Primary `#1d1d1f` · Secondary `#6e6e73` · Muted `#86868b` |
| Surfaces & Borders | Page `#f5f5f7` · Card `#ffffff` · Borders `#e3e3e8` / `#d2d2d7` · Lane `#f7f7f9` + `#eeeef2` |
| Elevation | `--shadow-1: 0 1px 2px rgba(0,0,0,.04), 0 4px 14px rgba(0,0,0,.04)` · `--shadow-2: 0 2px 4px rgba(0,0,0,.05), 0 14px 30px rgba(0,0,0,.08)` |
| Layer Accents | Source `#94a3b8` · Wiki `#0ea5e9` · Semantic `#8b5cf6` · Workflow `#f59e0b` · MCP `#10b981` · Agent `#ef4444` · Gemini `#4285f4` · System `#64748b` |
| Studio v6 Palette (`studio.css`) | Calm Slate (`#f8fafc`–`#334155`) + Indigo (`#eef2ff`, `#4f46e5`, `#4338ca`) · Semantic status muted (`#2f855a` ok · `#b7791f` warn · `#c53030` error) |
| Type Scale | Hero / h1 `26px / 750` · Stage header `24px` · Card h2 `17–19px / 720` · h3 `14px / 700` · Body `13px` · Secondary `12.5px` · Meta `11.5px` |
| Radii | Cards `16–18px` · Flow nodes `12px` · Badges `6px` · Pills `999px` |

---

## 2. Layout & Navigation

- **Top bar** (56 px fixed, translucent white + backdrop blur): Google G badge + `Agentic Ontology Starter` + version pill, quick links (`Reference wizard`, `Notebook lab`, `Admin · MCP Portal`), workspace chip, and `EN | KO` toggle.
- **Left rail**: Grouped sections (`Understand` · `Set up · build` · `Studio` · `Hand-off` · `Ops · governance`) with instant hash navigation (`#/start`, `#/studio/agents`, `#/studio/cg`, `#/admin`, etc.).
- **Unified dialogs**: All modals share `modalShell()` (56 px header · close `✕` · scrollable body · right-aligned footer · backdrop / `Esc` close). Native `confirm()` is replaced by `confirmModal()`.
- **Responsive**: Below `1180px`, evidence panels stack under conversations; below `980px`, the rail collapses and grids switch to single column.

---

## 3. Shared Flow Renderer (`aolflow.js` / `aolflow.css`)

- Kept **byte-identical** with the Notebook Lab renderer (`tests/test_wizard.py` enforces equality). Never edit `aolflow.js` or `aolflow.css` directly in isolation; keep starter-specific specs inside `flows_v5.js` and `flows.js`.
- All labels inside flow specs use `[ko, en]` tuples via `AOLFlow.T`.

---

## 4. Bilingual (`EN | KO`) & Quality Invariants

1. Every UI string lives in `studio_i18n.json` (Studio) or `i18n.json` (`/wizard`) with **100% identical key sets and `{placeholder}` parity** between `en` and `ko`.
2. Zero hardcoded Hangul is allowed in `studio.html`, `studio.js`, `index.html`, `app.js`, or any `en` i18n entry (`tests/test_v5.py` and `tests/test_admin_metering.py` enforce this automatically).
3. All interactive flows (`/`, `/wizard`, `#/studio/cg`, `/admin`) are verified at `1440px` desktop viewport with zero horizontal overflow and zero console/JS errors.

---

## 5. Studio v6 Components (Context Graph & Admin Portal)

- **Inline sentence feedback bar (`.fb-bar`)**: Appears calmly below every Wiki / Graph / Hybrid answer card; free-text input is primary with optional 👍/👎 and reason chips.
- **Context Graph tab (`#/studio/cg`)**: 4-Layer architecture strip, 1-click 3-agent demo stepper, layered SVG inspector (`Run → Feedback → Candidate → SME → ChangeSet`), and Before vs. After re-ask comparison.
- **Unified Admin Portal (`/admin`)**: Google Sign-In card (fail-closed RS256 ID token check + 12 h `HttpOnly` cookie), 57-tool Core MCP catalog with search and schema viewer, interactive flow with live BigQuery call counts, and PII-minimized account metering tables.
