"""Generate the bilingual User Manual PDF for Kuwait WhatsApp Growth Engine.

Run: cd docs && pip install reportlab arabic-reshaper python-bidi && python generate_user_manual.py
Output: USER_MANUAL.pdf
"""

import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether,
)

# ── Register Arabic fonts ────────────────────────────────────────────────────
FONT_DIR = os.path.dirname(os.path.abspath(__file__))
pdfmetrics.registerFont(TTFont("NotoArabic", os.path.join(FONT_DIR, "NotoSansArabic-Regular.ttf")))
pdfmetrics.registerFont(TTFont("NotoArabicBold", os.path.join(FONT_DIR, "NotoSansArabic-Bold.ttf")))


def reshape_arabic(text: str) -> str:
    """Reshape Arabic text for proper RTL rendering in reportlab."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except ImportError:
        return text


# ── Colors ────────────────────────────────────────────────────────────────────
PRIMARY = colors.HexColor("#10B981")
DARK = colors.HexColor("#0F172A")
GRAY = colors.HexColor("#64748B")
LIGHT_BG = colors.HexColor("#F8FAFC")
WHITE = colors.white
TABLE_HEADER_BG = colors.HexColor("#0F172A")
TABLE_ALT_BG = colors.HexColor("#F1F5F9")

# ── Styles ────────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

COVER_TITLE = ParagraphStyle("CoverTitle", parent=styles["Title"], fontSize=28, textColor=DARK, spaceAfter=8, alignment=TA_CENTER)
COVER_SUB = ParagraphStyle("CoverSub", parent=styles["Normal"], fontSize=14, textColor=GRAY, alignment=TA_CENTER, spaceAfter=4)
SECTION_H1 = ParagraphStyle("SectionH1", parent=styles["Heading1"], fontSize=20, textColor=DARK, spaceBefore=20, spaceAfter=10, borderWidth=0)
SECTION_H2 = ParagraphStyle("SectionH2", parent=styles["Heading2"], fontSize=15, textColor=PRIMARY, spaceBefore=14, spaceAfter=6)
SECTION_H3 = ParagraphStyle("SectionH3", parent=styles["Heading3"], fontSize=12, textColor=DARK, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14, textColor=DARK, spaceAfter=6, alignment=TA_JUSTIFY)
BULLET = ParagraphStyle("Bullet", parent=BODY, leftIndent=20, bulletIndent=10, spaceAfter=3)
STEP = ParagraphStyle("Step", parent=BODY, leftIndent=20, spaceAfter=4, textColor=DARK)
FOOTER_STYLE = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=GRAY, alignment=TA_CENTER)
TOC_ITEM = ParagraphStyle("TOCItem", parent=styles["Normal"], fontSize=11, leading=18, textColor=DARK)

# Arabic styles
AR_H1 = ParagraphStyle("ArH1", parent=SECTION_H1, fontName="NotoArabicBold", alignment=TA_RIGHT)
AR_H2 = ParagraphStyle("ArH2", parent=SECTION_H2, fontName="NotoArabicBold", alignment=TA_RIGHT)
AR_BODY = ParagraphStyle("ArBody", parent=BODY, fontName="NotoArabic", alignment=TA_RIGHT, leading=16)
AR_BULLET = ParagraphStyle("ArBullet", parent=AR_BODY, rightIndent=20, spaceAfter=3)


def hr():
    return HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceBefore=6, spaceAfter=6)


def make_table(headers, rows, col_widths=None):
    """Create a styled table."""
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), TABLE_ALT_BG))
    t.setStyle(TableStyle(style))
    return t


def build_pdf():
    output = os.path.join(FONT_DIR, "USER_MANUAL.pdf")
    doc = SimpleDocTemplate(
        output, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
        title="Kuwait WhatsApp Growth Engine - User Manual",
        author="KW Growth Engine",
    )

    story = []

    # ═══════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ═══════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 6 * cm))
    story.append(Paragraph("Kuwait WhatsApp Growth Engine", COVER_TITLE))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("User Manual", ParagraphStyle("CoverManual", parent=COVER_TITLE, fontSize=22, textColor=PRIMARY)))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("Enterprise WhatsApp CRM Platform for Kuwait", COVER_SUB))
    story.append(Spacer(1, 0.5 * cm))
    story.append(hr())
    story.append(Paragraph(f"Version 1.0  |  April 2026", COVER_SUB))
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph("Bilingual Edition: English + Arabic", ParagraphStyle("Lang", parent=COVER_SUB, fontSize=11, textColor=PRIMARY)))
    story.append(Spacer(1, 4 * cm))
    story.append(Paragraph("Confidential - For authorized users only", FOOTER_STYLE))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # TABLE OF CONTENTS
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("Table of Contents", SECTION_H1))
    story.append(hr())
    toc = [
        "1. Getting Started",
        "    1.1 System Requirements",
        "    1.2 Registration",
        "    1.3 First Login",
        "    1.4 Dashboard Overview",
        "2. New Customer Onboarding Guide (with Sample)",
        "    Step 1: Register the Company",
        "    Step 2: Connect WhatsApp Channel",
        "    Step 3: Import Contacts",
        "    Step 4: Create Sales Pipeline & First Deal",
        "    Step 5: Start First Conversation",
        "    Step 6: Set Up an Automation",
        "    Step 7: Launch First Campaign",
        "3. Feature Guide",
        "    3.1 Inbox & Conversations",
        "    3.2 Contacts & CRM",
        "    3.3 Sales Pipeline",
        "    3.4 Campaigns",
        "    3.5 Automations",
        "    3.6 Chatbot Flows",
        "    3.7 Landing Pages",
        "    3.8 Analytics Dashboard",
        "    3.9 Templates",
        "4. Settings & Administration",
        "    4.1 Security",
        "    4.2 Team Management",
        "    4.3 Channels",
        "    4.4 Billing & Subscription",
        "    4.5 Compliance & Data Residency",
        "5. User Roles & Permissions",
        "6. Arabic Section",
    ]
    for item in toc:
        indent = 20 if item.startswith("    ") else 0
        s = ParagraphStyle("toc", parent=TOC_ITEM, leftIndent=indent, fontSize=10 if indent else 11, textColor=DARK if not indent else GRAY)
        story.append(Paragraph(item.strip(), s))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 1: GETTING STARTED
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("1. Getting Started", SECTION_H1))
    story.append(hr())

    story.append(Paragraph("1.1 System Requirements", SECTION_H2))
    for r in ["Modern web browser (Chrome, Firefox, Safari, Edge)", "Stable internet connection", "WhatsApp Business account (for messaging features)", "Supported devices: Desktop, tablet, mobile (responsive design)"]:
        story.append(Paragraph(f"<bullet>&bull;</bullet> {r}", BULLET))

    story.append(Paragraph("1.2 Registration", SECTION_H2))
    steps = [
        ("<b>Step 1:</b> Navigate to <font color='#10B981'>https://app.kwgrowth.com/register</font>",),
        ("<b>Step 2:</b> Fill in the registration form:",),
    ]
    for s in steps:
        story.append(Paragraph(s[0], STEP))
    fields = ["Company Name (e.g., \"Al-Baraka Trading\")", "First Name, Last Name", "Email (e.g., owner@albaraka.kw)", "Username", "Password (minimum 8 characters)"]
    for f in fields:
        story.append(Paragraph(f"<bullet>&bull;</bullet> {f}", ParagraphStyle("FieldBullet", parent=BULLET, leftIndent=40, bulletIndent=30)))
    story.append(Paragraph("<b>Step 3:</b> Click <b>\"Get Started Free\"</b>", STEP))
    story.append(Paragraph("<b>Step 4:</b> You are redirected to the Inbox dashboard", STEP))

    story.append(Paragraph("1.3 First Login", SECTION_H2))
    for s in ["Navigate to https://app.kwgrowth.com/login", "Enter your email and password", "Click \"Sign In\"", "You land on the Inbox page - the central hub for all conversations"]:
        story.append(Paragraph(f"<bullet>&bull;</bullet> {s}", BULLET))

    story.append(Paragraph("1.4 Dashboard Overview", SECTION_H2))
    story.append(Paragraph("The sidebar navigation provides access to all platform modules:", BODY))
    nav_data = [
        ["Inbox", "Real-time WhatsApp conversations"],
        ["Contacts", "Customer database and CRM"],
        ["Pipeline", "Sales deals (Kanban board)"],
        ["Campaigns", "Bulk WhatsApp broadcasts"],
        ["Automations", "Workflow automation rules"],
        ["Chatbots", "AI chatbot flow builder"],
        ["Templates", "WhatsApp message templates"],
        ["Landing Pages", "Marketing page builder"],
        ["Analytics", "Business intelligence dashboard"],
        ["Settings", "Account, team, billing, compliance"],
    ]
    story.append(make_table(["Page", "Purpose"], nav_data, col_widths=[4 * cm, 12 * cm]))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 2: NEW CUSTOMER ONBOARDING GUIDE
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("2. New Customer Onboarding Guide", SECTION_H1))
    story.append(Paragraph("Complete Walkthrough with Sample: Al-Baraka Trading Company", ParagraphStyle("OnboardSub", parent=BODY, fontSize=12, textColor=PRIMARY, spaceAfter=10)))
    story.append(hr())

    # Step 1
    story.append(Paragraph("Step 1: Register the Company", SECTION_H2))
    story.append(Paragraph("Create the company account with the following sample data:", BODY))
    reg_data = [
        ["Company Name", "Al-Baraka Trading"],
        ["Owner Name", "Ahmad Al-Baraka"],
        ["Email", "owner@albaraka.kw"],
        ["Username", "ahmad"],
        ["Password", "(secure password, min 8 characters)"],
    ]
    story.append(make_table(["Field", "Sample Value"], reg_data, col_widths=[5 * cm, 11 * cm]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("<b>Result:</b> Company created. \"Owner\" role assigned automatically. JWT access token issued. Redirected to Inbox.", BODY))

    # Step 2
    story.append(Paragraph("Step 2: Connect WhatsApp Channel", SECTION_H2))
    for i, s in enumerate([
        "Go to <b>Settings > Channels</b>",
        "Click <b>\"Connect WhatsApp\"</b>",
        "Enter your <b>WhatsApp Business Phone Number ID</b> (from Meta Business Suite)",
        "Enter your <b>Cloud API Access Token</b>",
        "Set a <b>Webhook Verify Token</b>",
        "Click <b>\"Save & Verify\"</b>",
        "Status shows <font color='#10B981'><b>Connected</b></font> with green indicator",
    ], 1):
        story.append(Paragraph(f"{i}. {s}", STEP))

    # Step 3
    story.append(Paragraph("Step 3: Import Contacts", SECTION_H2))
    story.append(Paragraph("<b>Option A - Manual Entry:</b>", BODY))
    for i, s in enumerate(["Go to <b>Contacts</b>", "Click <b>\"+  New Contact\"</b>", "Enter: Phone (+96599001001), Name (Abdullah Al-Mutairi), Email", "Click <b>\"Create\"</b>"], 1):
        story.append(Paragraph(f"{i}. {s}", STEP))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("<b>Option B - CSV Import:</b>", BODY))
    for i, s in enumerate(["Go to <b>Contacts</b>", "Click <b>\"Import\"</b>", "Upload CSV file with columns: phone, first_name, last_name, email", "Map columns and confirm", "Import runs in background; progress is shown"], 1):
        story.append(Paragraph(f"{i}. {s}", STEP))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("<b>Sample CSV:</b>", BODY))
    csv_data = [
        ["+96599001001", "Abdullah", "Al-Mutairi", "abdullah@example.kw"],
        ["+96599001002", "Fatima", "Al-Sabah", "fatima@example.kw"],
        ["+96599001003", "Mohammed", "Al-Rashidi", "mohammed@example.kw"],
        ["+96599001004", "Noura", "Al-Kandari", "noura@example.kw"],
        ["+96599001005", "Yousef", "Al-Enezi", "yousef@example.kw"],
    ]
    story.append(make_table(["phone", "first_name", "last_name", "email"], csv_data, col_widths=[3.5 * cm, 3.5 * cm, 3.5 * cm, 5.5 * cm]))

    # Step 4
    story.append(PageBreak())
    story.append(Paragraph("Step 4: Create Sales Pipeline & First Deal", SECTION_H2))
    for i, s in enumerate([
        "Go to <b>Pipeline</b>",
        "Click <b>\"New Pipeline\"</b> - name it \"Sales Pipeline\"",
        "Add stages: <b>New Lead > Proposal Sent > Negotiation > Won</b>",
        "Click <b>\"New Deal\"</b> and fill in:",
    ], 1):
        story.append(Paragraph(f"{i}. {s}", STEP))
    deal_data = [
        ["Title", "Office Furniture Supply"],
        ["Value", "2,500.000 KWD"],
        ["Contact", "Abdullah Al-Mutairi"],
        ["Stage", "New Lead"],
        ["Expected Close", "30 days from now"],
    ]
    story.append(make_table(["Field", "Value"], deal_data, col_widths=[5 * cm, 11 * cm]))
    story.append(Paragraph("5. Drag the deal card between stages as it progresses through the sales cycle.", STEP))

    # Step 5
    story.append(Paragraph("Step 5: Start First Conversation", SECTION_H2))
    for i, s in enumerate([
        "Go to <b>Inbox</b>",
        "Click <b>\"New Conversation\"</b>",
        "Select contact: <b>Abdullah Al-Mutairi</b>",
        "Type: <i>\"Hello Abdullah! Welcome to Al-Baraka Trading. How can we help you today?\"</i>",
        "Click <b>Send</b> - message delivered via WhatsApp Cloud API",
        "When the customer replies, the message appears in <b>real-time</b> (no refresh needed)",
    ], 1):
        story.append(Paragraph(f"{i}. {s}", STEP))

    # Step 6
    story.append(Paragraph("Step 6: Set Up an Automation", SECTION_H2))
    for i, s in enumerate([
        "Go to <b>Automations</b>",
        "Click <b>\"New Automation\"</b>",
        "Configure the automation:",
    ], 1):
        story.append(Paragraph(f"{i}. {s}", STEP))
    auto_data = [
        ["Trigger", "When a new message is received"],
        ["Condition", "Message contains 'price' or 'how much'"],
        ["Action", "Auto-reply with pricing template"],
    ]
    story.append(make_table(["Setting", "Value"], auto_data, col_widths=[4 * cm, 12 * cm]))
    story.append(Paragraph("4. <b>Enable</b> the automation. Now when any customer asks about pricing, they receive an instant reply.", STEP))

    # Step 7
    story.append(Paragraph("Step 7: Launch First Campaign", SECTION_H2))
    for i, s in enumerate([
        "Go to <b>Campaigns</b>",
        "Click <b>\"New Campaign\"</b>",
        "Configure:",
    ], 1):
        story.append(Paragraph(f"{i}. {s}", STEP))
    camp_data = [
        ["Name", "Summer Sale 2026"],
        ["Message Type", "Template"],
        ["Template", "Select an approved WhatsApp template"],
        ["Audience", "All contacts with tag \"WhatsApp Active\""],
    ]
    story.append(make_table(["Setting", "Value"], camp_data, col_widths=[4 * cm, 12 * cm]))
    story.append(Paragraph("4. Click <b>\"Send Now\"</b> or schedule for later.", STEP))
    story.append(Paragraph("5. Track delivery, read receipts, and replies in the campaign dashboard.", STEP))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 3: FEATURE GUIDE
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("3. Feature Guide", SECTION_H1))
    story.append(hr())

    features = {
        "3.1 Inbox & Conversations": [
            "Real-time messaging via WhatsApp Cloud API",
            "Conversation status: Open, Pending, Closed, Snoozed",
            "Agent assignment for team collaboration",
            "Message types: Text, Image, Video, Document, Template",
            "Delivery status tracking: Sent > Delivered > Read",
            "WebSocket-powered live updates (no page refresh needed)",
            "Smart routing: auto-assigns conversations based on agent skills and availability",
        ],
        "3.2 Contacts & CRM": [
            "Unified contact database with phone, email, notes",
            "Custom fields for business-specific data",
            "Tag system with custom colors (VIP, Hot Lead, etc.)",
            "Contact status: Active, Inactive, Blocked",
            "Source tracking: WhatsApp, Import, Manual, Landing Page",
            "Lead scoring and bulk actions (assign, tag, delete, change status)",
            "CSV import/export and full activity timeline per contact",
        ],
        "3.3 Sales Pipeline": [
            "Kanban board with drag-and-drop deal management",
            "Multiple pipelines (Sales, Support, Renewals)",
            "Custom stages with colors and win/loss markers",
            "Deal fields: title, value (KWD 3 decimals), contact, expected close date",
            "Activity log per deal (stage changes, value updates, notes)",
            "Pipeline analytics: conversion rates, average deal value, time in stage",
        ],
        "3.4 Campaigns": [
            "Bulk WhatsApp message broadcasts",
            "Audience targeting: all contacts, by tag, by status, custom filter",
            "Rate-limited sending (80 msgs/sec per WhatsApp limits)",
            "Real-time stats: sent, delivered, read, failed, replied",
            "Pause/resume control",
        ],
        "3.5 Automations": [
            "Trigger-based workflow automation",
            "Triggers: message received, contact created, deal stage changed, tag added",
            "Actions: send message, assign agent, add/remove tag, create deal, webhook call",
            "Condition branching and execution logs for debugging",
        ],
        "3.6 Chatbot Flows": [
            "Visual flow builder with drag-and-drop nodes",
            "Node types: Send Message, Ask Question, Condition, Delay, Assign Agent, API Call, Payment Link",
            "Multi-language support with activation/deactivation toggle",
        ],
        "3.7 Landing Pages": [
            "Drag-and-drop page builder with block types: Hero, Text, Image, CTA, Form",
            "Custom URL slugs (e.g., /summer-sale)",
            "Publish/unpublish control with visit and conversion tracking",
            "SEO meta tags (title, description, OG image)",
        ],
        "3.8 Analytics Dashboard": [
            "Contact growth over time",
            "Conversation volume and response times",
            "Pipeline metrics: deals won/lost, revenue forecast",
            "Team performance: messages sent, conversations handled",
            "Landing page: visits, conversions, conversion rate",
            "Campaign performance: delivery rate, read rate, reply rate",
        ],
        "3.9 Templates": [
            "WhatsApp-approved message templates",
            "Template categories: Marketing, Utility, Authentication",
            "Language support (English, Arabic) with variable parameters for personalization",
        ],
    }
    for title, items in features.items():
        story.append(Paragraph(title, SECTION_H2))
        for item in items:
            story.append(Paragraph(f"<bullet>&bull;</bullet> {item}", BULLET))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 4: SETTINGS & ADMINISTRATION
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("4. Settings & Administration", SECTION_H1))
    story.append(hr())

    story.append(Paragraph("4.1 Security", SECTION_H2))
    for s in ["Change password (requires current password verification)", "Password requirements: minimum 8 characters", "JWT-based authentication with 15-minute access tokens", "Automatic token refresh"]:
        story.append(Paragraph(f"<bullet>&bull;</bullet> {s}", BULLET))

    story.append(Paragraph("4.2 Team Management", SECTION_H2))
    for s in ["Invite team members by email", "Assign roles: Owner, Admin, Manager, Agent", "Activate/deactivate team members", "Each member gets their own login credentials"]:
        story.append(Paragraph(f"<bullet>&bull;</bullet> {s}", BULLET))

    story.append(Paragraph("4.3 Channels", SECTION_H2))
    for s in ["WhatsApp Cloud API: connect phone number, set webhook", "Instagram: connect business page for comment-to-lead capture", "Web Chat: generate embed code for website widget", "Each channel has its own credentials and configuration"]:
        story.append(Paragraph(f"<bullet>&bull;</bullet> {s}", BULLET))

    story.append(Paragraph("4.4 Billing & Subscription", SECTION_H2))
    plan_data = [
        ["Starter", "9.900 KWD", "99.000 KWD", "500", "3", "No"],
        ["Growth", "29.900 KWD", "299.000 KWD", "5,000", "10", "Yes"],
        ["Enterprise", "79.900 KWD", "799.000 KWD", "50,000", "50", "Yes"],
    ]
    story.append(make_table(["Plan", "Monthly", "Yearly", "Contacts", "Team", "AI"], plan_data))
    story.append(Spacer(1, 4 * mm))
    for s in ["Payment via K-Net, Visa, Mastercard (Tap Payments)", "Cancel at period end or immediately", "Invoice history available"]:
        story.append(Paragraph(f"<bullet>&bull;</bullet> {s}", BULLET))

    story.append(Paragraph("4.5 Compliance & Data Residency", SECTION_H2))
    for s in [
        "CITRA Kuwait compliance dashboard with real-time checks",
        "Data hosted in AWS me-south-1 (Bahrain, GCC region)",
        "Row-Level Security: tenant data isolation at the database level",
        "Audit logging: all actions recorded with user, timestamp, IP address",
        "Data export: CSV export for GDPR right of access",
        "Contact deletion: soft delete + automated 365-day hard purge",
        "Encryption: AES-256 for sensitive fields, TLS for data in transit",
    ]:
        story.append(Paragraph(f"<bullet>&bull;</bullet> {s}", BULLET))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 5: USER ROLES & PERMISSIONS
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("5. User Roles & Permissions", SECTION_H1))
    story.append(hr())

    Y, N, R = "Yes", "No", "Read"
    perm_data = [
        ["View contacts", Y, Y, Y, Y],
        ["Create/edit contacts", Y, Y, Y, Y],
        ["Delete contacts", Y, Y, Y, N],
        ["Import/export contacts", Y, Y, Y, N],
        ["View conversations", Y, Y, Y, Y],
        ["Send messages", Y, Y, Y, Y],
        ["Assign conversations", Y, Y, Y, N],
        ["Create automations", Y, Y, Y, N],
        ["Manage pipeline", Y, Y, Y, R],
        ["Create deals", Y, Y, Y, Y],
        ["View analytics", Y, Y, Y, N],
        ["Manage billing", Y, Y, N, N],
        ["Manage team", Y, Y, N, N],
        ["Change settings", Y, Y, N, N],
        ["View audit logs", Y, Y, N, N],
    ]
    story.append(make_table(["Permission", "Owner", "Admin", "Manager", "Agent"], perm_data))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 6: ARABIC SECTION
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("6. Arabic Section", SECTION_H1))
    story.append(hr())
    story.append(Spacer(1, 0.5 * cm))

    # Arabic content
    ar = reshape_arabic

    story.append(Paragraph(ar("البدء السريع"), AR_H1))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(ar("متطلبات النظام"), AR_H2))
    for item in ["متصفح ويب حديث (Chrome, Firefox, Safari, Edge)", "اتصال إنترنت مستقر", "حساب واتساب للأعمال (لميزات المراسلة)"]:
        story.append(Paragraph(ar(item), AR_BULLET))

    story.append(Paragraph(ar("التسجيل"), AR_H2))
    for item in [
        "الخطوة 1: انتقل إلى https://app.kwgrowth.com/register",
        "الخطوة 2: أدخل اسم الشركة والاسم والبريد الإلكتروني وكلمة المرور",
        "الخطوة 3: انقر على ابدأ مجاناً",
        "الخطوة 4: يتم توجيهك إلى لوحة التحكم",
    ]:
        story.append(Paragraph(ar(item), AR_BODY))

    story.append(Paragraph(ar("تسجيل الدخول"), AR_H2))
    for item in ["انتقل إلى صفحة تسجيل الدخول", "أدخل البريد الإلكتروني وكلمة المرور", "انقر تسجيل الدخول"]:
        story.append(Paragraph(ar(item), AR_BULLET))
    story.append(PageBreak())

    # Arabic onboarding
    story.append(Paragraph(ar("دليل تأهيل العملاء الجدد"), AR_H1))
    story.append(Paragraph(ar("عينة: شركة البركة للتجارة"), ParagraphStyle("ArSub", parent=AR_BODY, fontSize=12, textColor=PRIMARY)))
    story.append(Spacer(1, 4 * mm))

    ar_steps = [
        ("الخطوة 1: تسجيل الشركة", [
            "اسم الشركة: شركة البركة للتجارة",
            "المالك: أحمد البركة",
            "البريد: owner@albaraka.kw",
            "النتيجة: يتم إنشاء الشركة وتعيين دور المالك تلقائياً",
        ]),
        ("الخطوة 2: ربط قناة واتساب", [
            "اذهب إلى الإعدادات ثم القنوات",
            "انقر ربط واتساب",
            "أدخل معرف رقم الهاتف من Meta Business Suite",
            "أدخل رمز الوصول لواجهة Cloud API",
            "انقر حفظ والتحقق",
        ]),
        ("الخطوة 3: استيراد جهات الاتصال", [
            "اذهب إلى جهات الاتصال",
            "انقر جهة اتصال جديدة أو استيراد CSV",
            "أدخل الهاتف والاسم والبريد الإلكتروني",
        ]),
        ("الخطوة 4: إنشاء خط مبيعات وأول صفقة", [
            "اذهب إلى خط المبيعات",
            "أنشئ خط مبيعات جديد",
            "أضف المراحل: عميل جديد ثم عرض مرسل ثم تفاوض ثم فاز",
            "أنشئ صفقة: توريد أثاث مكتبي بقيمة 2,500 دينار كويتي",
        ]),
        ("الخطوة 5: بدء أول محادثة", [
            "اذهب إلى صندوق الوارد",
            "انقر محادثة جديدة",
            "اختر جهة الاتصال واكتب رسالتك",
            "أرسلها عبر واتساب",
        ]),
        ("الخطوة 6: إعداد الأتمتة", [
            "اذهب إلى الأتمتة",
            "المشغل: عند استلام رسالة جديدة",
            "الشرط: الرسالة تحتوي على سعر أو كم",
            "الإجراء: رد تلقائي بقالب الأسعار",
        ]),
        ("الخطوة 7: إطلاق أول حملة", [
            "اذهب إلى الحملات",
            "أنشئ حملة جديدة: تخفيضات الصيف 2026",
            "الجمهور: جميع جهات الاتصال بعلامة واتساب نشط",
            "انقر إرسال الآن",
        ]),
    ]
    for title, items in ar_steps:
        story.append(Paragraph(ar(title), AR_H2))
        for item in items:
            story.append(Paragraph(ar(item), AR_BULLET))
    story.append(PageBreak())

    # Arabic features overview
    story.append(Paragraph(ar("نظرة عامة على الميزات"), AR_H1))
    story.append(Spacer(1, 4 * mm))

    ar_features = {
        "صندوق الوارد والمحادثات": ["مراسلة فورية عبر واتساب", "حالات المحادثة: مفتوحة ومعلقة ومغلقة", "تعيين الوكلاء للتعاون", "تحديثات مباشرة بدون تحديث الصفحة"],
        "جهات الاتصال وإدارة العملاء": ["قاعدة بيانات موحدة للعملاء", "حقول مخصصة وعلامات ملونة", "استيراد وتصدير CSV", "إجراءات جماعية"],
        "خط المبيعات": ["لوحة كانبان للصفقات", "مراحل قابلة للتخصيص", "تتبع النشاط لكل صفقة"],
        "التحليلات": ["نمو جهات الاتصال", "حجم المحادثات", "إيرادات المبيعات", "أداء الفريق"],
    }
    for title, items in ar_features.items():
        story.append(Paragraph(ar(title), AR_H2))
        for item in items:
            story.append(Paragraph(ar(item), AR_BULLET))

    story.append(Spacer(1, 1 * cm))

    # Arabic roles table
    story.append(Paragraph(ar("الأدوار والصلاحيات"), AR_H1))
    story.append(Spacer(1, 4 * mm))
    ar_perm_data = [
        [ar("نعم"), ar("نعم"), ar("نعم"), ar("نعم"), ar("عرض جهات الاتصال")],
        [ar("نعم"), ar("نعم"), ar("نعم"), ar("نعم"), ar("إنشاء وتعديل جهات الاتصال")],
        [ar("لا"), ar("نعم"), ar("نعم"), ar("نعم"), ar("حذف جهات الاتصال")],
        [ar("نعم"), ar("نعم"), ar("نعم"), ar("نعم"), ar("عرض المحادثات")],
        [ar("نعم"), ar("نعم"), ar("نعم"), ar("نعم"), ar("إرسال الرسائل")],
        [ar("لا"), ar("نعم"), ar("نعم"), ar("نعم"), ar("إنشاء الأتمتة")],
        [ar("لا"), ar("نعم"), ar("نعم"), ar("نعم"), ar("عرض التحليلات")],
        [ar("لا"), ar("لا"), ar("نعم"), ar("نعم"), ar("إدارة الفريق")],
        [ar("لا"), ar("لا"), ar("نعم"), ar("نعم"), ar("إدارة الفوترة")],
    ]
    ar_t = Table(
        [[ar("الوكيل"), ar("المشرف"), ar("المدير"), ar("المالك"), ar("الصلاحية")]] + ar_perm_data,
        colWidths=[2.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 6 * cm],
    )
    ar_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, -1), "NotoArabic"),
        ("FONTNAME", (0, 0), (-1, 0), "NotoArabicBold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ] + [("BACKGROUND", (0, i), (-1, i), TABLE_ALT_BG) for i in range(2, len(ar_perm_data) + 1, 2)]))
    story.append(ar_t)

    # ═══════════════════════════════════════════════════════════════════
    # BUILD
    # ═══════════════════════════════════════════════════════════════════
    doc.build(story)
    print(f"Generated: {output}")
    print(f"Pages: ~30 (cover + TOC + EN sections + AR sections)")


if __name__ == "__main__":
    build_pdf()
