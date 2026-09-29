#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Sean Jung (seanjung@google.com). All rights reserved.
# Licensed under CC BY-NC-ND 4.0 (Methodology & Slide Deck) & PolyForm Noncommercial 1.0.0 (Code).

"""
Generator for Agentic Ontology Starter 18-Slide Training Curriculum:
1. Native Google Workspace Slides (.pptx) files:
   - slides/ko/agentic_ontology_methodology_training_ko.pptx
   - slides/en/agentic_ontology_methodology_training_en.pptx
   - slides/agentic_ontology_methodology_training_ko.pptx
   - slides/agentic_ontology_methodology_training_en.pptx
2. Interactive Google Slides-Style HTML5 Presentation Decks (.html):
   - slides/ko/agentic_ontology_methodology_slides_ko.html (Bilingual KOR/ENG switcher, default KO)
   - slides/en/agentic_ontology_methodology_slides_en.html (100% English, 0 Hangul characters)
   - ../explanations/exp_agentic_ontology_methodology.html (Bilingual Google Slides-style deck)
"""

import base64
import json
import os
import shutil
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

THIS_DIR = Path(__file__).resolve().parent
STARTER_ROOT = THIS_DIR.parent
WORKSPACE_ROOT = STARTER_ROOT.parent
ASSETS_DIR = STARTER_ROOT / "notebooks" / "assets"

sys.path.insert(0, str(THIS_DIR))
from slide_specs_ko import SLIDES_KO
from slide_specs_en import SLIDES_EN


def hex_to_rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def tint_hex(hex_str: str, weight: float = 0.90) -> RGBColor:
    """Blend hex color with white for soft pastel badge/header backgrounds."""
    h = hex_str.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    tr = int(r + (255 - r) * weight)
    tg = int(g + (255 - g) * weight)
    tb = int(b + (255 - b) * weight)
    return RGBColor(tr, tg, tb)


def set_shape_fill_and_line(shape, fill_rgb: RGBColor, line_rgb: RGBColor = None, line_pt: float = 1.0):
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_rgb
    if line_rgb is not None:
        shape.line.color.rgb = line_rgb
        shape.line.width = Pt(line_pt)
    else:
        shape.line.fill.background()


def build_pptx_deck(slides_spec: list, out_path: Path, lang: str = "ko") -> None:
    prs = Presentation()
    # 16:9 Widescreen (13.333 in x 7.5 in) — Standard Google Workspace Slides aspect ratio
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    font_family = "Pretendard" if lang == "ko" else "Arial"
    total_slides = len(slides_spec)

    bg_color = hex_to_rgb("#F8FAFC")
    white = hex_to_rgb("#FFFFFF")
    slate_900 = hex_to_rgb("#0F172A")
    slate_700 = hex_to_rgb("#334155")
    slate_500 = hex_to_rgb("#64748B")
    border_slate = hex_to_rgb("#CBD5E1")
    table_alt = hex_to_rgb("#F1F5F9")

    for sp in slides_spec:
        slide = prs.slides.add_slide(blank_layout)
        accent_hex = sp.get("accent", "#1A73E8")
        accent_rgb = hex_to_rgb(accent_hex)
        accent_soft = tint_hex(accent_hex, 0.88)

        # 1. Full slide light canvas background
        bg_rect = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5)
        )
        set_shape_fill_and_line(bg_rect, bg_color, None)

        # 2. Top Google Enterprise accent bar
        top_bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.08)
        )
        set_shape_fill_and_line(top_bar, accent_rgb, None)

        # 3. Header container card
        hdr_box = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.40), Inches(0.16), Inches(12.533), Inches(0.96)
        )
        hdr_box.adjustments[0] = 0.02
        set_shape_fill_and_line(hdr_box, white, border_slate, 0.75)

        # Badge pill
        badge_pill = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.58), Inches(0.26), Inches(3.15), Inches(0.26)
        )
        badge_pill.adjustments[0] = 0.5
        set_shape_fill_and_line(badge_pill, accent_soft, accent_rgb, 0.75)
        tf_b = badge_pill.text_frame
        tf_b.word_wrap = False
        tf_b.margin_left = tf_b.margin_right = Inches(0.08)
        tf_b.margin_top = tf_b.margin_bottom = Inches(0.02)
        p_b = tf_b.paragraphs[0]
        p_b.alignment = PP_ALIGN.CENTER
        r_b = p_b.add_run()
        r_b.text = sp["badge"]
        r_b.font.name = font_family
        r_b.font.size = Pt(8.5)
        r_b.font.bold = True
        r_b.font.color.rgb = accent_rgb

        # Slide Number Pill (Right)
        num_pill = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(11.75), Inches(0.26), Inches(1.00), Inches(0.26)
        )
        num_pill.adjustments[0] = 0.5
        set_shape_fill_and_line(num_pill, hex_to_rgb("#F1F5F9"), border_slate, 0.75)
        tf_n = num_pill.text_frame
        tf_n.margin_left = tf_n.margin_right = Inches(0.04)
        tf_n.margin_top = tf_n.margin_bottom = Inches(0.02)
        p_n = tf_n.paragraphs[0]
        p_n.alignment = PP_ALIGN.CENTER
        r_n = p_n.add_run()
        r_n.text = f"{sp['slide_no']:02d} / {total_slides:02d}"
        r_n.font.name = font_family
        r_n.font.size = Pt(9)
        r_n.font.bold = True
        r_n.font.color.rgb = slate_700

        # Title & Subtitle inside header
        tb_title = slide.shapes.add_textbox(Inches(0.56), Inches(0.52), Inches(12.20), Inches(0.56))
        tf_t = tb_title.text_frame
        tf_t.word_wrap = True
        tf_t.margin_left = tf_t.margin_right = tf_t.margin_top = tf_t.margin_bottom = Inches(0.01)
        p_t = tf_t.paragraphs[0]
        r_t = p_t.add_run()
        r_t.text = sp["title"]
        r_t.font.name = font_family
        r_t.font.size = Pt(16.5)
        r_t.font.bold = True
        r_t.font.color.rgb = slate_900

        p_sub = tf_t.add_paragraph()
        r_sub = p_sub.add_run()
        r_sub.text = sp["subtitle"]
        r_sub.font.name = font_family
        r_sub.font.size = Pt(10.0)
        r_sub.font.color.rgb = slate_500

        # 4. Optional Architecture Flow Banner Image
        banner_name = sp.get("banner_img")
        banner_path = ASSETS_DIR / banner_name if banner_name else None
        has_banner = bool(banner_path and banner_path.exists())

        if has_banner:
            banner_card = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.40), Inches(1.20), Inches(12.533), Inches(1.62)
            )
            banner_card.adjustments[0] = 0.02
            set_shape_fill_and_line(banner_card, white, border_slate, 0.75)
            slide.shapes.add_picture(
                str(banner_path), Inches(0.55), Inches(1.25), height=Inches(1.52)
            )
            cards_top = Inches(2.90)
            cards_height = Inches(1.86)
            table_top = Inches(4.84)
            table_height = Inches(1.86)
        else:
            cards_top = Inches(1.22)
            cards_height = Inches(2.42)
            table_top = Inches(3.74)
            table_height = Inches(2.96)

        # 5. Visual Cards Row (3 cards)
        cards = sp.get("cards", [])
        num_cards = len(cards)
        if num_cards > 0:
            gap = Inches(0.20)
            total_w = Inches(12.533)
            card_w = (total_w - gap * (num_cards - 1)) / num_cards
            for idx, c in enumerate(cards):
                c_left = Inches(0.40) + idx * (card_w + gap)
                c_accent = hex_to_rgb(c.get("accent", accent_hex))
                c_soft = tint_hex(c.get("accent", accent_hex), 0.90)

                card_shape = slide.shapes.add_shape(
                    MSO_SHAPE.ROUNDED_RECTANGLE, c_left, cards_top, card_w, cards_height
                )
                card_shape.adjustments[0] = 0.03
                set_shape_fill_and_line(card_shape, white, border_slate, 0.75)

                # Card top stripe
                stripe = slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE, c_left, cards_top, card_w, Inches(0.06)
                )
                set_shape_fill_and_line(stripe, c_accent, None)

                # Tag pill inside card
                tag_pill = slide.shapes.add_shape(
                    MSO_SHAPE.ROUNDED_RECTANGLE,
                    c_left + Inches(0.14),
                    cards_top + Inches(0.12),
                    card_w - Inches(0.28),
                    Inches(0.24),
                )
                tag_pill.adjustments[0] = 0.4
                set_shape_fill_and_line(tag_pill, c_soft, None)
                tf_tag = tag_pill.text_frame
                tf_tag.margin_left = Inches(0.08)
                tf_tag.margin_top = Inches(0.01)
                p_tag = tf_tag.paragraphs[0]
                r_tag = p_tag.add_run()
                r_tag.text = c["tag"]
                r_tag.font.name = font_family
                r_tag.font.size = Pt(8.0)
                r_tag.font.bold = True
                r_tag.font.color.rgb = c_accent

                # Card title & bullets
                tb_c = slide.shapes.add_textbox(
                    c_left + Inches(0.14),
                    cards_top + Inches(0.40),
                    card_w - Inches(0.28),
                    cards_height - Inches(0.46),
                )
                tf_c = tb_c.text_frame
                tf_c.word_wrap = True
                tf_c.margin_left = tf_c.margin_right = tf_c.margin_top = tf_c.margin_bottom = Inches(0.02)

                p_ct = tf_c.paragraphs[0]
                p_ct.space_after = Pt(4)
                r_ct = p_ct.add_run()
                r_ct.text = c["title"]
                r_ct.font.name = font_family
                r_ct.font.size = Pt(11.5 if has_banner else 12.5)
                r_ct.font.bold = True
                r_ct.font.color.rgb = slate_900

                for b_line in c.get("bullets", []):
                    p_bl = tf_c.add_paragraph()
                    p_bl.space_after = Pt(2.5 if has_banner else 4.0)
                    r_bl = p_bl.add_run()
                    r_bl.text = f"• {b_line}"
                    r_bl.font.name = font_family
                    r_bl.font.size = Pt(8.8 if has_banner else 9.5)
                    r_bl.font.color.rgb = slate_700

        # 6. Structured Comparison / Specification Table
        tbl_spec = sp.get("table")
        if tbl_spec:
            headers = tbl_spec["headers"]
            rows = tbl_spec["rows"]
            n_rows = len(rows) + 1
            n_cols = len(headers)

            t_shape = slide.shapes.add_table(
                n_rows, n_cols, Inches(0.40), table_top, Inches(12.533), table_height
            )
            table = t_shape.table

            # Column widths proportional
            col_weights = [1.15, 2.15, 2.25, 2.0] if n_cols == 4 else (
                [1.1, 1.5, 1.8, 1.1, 1.5] if n_cols == 5 else [1.3, 0.8, 1.2, 1.6, 1.0, 1.6]
            )
            weight_sum = sum(col_weights[:n_cols])
            for ci in range(n_cols):
                table.columns[ci].width = int(Inches(12.533) * (col_weights[ci] / weight_sum))

            # Header Row
            for ci, h_text in enumerate(headers):
                cell = table.cell(0, ci)
                cell.fill.solid()
                cell.fill.fore_color.rgb = slate_900
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                cell.margin_left = cell.margin_right = Inches(0.08)
                cell.margin_top = cell.margin_bottom = Inches(0.03)
                p = cell.text_frame.paragraphs[0]
                r = p.add_run()
                r.text = h_text
                r.font.name = font_family
                r.font.size = Pt(8.8 if has_banner else 9.2)
                r.font.bold = True
                r.font.color.rgb = white

            # Data Rows
            for ri, row_data in enumerate(rows):
                row_bg = white if ri % 2 == 0 else table_alt
                for ci, val in enumerate(row_data):
                    cell = table.cell(ri + 1, ci)
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = row_bg
                    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                    cell.margin_left = cell.margin_right = Inches(0.08)
                    cell.margin_top = cell.margin_bottom = Inches(0.02)
                    p = cell.text_frame.paragraphs[0]
                    r = p.add_run()
                    r.text = str(val)
                    r.font.name = font_family
                    r.font.size = Pt(8.3 if has_banner else 8.8)
                    r.font.bold = (ci == 0)
                    r.font.color.rgb = accent_rgb if ci == 0 else slate_700

        # 7. Bottom Takeaway & Footer Bar
        takeaway_box = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.40), Inches(6.78), Inches(12.533), Inches(0.46)
        )
        takeaway_box.adjustments[0] = 0.15
        set_shape_fill_and_line(takeaway_box, accent_soft, accent_rgb, 0.75)
        tf_tk = takeaway_box.text_frame
        tf_tk.word_wrap = True
        tf_tk.margin_left = tf_tk.margin_right = Inches(0.14)
        tf_tk.margin_top = tf_tk.margin_bottom = Inches(0.04)
        p_tk = tf_tk.paragraphs[0]
        r_tk = p_tk.add_run()
        r_tk.text = f"KEY TAKEAWAY  |  {sp['takeaway']}"
        r_tk.font.name = font_family
        r_tk.font.size = Pt(9.2)
        r_tk.font.bold = True
        r_tk.font.color.rgb = slate_900

        # Copyright & License micro-footer
        tb_foot = slide.shapes.add_textbox(Inches(0.42), Inches(7.25), Inches(12.50), Inches(0.22))
        tf_f = tb_foot.text_frame
        tf_f.margin_left = tf_f.margin_top = Inches(0)
        p_f = tf_f.paragraphs[0]
        r_f = p_f.add_run()
        if lang == "ko":
            r_f.text = (
                "Agentic Ontology Starter Methodology Training Deck  |  "
                "Methodology: CC BY-NC-ND 4.0 · Code: PolyForm Noncommercial 1.0.0  |  Contact: seanjung@google.com"
            )
        else:
            r_f.text = (
                "Agentic Ontology Starter Methodology Training Deck  |  "
                "Methodology: CC BY-NC-ND 4.0 · Code: PolyForm Noncommercial 1.0.0  |  Contact: seanjung@google.com"
            )
        r_f.font.name = font_family
        r_f.font.size = Pt(7.5)
        r_f.font.color.rgb = slate_500

        # 8. Speaker Notes (Google Workspace Slides native speaker notes)
        notes_slide = slide.notes_slide
        notes_tf = notes_slide.notes_text_frame
        notes_tf.text = sp.get("speaker_notes", "")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    print(f"[OK] Saved PPTX ({lang.upper()}): {out_path} ({out_path.stat().st_size:,} bytes)")


def load_banner_data_uris() -> dict:
    uris = {}
    if not ASSETS_DIR.exists():
        return uris
    for png in sorted(ASSETS_DIR.glob("*.png")):
        b64 = base64.b64encode(png.read_bytes()).decode("ascii")
        uris[png.name] = f"data:image/png;base64,{b64}"
    return uris


def build_html_deck(
    out_path: Path,
    default_lang: str = "ko",
    english_only: bool = False,
    pptx_rel_path: str = "agentic_ontology_methodology_training_ko.pptx",
) -> None:
    banner_uris = load_banner_data_uris()

    def enrich_slides(slides_list):
        enriched = []
        for s in slides_list:
            item = dict(s)
            bname = item.get("banner_img")
            item["banner_data_uri"] = banner_uris.get(bname, "") if bname else ""
            enriched.append(item)
        return enriched

    en_data = enrich_slides(SLIDES_EN)
    ko_data = enrich_slides(SLIDES_KO) if not english_only else en_data

    payload_json = json.dumps(
        {"en": en_data, "ko": ko_data},
        ensure_ascii=(english_only),
        indent=2,
    )

    lang_btn_html = (
        ""
        if english_only
        else """
        <div class="lang-pill" role="group" aria-label="Language Switch">
          <button id="btn-lang-ko" class="lang-btn active" onclick="setDeckLang('ko')">KOR</button>
          <button id="btn-lang-en" class="lang-btn" onclick="setDeckLang('en')">ENG</button>
        </div>
        """
    )

    page_title = (
        "Agentic Ontology Starter — 5-Stage Methodology Training Slides (Google Slides Deck)"
        if english_only
        else "Agentic Ontology Starter — 5-Stage 방법론 교육용 슬라이드 (Google Workspace Slides)"
    )

    html = f"""<!DOCTYPE html>
<html lang="{default_lang}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{page_title}</title>
  <link rel="preconnect" href="https://cdn.jsdelivr.net" />
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" />
  <style>
    :root {{
      --bg-app: #F1F3F4;
      --bg-surface: #FFFFFF;
      --bg-stage: #F8FAFC;
      --text-primary: #0F172A;
      --text-secondary: #334155;
      --text-muted: #64748B;
      --border-light: #DADCE0;
      --border-card: #CBD5E1;
      --google-blue: #1A73E8;
      --google-green: #0F9D58;
      --google-indigo: #4F46E5;
      --google-amber: #D97706;
      --slides-yellow: #FBBC04;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
      background: var(--bg-app);
      color: var(--text-primary);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    /* Google Workspace Slides Top Header (48px) */
    .gslides-topbar {{
      height: 48px;
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-light);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      flex-shrink: 0;
      z-index: 20;
    }}
    .brand-left {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .slides-icon {{
      width: 28px;
      height: 28px;
      border-radius: 6px;
      background: var(--slides-yellow);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-weight: 800;
      font-size: 14px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.12);
    }}
    .deck-title-wrap {{
      display: flex;
      flex-direction: column;
    }}
    .deck-title {{
      font-size: 14px;
      font-weight: 700;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .format-badge {{
      font-size: 10px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 999px;
      background: #FEF7E0;
      color: #B06000;
      border: 1px solid #FDE293;
    }}
    .deck-subtitle {{
      font-size: 11px;
      color: var(--text-muted);
    }}
    .toolbar-right {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .nav-pill {{
      display: flex;
      align-items: center;
      gap: 4px;
      background: #F8FAFC;
      border: 1px solid var(--border-light);
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 12px;
      font-weight: 600;
    }}
    .nav-btn {{
      border: none;
      background: transparent;
      cursor: pointer;
      padding: 3px 8px;
      border-radius: 999px;
      font-weight: 700;
      color: var(--text-secondary);
    }}
    .nav-btn:hover {{ background: #E2E8F0; }}
    .lang-pill {{
      display: flex;
      background: #F1F5F9;
      border: 1px solid var(--border-card);
      border-radius: 999px;
      padding: 2px;
    }}
    .lang-btn {{
      border: none;
      background: transparent;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      cursor: pointer;
    }}
    .lang-btn.active {{
      background: var(--google-blue);
      color: #fff;
    }}
    .action-btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      border: 1px solid var(--border-light);
      background: var(--bg-surface);
      color: var(--text-secondary);
      cursor: pointer;
      text-decoration: none;
      transition: all 0.15s ease;
    }}
    .action-btn:hover {{
      background: #F8FAFC;
      border-color: var(--google-blue);
      color: var(--google-blue);
    }}
    .action-btn.primary {{
      background: var(--google-blue);
      color: #fff;
      border-color: var(--google-blue);
    }}
    .action-btn.primary:hover {{
      background: #1557B0;
    }}
    /* Workspace Layout */
    .gslides-workspace {{
      flex: 1;
      display: flex;
      overflow: hidden;
    }}
    /* Left Filmstrip Thumbnail Rail */
    .filmstrip {{
      width: 230px;
      background: var(--bg-surface);
      border-right: 1px solid var(--border-light);
      overflow-y: auto;
      padding: 12px 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      flex-shrink: 0;
    }}
    .thumb-item {{
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 8px;
      border-radius: 8px;
      border: 2px solid transparent;
      background: #F8FAFC;
      cursor: pointer;
      transition: all 0.12s ease;
    }}
    .thumb-item:hover {{
      background: #EFF6FF;
      border-color: #BFDBFE;
    }}
    .thumb-item.active {{
      background: #E8F0FE;
      border-color: var(--google-blue);
    }}
    .thumb-no {{
      font-size: 11px;
      font-weight: 800;
      color: var(--text-muted);
      min-width: 20px;
      padding-top: 2px;
    }}
    .thumb-item.active .thumb-no {{
      color: var(--google-blue);
    }}
    .thumb-card {{
      flex: 1;
      background: #fff;
      border: 1px solid var(--border-light);
      border-radius: 5px;
      padding: 6px 8px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }}
    .thumb-badge {{
      font-size: 8.5px;
      font-weight: 800;
      color: var(--google-blue);
      letter-spacing: 0.02em;
      margin-bottom: 3px;
      display: block;
    }}
    .thumb-title {{
      font-size: 10.5px;
      font-weight: 600;
      color: var(--text-primary);
      line-height: 1.3;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}
    /* Center Stage + Bottom Speaker Notes */
    .stage-column {{
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      background: var(--bg-app);
    }}
    .canvas-viewport {{
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 18px 24px;
      overflow: auto;
    }}
    /* 16:9 Slide Canvas */
    .slide-canvas {{
      width: min(1180px, 100%);
      aspect-ratio: 16 / 9;
      background: var(--bg-stage);
      border-radius: 12px;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.14), 0 1px 3px rgba(15, 23, 42, 0.08);
      border: 1px solid var(--border-card);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      position: relative;
    }}
    .slide-top-stripe {{
      height: 6px;
      width: 100%;
      background: var(--google-blue);
      flex-shrink: 0;
    }}
    .slide-body {{
      flex: 1;
      padding: 16px 24px 12px 24px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      overflow: hidden;
    }}
    .slide-header-card {{
      background: #FFFFFF;
      border: 1px solid var(--border-card);
      border-radius: 10px;
      padding: 10px 16px;
      display: flex;
      flex-direction: column;
      gap: 4px;
      flex-shrink: 0;
    }}
    .slide-header-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .slide-badge-pill {{
      font-size: 10px;
      font-weight: 800;
      padding: 3px 10px;
      border-radius: 999px;
      letter-spacing: 0.03em;
    }}
    .slide-num-pill {{
      font-size: 11px;
      font-weight: 700;
      color: var(--text-secondary);
      background: #F1F5F9;
      border: 1px solid var(--border-card);
      padding: 2px 10px;
      border-radius: 999px;
    }}
    .slide-main-title {{
      font-size: 20px;
      font-weight: 800;
      color: var(--text-primary);
      letter-spacing: -0.02em;
      line-height: 1.25;
    }}
    .slide-main-subtitle {{
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.35;
    }}
    .slide-banner-box {{
      background: #FFFFFF;
      border: 1px solid var(--border-card);
      border-radius: 10px;
      padding: 6px 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      max-height: 128px;
      flex-shrink: 0;
    }}
    .slide-banner-box img {{
      max-height: 114px;
      max-width: 100%;
      object-fit: contain;
    }}
    .cards-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      flex-shrink: 0;
    }}
    .v-card {{
      background: #FFFFFF;
      border: 1px solid var(--border-card);
      border-radius: 10px;
      padding: 10px 14px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      position: relative;
      overflow: hidden;
    }}
    .v-card-stripe {{
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 4px;
    }}
    .v-card-tag {{
      font-size: 9.5px;
      font-weight: 800;
      padding: 2px 8px;
      border-radius: 999px;
      align-self: flex-start;
      margin-top: 2px;
    }}
    .v-card-title {{
      font-size: 13.5px;
      font-weight: 800;
      color: var(--text-primary);
    }}
    .v-card-bullets {{
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .v-card-bullets li {{
      font-size: 11px;
      color: var(--text-secondary);
      line-height: 1.35;
      padding-left: 10px;
      position: relative;
    }}
    .v-card-bullets li::before {{
      content: "•";
      position: absolute;
      left: 0;
      color: var(--google-blue);
      font-weight: 700;
    }}
    /* Slide Table */
    .slide-table-wrap {{
      flex: 1;
      background: #FFFFFF;
      border: 1px solid var(--border-card);
      border-radius: 10px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    table.slide-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
    }}
    table.slide-table th {{
      background: #0F172A;
      color: #FFFFFF;
      text-align: left;
      padding: 6px 10px;
      font-weight: 700;
      font-size: 10.5px;
    }}
    table.slide-table td {{
      padding: 6px 10px;
      border-bottom: 1px solid #E2E8F0;
      color: var(--text-secondary);
      line-height: 1.3;
    }}
    table.slide-table tr:nth-child(even) td {{
      background: #F8FAFC;
    }}
    table.slide-table td:first-child {{
      font-weight: 700;
      color: var(--google-blue);
      white-space: nowrap;
    }}
    /* Takeaway Bar */
    .slide-takeaway {{
      border-radius: 8px;
      padding: 7px 14px;
      font-size: 11.5px;
      font-weight: 700;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }}
    .slide-footer-meta {{
      font-size: 9.5px;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      padding: 0 2px;
      flex-shrink: 0;
    }}
    /* Speaker Notes Panel */
    .speaker-notes-drawer {{
      height: 155px;
      background: var(--bg-surface);
      border-top: 1px solid var(--border-light);
      padding: 10px 20px;
      overflow-y: auto;
      flex-shrink: 0;
      transition: height 0.2s ease;
    }}
    .speaker-notes-drawer.collapsed {{
      height: 34px;
      overflow: hidden;
    }}
    .notes-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
      cursor: pointer;
    }}
    .notes-title {{
      font-size: 11.5px;
      font-weight: 800;
      color: var(--google-blue);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .notes-content {{
      font-size: 12.5px;
      color: var(--text-secondary);
      line-height: 1.55;
      white-space: pre-line;
    }}
  </style>
</head>
<body>
  <header class="gslides-topbar">
    <div class="brand-left">
      <div class="slides-icon" title="Google Workspace Slides">S</div>
      <div class="deck-title-wrap">
        <div class="deck-title">
          <span id="ui-deck-title">Agentic Ontology Starter — 5-Stage Methodology Training Slides</span>
          <span class="format-badge">Google Slides (.pptx + HTML5)</span>
        </div>
        <div class="deck-subtitle" id="ui-deck-sub">
          18-Slide Curriculum · BigQuery Property Graph (ISO GQL) · 3-Layer OKF Wiki · 8 Domain MCPs · 2-Pass Gemini Agent
        </div>
      </div>
    </div>
    <div class="toolbar-right">
      <div class="nav-pill">
        <button class="nav-btn" onclick="prevSlide()" title="Previous Slide (←)">◀</button>
        <span id="slide-counter">01 / 18</span>
        <button class="nav-btn" onclick="nextSlide()" title="Next Slide (→)">▶</button>
      </div>
      {lang_btn_html}
      <button class="action-btn" onclick="toggleNotes()" id="btn-notes">Speaker Notes</button>
      <a class="action-btn primary" id="btn-download-pptx" href="{pptx_rel_path}" download>⬇ Download Google Slides (.pptx)</a>
      <button class="action-btn" onclick="toggleFullscreen()" title="Fullscreen Presentation (F)">⛶ Present</button>
    </div>
  </header>

  <div class="gslides-workspace">
    <aside class="filmstrip" id="filmstrip-list"></aside>
    <main class="stage-column">
      <div class="canvas-viewport">
        <div class="slide-canvas" id="slide-canvas">
          <div class="slide-top-stripe" id="slide-stripe"></div>
          <div class="slide-body" id="slide-body"></div>
        </div>
      </div>
      <section class="speaker-notes-drawer" id="notes-drawer">
        <div class="notes-header" onclick="toggleNotes()">
          <span class="notes-title" id="ui-notes-label">Instructor Speaker Notes (Click to toggle · Press N)</span>
          <span style="font-size:11px;color:#64748B;">Use ← / → / Space to navigate · Press F for Fullscreen</span>
        </div>
        <div class="notes-content" id="notes-body"></div>
      </section>
    </main>
  </div>

  <script>
    const DECK_DATA = {payload_json};
    let currentLang = "{default_lang}";
    let currentIndex = 0;

    function hexWithAlpha(hex, alphaHex) {{
      return hex + alphaHex;
    }}

    function renderFilmstrip() {{
      const slides = DECK_DATA[currentLang];
      const rail = document.getElementById("filmstrip-list");
      rail.innerHTML = slides.map((s, idx) => `
        <div class="thumb-item ${{idx === currentIndex ? 'active' : ''}}" onclick="goToSlide(${{idx}})" id="thumb-${{idx}}">
          <span class="thumb-no">${{String(s.slide_no).padStart(2, '0')}}</span>
          <div class="thumb-card">
            <span class="thumb-badge" style="color:${{s.accent}}">${{s.badge}}</span>
            <div class="thumb-title">${{s.title}}</div>
          </div>
        </div>
      `).join("");
    }}

    function renderActiveSlide() {{
      const slides = DECK_DATA[currentLang];
      const s = slides[currentIndex];
      const total = slides.length;

      document.getElementById("slide-counter").textContent =
        `${{String(s.slide_no).padStart(2, '0')}} / ${{String(total).padStart(2, '0')}}`;
      document.getElementById("slide-stripe").style.background = s.accent;

      const bannerHtml = s.banner_data_uri
        ? `<div class="slide-banner-box"><img src="${{s.banner_data_uri}}" alt="Stage Architecture Flow" /></div>`
        : "";

      const cardsHtml = (s.cards || []).map(c => `
        <div class="v-card">
          <div class="v-card-stripe" style="background:${{c.accent || s.accent}}"></div>
          <span class="v-card-tag" style="background:${{hexWithAlpha(c.accent || s.accent, '18')}};color:${{c.accent || s.accent}}">${{c.tag}}</span>
          <div class="v-card-title">${{c.title}}</div>
          <ul class="v-card-bullets">
            ${{(c.bullets || []).map(b => `<li>${{b}}</li>`).join("")}}
          </ul>
        </div>
      `).join("");

      let tableHtml = "";
      if (s.table) {{
        const ths = s.table.headers.map(h => `<th>${{h}}</th>`).join("");
        const trs = s.table.rows.map(r => `<tr>${{r.map(cell => `<td>${{cell}}</td>`).join("")}}</tr>`).join("");
        tableHtml = `
          <div class="slide-table-wrap">
            <table class="slide-table">
              <thead><tr>${{ths}}</tr></thead>
              <tbody>${{trs}}</tbody>
            </table>
          </div>
        `;
      }}

      const bodyEl = document.getElementById("slide-body");
      bodyEl.innerHTML = `
        <div class="slide-header-card">
          <div class="slide-header-top">
            <span class="slide-badge-pill" style="background:${{hexWithAlpha(s.accent, '18')}};color:${{s.accent}};border:1px solid ${{hexWithAlpha(s.accent, '40')}}">${{s.badge}}</span>
            <span class="slide-num-pill">${{String(s.slide_no).padStart(2, '0')}} / ${{String(total).padStart(2, '0')}}</span>
          </div>
          <div class="slide-main-title">${{s.title}}</div>
          <div class="slide-main-subtitle">${{s.subtitle}}</div>
        </div>
        ${{bannerHtml}}
        <div class="cards-grid">${{cardsHtml}}</div>
        ${{tableHtml}}
        <div class="slide-takeaway" style="background:${{hexWithAlpha(s.accent, '14')}};border:1px solid ${{hexWithAlpha(s.accent, '45')}}">
          <span style="color:${{s.accent}};font-weight:800;">KEY TAKEAWAY |</span>
          <span>${{s.takeaway}}</span>
        </div>
        <div class="slide-footer-meta">
          <span>Agentic Ontology Starter Methodology Training Deck (CC BY-NC-ND 4.0 / PolyForm Noncommercial 1.0.0)</span>
          <span>Commercial Inquiries: seanjung@google.com</span>
        </div>
      `;

      document.getElementById("notes-body").textContent = s.speaker_notes || "";

      // Highlight active thumbnail
      slides.forEach((_, idx) => {{
        const el = document.getElementById(`thumb-${{idx}}`);
        if (el) {{
          el.classList.toggle("active", idx === currentIndex);
          if (idx === currentIndex) {{
            el.scrollIntoView({{ block: "nearest", behavior: "smooth" }});
          }}
        }}
      }});
    }}

    function goToSlide(idx) {{
      const slides = DECK_DATA[currentLang];
      if (idx < 0 || idx >= slides.length) return;
      currentIndex = idx;
      renderActiveSlide();
    }}

    function nextSlide() {{
      const slides = DECK_DATA[currentLang];
      if (currentIndex < slides.length - 1) goToSlide(currentIndex + 1);
    }}

    function prevSlide() {{
      if (currentIndex > 0) goToSlide(currentIndex - 1);
    }}

    function setDeckLang(lang) {{
      if (!DECK_DATA[lang]) return;
      currentLang = lang;
      const btnKo = document.getElementById("btn-lang-ko");
      const btnEn = document.getElementById("btn-lang-en");
      if (btnKo && btnEn) {{
        btnKo.classList.toggle("active", lang === "ko");
        btnEn.classList.toggle("active", lang === "en");
      }}
      const dlBtn = document.getElementById("btn-download-pptx");
      if (dlBtn) {{
        if (window.location.pathname.includes("/slides/ko/") || window.location.pathname.includes("/slides/en/")) {{
          dlBtn.href = lang === "ko"
            ? "../ko/agentic_ontology_methodology_training_ko.pptx"
            : "../en/agentic_ontology_methodology_training_en.pptx";
        }}
      }}
      renderFilmstrip();
      renderActiveSlide();
    }}

    function toggleNotes() {{
      document.getElementById("notes-drawer").classList.toggle("collapsed");
    }}

    function toggleFullscreen() {{
      if (!document.fullscreenElement) {{
        document.documentElement.requestFullscreen().catch(() => {{}});
      }} else {{
        document.exitFullscreen().catch(() => {{}});
      }}
    }}

    window.addEventListener("keydown", (e) => {{
      if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") {{
        e.preventDefault();
        nextSlide();
      }} else if (e.key === "ArrowLeft" || e.key === "PageUp") {{
        e.preventDefault();
        prevSlide();
      }} else if (e.key === "f" || e.key === "F") {{
        e.preventDefault();
        toggleFullscreen();
      }} else if (e.key === "n" || e.key === "N") {{
        e.preventDefault();
        toggleNotes();
      }}
    }});

    renderFilmstrip();
    renderActiveSlide();
  </script>
</body>
</html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"[OK] Saved HTML5 Google Slides Deck: {out_path} ({out_path.stat().st_size:,} bytes)")


def main() -> None:
    ko_dir = THIS_DIR / "ko"
    en_dir = THIS_DIR / "en"
    ko_dir.mkdir(parents=True, exist_ok=True)
    en_dir.mkdir(parents=True, exist_ok=True)

    ko_pptx = ko_dir / "agentic_ontology_methodology_training_ko.pptx"
    en_pptx = en_dir / "agentic_ontology_methodology_training_en.pptx"

    build_pptx_deck(SLIDES_KO, ko_pptx, lang="ko")
    build_pptx_deck(SLIDES_EN, en_pptx, lang="en")

    # Root convenience copies in slides/
    shutil.copy2(ko_pptx, THIS_DIR / "agentic_ontology_methodology_training_ko.pptx")
    shutil.copy2(en_pptx, THIS_DIR / "agentic_ontology_methodology_training_en.pptx")

    # Interactive HTML5 Google Slides-style decks
    build_html_deck(
        ko_dir / "agentic_ontology_methodology_slides_ko.html",
        default_lang="ko",
        english_only=False,
        pptx_rel_path="agentic_ontology_methodology_training_ko.pptx",
    )
    build_html_deck(
        en_dir / "agentic_ontology_methodology_slides_en.html",
        default_lang="en",
        english_only=True,
        pptx_rel_path="agentic_ontology_methodology_training_en.pptx",
    )

    # Also generate explanations/exp_agentic_ontology_methodology.html per `exp` skill
    exp_dir = WORKSPACE_ROOT / "explanations"
    exp_dir.mkdir(parents=True, exist_ok=True)
    build_html_deck(
        exp_dir / "exp_agentic_ontology_methodology.html",
        default_lang="ko",
        english_only=False,
        pptx_rel_path="../agentic-ontology-starter/slides/ko/agentic_ontology_methodology_training_ko.pptx",
    )


if __name__ == "__main__":
    main()
