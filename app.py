
import io
from datetime import date
import pandas as pd
import streamlit as st

from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.graphics.barcode import code128
from reportlab.lib.units import inch as rl_inch


APP_TITLE = "SBD Carton Label Generator"

LABEL_WIDTH = 4 * inch
LABEL_HEIGHT = 6 * inch


def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def carton_text(carton_num: int, total_cartons: int) -> str:
    width = max(3, len(str(total_cartons)))
    return f"{carton_num:0{width}d} OF {total_cartons:0{width}d}"


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
):
    rows = []
    for i in range(1, total_cartons + 1):
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
                "Carton #": i,
                "Total Cartons": total_cartons,
                "Carton Text": carton_text(i, total_cartons),
            }
        )
    return pd.DataFrame(rows)


def draw_wrapped_text(c, text, x, y, max_width, font_name="Helvetica", font_size=10, leading=12, max_lines=3):
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


def draw_barcode(c, value, x, y, width=2.8 * inch, height=0.38 * inch):
    value = clean_text(value)
    if not value:
        return

    barcode = code128.Code128(value, barHeight=height, barWidth=0.012 * inch)
    barcode_width = barcode.width
    scale = min(1, width / barcode_width) if barcode_width else 1

    c.saveState()
    c.translate(x, y)
    c.scale(scale, 1)
    barcode.drawOn(c, 0, 0)
    c.restoreState()


def draw_section_line(c, y):
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(0.25 * inch, y, 3.75 * inch, y)


def create_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))

    for _, row in df.iterrows():
        # Outer border
        c.setStrokeColor(colors.black)
        c.setLineWidth(1.25)
        c.rect(0.18 * inch, 0.18 * inch, 3.64 * inch, 5.64 * inch)

        # Header
        c.setFont("Helvetica-Bold", 11)
        c.drawString(0.32 * inch, 5.52 * inch, "SHIP TO:")
        c.setFont("Helvetica-Bold", 13)
        c.drawString(1.15 * inch, 5.52 * inch, clean_text(row["Ship To"])[:28])

        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.32 * inch, 5.28 * inch, "FROM:")
        c.setFont("Helvetica", 10)
        c.drawString(1.15 * inch, 5.28 * inch, clean_text(row["From"])[:32])

        draw_section_line(c, 5.08 * inch)

        # Job #
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.32 * inch, 4.86 * inch, "JOB #")
        draw_barcode(c, row["Job #"], 0.32 * inch, 4.39 * inch)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(2.0 * inch, 4.20 * inch, clean_text(row["Job #"]))

        draw_section_line(c, 4.05 * inch)

        # PO #
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.32 * inch, 3.83 * inch, "CUSTOMER PO #")
        draw_barcode(c, row["PO #"], 0.32 * inch, 3.36 * inch)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(2.0 * inch, 3.17 * inch, clean_text(row["PO #"]))

        draw_section_line(c, 3.02 * inch)

        # Description
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.32 * inch, 2.80 * inch, "DESCRIPTION")
        draw_wrapped_text(
            c,
            row["Description"],
            0.32 * inch,
            2.60 * inch,
            3.36 * inch,
            font_name="Helvetica-Bold",
            font_size=10,
            leading=12,
            max_lines=3,
        )

        draw_section_line(c, 2.05 * inch)

        # Qty / Part / Date
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.32 * inch, 1.84 * inch, "QTY:")
        c.setFont("Helvetica", 10)
        c.drawString(0.90 * inch, 1.84 * inch, clean_text(row["Qty Per Carton"]))

        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.32 * inch, 1.62 * inch, "CUSTOMER PART #:")
        c.setFont("Helvetica", 10)
        c.drawString(1.72 * inch, 1.62 * inch, clean_text(row["Customer Part #"])[:22])

        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.32 * inch, 1.40 * inch, "SHIP DATE:")
        c.setFont("Helvetica", 10)
        c.drawString(1.32 * inch, 1.40 * inch, clean_text(row["Ship Date"]))

        draw_section_line(c, 1.20 * inch)

        # Carton
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.32 * inch, 0.98 * inch, "CARTON")
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(2.0 * inch, 0.57 * inch, clean_text(row["Carton Text"]))

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


st.set_page_config(page_title=APP_TITLE, page_icon="🏷️", layout="centered")

st.title("🏷️ SBD Carton Label Generator")
st.caption("Generates 4 × 6 carton labels with automatic carton numbering.")

with st.form("label_form"):
    st.subheader("Shipment Information")

    ship_to = st.text_input("Ship To", value="Stanley Black & Decker")
    ship_from = st.text_input("From", value="Sterling Digital Print")

    col1, col2 = st.columns(2)
    with col1:
        job_number = st.text_input("Job #", value="")
        po_number = st.text_input("PO #", value="")
        qty_per_carton = st.text_input("Qty Per Carton", value="")
    with col2:
        customer_part = st.text_input("Customer Part #", value="")
        ship_date_value = st.date_input("Ship Date", value=date.today())
        total_cartons = st.number_input("Total Cartons", min_value=1, max_value=5000, value=1, step=1)

    description = st.text_area("Description", value="", height=80)

    submitted = st.form_submit_button("Generate Labels")

if submitted:
    errors = []

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
            total_cartons=int(total_cartons),
        )

        pdf_bytes = create_pdf(df)
        excel_bytes = create_excel(df)

        st.success(f"Generated {len(df)} label(s).")

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
