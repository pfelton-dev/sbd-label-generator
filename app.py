import io
import math
from datetime import date

import pandas as pd
import streamlit as st

from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.graphics.barcode import code128


APP_TITLE = "SBD Carton Label Generator"

LABEL_WIDTH = 4 * inch
LABEL_HEIGHT = 6 * inch


CUSTOMER_TEMPLATES = {
    "Stanley / ADM": {
        "ship_to": "Stanley Black & Decker",
        "ship_from": "Konica Minolta",
    },
    "US Foods": {
        "ship_to": "US Foods",
        "ship_from": "Sterling Digital Print",
    },
    "GSK": {
        "ship_to": "GSK",
        "ship_from": "Sterling Digital Print",
    },
    "Custom": {
        "ship_to": "",
        "ship_from": "Sterling Digital Print",
    },
}


def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def carton_text(carton_num: int, total_cartons: int) -> str:
    width = max(3, len(str(total_cartons)))
    return f"{carton_num:0{width}d} OF {total_cartons:0{width}d}"


def calculate_cartons(total_pieces, pieces_per_carton):
    if total_pieces <= 0 or pieces_per_carton <= 0:
        return 1
    return math.ceil(total_pieces / pieces_per_carton)


def build_label_rows(
    ship_to,
    ship_from,
    job_number,
    po_number,
    description,
    customer_part,
    qty_per_carton,
    ship_date,
    total_cartons,
    start_container=1,
    end_container=None,
):
    if end_container is None:
        end_container = total_cartons

    rows = []

    for i in range(int(start_container), int(end_container) + 1):
        rows.append(
            {
                "Ship To": ship_to,
                "From": ship_from,
                "Job #": job_number,
                "PO #": po_number,
                "Description": description,
                "Customer Part #": customer_part,
                "Qty Per Carton": qty_per_carton,
                "Ship Date": ship_date,
                "Container #": i,
                "Total Containers": total_cartons,
                "Container Text": carton_text(i, int(total_cartons)),
            }
        )

    return pd.DataFrame(rows)


def draw_section_line(c, y):
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(0.25 * inch, y, 3.75 * inch, y)


def draw_barcode(c, value, x, y, width=1.45 * inch, height=0.35 * inch):
    value = clean_text(value)

    if not value:
        return

    barcode = code128.Code128(value, barHeight=height, barWidth=0.011 * inch)
    scale = min(1, width / barcode.width) if barcode.width else 1

    c.saveState()
    c.translate(x, y)
    c.scale(scale, 1)
    barcode.drawOn(c, 0, 0)
    c.restoreState()


def draw_wrapped_text(
    c,
    text,
    x,
    y,
    max_width,
    font_name="Helvetica-Bold",
    font_size=10,
    leading=12,
    max_lines=3,
):
    c.setFont(font_name, font_size)

    words = clean_text(text).split()
    lines = []
    current = ""

    for word in words:
        test = word if not current else current + " " + word

        if c.stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    lines = lines[:max_lines]

    for line in lines:
        c.drawString(x, y, line)
        y -= leading

    return y


def draw_single_label(c, row):
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.25)
    c.rect(0.18 * inch, 0.18 * inch, 3.64 * inch, 5.64 * inch)

    # Header
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.32 * inch, 5.52 * inch, "SHIP TO:")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1.15 * inch, 5.52 * inch, clean_text(row["Ship To"])[:30])

    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.32 * inch, 5.31 * inch, "FROM:")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1.15 * inch, 5.31 * inch, clean_text(row["From"])[:30])

    draw_section_line(c, 5.10 * inch)

    # Job + PO
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.32 * inch, 4.91 * inch, "JOB #")
    c.drawString(2.05 * inch, 4.91 * inch, "CUSTOMER PO #")

    draw_barcode(c, row["Job #"], 0.45 * inch, 4.43 * inch, width=1.35 * inch)
    draw_barcode(c, row["PO #"], 2.13 * inch, 4.43 * inch, width=1.45 * inch)

    c.setFont("Helvetica", 8)
    c.drawCentredString(1.12 * inch, 4.26 * inch, clean_text(row["Job #"]))
    c.drawCentredString(2.85 * inch, 4.26 * inch, clean_text(row["PO #"]))

    draw_section_line(c, 4.08 * inch)

    # Qty + Description
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.32 * inch, 3.88 * inch, "QTY:")
    draw_barcode(c, row["Qty Per Carton"], 0.65 * inch, 3.46 * inch, width=1.20 * inch)

    c.setFont("Helvetica", 8)
    c.drawCentredString(1.25 * inch, 3.30 * inch, clean_text(row["Qty Per Carton"]))

    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(2.05 * inch, 3.88 * inch, "DESCRIPTION:")
    draw_wrapped_text(
        c,
        row["Description"],
        2.05 * inch,
        3.68 * inch,
        1.55 * inch,
        font_name="Helvetica-Bold",
        font_size=8.5,
        leading=10,
        max_lines=4,
    )

    draw_section_line(c, 3.12 * inch)

    # Customer Part
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.32 * inch, 2.93 * inch, "CUSTOMER PART #:")

    draw_barcode(c, row["Customer Part #"], 1.18 * inch, 2.45 * inch, width=1.70 * inch)

    c.setFont("Helvetica", 8)
    c.drawCentredString(2.0 * inch, 2.28 * inch, clean_text(row["Customer Part #"]))

    draw_section_line(c, 2.08 * inch)

    # Date + Container
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.32 * inch, 1.88 * inch, "DATE:")
    draw_barcode(c, row["Ship Date"], 0.70 * inch, 1.48 * inch, width=1.30 * inch)

    c.setFont("Helvetica", 8)
    c.drawCentredString(1.35 * inch, 1.31 * inch, clean_text(row["Ship Date"]))

    c.setFont("Helvetica-Bold", 9)
    c.drawString(2.25 * inch, 1.88 * inch, "CONTAINER")

    c.setFont("Helvetica-Bold", 17)
    c.drawCentredString(3.0 * inch, 1.35 * inch, clean_text(row["Container Text"]))


def create_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))

    for _, row in df.iterrows():
        draw_single_label(c, row)
        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def create_preview_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))

    draw_single_label(c, df.iloc[0])
    c.showPage()

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def create_excel(df):
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="SBD Labels")
        ws = writer.book["SBD Labels"]

        for col in ws.columns:
            max_len = max(len(str(cell.value)) if cell.value is not None else 0 for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 35)

    buffer.seek(0)
    return buffer.getvalue()


def normalize_uploaded_columns(df):
    rename_map = {}

    for col in df.columns:
        c = str(col).strip().lower()

        if c in ["ship to", "ship_to", "customer"]:
            rename_map[col] = "Ship To"
        elif c in ["from", "ship from", "ship_from"]:
            rename_map[col] = "From"
        elif c in ["job #", "job", "job no", "job number"]:
            rename_map[col] = "Job #"
        elif c in ["po #", "po", "po number", "customer po", "customer po #"]:
            rename_map[col] = "PO #"
        elif c in ["description", "desc"]:
            rename_map[col] = "Description"
        elif c in ["customer part #", "customer part", "part #", "part number", "part"]:
            rename_map[col] = "Customer Part #"
        elif c in ["qty per carton", "qty", "quantity", "quantity per carton"]:
            rename_map[col] = "Qty Per Carton"
        elif c in ["ship date", "date"]:
            rename_map[col] = "Ship Date"
        elif c in ["total cartons", "cartons", "total containers", "containers"]:
            rename_map[col] = "Total Cartons"
        elif c in ["start container", "start carton"]:
            rename_map[col] = "Start Container"
        elif c in ["end container", "end carton"]:
            rename_map[col] = "End Container"
        elif c in ["total pieces", "pieces"]:
            rename_map[col] = "Total Pieces"
        elif c in ["pieces per carton", "pieces/carton", "per carton"]:
            rename_map[col] = "Pieces Per Carton"

    return df.rename(columns=rename_map)


st.set_page_config(page_title=APP_TITLE, page_icon="🏷️", layout="centered")

st.title("🏷️ SBD Carton Label Generator")
st.caption("Generates 4 × 6 carton labels with automatic container numbering.")

tabs = st.tabs(["Manual Entry", "Import Excel"])

with tabs[0]:
    with st.form("manual_form"):
        st.subheader("Shipment Information")

        customer_template = st.selectbox(
            "Customer Template",
            list(CUSTOMER_TEMPLATES.keys()),
            index=0,
        )

        default_ship_to = CUSTOMER_TEMPLATES[customer_template]["ship_to"]
        default_ship_from = CUSTOMER_TEMPLATES[customer_template]["ship_from"]

        ship_to = st.text_input("Ship To", value=default_ship_to)
        ship_from = st.text_input("From", value=default_ship_from)

        col1, col2 = st.columns(2)

        with col1:
            job_number = st.text_input("Job #", value="")
            po_number = st.text_input("PO #", value="")
            customer_part = st.text_input("Customer Part #", value="")

        with col2:
            qty_per_carton = st.text_input("Qty Per Carton", value="")
            ship_date_value = st.date_input("Ship Date", value=date.today())
            total_cartons_manual = st.number_input(
                "Total Cartons / Containers",
                min_value=1,
                max_value=5000,
                value=1,
                step=1,
            )

        description = st.text_area("Description", value="", height=80)

        st.subheader("Optional Carton Calculation")

        use_carton_calculation = st.checkbox("Calculate cartons from total pieces")

        calc_col1, calc_col2 = st.columns(2)

        with calc_col1:
            total_pieces = st.number_input(
                "Total Pieces",
                min_value=0,
                value=0,
                step=1,
                disabled=not use_carton_calculation,
            )

        with calc_col2:
            pieces_per_carton = st.number_input(
                "Pieces Per Carton",
                min_value=0,
                value=0,
                step=1,
                disabled=not use_carton_calculation,
            )

        if use_carton_calculation and total_pieces > 0 and pieces_per_carton > 0:
            calculated_cartons = calculate_cartons(total_pieces, pieces_per_carton)
            st.info(f"Calculated Total Cartons: {calculated_cartons}")
        else:
            calculated_cartons = total_cartons_manual

        st.subheader("Optional Reprint Range")

        range_col1, range_col2 = st.columns(2)

        with range_col1:
            start_container = st.number_input(
                "Start Container",
                min_value=1,
                max_value=5000,
                value=1,
                step=1,
            )

        with range_col2:
            end_container = st.number_input(
                "End Container",
                min_value=1,
                max_value=5000,
                value=int(calculated_cartons),
                step=1,
            )

        submitted = st.form_submit_button("Generate Labels")

    if submitted:
        errors = []

        total_cartons = int(calculated_cartons)

        if not clean_text(job_number):
            errors.append("Job # is required.")
        if not clean_text(po_number):
            errors.append("PO # is required.")
        if not clean_text(description):
            errors.append("Description is required.")
        if not clean_text(customer_part):
            errors.append("Customer Part # is required.")
        if not clean_text(qty_per_carton):
            errors.append("Qty Per Carton is required.")
        if int(start_container) > int(end_container):
            errors.append("Start Container cannot be greater than End Container.")
        if int(end_container) > total_cartons:
            errors.append("End Container cannot be greater than Total Cartons.")

        if errors:
            for error in errors:
                st.error(error)
        else:
            ship_date_text = ship_date_value.strftime("%m/%d/%Y")

            df = build_label_rows(
                ship_to=clean_text(ship_to),
                ship_from=clean_text(ship_from),
                job_number=clean_text(job_number),
                po_number=clean_text(po_number),
                description=clean_text(description),
                customer_part=clean_text(customer_part),
                qty_per_carton=clean_text(qty_per_carton),
                ship_date=ship_date_text,
                total_cartons=total_cartons,
                start_container=int(start_container),
                end_container=int(end_container),
            )

            pdf_bytes = create_pdf(df)
            preview_pdf_bytes = create_preview_pdf(df)
            excel_bytes = create_excel(df)

            st.success(f"Generated {len(df)} label(s).")

            st.download_button(
                label="Preview First Label PDF",
                data=preview_pdf_bytes,
                file_name=f"SBD_Label_Preview_{clean_text(job_number)}.pdf",
                mime="application/pdf",
            )

            st.download_button(
                label="Download PDF Labels",
                data=pdf_bytes,
                file_name=f"SBD_Labels_{clean_text(job_number)}.pdf",
                mime="application/pdf",
            )

            st.download_button(
                label="Download Excel Label Data",
                data=excel_bytes,
                file_name=f"SBD_Label_Data_{clean_text(job_number)}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            st.subheader("Preview Data")
            st.dataframe(df.head(20), use_container_width=True)

            if len(df) > 20:
                st.caption("Showing first 20 rows only.")


with tabs[1]:
    st.subheader("Import Excel File")

    st.write(
        "Upload an Excel file with columns like: Job #, PO #, Description, Customer Part #, Qty Per Carton, Ship Date, Total Cartons."
    )

    sample_df = pd.DataFrame(
        [
            {
                "Ship To": "Stanley Black & Decker",
                "From": "Sterling Digital Print",
                "Job #": "469380",
                "PO #": "5764295",
                "Description": "DCS565, DCS566 SAW MANUAL 32PG",
                "Customer Part #": "NA494285",
                "Qty Per Carton": "540",
                "Ship Date": "06/09/2026",
                "Total Cartons": 52,
                "Start Container": 1,
                "End Container": 52,
            }
        ]
    )

    sample_excel = create_excel(sample_df)

    st.download_button(
        label="Download Sample Excel Template",
        data=sample_excel,
        file_name="SBD_Label_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

    if uploaded_file:
        try:
            imported = pd.read_excel(uploaded_file)
            imported = normalize_uploaded_columns(imported)

            required_cols = [
                "Job #",
                "PO #",
                "Description",
                "Customer Part #",
                "Qty Per Carton",
                "Ship Date",
            ]

            has_total_cartons = "Total Cartons" in imported.columns
            has_calculation = "Total Pieces" in imported.columns and "Pieces Per Carton" in imported.columns

            missing = [col for col in required_cols if col not in imported.columns]

            if not has_total_cartons and not has_calculation:
                missing.append("Total Cartons OR Total Pieces + Pieces Per Carton")

            if missing:
                st.error("Missing required columns: " + ", ".join(missing))
            else:
                all_rows = []

                for _, r in imported.iterrows():
                    ship_to_value = clean_text(r.get("Ship To", "Stanley Black & Decker")) or "Stanley Black & Decker"
                    ship_from_value = clean_text(r.get("From", "Sterling Digital Print")) or "Sterling Digital Print"

                    if has_total_cartons and not pd.isna(r.get("Total Cartons")):
                        total = int(r["Total Cartons"])
                    else:
                        total = calculate_cartons(
                            int(r["Total Pieces"]),
                            int(r["Pieces Per Carton"]),
                        )

                    start_value = int(r.get("Start Container", 1)) if not pd.isna(r.get("Start Container", 1)) else 1
                    end_value = int(r.get("End Container", total)) if not pd.isna(r.get("End Container", total)) else total

                    ship_date_raw = r["Ship Date"]

                    if isinstance(ship_date_raw, pd.Timestamp):
                        ship_date_text = ship_date_raw.strftime("%m/%d/%Y")
                    else:
                        ship_date_text = clean_text(ship_date_raw)

                    temp_df = build_label_rows(
                        ship_to=ship_to_value,
                        ship_from=ship_from_value,
                        job_number=clean_text(r["Job #"]),
                        po_number=clean_text(r["PO #"]),
                        description=clean_text(r["Description"]),
                        customer_part=clean_text(r["Customer Part #"]),
                        qty_per_carton=clean_text(r["Qty Per Carton"]),
                        ship_date=ship_date_text,
                        total_cartons=total,
                        start_container=start_value,
                        end_container=end_value,
                    )

                    all_rows.append(temp_df)

                final_df = pd.concat(all_rows, ignore_index=True)

                pdf_bytes = create_pdf(final_df)
                preview_pdf_bytes = create_preview_pdf(final_df)
                excel_bytes = create_excel(final_df)

                st.success(f"Generated {len(final_df)} label(s) from uploaded file.")

                st.download_button(
                    label="Preview First Label PDF",
                    data=preview_pdf_bytes,
                    file_name="SBD_Imported_Label_Preview.pdf",
                    mime="application/pdf",
                )

                st.download_button(
                    label="Download PDF Labels",
                    data=pdf_bytes,
                    file_name="SBD_Imported_Labels.pdf",
                    mime="application/pdf",
                )

                st.download_button(
                    label="Download Excel Label Data",
                    data=excel_bytes,
                    file_name="SBD_Imported_Label_Data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

                st.subheader("Preview Imported Data")
                st.dataframe(final_df.head(50), use_container_width=True)

        except Exception as e:
            st.error(f"Could not process file: {e}")