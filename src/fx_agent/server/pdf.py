"""PDF report generator for FX analysis runs."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from fpdf import FPDF

from .models import RunEntry

UTC = timezone.utc

MARGIN = 15
LH = 6  # line height


# Map of Unicode chars that fpdf2 latin-1 can't encode
_UNICODE_MAP = {
    "\u2014": "--",
    "\u2013": "-",
    "\u2019": "'",
    "\u2018": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2022": "-",
    "\u2026": "...",
    "\u00b0": " deg",
    "\u00b1": "+/-",
    "\u00d7": "x",
    "\u00f7": "/",
    "\u00e9": "e",
    "\u00e8": "e",
    "\u00e0": "a",
    "\u00fc": "u",
}


def _s(value: Any) -> str:
    text = str(value)
    for ch, repl in _UNICODE_MAP.items():
        text = text.replace(ch, repl)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class FXReport(FPDF):
    def __init__(self, pair: str, date: str) -> None:
        super().__init__()
        self.pair = pair
        self.date = date
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(auto=True, margin=MARGIN)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, _s(f"FX Analysis Report — {self.pair} — {self.date}"), ln=True, align="R")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)

    def section_title(self, title: str) -> None:
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_fill_color(30, 80, 162)
        self.set_text_color(255, 255, 255)
        self.cell(0, 9, _s(f"  {title}"), ln=True, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def sub_title(self, title: str) -> None:
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(30, 80, 162)
        self.cell(0, 7, _s(title), ln=True)
        self.set_text_color(0, 0, 0)

    def summary_box(self, items: list[str]) -> None:
        """Render a shaded summary box."""
        self.set_fill_color(240, 244, 255)
        self.set_font("Helvetica", "", 9)
        for item in items:
            self.set_x(MARGIN)
            self.multi_cell(self.epw, LH, _s(f"  * {item}"), fill=True)
        self.ln(2)

    def body_text(self, text: str) -> None:
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, LH, _s(text))
        self.ln(1)

    def kv(self, label: str, value: Any) -> None:
        self.set_font("Helvetica", "B", 9)
        self.cell(48, LH, _s(label + ":"))
        self.set_font("Helvetica", "", 9)
        val_w = self.w - self.r_margin - self.get_x()
        self.multi_cell(max(val_w, 20), LH, _s(str(value)))

    def bullet_list(self, label: str, items: list) -> None:
        if not items:
            return
        self.set_font("Helvetica", "B", 9)
        self.cell(0, LH, _s(label + ":"), ln=True)
        self.set_font("Helvetica", "", 9)
        for item in items:
            self.set_x(MARGIN + 4)
            self.multi_cell(self.epw - 4, LH, _s(f"- {item}"))

    def analyst_section(self, title: str, data: dict) -> None:
        if not data:
            return
        self.section_title(title)

        key_points = data.get("key_points", [])
        if key_points:
            self.sub_title("Summary")
            self.summary_box([str(p) for p in key_points])

        summary = data.get("summary", "")
        if summary:
            self.body_text(summary)

        detail_fields = {k: v for k, v in data.items()
                         if k not in ("key_points", "summary", "base_rate", "quote_rate")
                         and v not in (None, "", [], {})}
        if detail_fields:
            self.sub_title("Detail")
            for key, value in detail_fields.items():
                label = key.replace("_", " ").title()
                if isinstance(value, list):
                    self.bullet_list(label, value)
                else:
                    self.kv(label, value)
            self.ln(2)


def generate_pdf(entry: RunEntry) -> bytes:
    result = entry.result
    pair = entry.pair
    date = entry.date

    pdf = FXReport(pair, date)
    pdf.add_page()

    # ── Cover ──────────────────────────────────────────────────────────────────
    pdf.ln(20)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(30, 80, 162)
    pdf.cell(0, 14, pair, ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 10, "FX Analysis Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, date, ln=True, align="C")
    pdf.ln(6)

    final = result.get("final_decision", {})
    if final:
        direction = str(final.get("final_direction", "")).upper()
        conviction = str(final.get("conviction", "")).upper()
        confidence = final.get("confidence", "")
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(0, 128, 0) if direction == "BUY" else (
            pdf.set_text_color(180, 0, 0) if direction == "SELL" else
            pdf.set_text_color(80, 80, 80)
        )
        pdf.cell(0, 12, f"Decision: {direction}", ln=True, align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, f"Conviction: {conviction}  |  Confidence: {confidence}", ln=True, align="C")
        entry_price = final.get("entry_price", 0)
        sl_pips = final.get("stop_loss_pips", 0)
        tp_pips = final.get("take_profit_pips", 0)
        rr = final.get("risk_reward_ratio", 0)
        if entry_price:
            pdf.cell(0, 7,
                f"Entry: {entry_price:.5f}  SL: {sl_pips} pips  TP: {tp_pips} pips  R/R: {rr}",
                ln=True, align="C")

    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 7,
        "This report is AI-generated and for informational purposes only. Not financial advice.",
        ln=True, align="C")
    pdf.set_text_color(0, 0, 0)

    # ── Analyst sections ───────────────────────────────────────────────────────
    pdf.add_page()
    pdf.analyst_section("Macro Analysis", result.get("macro_analysis", {}))
    pdf.analyst_section("Carry Analysis", result.get("carry_analysis", {}))
    pdf.add_page()
    pdf.analyst_section("Technical Analysis", result.get("technical_analysis", {}))
    pdf.add_page()
    pdf.analyst_section("Sentiment Analysis", result.get("sentiment_analysis", {}))
    pdf.analyst_section("News Analysis", result.get("news_analysis", {}))

    # ── Research Debate ────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("Research Debate")
    bull = result.get("bullish_case", {})
    bear = result.get("bearish_case", {})
    if bull:
        pdf.sub_title("Bullish Case")
        pdf.summary_box([str(p) for p in bull.get("key_points", [])])
        if bull.get("strongest_argument"):
            pdf.body_text(bull["strongest_argument"])
    if bear:
        pdf.sub_title("Bearish Case")
        pdf.summary_box([str(p) for p in bear.get("key_points", [])])
        if bear.get("strongest_argument"):
            pdf.body_text(bear["strongest_argument"])
    debate_conc = result.get("debate_conclusion", {})
    if debate_conc:
        pdf.sub_title("Debate Conclusion")
        pdf.summary_box([str(p) for p in debate_conc.get("key_points", [])])
        if debate_conc.get("summary"):
            pdf.body_text(debate_conc["summary"])
        for k in ("conclusion_direction", "conviction", "confidence"):
            if debate_conc.get(k) is not None:
                pdf.kv(k.replace("_", " ").title(), debate_conc[k])

    # ── Trade Recommendation ───────────────────────────────────────────────────
    pdf.add_page()
    pdf.analyst_section("Trade Recommendation", result.get("trade_recommendation", {}))

    # ── Risk Debate ────────────────────────────────────────────────────────────
    pdf.section_title("Risk Analysis")
    for stance in ("aggressive", "neutral", "conservative"):
        data = result.get(f"risk_{stance}", {})
        if data:
            pdf.sub_title(f"{stance.title()} Risk")
            pdf.summary_box([str(p) for p in data.get("key_points", [])])
            if data.get("summary"):
                pdf.body_text(data["summary"])
    risk_conc = result.get("risk_conclusion", {})
    if risk_conc:
        pdf.sub_title("Risk Conclusion")
        pdf.summary_box([str(p) for p in risk_conc.get("key_points", [])])
        if risk_conc.get("summary"):
            pdf.body_text(risk_conc["summary"])

    # ── Final Decision ─────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.analyst_section("Final Decision (Fund Manager)", result.get("final_decision", {}))

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
