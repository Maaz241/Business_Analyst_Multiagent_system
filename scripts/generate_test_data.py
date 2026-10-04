"""
Generator for realistic test files (Business Data and Knowledge Base).
Creates:
1. data/test_upload/novamart_q4_2022_sales.csv (CSV business data)
2. data/test_upload/novamart_retail_sample_2022.xlsx (Excel business data)
3. data/test_upload/novamart_q4_2022_executive_memo.pdf (PDF corporate knowledge)
4. data/test_upload/novamart_omnichannel_policy_2022.docx (DOCX corporate knowledge)
"""

import os
import random
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import openpyxl
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

OUTPUT_DIR = Path("data/test_upload")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════
# 1. Generate Business Data: CSV & Excel
# ═══════════════════════════════════════════════════════════════════

def generate_business_datasets():
    print("Generating business datasets (CSV and Excel)...")
    random.seed(42)

    categories = {
        "Electronics": [
            ("PROD-ELEC-101", "NovaSonic Wireless ANC Headphones", 89.99),
            ("PROD-ELEC-102", "NovaCharge 65W GaN Multi-Port Hub", 34.50),
            ("PROD-ELEC-103", "NovaVision 4K Ultra HD Streaming Stick", 49.00),
            ("PROD-ELEC-104", "NovaFit Smart Fitness Tracker v3", 65.00),
            ("PROD-ELEC-105", "NovaBass Bluetooth Water-Resistant Speaker", 42.00),
        ],
        "Home & Living": [
            ("PROD-HOME-201", "Nordic Minimalist Ceramic Lamp", 38.00),
            ("PROD-HOME-202", "Smart Aroma Diffuser & Humidifier", 29.50),
            ("PROD-HOME-203", "Ergonomic Memory Foam Lumbar Support", 24.99),
            ("PROD-HOME-204", "Stainless Steel Thermal Brew Travel Tumbler", 19.95),
            ("PROD-HOME-205", "Bamboo Fiber Luxury Bed Sheet Set", 55.00),
        ],
        "Gifts": [
            ("PROD-GIFT-301", "Executive Handcrafted Leather Journal", 22.50),
            ("PROD-GIFT-302", "Gourmet Artisan Tea Selection Gift Box", 32.00),
            ("PROD-GIFT-303", "Vintage Constellation Brass Pocket Compass", 18.00),
            ("PROD-GIFT-304", "Luxury Scented Soy Candle Holiday Trio", 27.50),
        ],
        "Accessories": [
            ("PROD-ACC-401", "RFID-Blocking Slim Carbon Fiber Cardholder", 16.50),
            ("PROD-ACC-402", "Waterproof Tech Accessory Cable Organizer", 14.00),
            ("PROD-ACC-403", "Polarized Lightweight Titanium Sunglasses", 45.00),
            ("PROD-ACC-404", "Genuine Italian Leather Dress Belt", 28.00),
        ],
    }

    countries = [
        ("United Kingdom", 0.35),
        ("Germany", 0.20),
        ("France", 0.15),
        ("Netherlands", 0.10),
        ("Australia", 0.08),
        ("United States", 0.07),
        ("Japan", 0.05),
    ]

    country_list = [c[0] for c in countries]
    country_weights = [c[1] for c in countries]

    start_date = datetime(2022, 10, 1)
    end_date = datetime(2022, 12, 31)
    days_delta = (end_date - start_date).days

    num_customers = 180
    customers = [f"CUST-2022-{i:04d}" for i in range(1, num_customers + 1)]

    records = []
    order_id_counter = 10001

    # Generate 650 transactions
    for _ in range(650):
        rand_days = random.randint(0, days_delta)
        order_date = start_date + timedelta(days=rand_days)
        
        # Black Friday / Cyber Monday surge (Nov 24 - Nov 30)
        if 54 <= rand_days <= 60:
            order_count_boost = random.choice([2, 3])
        else:
            order_count_boost = 1

        cat_name = random.choice(list(categories.keys()))
        prod_id, prod_name, base_price = random.choice(categories[cat_name])

        qty = random.randint(1, 8) if cat_name != "Electronics" else random.randint(1, 3)
        country = random.choices(country_list, weights=country_weights)[0]
        cust_id = random.choice(customers)

        # slight price variation / discount
        discount = random.choice([0.0, 0.05, 0.10, 0.15]) if rand_days >= 50 else 0.0
        unit_price = round(base_price * (1.0 - discount), 2)
        revenue = round(qty * unit_price, 2)

        order_id = f"ORD-2022-{order_id_counter}"
        order_id_counter += 1

        records.append({
            "order_id": order_id,
            "order_date": order_date.strftime("%Y-%m-%d"),
            "customer_id": cust_id,
            "product_id": prod_id,
            "product_name": prod_name,
            "category": cat_name,
            "country": country,
            "quantity": qty,
            "unit_price": unit_price,
            "revenue": revenue,
            "year": order_date.year,
            "quarter": f"{order_date.year}-Q{(order_date.month - 1) // 3 + 1}",
            "month": order_date.month,
            "month_name": order_date.strftime("%B"),
        })

    df = pd.DataFrame(records)
    df = df.sort_values("order_date").reset_index(drop=True)

    # 1. Save CSV
    csv_path = OUTPUT_DIR / "novamart_q4_2022_sales.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved CSV: {csv_path} ({len(df)} rows, £{df['revenue'].sum():,.2f} total revenue)")

    # 2. Save Excel (.xlsx) with 2 sheets
    xlsx_path = OUTPUT_DIR / "novamart_retail_sample_2022.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Transactions", index=False)
        
        targets_data = [
            {"metric": "Q4 Total Revenue Target", "target_value": "£125,000", "period": "2022-Q4", "region": "Global", "notes": "Holiday expansion goal"},
            {"metric": "Electronics Revenue Target", "target_value": "£45,000", "period": "2022-Q4", "region": "Global", "notes": "Recovery after component shortages"},
            {"metric": "North America Expansion Revenue", "target_value": "£18,000", "period": "2022-Q4", "region": "North America", "notes": "New Chicago hub testing"},
            {"metric": "Black Friday Week AOV", "target_value": "£85.00", "period": "2022-W48", "region": "Global", "notes": "Promotional bundling threshold"},
        ]
        pd.DataFrame(targets_data).to_excel(writer, sheet_name="QuarterlyTargets", index=False)
    print(f"Saved Excel: {xlsx_path} (2 sheets: Transactions, QuarterlyTargets)")


# ═══════════════════════════════════════════════════════════════════
# 2. Generate Corporate Knowledge: PDF
# ═══════════════════════════════════════════════════════════════════

def generate_pdf_knowledge():
    print("Generating corporate knowledge PDF...")
    pdf_path = OUTPUT_DIR / "novamart_q4_2022_executive_memo.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45,
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=10,
    )
    
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#6366F1"),
        spaceAfter=15,
    )

    heading2_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=8,
    )

    callout_style = ParagraphStyle(
        "Callout",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#4338CA"),
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("NovaMart International Retail — Executive Strategy Memo", title_style))
    story.append(Paragraph("CONFIDENTIAL & PROPRIETARY — FOR BOARD OF DIRECTORS & EXECUTIVE COMMITTEE", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#6366F1"), spaceAfter=15))

    # Memo metadata table
    meta_data = [
        [Paragraph("<b>Date:</b> October 4, 2022", body_style), Paragraph("<b>Author:</b> Sarah Sterling, Chief Operating Officer", body_style)],
        [Paragraph("<b>Subject:</b> Q4 2022 Commercial Strategy & Regional Expansion", body_style), Paragraph("<b>Distribution:</b> Executive Leadership Team", body_style)],
    ]
    t = Table(meta_data, colWidths=[260, 260])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    # Section 1
    story.append(Paragraph("1. Executive Summary & Macroeconomic Context", heading2_style))
    story.append(Paragraph(
        "As NovaMart enters the fourth quarter of 2022, management forecasts accelerated transaction volumes across all primary European territories, bolstered by our newly operational North American and Japanese pilot markets. Following the inventory rationalization and supplier realignment executed during mid-2022, core stock levels for our high-margin Electronics and Home & Living categories have reached optimal inventory health. Q4 revenue is targeted at £125,000 with a stretch objective of £140,000.",
        body_style
    ))

    # Section 2
    story.append(Paragraph("2. Operational Milestone: North American Hub Commissioning", heading2_style))
    story.append(Paragraph(
        "In October 2022, NovaMart formally inaugurated its automated fulfillment hub in Chicago, Illinois, partnering with ShipWire Logistics. This facility enables 48-hour delivery across 85% of continental US and Canadian metro corridors. Initial transaction data shows strong basket adoption for the NovaSonic Wireless ANC Headphones and NovaCharge GaN Hubs. Management anticipates North American revenue to contribute between 7% and 10% of total Q4 turnover.",
        body_style
    ))

    # Section 3
    story.append(Paragraph("3. Electronics Category Recovery & Component Sourcing", heading2_style))
    story.append(Paragraph(
        "Unlike the supply chain bottlenecks experienced during 2021, NovaMart's dual-sourcing agreement with semiconductor fabricators in Taiwan and South Korea has secured 100% allocation for critical Bluetooth and charging modules. Consequently, out-of-stock rates for top-selling Electronics SKUs dropped to 1.4% in October, compared to an average of 18.2% during prior quarters. Gross margins for Electronics are projected at 42.5%.",
        body_style
    ))

    # Section 4
    story.append(Paragraph("4. Black Friday / Cyber Monday Commercial Posture", heading2_style))
    story.append(Paragraph(
        "Management has authorized a structured discount strategy for Week 48 (November 21–28). Promotional discounts are capped strictly at 15% for premium Electronics and 20% for select Home & Living lines. Flash promotions must preserve an Average Order Value (AOV) exceeding £80.00. Marketing spend will scale by 35% during this window, concentrated on targeted programmatic display and VIP customer email flows.",
        body_style
    ))

    # Section 5
    story.append(Paragraph("5. APAC Distribution Partnership Realignment", heading2_style))
    story.append(Paragraph(
        "Following earlier logistical transitions in the Asia-Pacific region, NovaMart has deepened its integration with Kerry Logistics and local courier networks in Australia and Japan. Freight transit times have decreased from 14 business days to 5.5 days, restoring customer satisfaction scores in Australia to 91%. APAC is projected to deliver 12% to 15% of fourth-quarter global orders.",
        body_style
    ))

    # Callout Box
    story.append(Spacer(1, 10))
    callout_data = [[Paragraph(
        "<b>Governance Directive:</b> All financial analysts must verify transaction totals against the central Postgres/Pandas sales ledger before reporting regional margin variances. Do not infer price elasticity without deterministic basket calculations.",
        callout_style
    )]]
    callout_table = Table(callout_data, colWidths=[520])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EEF2FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#6366F1")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(callout_table)

    doc.build(story)
    print(f"Saved PDF: {pdf_path}")


# ═══════════════════════════════════════════════════════════════════
# 3. Generate Corporate Knowledge: Word DOCX
# ═══════════════════════════════════════════════════════════════════

def generate_docx_knowledge():
    print("Generating corporate knowledge Word document (DOCX)...")
    docx_path = OUTPUT_DIR / "novamart_omnichannel_policy_2022.docx"

    doc = Document()

    # Title
    title = doc.add_heading("NovaMart Global Omnichannel & Wholesale Distribution Policy (2022)", level=0)
    title.style.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph("Document Ref: POL-DIST-2022-V3 | Effective Date: October 1, 2022 | Classification: Internal Operational Standard")

    # Section 1
    doc.add_heading("1. Purpose and Scope", level=1)
    doc.add_paragraph(
        "This policy governs all direct-to-consumer (D2C) and business-to-business (B2B) wholesale transactions across NovaMart's e-commerce storefronts, mobile channels, and international distribution hubs. Compliance is mandatory for all regional sales directors, warehouse operations leads, and finance controllers."
    )

    # Section 2
    doc.add_heading("2. Minimum Order Quantities (MOQ) & Volume Pricing", level=1)
    doc.add_paragraph(
        "To preserve logistics efficiency and pallet optimization, corporate wholesale orders are subject to the following tiering:\n"
        "• Tier 1 (Standard Retail): 1 to 20 units. Standard catalog pricing applies.\n"
        "• Tier 2 (Commercial Partner): 21 to 100 units. Eligible for 5.0% volume discount.\n"
        "• Tier 3 (Master Wholesale Distributor): 101+ units. Eligible for negotiated pricing up to a strict ceiling of 15.0% discount upon VP Commercial approval.\n"
        "Unauthorized off-invoice discounting exceeding 15% is prohibited under Section 4 of our corporate governance guidelines."
    )

    # Section 3
    doc.add_heading("3. Shipping Service Level Agreements (SLAs)", level=1)
    doc.add_paragraph(
        "Standard order processing benchmarks by region:\n"
        "• United Kingdom & Domestic Hub: Same-day dispatch for orders received before 14:00 GMT. 24-hour tracked delivery.\n"
        "• Western Europe (Germany, France, Netherlands): 48-hour delivery via DHL Express.\n"
        "• North America (United States, Canada): 48-to-72 hour delivery via Chicago fulfillment center.\n"
        "• Asia-Pacific (Australia, Japan): 5-to-7 business days via Kerry Logistics priority air freight."
    )

    # Section 4
    doc.add_heading("4. Returns, Cancellations, and Defect Handling", level=1)
    doc.add_paragraph(
        "NovaMart maintains a customer-friendly 30-day return policy for unopened items in original packaging. "
        "For Electronics, opened items may be returned within 14 days subject to automated serial number verification. "
        "Defective merchandise will receive immediate advance replacement. Historical return rates across all categories "
        "must remain under 3.5% of total quarterly gross sales; any SKU exceeding 5.0% return frequency will trigger an automated supply audit."
    )

    # Section 5
    doc.add_heading("5. Audit Provenance & Analytical Transparency", level=1)
    doc.add_paragraph(
        "When business analysts evaluate channel performance, all sales figures must cite order_id records directly from the cleaned transactions dataset. "
        "Discounts must be derived by comparing realized unit_price against the baseline catalog MSRP. Speculative conclusions lacking document or transaction citations will be rejected by internal auditing."
    )

    doc.save(str(docx_path))
    print(f"Saved DOCX: {docx_path}")


if __name__ == "__main__":
    generate_business_datasets()
    generate_pdf_knowledge()
    generate_docx_knowledge()
    print("\n[SUCCESS] All 4 test files generated successfully in data/test_upload/!")
