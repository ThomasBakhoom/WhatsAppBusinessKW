"""Generate English and Arabic user manuals for Kuwait WhatsApp Growth Engine."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# Colors
PRIMARY = HexColor("#25D366")
DARK = HexColor("#1A1A2E")
GRAY = HexColor("#6B7280")
LIGHT_BG = HexColor("#F8FAFC")
WHITE = white
BLACK = black

WIDTH, HEIGHT = A4


def build_english_manual():
    """Build the English user manual."""
    output = os.path.join(os.path.dirname(__file__), "KW_Growth_Engine_Manual_EN.pdf")
    doc = SimpleDocTemplate(output, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2.5*cm, rightMargin=2.5*cm)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", fontSize=28, leading=34, textColor=DARK, alignment=TA_CENTER, spaceAfter=10, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="CoverSub", fontSize=14, leading=18, textColor=GRAY, alignment=TA_CENTER, spaceAfter=30))
    styles.add(ParagraphStyle(name="H1", fontSize=22, leading=28, textColor=DARK, spaceBefore=30, spaceAfter=14, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="H2", fontSize=16, leading=22, textColor=PRIMARY, spaceBefore=20, spaceAfter=10, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="H3", fontSize=13, leading=18, textColor=DARK, spaceBefore=14, spaceAfter=8, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Body", fontSize=10.5, leading=16, textColor=BLACK, spaceAfter=8))
    styles.add(ParagraphStyle(name="BulletItem", fontSize=10.5, leading=16, textColor=BLACK, spaceAfter=4, leftIndent=20, bulletIndent=10))
    styles.add(ParagraphStyle(name="Note", fontSize=10, leading=14, textColor=GRAY, spaceAfter=8, leftIndent=15, borderWidth=1, borderColor=PRIMARY, borderPadding=8))
    styles.add(ParagraphStyle(name="Footer", fontSize=8, leading=10, textColor=GRAY, alignment=TA_CENTER))

    story = []

    # ── COVER PAGE ────────────────────────────────────────────────────
    story.append(Spacer(1, 80))
    story.append(Paragraph("KUWAIT WHATSAPP<br/>GROWTH ENGINE", styles["CoverTitle"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Enterprise User Manual", styles["CoverSub"]))
    story.append(Spacer(1, 20))

    cover_data = [
        ["Version", "1.0"],
        ["Date", "April 2026"],
        ["Platform", "WhatsApp CRM SaaS"],
        ["Market", "Kuwait / GCC"],
        ["Modules", "26 API modules"],
        ["API Routes", "135 endpoints"],
    ]
    cover_table = Table(cover_data, colWidths=[120, 200])
    cover_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), GRAY),
        ("TEXTCOLOR", (1, 0), (1, -1), DARK),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, HexColor("#E5E7EB")),
    ]))
    story.append(cover_table)
    story.append(PageBreak())

    # ── TABLE OF CONTENTS ─────────────────────────────────────────────
    story.append(Paragraph("Table of Contents", styles["H1"]))
    toc_items = [
        "1. Getting Started",
        "2. Dashboard Overview",
        "3. Contacts & CRM",
        "4. Shared Inbox (WhatsApp)",
        "5. Campaigns & Broadcasts",
        "6. Chatbot Flow Builder",
        "7. Automations",
        "8. Sales Pipeline",
        "9. Landing Pages",
        "10. Templates",
        "11. Analytics",
        "12. Shipping",
        "13. Payments & Billing",
        "14. Settings & Administration",
        "15. Compliance & Security",
        "16. API Reference",
    ]
    for item in toc_items:
        story.append(Paragraph(item, styles["Body"]))
    story.append(PageBreak())

    # ── CHAPTER 1: GETTING STARTED ────────────────────────────────────
    story.append(Paragraph("1. Getting Started", styles["H1"]))

    story.append(Paragraph("1.1 Registration", styles["H2"]))
    story.append(Paragraph("Visit <b>app.kwgrowth.com/register</b> and fill in your company name, email, and password. You will be assigned the <b>Owner</b> role with full access to all features.", styles["Body"]))

    story.append(Paragraph("1.2 First Login", styles["H2"]))
    story.append(Paragraph("After registration, you are automatically logged in and redirected to the dashboard. Your JWT access token lasts 15 minutes and automatically refreshes.", styles["Body"]))

    story.append(Paragraph("1.3 System Requirements", styles["H2"]))
    req_data = [
        ["Component", "Requirement"],
        ["Browser", "Chrome 90+, Firefox 88+, Safari 14+, Edge 90+"],
        ["WhatsApp", "Cloud API (Meta Business Account)"],
        ["Payments", "Tap Payments account (for K-Net)"],
        ["Mobile", "Responsive - works on all screen sizes"],
    ]
    req_table = Table(req_data, colWidths=[120, 320])
    req_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#E5E7EB")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(req_table)
    story.append(PageBreak())

    # ── CHAPTER 2: DASHBOARD ──────────────────────────────────────────
    story.append(Paragraph("2. Dashboard Overview", styles["H1"]))
    story.append(Paragraph("The main dashboard shows key performance indicators at a glance:", styles["Body"]))
    for item in [
        "<b>Total Contacts</b> - Number of contacts in your CRM",
        "<b>Open Conversations</b> - Active WhatsApp conversations",
        "<b>Messages (period)</b> - Inbound and outbound message count",
        "<b>Revenue</b> - Total value of won deals in KWD",
    ]:
        story.append(Paragraph(item, styles["BulletItem"], bulletText="\u2022"))

    story.append(Paragraph("The sidebar navigation provides access to all modules. On mobile devices, tap the hamburger menu to open the sidebar.", styles["Body"]))
    story.append(PageBreak())

    # ── CHAPTER 3: CONTACTS ───────────────────────────────────────────
    story.append(Paragraph("3. Contacts & CRM", styles["H1"]))

    story.append(Paragraph("3.1 Contact Management", styles["H2"]))
    story.append(Paragraph("The Contacts page displays all your contacts in a searchable, filterable data table. You can:", styles["Body"]))
    for item in [
        "Search by name, phone number, or email",
        "Filter by status (active/inactive/blocked), source, and tags",
        "Sort by any column (click column header)",
        "Select multiple contacts for bulk actions (delete, add tag, change status)",
        "Click any row to open the contact detail page",
    ]:
        story.append(Paragraph(item, styles["BulletItem"], bulletText="\u2022"))

    story.append(Paragraph("3.2 Creating Contacts", styles["H2"]))
    story.append(Paragraph('Click <b>"+ Add Contact"</b> to create a new contact. Phone number is required (Kuwait format: +965XXXXXXXX). You can also assign tags during creation.', styles["Body"]))

    story.append(Paragraph("3.3 Tags", styles["H2"]))
    story.append(Paragraph("Tags are color-coded labels for organizing contacts. Manage tags in <b>Settings > Tags</b>. Each tag has a name, color, and optional description.", styles["Body"]))

    story.append(Paragraph("3.4 Custom Fields", styles["H2"]))
    story.append(Paragraph("Create custom fields to store additional data per contact. Supported types: text, number, date, select (dropdown), and boolean (yes/no).", styles["Body"]))

    story.append(Paragraph("3.5 CSV Import", styles["H2"]))
    story.append(Paragraph('Click <b>"Import CSV"</b> to bulk import contacts. The CSV must have a <b>phone</b> column. Optional columns: first_name, last_name, email, notes. Duplicate phones are updated, new ones are created.', styles["Body"]))
    story.append(PageBreak())

    # ── CHAPTER 4: INBOX ──────────────────────────────────────────────
    story.append(Paragraph("4. Shared Inbox (WhatsApp)", styles["H1"]))

    story.append(Paragraph("4.1 Conversation List", styles["H2"]))
    story.append(Paragraph("The left panel shows all conversations sorted by last message time. Each conversation shows the contact name, last message preview, unread count (green badge), and status indicator:", styles["Body"]))
    for item in [
        "<font color='#22C55E'><b>Green</b></font> - Open",
        "<font color='#EAB308'><b>Yellow</b></font> - Pending",
        "<font color='#3B82F6'><b>Blue</b></font> - Snoozed",
        "<font color='#9CA3AF'><b>Gray</b></font> - Closed",
    ]:
        story.append(Paragraph(item, styles["BulletItem"], bulletText="\u2022"))

    story.append(Paragraph("4.2 Sending Messages", styles["H2"]))
    story.append(Paragraph("Select a conversation, type your message, and press <b>Enter</b> or click <b>Send</b>. Messages are delivered via WhatsApp Cloud API. Delivery status icons:", styles["Body"]))
    for item in [
        "\u23F3 Pending - Message queued",
        "\u2713 Sent - Delivered to WhatsApp servers",
        "\u2713\u2713 Delivered - Received on device",
        "\u2713\u2713 (blue) Read - Message read by recipient",
    ]:
        story.append(Paragraph(item, styles["BulletItem"], bulletText="\u2022"))

    story.append(Paragraph("4.3 Conversation Management", styles["H2"]))
    story.append(Paragraph("Use the status dropdown in the conversation header to change status (Open, Pending, Snoozed, Closed). Conversations auto-refresh every 3 seconds.", styles["Body"]))
    story.append(PageBreak())

    # ── CHAPTER 5: CAMPAIGNS ──────────────────────────────────────────
    story.append(Paragraph("5. Campaigns & Broadcasts", styles["H1"]))
    story.append(Paragraph("Send bulk WhatsApp messages to your contacts. Campaigns support:", styles["Body"]))
    for item in [
        "<b>Template messages</b> - Pre-approved WhatsApp templates",
        "<b>Audience targeting</b> - All contacts, by tag, or by segment",
        "<b>Scheduling</b> - Send immediately or schedule for later",
        "<b>Delivery tracking</b> - Sent, delivered, read, and failed counts",
        "<b>Pause/Resume</b> - Pause a running campaign at any time",
    ]:
        story.append(Paragraph(item, styles["BulletItem"], bulletText="\u2022"))
    story.append(Paragraph("<b>Note:</b> WhatsApp requires approved templates for broadcast messages. Create templates in the Templates section first.", styles["Note"]))
    story.append(PageBreak())

    # ── CHAPTER 6: CHATBOTS ───────────────────────────────────────────
    story.append(Paragraph("6. Chatbot Flow Builder", styles["H1"]))
    story.append(Paragraph("Build automated conversation flows with a visual editor. Each flow has:", styles["Body"]))

    story.append(Paragraph("6.1 Trigger Types", styles["H2"]))
    for item in [
        "<b>Keyword Match</b> - Activates when message contains specific keywords",
        "<b>Any Message</b> - Activates on every inbound message",
        "<b>New Conversation</b> - Activates when a new conversation starts",
        "<b>Webhook</b> - Triggered by external API call",
    ]:
        story.append(Paragraph(item, styles["BulletItem"], bulletText="\u2022"))

    story.append(Paragraph("6.2 Node Types", styles["H2"]))
    node_data = [
        ["Node Type", "Description"],
        ["Send Message", "Send a text message to the customer"],
        ["Ask Question", "Ask a question and wait for response"],
        ["Condition", "Branch based on message content or contact data"],
        ["Delay", "Wait a specified number of seconds"],
        ["Assign Agent", "Hand off to a human agent"],
        ["Action", "Tag contact, update field, or change status"],
        ["API Call", "Make an HTTP request to an external service"],
    ]
    node_table = Table(node_data, colWidths=[120, 320])
    node_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#E5E7EB")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(node_table)
    story.append(PageBreak())

    # ── CHAPTER 7: AUTOMATIONS ────────────────────────────────────────
    story.append(Paragraph("7. Automations", styles["H1"]))
    story.append(Paragraph("Automations trigger actions automatically when events occur.", styles["Body"]))

    story.append(Paragraph("7.1 Triggers", styles["H2"]))
    for item in ["Message Received", "Contact Created", "Contact Updated", "Conversation Created", "Deal Stage Changed"]:
        story.append(Paragraph(item, styles["BulletItem"], bulletText="\u2022"))

    story.append(Paragraph("7.2 Conditions", styles["H2"]))
    story.append(Paragraph("Add conditions to filter which events trigger the automation. Operators: equals, not equals, contains, starts with, greater than, less than, in list.", styles["Body"]))

    story.append(Paragraph("7.3 Actions", styles["H2"]))
    for item in ["Auto Reply", "Send Template", "Add/Remove Tag", "Change Status", "Update Lead Score", "Assign Agent (Smart Routing)", "Webhook Call"]:
        story.append(Paragraph(item, styles["BulletItem"], bulletText="\u2022"))
    story.append(PageBreak())

    # ── CHAPTER 8: PIPELINE ───────────────────────────────────────────
    story.append(Paragraph("8. Sales Pipeline", styles["H1"]))
    story.append(Paragraph("The Pipeline module provides a Kanban board for tracking deals through sales stages.", styles["Body"]))

    story.append(Paragraph("8.1 Stages", styles["H2"]))
    story.append(Paragraph("Each pipeline has colored stages that deals move through. Default stages: New Lead, Contacted, Qualified, Proposal, Negotiation, Won, Lost. Mark stages as Won or Lost for analytics.", styles["Body"]))

    story.append(Paragraph("8.2 Deals", styles["H2"]))
    story.append(Paragraph("Create deals with a title, value (KWD with 3 decimal places), and optional contact link. Drag deals between columns to change stage. All stage changes, value changes, and notes are logged in the activity timeline.", styles["Body"]))

    story.append(Paragraph("8.3 Analytics", styles["H2"]))
    story.append(Paragraph("Pipeline analytics include: win rate percentage, average deal value, total pipeline value per stage, and per-agent performance.", styles["Body"]))
    story.append(PageBreak())

    # ── CHAPTER 9: LANDING PAGES ──────────────────────────────────────
    story.append(Paragraph("9. Landing Pages", styles["H1"]))
    story.append(Paragraph("Create landing pages with a block-based editor and WhatsApp call-to-action buttons.", styles["Body"]))

    story.append(Paragraph("9.1 Block Types", styles["H2"]))
    for item in ["Hero Section", "Text Block", "Image", "Features Grid", "Call to Action", "Testimonial", "FAQ", "Divider"]:
        story.append(Paragraph(item, styles["BulletItem"], bulletText="\u2022"))

    story.append(Paragraph("9.2 WhatsApp CTA", styles["H2"]))
    story.append(Paragraph("Configure a WhatsApp number and pre-filled message. When visitors click the CTA button, it opens WhatsApp with your number and message pre-filled.", styles["Body"]))

    story.append(Paragraph("9.3 Analytics", styles["H2"]))
    story.append(Paragraph("Each page tracks visits and conversions (CTA clicks). View conversion rate on the page list and detail views.", styles["Body"]))
    story.append(PageBreak())

    # ── CHAPTERS 10-16 ────────────────────────────────────────────────
    story.append(Paragraph("10. Templates", styles["H1"]))
    story.append(Paragraph("WhatsApp requires pre-approved message templates for outbound conversations. Create templates with variables ({{1}}, {{2}}) and submit for Meta approval. Supported categories: Marketing, Utility, Authentication.", styles["Body"]))
    story.append(PageBreak())

    story.append(Paragraph("11. Analytics", styles["H1"]))
    story.append(Paragraph("The Analytics dashboard provides real-time insights across all modules:", styles["Body"]))
    for item in [
        "<b>Dashboard</b> - KPI cards (contacts, conversations, messages, revenue)",
        "<b>Messages</b> - Daily volume chart, delivery rate breakdown",
        "<b>Pipeline</b> - Stage distribution, win rate, average deal value",
        "<b>Team</b> - Per-agent performance (messages, conversations, deals, revenue)",
        "<b>Landing Pages</b> - Visit and conversion stats per page",
        "<b>Automations</b> - Execution counts and success rates",
    ]:
        story.append(Paragraph(item, styles["BulletItem"], bulletText="\u2022"))
    story.append(PageBreak())

    story.append(Paragraph("12. Shipping", styles["H1"]))
    story.append(Paragraph("Manage shipments with integrated carrier tracking. Supported carriers: Aramex Kuwait, DHL, Fetchr, Shipa. Features include:", styles["Body"]))
    for item in [
        "Create shipments with origin/destination addresses",
        "Automatic tracking number generation",
        "7 status states: Created, Picked Up, In Transit, Out for Delivery, Delivered, Failed, Returned",
        "Cash on Delivery (COD) support with KWD amounts",
        "Automatic WhatsApp tracking notifications to customers",
    ]:
        story.append(Paragraph(item, styles["BulletItem"], bulletText="\u2022"))
    story.append(PageBreak())

    story.append(Paragraph("13. Payments & Billing", styles["H1"]))
    story.append(Paragraph("13.1 Subscription Plans", styles["H2"]))
    plan_data = [
        ["Feature", "Starter (9.9 KWD)", "Growth (29.9 KWD)", "Enterprise (79.9 KWD)"],
        ["Contacts", "500", "5,000", "50,000"],
        ["Conversations/mo", "1,000", "10,000", "100,000"],
        ["Team Members", "3", "10", "50"],
        ["Automations", "5", "25", "100"],
        ["AI Features", "No", "Yes", "Yes"],
        ["API Access", "No", "No", "Yes"],
    ]
    plan_table = Table(plan_data, colWidths=[110, 110, 110, 110])
    plan_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#E5E7EB")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))
    story.append(plan_table)

    story.append(Paragraph("13.2 Payment Methods", styles["H2"]))
    story.append(Paragraph("Payments are processed via Tap Payments supporting K-Net (Kuwait debit), Visa, Mastercard, and Apple Pay. All amounts are in KWD with 3 decimal places.", styles["Body"]))
    story.append(PageBreak())

    story.append(Paragraph("14. Settings & Administration", styles["H1"]))
    story.append(Paragraph("14.1 Team Management", styles["H2"]))
    story.append(Paragraph("Invite team members by email. Assign roles: Admin (full access), Manager (no billing), Agent (conversations and contacts only). Deactivate members to revoke access.", styles["Body"]))

    story.append(Paragraph("14.2 Channels", styles["H2"]))
    story.append(Paragraph("Connect messaging channels: WhatsApp (primary), Instagram DM, Facebook Messenger, Web Chat, SMS, Email. Each channel requires its own credentials.", styles["Body"]))

    story.append(Paragraph("14.3 Data Export", styles["H2"]))
    story.append(Paragraph("Export contacts, conversations, and deals as CSV files. Navigate to Settings > Data Export and click the download button.", styles["Body"]))
    story.append(PageBreak())

    story.append(Paragraph("15. Compliance & Security", styles["H1"]))
    story.append(Paragraph("The compliance dashboard shows 8 security checks:", styles["Body"]))
    for item in [
        "Data Residency - AWS me-south-1 (Bahrain, GCC)",
        "Encryption at Rest - PostgreSQL disk encryption",
        "Encryption in Transit - TLS 1.3",
        "Consent Tracking - WhatsApp opt-in per contact",
        "Data Retention Policy - Configurable",
        "Audit Logging - All actions recorded",
        "Right to Deletion - Soft delete available",
        "Data Export - CSV export available",
    ]:
        story.append(Paragraph(item, styles["BulletItem"], bulletText="\u2713"))

    story.append(Paragraph("Security measures include: JWT authentication (15-min tokens), bcrypt password hashing (12 rounds), PostgreSQL Row-Level Security for tenant isolation, RBAC with 34 permissions, and rate limiting.", styles["Body"]))
    story.append(PageBreak())

    story.append(Paragraph("16. API Reference", styles["H1"]))
    story.append(Paragraph("The platform exposes a RESTful API at <b>/v1/</b> with 135 endpoints across 26 modules. Interactive documentation is available at <b>/docs</b> (Swagger UI) and <b>/redoc</b> (ReDoc).", styles["Body"]))

    story.append(Paragraph("16.1 Authentication", styles["H2"]))
    story.append(Paragraph("All API requests require a Bearer token in the Authorization header. Obtain tokens via POST /v1/auth/login. Tokens expire in 15 minutes and can be refreshed via POST /v1/auth/refresh.", styles["Body"]))

    story.append(Paragraph("16.2 API Modules", styles["H2"]))
    api_data = [
        ["Module", "Prefix", "Endpoints"],
        ["Auth", "/v1/auth", "4"], ["Contacts", "/v1/contacts", "7"], ["Tags", "/v1/tags", "5"],
        ["Conversations", "/v1/conversations", "6"], ["Campaigns", "/v1/campaigns", "8"],
        ["Chatbots", "/v1/chatbots", "6"], ["Automations", "/v1/automations", "7"],
        ["Pipelines", "/v1/pipelines", "16"], ["Payments", "/v1/payments", "10"],
        ["Shipping", "/v1/shipping", "9"], ["Landing Pages", "/v1/landing-pages", "10"],
        ["Analytics", "/v1/analytics", "6"], ["AI Engine", "/v1/ai", "3"],
        ["Catalog", "/v1/catalog", "3"], ["Surveys", "/v1/surveys", "3"],
        ["Export", "/v1/export", "3"], ["QR Codes", "/v1/qr", "2"],
    ]
    api_table = Table(api_data, colWidths=[110, 160, 80])
    api_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#E5E7EB")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
    ]))
    story.append(api_table)

    # Footer
    story.append(Spacer(1, 40))
    story.append(Paragraph("Kuwait WhatsApp Growth Engine v1.0 | app.kwgrowth.com | 2026", styles["Footer"]))

    doc.build(story)
    print(f"English manual: {output}")
    return output


def build_arabic_manual():
    """Build the Arabic user manual."""
    output = os.path.join(os.path.dirname(__file__), "KW_Growth_Engine_Manual_AR.pdf")
    doc = SimpleDocTemplate(output, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2.5*cm, rightMargin=2.5*cm)

    styles = getSampleStyleSheet()
    # Arabic styles use right alignment
    styles.add(ParagraphStyle(name="ARTitle", fontSize=26, leading=36, textColor=DARK, alignment=TA_CENTER, spaceAfter=10, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="ARSub", fontSize=13, leading=18, textColor=GRAY, alignment=TA_CENTER, spaceAfter=30))
    styles.add(ParagraphStyle(name="ARH1", fontSize=20, leading=28, textColor=DARK, spaceBefore=30, spaceAfter=14, fontName="Helvetica-Bold", alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="ARH2", fontSize=15, leading=22, textColor=PRIMARY, spaceBefore=20, spaceAfter=10, fontName="Helvetica-Bold", alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="ARBody", fontSize=10.5, leading=18, textColor=BLACK, spaceAfter=8, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="ARBullet", fontSize=10.5, leading=18, textColor=BLACK, spaceAfter=4, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="ARNote", fontSize=10, leading=14, textColor=GRAY, spaceAfter=8, alignment=TA_RIGHT, borderWidth=1, borderColor=PRIMARY, borderPadding=8))
    styles.add(ParagraphStyle(name="ARFooter", fontSize=8, leading=10, textColor=GRAY, alignment=TA_CENTER))

    story = []

    # Cover
    story.append(Spacer(1, 80))
    story.append(Paragraph("محرك نمو واتساب الكويت", styles["ARTitle"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("دليل المستخدم للمؤسسات", styles["ARSub"]))
    story.append(Spacer(1, 20))

    cover_data = [
        ["1.0", "الإصدار"],
        ["أبريل 2026", "التاريخ"],
        ["نظام إدارة علاقات العملاء عبر واتساب", "المنصة"],
        ["الكويت / دول الخليج", "السوق"],
        ["26 وحدة", "الوحدات"],
        ["135 نقطة وصول", "واجهات API"],
    ]
    cover_table = Table(cover_data, colWidths=[200, 120])
    cover_table.setStyle(TableStyle([
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), DARK),
        ("TEXTCOLOR", (1, 0), (1, -1), GRAY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, HexColor("#E5E7EB")),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
    ]))
    story.append(cover_table)
    story.append(PageBreak())

    # TOC
    story.append(Paragraph("فهرس المحتويات", styles["ARH1"]))
    toc = [
        "البدء .1",
        "لوحة التحكم .2",
        "جهات الاتصال وإدارة العملاء .3",
        "صندوق الوارد (واتساب) .4",
        "الحملات والبث الجماعي .5",
        "منشئ بوت المحادثة .6",
        "الأتمتة .7",
        "خط المبيعات .8",
        "صفحات الهبوط .9",
        "القوالب .10",
        "التحليلات .11",
        "الشحن .12",
        "المدفوعات والفواتير .13",
        "الإعدادات والإدارة .14",
        "الامتثال والأمان .15",
        "مرجع واجهة API .16",
    ]
    for item in toc:
        story.append(Paragraph(item, styles["ARBody"]))
    story.append(PageBreak())

    # Chapter 1
    story.append(Paragraph("البدء .1", styles["ARH1"]))

    story.append(Paragraph("التسجيل 1.1", styles["ARH2"]))
    story.append(Paragraph("قم بزيارة app.kwgrowth.com/register وأدخل اسم شركتك والبريد الإلكتروني وكلمة المرور. سيتم تعيينك بدور المالك مع صلاحيات كاملة لجميع الميزات.", styles["ARBody"]))

    story.append(Paragraph("تسجيل الدخول الأول 1.2", styles["ARH2"]))
    story.append(Paragraph("بعد التسجيل، يتم تسجيل دخولك تلقائياً وتوجيهك إلى لوحة التحكم. رمز الوصول JWT صالح لمدة 15 دقيقة ويتم تجديده تلقائياً.", styles["ARBody"]))
    story.append(PageBreak())

    # Chapter 3
    story.append(Paragraph("جهات الاتصال وإدارة العملاء .3", styles["ARH1"]))

    story.append(Paragraph("إدارة جهات الاتصال 3.1", styles["ARH2"]))
    story.append(Paragraph("تعرض صفحة جهات الاتصال جميع جهات اتصالك في جدول بيانات قابل للبحث والتصفية. يمكنك:", styles["ARBody"]))
    for item in [
        "البحث بالاسم أو رقم الهاتف أو البريد الإلكتروني",
        "التصفية حسب الحالة والمصدر والوسوم",
        "الفرز حسب أي عمود",
        "تحديد عدة جهات اتصال للإجراءات الجماعية",
        "النقر على أي صف لفتح صفحة تفاصيل جهة الاتصال",
    ]:
        story.append(Paragraph(item + " \u2022", styles["ARBullet"]))

    story.append(Paragraph("إنشاء جهات الاتصال 3.2", styles["ARH2"]))
    story.append(Paragraph("انقر على 'إضافة جهة اتصال' لإنشاء جهة اتصال جديدة. رقم الهاتف مطلوب بصيغة الكويت: 965XXXXXXXX+. يمكنك أيضاً تعيين الوسوم أثناء الإنشاء.", styles["ARBody"]))

    story.append(Paragraph("استيراد CSV 3.5", styles["ARH2"]))
    story.append(Paragraph("انقر على 'استيراد CSV' لاستيراد جهات الاتصال بشكل جماعي. يجب أن يحتوي ملف CSV على عمود phone. الأرقام المكررة يتم تحديثها والجديدة يتم إنشاؤها.", styles["ARBody"]))
    story.append(PageBreak())

    # Chapter 4
    story.append(Paragraph("صندوق الوارد (واتساب) .4", styles["ARH1"]))

    story.append(Paragraph("قائمة المحادثات 4.1", styles["ARH2"]))
    story.append(Paragraph("يعرض اللوحة اليسرى جميع المحادثات مرتبة حسب آخر رسالة. كل محادثة تعرض اسم جهة الاتصال ومعاينة آخر رسالة وعدد الرسائل غير المقروءة ومؤشر الحالة.", styles["ARBody"]))

    story.append(Paragraph("إرسال الرسائل 4.2", styles["ARH2"]))
    story.append(Paragraph("اختر محادثة، اكتب رسالتك، واضغط Enter أو انقر إرسال. يتم تسليم الرسائل عبر WhatsApp Cloud API.", styles["ARBody"]))
    story.append(PageBreak())

    # Chapter 5
    story.append(Paragraph("الحملات والبث الجماعي .5", styles["ARH1"]))
    story.append(Paragraph("أرسل رسائل واتساب جماعية لجهات اتصالك. تدعم الحملات:", styles["ARBody"]))
    for item in [
        "رسائل القوالب - قوالب واتساب المعتمدة مسبقاً",
        "استهداف الجمهور - جميع جهات الاتصال أو حسب الوسم أو الشريحة",
        "الجدولة - إرسال فوري أو مجدول",
        "تتبع التسليم - عدد المرسلة والمستلمة والمقروءة والفاشلة",
        "إيقاف مؤقت/استئناف - إيقاف حملة قيد الإرسال",
    ]:
        story.append(Paragraph(item + " \u2022", styles["ARBullet"]))
    story.append(PageBreak())

    # Chapter 7
    story.append(Paragraph("الأتمتة .7", styles["ARH1"]))
    story.append(Paragraph("تُشغل الأتمتة إجراءات تلقائية عند حدوث أحداث معينة.", styles["ARBody"]))

    story.append(Paragraph("المحفزات 7.1", styles["ARH2"]))
    for item in ["رسالة مستلمة", "جهة اتصال جديدة", "تحديث جهة اتصال", "محادثة جديدة", "تغيير مرحلة الصفقة"]:
        story.append(Paragraph(item + " \u2022", styles["ARBullet"]))

    story.append(Paragraph("الإجراءات 7.3", styles["ARH2"]))
    for item in ["رد تلقائي", "إرسال قالب", "إضافة/إزالة وسم", "تغيير الحالة", "تحديث نتيجة العميل المحتمل", "تعيين موظف (التوجيه الذكي)"]:
        story.append(Paragraph(item + " \u2022", styles["ARBullet"]))
    story.append(PageBreak())

    # Chapter 8
    story.append(Paragraph("خط المبيعات .8", styles["ARH1"]))
    story.append(Paragraph("توفر وحدة خط المبيعات لوحة كانبان لتتبع الصفقات عبر مراحل البيع.", styles["ARBody"]))
    story.append(Paragraph("أنشئ صفقات بعنوان وقيمة (دينار كويتي بثلاث خانات عشرية) وربط اختياري بجهة اتصال. اسحب الصفقات بين الأعمدة لتغيير المرحلة. يتم تسجيل جميع التغييرات في سجل النشاط.", styles["ARBody"]))
    story.append(PageBreak())

    # Chapter 13
    story.append(Paragraph("المدفوعات والفواتير .13", styles["ARH1"]))

    story.append(Paragraph("خطط الاشتراك 13.1", styles["ARH2"]))
    plan_data_ar = [
        ["المؤسسات (79.9 د.ك)", "النمو (29.9 د.ك)", "المبتدئ (9.9 د.ك)", "الميزة"],
        ["50,000", "5,000", "500", "جهات الاتصال"],
        ["100,000", "10,000", "1,000", "المحادثات/شهر"],
        ["50", "10", "3", "أعضاء الفريق"],
        ["100", "25", "5", "الأتمتة"],
        ["نعم", "نعم", "لا", "ميزات الذكاء الاصطناعي"],
        ["نعم", "لا", "لا", "وصول API"],
    ]
    plan_table_ar = Table(plan_data_ar, colWidths=[110, 110, 110, 110])
    plan_table_ar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#E5E7EB")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(plan_table_ar)

    story.append(Paragraph("طرق الدفع 13.2", styles["ARH2"]))
    story.append(Paragraph("تتم معالجة المدفوعات عبر Tap Payments وتدعم كي-نت (بطاقات الخصم الكويتية) وفيزا وماستركارد و Apple Pay. جميع المبالغ بالدينار الكويتي بثلاث خانات عشرية.", styles["ARBody"]))
    story.append(PageBreak())

    # Chapter 15
    story.append(Paragraph("الامتثال والأمان .15", styles["ARH1"]))
    story.append(Paragraph("تعرض لوحة الامتثال 8 فحوصات أمنية:", styles["ARBody"]))
    for item in [
        "إقامة البيانات - AWS me-south-1 (البحرين، دول الخليج)",
        "التشفير أثناء التخزين - تشفير قرص PostgreSQL",
        "التشفير أثناء النقل - TLS 1.3",
        "تتبع الموافقة - اشتراك واتساب لكل جهة اتصال",
        "سياسة الاحتفاظ بالبيانات - قابلة للتكوين",
        "تسجيل التدقيق - تسجيل جميع الإجراءات",
        "حق الحذف - الحذف المرن متاح",
        "تصدير البيانات - تصدير CSV متاح",
    ]:
        story.append(Paragraph(item + " \u2713", styles["ARBullet"]))
    story.append(PageBreak())

    # Chapter 16
    story.append(Paragraph("مرجع واجهة API .16", styles["ARH1"]))
    story.append(Paragraph("توفر المنصة واجهة RESTful API على /v1/ مع 135 نقطة وصول عبر 26 وحدة. الوثائق التفاعلية متاحة على /docs (Swagger UI) و /redoc (ReDoc).", styles["ARBody"]))

    story.append(Paragraph("المصادقة 16.1", styles["ARH2"]))
    story.append(Paragraph("تتطلب جميع طلبات API رمز Bearer في رأس Authorization. احصل على الرموز عبر POST /v1/auth/login. تنتهي صلاحية الرموز في 15 دقيقة ويمكن تجديدها.", styles["ARBody"]))

    # Footer
    story.append(Spacer(1, 40))
    story.append(Paragraph("محرك نمو واتساب الكويت الإصدار 1.0 | app.kwgrowth.com | 2026", styles["ARFooter"]))

    doc.build(story)
    print(f"Arabic manual: {output}")
    return output


if __name__ == "__main__":
    en = build_english_manual()
    ar = build_arabic_manual()
    print(f"\nDone! Files:\n  {en}\n  {ar}")
