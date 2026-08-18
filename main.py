import pymupdf
import pandas as pd
import re
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

folder = Path("2026.08.12")

percentage_pattern = r"(\d+(?:\.\d+)?)\s*%"


# ============================================================
# EXTRACT SECTOR NAME FROM PDF FILENAME
# ============================================================

def extract_sector_name(pdf_path):

    filename = pdf_path.stem

    # Example:
    # Sector Report - Construction _ Report _ PRTG...
    #
    # We want:
    # Construction

    match = re.search(
        r"Sector Report\s*-\s*(.*?)\s*[_-]\s*Report",
        filename,
        re.IGNORECASE
    )

    if match:
        return match.group(1).strip()

    # Fallback if filename doesn't match expected format
    return "Unknown"


# ============================================================
# EXTRACT DEVICE NAME FROM NORMAL ROW
# ============================================================

def extract_device(text):

    if not text:
        return None

    # Split Probe » Group » Device
    parts = re.split(r"\s*»\s*", text)

    # Remove empty pieces
    parts = [
        part.strip()
        for part in parts
        if part.strip()
    ]

    if not parts:
        return None

    # Last part is normally the device
    device = parts[-1]

    # Remove anything after Uptime
    device = re.split(
        r"\s+Uptime\b",
        device
    )[0]

    return device.strip()


# ============================================================
# RECOVER MALFORMED ROW
# ============================================================

def extract_malformed_row(text):

    # Normalize whitespace
    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    # --------------------------------------------------------
    # Extract device
    #
    # Example:
    #
    # » JA - Berger Paints Montego Bay 100 %
    # --------------------------------------------------------

    device_match = re.search(
        r"»\s*([^»]+?)\s+\d+(?:\.\d+)?\s*%",
        text
    )

    if not device_match:
        return None

    device = device_match.group(1).strip()

    # --------------------------------------------------------
    # Extract percentages
    # --------------------------------------------------------

    percentages = re.findall(
        percentage_pattern,
        text
    )

    if not percentages:
        return None

    # First percentage = Uptime
    uptime = float(percentages[0])

    return {
        "Probe, Group, Device": device,
        "Uptime": uptime
    }


# ============================================================
# PROCESS ONE PDF
# ============================================================

def process_pdf(pdf_path):

    sector = extract_sector_name(pdf_path)

    print("\n" + "=" * 80)
    print(f"PROCESSING: {sector}")
    print(f"PDF: {pdf_path.name}")
    print("=" * 80)

    data = []

    with pymupdf.open(pdf_path) as doc:

        for page_number, page in enumerate(doc):

            print(
                f"Processing page "
                f"{page_number + 1}/{len(doc)}"
            )

            tables = page.find_tables()

            for table in tables.tables:

                rows = table.extract()

                # --------------------------------------------
                # Go through every row
                # --------------------------------------------

                for row in rows:

                    # Skip empty rows
                    if not row or not any(row):
                        continue


                    # ========================================
                    # NORMAL ROW
                    # ========================================

                    if (
                        len(row) >= 13
                        and row[2] == "Uptime"
                    ):

                        device = extract_device(
                            row[0]
                        )

                        uptime_downtime = row[6]

                        percentages = re.findall(
                            percentage_pattern,
                            uptime_downtime or ""
                        )

                        if len(percentages) >= 1:

                            uptime = float(
                                percentages[0]
                            )

                            data.append({
                                "Probe, Group, Device": device,
                                "Uptime": uptime
                            })

                        continue


                    # ========================================
                    # MALFORMED ROW
                    # ========================================

                    first_cell = str(row[0])

                    if (
                        "Uptime" in first_cell
                        and "%" in first_cell
                    ):

                        recovered = (
                            extract_malformed_row(
                                first_cell
                            )
                        )

                        if recovered:

                            data.append(
                                recovered
                            )


    # ========================================================
    # CREATE DATAFRAME
    # ========================================================

    df = pd.DataFrame(data)

    if df.empty:
        print(
            f"WARNING: No data extracted "
            f"from {sector}"
        )
        return None


    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    df = df.drop_duplicates(
        subset=[
            "Probe, Group, Device"
        ]
    )


    # ========================================================
    # CALCULATE DOWNTIME
    # ========================================================

    df["Downtime"] = (
        100 - df["Uptime"]
    )


    # ========================================================
    # ORDER COLUMNS
    # ========================================================

    df = df[
        [
            "Probe, Group, Device",
            "Uptime",
            "Downtime"
        ]
    ]


    # ========================================================
    # CREATE EXCEL FILE
    # ========================================================

    output_file = (
        folder /
        f"{sector}.xlsx"
    )

    # Replace characters that Windows doesn't allow
    safe_output_name = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        f"{sector}.xlsx"
    )

    output_file = folder / safe_output_name


    # --------------------------------------------------------
    # Write Excel
    # --------------------------------------------------------

    with pd.ExcelWriter(
        output_file,
        engine="xlsxwriter"
    ) as writer:

        df.to_excel(
            writer,
            sheet_name=sector[:31],
            index=False,
            startrow=2
        )

        workbook = writer.book
        worksheet = writer.sheets[
            sector[:31]
        ]

        # ----------------------------------------------------
        # Title
        # ----------------------------------------------------

        title_format = workbook.add_format({
            "bold": True,
            "font_size": 16
        })

        worksheet.write(
            "A1",
            f"{sector} Sector Report",
            title_format
        )


        # ----------------------------------------------------
        # Formatting
        # ----------------------------------------------------

        percentage_format = workbook.add_format({
            "num_format": "0.000"
        })

        worksheet.set_column(
            "A:A",
            60
        )

        worksheet.set_column(
            "B:C",
            15,
            percentage_format
        )

        worksheet.freeze_panes(
            3,
            0
        )


    # ========================================================
    # PRINT RESULTS
    # ========================================================

    print(
        f"\n{sector}: "
        f"{len(df)} rows extracted"
    )

    print(df.to_string(index=False))

    print(
        f"\nCreated: {output_file}"
    )


    return output_file


# ============================================================
# PROCESS ALL SECTOR PDFs
# ============================================================

print("\nSearching for sector PDFs...\n")

pdf_files = list(
    folder.glob("Sector Report*.pdf")
)

if not pdf_files:

    raise FileNotFoundError(
        "No Sector Report PDFs found."
    )


created_files = []


for pdf_path in pdf_files:

    output = process_pdf(
        pdf_path
    )

    if output:
        created_files.append(
            output
        )


# ============================================================
# CREATE SUMMARY
# ============================================================

print("\n" + "=" * 80)
print("CREATING SECTOR SUMMARY")
print("=" * 80)


summary_data = []


for excel_file in created_files:

    print(
        f"Reading: {excel_file.name}"
    )

    # Read the sector Excel file
    df = pd.read_excel(
        excel_file,
        sheet_name=0,
        skiprows=2
    )

    if df.empty:
        continue


    # Calculate averages
    average_uptime = df[
        "Uptime"
    ].mean()

    average_downtime = df[
        "Downtime"
    ].mean()


    # Sector name from filename
    sector = excel_file.stem


    summary_data.append({

        "Sector": sector,

        "Average Uptime":
            average_uptime,

        "Average Downtime":
            average_downtime

    })


# ============================================================
# SUMMARY DATAFRAME
# ============================================================

summary_df = pd.DataFrame(
    summary_data
)


# Sort alphabetically
summary_df = summary_df.sort_values(
    "Sector"
)


print("\nFINAL SUMMARY:")
print(
    summary_df.to_string(
        index=False
    )
)


# ============================================================
# CREATE SUMMARY EXCEL
# ============================================================

summary_file = (
    folder /
    "Sector_Summary.xlsx"
)


with pd.ExcelWriter(
    summary_file,
    engine="xlsxwriter"
) as writer:

    summary_df.to_excel(
        writer,
        sheet_name="Summary",
        index=False,
        startrow=2
    )

    workbook = writer.book
    worksheet = writer.sheets[
        "Summary"
    ]


    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    title_format = workbook.add_format({
        "bold": True,
        "font_size": 16
    })

    worksheet.write(
        "A1",
        "Sector Uptime / Downtime Summary",
        title_format
    )


    # --------------------------------------------------------
    # Formatting
    # --------------------------------------------------------

    percentage_format = workbook.add_format({
        "num_format": "0.000"
    })

    worksheet.set_column(
        "A:A",
        25
    )

    worksheet.set_column(
        "B:C",
        20,
        percentage_format
    )

    worksheet.freeze_panes(
        3,
        0
    )


print(
    f"\nSummary Excel created: "
    f"{summary_file}"
)
# import pymupdf
# import pandas as pd
# import re

# with pymupdf.open(r"2026.08.12/Sector Report - Construction _ Report _ PRTG Network Monitor (TTOVRW-PRTG01).pdf") as doc :
#     headers = [
#     "Probe, Group, Device",
#     "Sensor",
#     "Average-Total",
#     "Uptime/Downtime",
#     "Good/Failed"
# ]

#     for page_number, page in enumerate(doc):

#         tables = page.find_tables()

#         for table_number, table in enumerate(tables.tables):

#             rows = table.extract()
              

#             for row in rows:

#                 # Skip empty rows
#                 if not row or not any(row):
#                     continue

#                 # Make sure the row has enough columns
#                 if len(row) < 4:
#                     continue

#                 # Get the Uptime/Downtime cell
#                 uptime_downtime = row[3]

#                 if not uptime_downtime:
#                     continue

#                 # Find percentages
#                 percentages = re.findall(
#                     percentage_pattern,
#                     uptime_downtime
#                 )

#                 # Need at least uptime + downtime
#                 if len(percentages) < 2:
#                     continue

#                 uptime = float(percentages[0])
#                 downtime = float(percentages[1])

#                 data.append({
#                     "Probe, Group, Device": row[0],
#                     "Sensor": row[1],
#                     "Average Total": row[2],
#                     "Uptime": uptime,
#                     "Downtime": downtime
#                 })


# # Create DataFrame
# df = pd.DataFrame(data)

# print(df)


# # Export to Excel
# df.to_excel("automotive_report.xlsx", index=False)

# print("Excel file created!")
#             # print("=" * 80)
#             # print(f"PAGE: {page_number + 1}")
#             # print(f"TABLE: {table_number + 1}")
#             # print("=" * 80)
#             # print(headers)

#             # for row in rows:
#                 # print(row)


# # C:\Users\Admin\finalProject\2026.08.12\Sector Report - Automotive _ Report _ PRTG Network Monitor (TTOVRW-PRTG01).pdf

