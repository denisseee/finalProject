import streamlit as st
import pymupdf
import pandas as pd
import re
from pathlib import Path
import io
import zipfile
from datetime import datetime
import os


# ====================================================================
# PAGE CONFIG
# ====================================================================

st.set_page_config(
    page_title="Sector Report Automation",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ====================================================================
# THEME / DESIGN TOKENS
# ====================================================================
# Palette:
#   Navy   -> background / structure
#   Teal   -> uptime / healthy / success
#   Orange -> downtime / alerts / primary action
#   White  -> text / clarity
#
# Font: JetBrains Mono (a sharper, more legible cousin of Courier New)
# with Courier New as an explicit fallback, for that terminal / SOC
# console feel that fits a cybersecurity monitoring product.
# ====================================================================

NAVY_950 = "#050B14"
NAVY_900 = "#0A1628"
NAVY_800 = "#101F38"
NAVY_700 = "#17304F"
NAVY_600 = "#20456E"
TEAL = "#2DD4BF"
TEAL_DARK = "#0F6E5C"
ORANGE = "#FF7A29"
ORANGE_DARK = "#B84E12"
WHITE = "#F4F7FA"
SLATE = "#7C93AD"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'JetBrains Mono', 'Courier New', monospace !important;
}}

/* ---------- App background ---------- */
.stApp {{
    background:
        radial-gradient(circle at 15% 0%, {NAVY_800} 0%, {NAVY_950} 55%),
        {NAVY_950};
    color: {WHITE};
}}

/* moving scanline accent along the very top of the page */
.stApp::before {{
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 3px;
    z-index: 999999;
    background: linear-gradient(90deg, {TEAL} 0%, {ORANGE} 50%, {TEAL} 100%);
    background-size: 200% 100%;
    animation: scan-sweep 6s linear infinite;
}}
@keyframes scan-sweep {{
    0% {{ background-position: 0% 0%; }}
    100% {{ background-position: 200% 0%; }}
}}

/* hide default streamlit chrome */
#MainMenu, footer, header {{ visibility: hidden; }}
[data-testid="stToolbar"] {{ display: none; }}

.block-container {{
    padding-top: 2rem;
    max-width: 1100px;
}}

/* ---------- Headings ---------- */
h1, h2, h3, h4 {{
    font-family: 'JetBrains Mono', 'Courier New', monospace !important;
    color: {WHITE} !important;
    letter-spacing: 0.5px;
}}

/* ---------- Hero ---------- */
.hero {{
    border: 1px solid {NAVY_600};
    background: linear-gradient(135deg, {NAVY_800} 0%, {NAVY_900} 100%);
    border-radius: 6px;
    padding: 28px 32px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}}
.hero::after {{
    content: "";
    position: absolute;
    top: -40%; right: -10%;
    width: 260px; height: 260px;
    background: radial-gradient(circle, rgba(45,212,191,0.10) 0%, rgba(45,212,191,0) 70%);
}}
.hero-eyebrow {{
    color: {TEAL};
    font-size: 12px;
    letter-spacing: 3px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.hero-eyebrow .dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: {TEAL};
    box-shadow: 0 0 8px {TEAL};
    animation: pulse-dot 1.8s ease-in-out infinite;
    display: inline-block;
}}
@keyframes pulse-dot {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.35; }}
}}
.hero-title {{
    font-size: 30px;
    font-weight: 800;
    color: {WHITE};
    margin: 10px 0 6px 0;
    letter-spacing: 1px;
}}
.hero-sub {{
    color: {SLATE};
    font-size: 14px;
}}
.hero-sub .prompt {{
    color: {ORANGE};
}}

/* ---------- Section labels ---------- */
.section-label {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 34px 0 14px 0;
}}
.section-num {{
    background: {ORANGE};
    color: {NAVY_950};
    font-weight: 800;
    font-size: 12px;
    padding: 3px 9px;
    border-radius: 3px;
    letter-spacing: 1px;
}}
.section-text {{
    color: {WHITE};
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 2px;
}}
.section-rule {{
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, {NAVY_600} 0%, transparent 100%);
}}

/* ---------- File uploader ---------- */
[data-testid="stFileUploader"] {{
    border: 1px dashed {NAVY_600};
    border-radius: 6px;
    padding: 10px;
    background: {NAVY_900};
}}
[data-testid="stFileUploader"] section {{
    background: transparent;
}}
[data-testid="stFileUploaderDropzone"] {{
    background: {NAVY_900} !important;
}}

/* ---------- Buttons ---------- */
.stButton button, .stDownloadButton button {{
    background: linear-gradient(135deg, {ORANGE} 0%, {ORANGE_DARK} 100%) !important;
    color: {NAVY_950} !important;
    border: none !important;
    font-weight: 800 !important;
    font-family: 'JetBrains Mono', 'Courier New', monospace !important;
    letter-spacing: 1px;
    border-radius: 4px !important;
    padding: 10px 22px !important;
    transition: transform 0.12s ease, box-shadow 0.12s ease;
    box-shadow: 0 0 0 1px {ORANGE_DARK};
}}
.stButton button:hover, .stDownloadButton button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(255,122,41,0.35);
    color: {NAVY_950} !important;
}}

/* ---------- File uploader "Browse files" button ---------- */
[data-testid="stFileUploader"] button {{
    color: {NAVY_950} !important;
    font-weight: 700 !important;
}}
[data-testid="stFileUploader"] button:hover {{
    color: {NAVY_950} !important;
}}
[data-testid="stFileUploader"] button p {{
    color: {NAVY_950} !important;
}}
[data-testid="stIconMaterial"] {{
    color: {NAVY_950} !important;
}}
/* ---------- File uploader icon (dropzone + button) ---------- */
[data-testid="stFileUploader"] svg,
[data-testid="stFileUploaderDropzone"] svg {{
    fill: {NAVY_950} !important;
    stroke: {NAVY_950} !important;
    color: {NAVY_950} !important;
}}
[data-testid="stFileUploader"] svg path,
[data-testid="stFileUploaderDropzone"] svg path {{
    fill: {NAVY_950} !important;
    stroke: {NAVY_950} !important;
}}

/* ---------- File uploader helper text ---------- */
[data-testid="stFileUploaderDropzoneInstructions"] div,
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small {{
    color: {WHITE} !important;
}}

/* ---------- Progress bar ---------- */
[data-testid="stProgress"] > div > div {{
    background: linear-gradient(90deg, {TEAL} 0%, {ORANGE} 100%) !important;
}}
[data-testid="stProgress"] {{
    background: {NAVY_800};
    border-radius: 4px;
}}

/* ---------- Console log ---------- */
.console {{
    background: {NAVY_950};
    border: 1px solid {NAVY_700};
    border-radius: 6px;
    padding: 14px 16px;
    font-size: 13px;
    color: {TEAL};
    max-height: 220px;
    overflow-y: auto;
    margin-bottom: 10px;
}}
.console .line {{
    color: {SLATE};
    margin-bottom: 3px;
}}
.console .line .prompt {{
    color: {TEAL};
}}
.console .line .ok {{
    color: {TEAL};
}}

/* ---------- Metric cards ---------- */
.metric-card {{
    background: {NAVY_800};
    border: 1px solid {NAVY_600};
    border-radius: 6px;
    padding: 16px 18px;
    text-align: left;
}}
.metric-label {{
    color: {SLATE};
    font-size: 11px;
    letter-spacing: 2px;
    font-weight: 600;
    margin-bottom: 6px;
}}
.metric-value {{
    font-size: 26px;
    font-weight: 800;
    color: {WHITE};
}}
.metric-value.teal {{ color: {TEAL}; }}
.metric-value.orange {{ color: {ORANGE}; }}

/* ---------- Badge / pill ---------- */
.badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(45,212,191,0.10);
    border: 1px solid {TEAL_DARK};
    color: {TEAL};
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
}}

/* ---------- Dataframe ---------- */
[data-testid="stDataFrame"] {{
    border: 1px solid {NAVY_600};
    border-radius: 6px;
    overflow: hidden;
}}

/* ---------- Expander ---------- */
[data-testid="stExpander"] {{
    background: {NAVY_800};
    border: 1px solid {NAVY_600};
    border-radius: 6px;
}}

/* ---------- Misc text ---------- */
p, li, label, span {{
    color: {WHITE};
}}
.stMarkdown p {{
    color: {SLATE};
}}

/* footer */
.app-footer {{
    margin-top: 48px;
    padding-top: 16px;
    border-top: 1px solid {NAVY_700};
    color: {SLATE};
    font-size: 11px;
    letter-spacing: 1.5px;
    text-align: center;
}}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# Initialize Session State keys for clearing / persistence
if "file_uploader_key" not in st.session_state:
    st.session_state["file_uploader_key"] = 0


# ====================================================================
# HERO
# ====================================================================

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-eyebrow"><span class="dot"></span>SYSTEM ONLINE &nbsp;/&nbsp; PRTG DATA PIPELINE</div>
        <div class="hero-title">🛡️ SECTOR REPORT AUTOMATION</div>
        <div class="hero-sub"><span class="prompt"></span> Upload sector PDFs → extract uptime / downtime → export Excel</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ====================================================================
# EXTRACT DEVICE NAME
# ====================================================================

def extract_device(text):
    if not text:
        return None
    parts = re.split(r"\s*»\s*", text)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return None
    device = parts[-1]
    device = re.split(r"\s+Uptime\b", device)[0]
    return device.strip()


# ====================================================================
# VALIDATE FILENAME FORMAT
# ====================================================================

def validate_and_extract_sector(filename):
    """Validates if filename follows the required PRTG sector pattern: Sector Report - <Sector> _ ..."""
    match = re.search(r"Sector Report\s*-\s*(.*?)\s*_", filename, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


# ====================================================================
# PROCESS ONE PDF
# ====================================================================

def process_pdf(pdf_file):
    data = []
    percentage_pattern = r"(\d+(?:\.\d+)?)\s*%"
    
    # Get PDF bytes securely from memory
    pdf_bytes = pdf_file.getvalue()

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            tables = page.find_tables()
            for table in tables.tables:
                rows = table.extract()
                for row in rows:
                    if not row or not any(row):
                        continue

                    # Normal row
                    if len(row) >= 13 and row[2] == "Uptime":
                        device = extract_device(row[0])
                        uptime_downtime = row[6]
                        percentages = re.findall(percentage_pattern, uptime_downtime or "")
                        if len(percentages) >= 1:
                            uptime = round(float(percentages[0]), 2)
                            data.append({
                                "Probe, Group, Device": device,
                                "Uptime": uptime
                            })
                        continue

                    # Malformed row
                    first_cell = str(row[0])
                    if "Uptime" in first_cell and "%" in first_cell:
                        device_match = re.search(r"»\s*([^»]+?)\s+Uptime\b", first_cell, re.DOTALL)
                        if device_match:
                            device = device_match.group(1).strip()
                        else:
                            device = extract_device(first_cell)

                        percentages = re.findall(percentage_pattern, first_cell)
                        if len(percentages) >= 1:
                            uptime = round(float(percentages[0]), 2)
                            data.append({
                                "Probe, Group, Device": device,
                                "Uptime": uptime
                            })

    df = pd.DataFrame(data)
    if df.empty:
        return df

    df["Downtime"] = 100 - df["Uptime"]
    df = df.drop_duplicates(subset=["Probe, Group, Device"])
    return df


# ====================================================================
# EXCEL STYLING HELPER
# ====================================================================
def write_styled_sheet(writer, df, sheet_name, title):
    safe_sheet = sheet_name[:31]

    # 1. Calculate and append Average Row if DataFrame has numeric columns (Uptime/Downtime)
    # if not df.empty and ("Uptime" in df.columns or "Average Uptime" in df.columns):
    #     avg_row = {}
    #     for col in df.columns:
    #         if pd.api.types.is_numeric_dtype(df[col]):
    #             avg_row[col] = df[col].mean().round(2).astype(str).str.rstrip("0").str.rstrip(".")
    #         else:
    #             avg_row[col] = "OVERALL AVERAGE" if col == df.columns[0] else ""
        
    #     # Append average row to dataframe copy
    #     df_with_avg = pd.concat([df, pd.DataFrame([avg_row])], ignore_index=True)
    # else:
    #     df_with_avg = df
    # 1. Calculate and append Average Row if DataFrame has numeric columns (Uptime/Downtime)
    # if not df.empty and ("Uptime" in df.columns or "Average Uptime" in df.columns):
    #     avg_row = {}
    #     for col in df.columns:
    #         if pd.api.types.is_numeric_dtype(df[col]):
    #             avg_row[col] = f"{df[col].mean():.2f}".rstrip("0").rstrip(".")
    #         else:
    #             avg_row[col] = "OVERALL AVERAGE" if col == df.columns[0] else ""
        
    #     # Append average row to dataframe copy
    #     df_with_avg = pd.concat([df, pd.DataFrame([avg_row])], ignore_index=True)
    # else:
    #     df_with_avg = df
    # 1. Calculate and append Average Row if DataFrame has numeric columns
    if not df.empty and ("Uptime" in df.columns or "Average Uptime" in df.columns):
        avg_row = {}
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                avg_row[col] = round(float(df[col].mean()),2)
            else:
                avg_row[col] = "OVERALL AVERAGE" if col == df.columns[0] else ""
        
        df_with_avg = pd.concat([df, pd.DataFrame([avg_row])], ignore_index=True)
    else:
        df_with_avg = df

    df_with_avg.to_excel(
        writer,
        sheet_name=safe_sheet,
        index=False,
        startrow=2,
    )

    workbook = writer.book
    worksheet = writer.sheets[safe_sheet]

    title_format = workbook.add_format({
        "bold": True,
        "font_size": 14,
        "font_color": "#FFFFFF",
        "bg_color": NAVY_900,
        "valign": "vcenter",
        "indent": 1,
    })
    worksheet.merge_range(
        0, 0, 0, max(len(df_with_avg.columns) - 1, 0),
        title,
        title_format,
    )

    header_format = workbook.add_format({
        "bold": True,
        "font_color": "#FFFFFF",
        "bg_color": NAVY_700,
        "border": 1,
        "border_color": NAVY_600,
    })
    for col_num, col_name in enumerate(df_with_avg.columns):
        worksheet.write(2, col_num, col_name, header_format)

    # 2. Add distinct format for the total/average summary row at the bottom
    avg_row_format = workbook.add_format({
        "bold": True,
        "font_color": "#FFFFFF",
        "bg_color": NAVY_700,
        "num_format": "0.00",
        "border": 1,
        "border_color": NAVY_600,
    })
    
    number_format = workbook.add_format({"num_format": "0.00"})

    worksheet.set_column(0, 0, 55)
    if len(df_with_avg.columns) > 1:
        worksheet.set_column(1, len(df_with_avg.columns) - 1, 16, number_format)

    # Write the average row cells with bold/highlighted formatting if data exists
    if len(df_with_avg) > len(df):
        last_row = 2 + len(df_with_avg)
        for col_num in range(len(df_with_avg.columns)):
            val = df_with_avg.iloc[-1, col_num]
            if pd.isna(val) or val == "":
                worksheet.write(last_row, col_num, "", avg_row_format)
            elif isinstance(val, (int, float)):
                worksheet.write(last_row, col_num, val, avg_row_format)
            else:
                worksheet.write(last_row, col_num, val, avg_row_format)

    if "Uptime" in df_with_avg.columns or "Average Uptime" in df_with_avg.columns:
        uptime_col = df_with_avg.columns.get_loc("Uptime") if "Uptime" in df_with_avg.columns else df_with_avg.columns.get_loc("Average Uptime")
        first_data_row = 3
        last_data_row = 2 + len(df) # Exclude the average row from conditional formatting
        if len(df) > 0:
            worksheet.conditional_format(
                first_data_row, uptime_col, last_data_row, uptime_col,
                {
                    "type": "3_color_scale",
                    "min_color": "#B84E12",
                    "mid_color": "#FAC775",
                    "max_color": "#2DD4BF",
                },
            )

    worksheet.freeze_panes(3, 0)

# ====================================================================
# UPLOAD SECTION
# ====================================================================

st.markdown(
    """
    <div class="section-label">
        <span class="section-num">01</span>
        <span class="section-text">UPLOAD REPORTS</span>
        <span class="section-rule"></span>
    </div>
    """,
    unsafe_allow_html=True,
)

col_upload, col_clear = st.columns([5, 1])

with col_upload:
    uploaded_files = st.file_uploader(
        "Drop PRTG sector report PDFs here",
        type=["pdf"],
        accept_multiple_files=True,
        key=st.session_state["file_uploader_key"],
        label_visibility="collapsed",
    )

with col_clear:
    st.write("") # spacing alignment
    if st.button("🗑️ CLEAR ALL"):
        st.session_state["file_uploader_key"] += 1
        if "results" in st.session_state:
            del st.session_state["results"]
        st.rerun()

# Validate files
valid_files = []
invalid_files = []

if uploaded_files:
    for file in uploaded_files:
        sector_name = validate_and_extract_sector(file.name)
        if sector_name:
            valid_files.append((file, sector_name))
        else:
            invalid_files.append(file.name)

    if invalid_files:
        st.error(
            f"⚠️ **Format Warning:** {len(invalid_files)} file(s) do not match the required naming convention (`Sector Report - <Sector> _ ...`) and will be skipped:"
        )
        for inv in invalid_files:
            st.code(inv, language="text")

    if valid_files:
        st.markdown(
            f'<span class="badge">📡 {len(valid_files)} VALID FILE(S) QUEUED</span>',
            unsafe_allow_html=True,
        )


# ====================================================================
# PROCESS SECTION
# ====================================================================

if valid_files:

    st.markdown(
        """
        <div class="section-label">
            <span class="section-num">02</span>
            <span class="section-text">PROCESS &amp; REVIEW</span>
            <span class="section-rule"></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    run = st.button("⚡ RUN EXTRACTION")

    if run or "results" in st.session_state:
        if run:
            results = {}
            console_placeholder = st.empty()
            progress = st.progress(0)
            log_lines = []

            for i, (pdf_file, sector) in enumerate(valid_files):
                log_lines.append(
                    f'<div class="line"><span class="prompt">$</span> extracting sector: <span class="ok">{sector}</span> ({pdf_file.name}) ...</div>'
                )
                console_placeholder.markdown(
                    f'<div class="console">{"".join(log_lines)}</div>',
                    unsafe_allow_html=True,
                )

                df = process_pdf(pdf_file)
                results[sector] = df

                progress.progress((i + 1) / len(valid_files))

            log_lines.append(
                '<div class="line"><span class="prompt">$</span> <span class="ok">done — all valid reports processed securely in memory.</span></div>'
            )
            console_placeholder.markdown(
                f'<div class="console">{"".join(log_lines)}</div>',
                unsafe_allow_html=True,
            )

            st.success("All reports processed successfully.")
            st.session_state["results"] = results

        results = st.session_state.get("results", {})

        # ------------------------------------------
        # Create Excel files in memory
        # ------------------------------------------
# ------------------------------------------
        # Create a Single Multi-Tab Excel File in Memory
        # # ------------------------------------------
        # summary_data = []
        # for sector, df in results.items():
        #     if df.empty:
        #         continue
        #     summary_data.append({
        #         "Sector": sector,
        #         "Average Uptime": f"{df["Uptime"].mean():.2f}".rstrip("0").rstrip("."),
        #         "Average Downtime": f"{df["Downtime"].mean():.2f}".rstrip("0").rstrip(".")
        #     })
        # summary_df = pd.DataFrame(summary_data)
        # multi_tab_buffer = io.BytesIO()

        # with pd.ExcelWriter(
        #     multi_tab_buffer,
        #     engine="xlsxwriter"
        # ) as writer:
            
        #     # 1. Write the Summary sheet first (or wherever you prefer)
        #     if not summary_df.empty:
        #         write_styled_sheet(
        #             writer, summary_df, "Sector Summary", "PRTG Sector Summary"
        #         )

        #     # 2. Write each sector's data into its own separate tab
        #     for sector, df in results.items():
        #         if df.empty:
        #             continue
        #         write_styled_sheet(
        #             writer, df, sector, f"{sector} Sector Report"
        #         )

        # multi_tab_buffer.seek(0)

        # # Store the multi-tab file bytes for download
        # excel_files = {
        #     "All_Sectors_Combined_Report.xlsx": multi_tab_buffer.getvalue()
        # }
        
        # # ------------------------------------------
        # # Metric cards
        # # ------------------------------------------

        # total_sectors = len(summary_df)
        # total_devices = sum(len(df) for df in results.values() if not df.empty)
        # avg_uptime = summary_df["Average Uptime"].mean() if not summary_df.empty else 0
        # avg_downtime = summary_df["Average Downtime"].mean() if not summary_df.empty else 0

        # c1, c2, c3, c4 = st.columns(4)
        # for col, label, value, cls in [
        #     (c1, "SECTORS", total_sectors, ""),
        #     (c2, "DEVICES MONITORED", total_devices, ""),
        #     (c3, "AVG UPTIME", f"{avg_uptime:.2f}%", "teal"),
        #     (c4, "AVG DOWNTIME", f"{avg_downtime:.2f}%", "orange"),
        # ]:
        #     with col:
        #         st.markdown(
        #             f"""
        #             <div class="metric-card">
        #                 <div class="metric-label">{label}</div>
        #                 <div class="metric-value {cls}">{value}</div>
        #             </div>
        #             """,
        #             unsafe_allow_html=True,
        #         )

        # st.markdown("<br>", unsafe_allow_html=True)
        # st.subheader("Sector Summary")
        # st.dataframe(summary_df, use_container_width=True)

        # with st.expander("View per-sector detail"):
        #     for sector, df in results.items():
        #         if df.empty:
        #             st.markdown(f"**{sector}** — no data extracted")
        #             continue
        #         st.markdown(f"**{sector}** &nbsp; ({len(df)} devices)")
        #         st.dataframe(df, use_container_width=True)

        # ------------------------------------------
        # Create Summary Excel
        # ------------------------------------------
        # ------------------------------------------
        # Create summary DataFrame with pure numeric floats
        # ------------------------------------------
        summary_data = []
        for sector, df in results.items():
            if df.empty:
                continue
            summary_data.append({
                "Sector": sector,
                "Average Uptime": round(df["Uptime"].mean(),2),
                "Average Downtime": round(df["Downtime"].mean(),2)
            })
        summary_df = pd.DataFrame(summary_data)

        # ------------------------------------------
        # Create a Single Multi-Tab Excel File in Memory
        # ------------------------------------------
        multi_tab_buffer = io.BytesIO()

        with pd.ExcelWriter(
            multi_tab_buffer,
            engine="xlsxwriter"
        ) as writer:
            
            # 1. Write the Summary sheet first
            if not summary_df.empty:
                write_styled_sheet(
                    writer, summary_df, "Sector Summary", "PRTG Sector Summary"
                )

            # 2. Write each sector's data into its own separate tab
            for sector, df in results.items():
                if df.empty:
                    continue
                write_styled_sheet(
                    writer, df, sector, f"{sector} Sector Report"
                )

        multi_tab_buffer.seek(0)

        # Store the multi-tab file bytes for download
        excel_files = {
            "All_Sectors_Combined_Report.xlsx": multi_tab_buffer.getvalue()
        }
        
        # ------------------------------------------
        # Metric cards
        # ------------------------------------------

        total_sectors = len(summary_df)
        total_devices = sum(len(df) for df in results.values() if not df.empty)
        avg_uptime = summary_df["Average Uptime"].mean() if not summary_df.empty else 0
        avg_downtime = summary_df["Average Downtime"].mean() if not summary_df.empty else 0

        c1, c2, c3, c4 = st.columns(4)
        for col, label, value, cls in [
            (c1, "SECTORS", total_sectors, ""),
            (c2, "DEVICES MONITORED", total_devices, ""),
            (c3, "AVG UPTIME", f"{avg_uptime:.2f}%", "teal"),
            (c4, "AVG DOWNTIME", f"{avg_downtime:.2f}%", "orange"),
        ]:
            with col:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">{label}</div>
                        <div class="metric-value {cls}">{value}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Sector Summary")
        st.dataframe(summary_df, use_container_width=True)

        with st.expander("View per-sector detail"):
            for sector, df in results.items():
                if df.empty:
                    st.markdown(f"**{sector}** — no data extracted")
                    continue
                st.markdown(f"**{sector}** &nbsp; ({len(df)} devices)")
                st.dataframe(df, use_container_width=True)

        summary_buffer = io.BytesIO()

        with pd.ExcelWriter(
            summary_buffer,
            engine="xlsxwriter"
        ) as writer:
            write_styled_sheet(
                writer, summary_df, "Sector Summary", "PRTG Sector Summary"
            )

        summary_buffer.seek(0)
        excel_files["Sector_Summary.xlsx"] = summary_buffer.getvalue()

        # ------------------------------------------
        # Create ZIP
        # ------------------------------------------

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(
            zip_buffer,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zip_file:
            for filename, file_data in excel_files.items():
                zip_file.writestr(filename, file_data)

        zip_buffer.seek(0)

        # ------------------------------------------
        # Download section
        # ------------------------------------------

        st.markdown(
            """
            <div class="section-label">
                <span class="section-num">03</span>
                <span class="section-text">DOWNLOAD</span>
                <span class="section-rule"></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.download_button(
            label="⬇ DOWNLOAD ALL EXCEL REPORTS (.zip)",
            data=zip_buffer.getvalue(),
            file_name="Sector_Report_Results.zip",
            mime="application/zip"
        )

else:
    st.markdown(
        f'<p style="color:{SLATE}; font-size:13px;">Awaiting input - upload valid PRTG sector report PDFs to begin.</p>',
        unsafe_allow_html=True,
    )


# ====================================================================
# FOOTER
# ====================================================================

st.markdown(
    f"""
    <div class="app-footer">
        PRTG NETWORK MONITORING &nbsp;•&nbsp; AUTOMATED REPORTING &nbsp;•&nbsp; {datetime.now().strftime('%Y.%m.%d')}
    </div>
    """,
    unsafe_allow_html=True,
)