"""Generate Cost Analysis spreadsheet using xlsxwriter (no fill bugs)."""
import xlsxwriter
import os

output = os.path.join(os.path.dirname(__file__), "KW_Growth_Engine_Cost_Analysis.xlsx")
wb = xlsxwriter.Workbook(output)

# Formats
hdr_fmt = wb.add_format({"bold": True, "bg_color": "#1A1A2E", "font_color": "white", "font_size": 11, "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True, "font_name": "Arial"})
title_fmt = wb.add_format({"bold": True, "bg_color": "#1A1A2E", "font_color": "white", "font_size": 14, "align": "center", "valign": "vcenter", "font_name": "Arial"})
norm = wb.add_format({"font_size": 10, "border": 1, "font_name": "Arial", "valign": "vcenter"})
bold = wb.add_format({"font_size": 10, "border": 1, "bold": True, "font_name": "Arial", "valign": "vcenter"})
blue = wb.add_format({"font_size": 10, "border": 1, "font_color": "#0000FF", "font_name": "Arial", "valign": "vcenter"})
green_link = wb.add_format({"font_size": 10, "border": 1, "font_color": "#008000", "font_name": "Arial", "valign": "vcenter"})
kwd = wb.add_format({"font_size": 10, "border": 1, "num_format": "#,##0.000", "font_name": "Arial", "valign": "vcenter"})
kwd_blue = wb.add_format({"font_size": 10, "border": 1, "num_format": "#,##0.000", "font_color": "#0000FF", "font_name": "Arial", "valign": "vcenter"})
kwd_bold = wb.add_format({"font_size": 10, "border": 1, "num_format": "#,##0.000", "bold": True, "font_name": "Arial", "valign": "vcenter"})
kwd_yellow = wb.add_format({"font_size": 10, "border": 1, "num_format": "#,##0.000", "bold": True, "bg_color": "#FFFDE7", "font_name": "Arial", "valign": "vcenter"})
kwd_green = wb.add_format({"font_size": 10, "border": 1, "num_format": "#,##0.000", "bold": True, "bg_color": "#E8F5E9", "font_name": "Arial", "valign": "vcenter"})
pct = wb.add_format({"font_size": 10, "border": 1, "num_format": "0.0%", "font_name": "Arial", "valign": "vcenter"})
pct_bold = wb.add_format({"font_size": 10, "border": 1, "num_format": "0.0%", "bold": True, "bg_color": "#E8F5E9", "font_name": "Arial", "valign": "vcenter"})
num = wb.add_format({"font_size": 10, "border": 1, "num_format": "#,##0", "font_name": "Arial", "valign": "vcenter"})
num_blue = wb.add_format({"font_size": 10, "border": 1, "num_format": "#,##0", "font_color": "#0000FF", "font_name": "Arial", "valign": "vcenter"})
section = wb.add_format({"font_size": 10, "border": 1, "bold": True, "bg_color": "#E3F2FD", "font_name": "Arial", "valign": "vcenter"})
usd = wb.add_format({"font_size": 10, "border": 1, "num_format": "$#,##0.000", "font_name": "Arial", "valign": "vcenter"})
usd_blue = wb.add_format({"font_size": 10, "border": 1, "num_format": "$#,##0.000", "font_color": "#0000FF", "font_name": "Arial", "valign": "vcenter"})
usd_bold = wb.add_format({"font_size": 10, "border": 1, "num_format": "$#,##0.00", "bold": True, "font_name": "Arial", "valign": "vcenter"})
usd_int = wb.add_format({"font_size": 10, "border": 1, "num_format": "$#,##0", "font_name": "Arial", "valign": "vcenter"})
green_bg = wb.add_format({"font_size": 10, "border": 1, "bg_color": "#E8F5E9", "font_name": "Arial", "valign": "vcenter"})
red_bg = wb.add_format({"font_size": 10, "border": 1, "bg_color": "#FFEBEE", "font_name": "Arial", "valign": "vcenter"})
note = wb.add_format({"font_size": 9, "font_color": "#666666", "italic": True, "align": "center", "font_name": "Arial"})

# ═══ SHEET 1: Plan Pricing ═══════════════════════════════════════════
ws1 = wb.add_worksheet("Plan Pricing")
ws1.set_tab_color("#25D366")
ws1.set_column("A:A", 35); ws1.set_column("B:D", 18); ws1.set_column("E:E", 22)
ws1.set_row(0, 35)

ws1.merge_range("A1:E1", "KW GROWTH ENGINE - SUBSCRIPTION PLAN PRICING (KWD)", title_fmt)
ws1.write_row(2, 0, ["Feature / Limit", "Starter", "Growth", "Enterprise", "Notes"], hdr_fmt)

r = 3
ws1.write(r, 0, "Monthly Price (KWD)", bold); ws1.write(r, 1, 9.900, kwd_blue); ws1.write(r, 2, 29.900, kwd_blue); ws1.write(r, 3, 79.900, kwd_blue); ws1.write(r, 4, "Billed monthly", norm); r+=1
ws1.write(r, 0, "Yearly Price (KWD)", bold); ws1.write(r, 1, 99.000, kwd_blue); ws1.write(r, 2, 299.000, kwd_blue); ws1.write(r, 3, 799.000, kwd_blue); ws1.write(r, 4, "Billed annually (save ~17%)", norm); r+=1
ws1.write(r, 0, "Yearly Discount %", bold); ws1.write_formula(r, 1, "=1-(B5/(B4*12))", pct); ws1.write_formula(r, 2, "=1-(C5/(C4*12))", pct); ws1.write_formula(r, 3, "=1-(D5/(D4*12))", pct); ws1.write(r, 4, "Formula", norm); r+=1
ws1.write(r, 0, "", norm); r+=1

ws1.write(r, 0, "FEATURE LIMITS", section); ws1.write(r, 1, "", section); ws1.write(r, 2, "", section); ws1.write(r, 3, "", section); ws1.write(r, 4, "", section); r+=1

for label, s, g, e, n in [
    ("Max Contacts", 500, 5000, 50000, ""),
    ("Conversations / Month", 1000, 10000, 100000, ""),
    ("Team Members", 3, 10, 50, ""),
    ("Automations", 5, 25, 100, ""),
    ("Pipelines", 1, 3, 10, ""),
    ("Landing Pages", 3, 10, 50, ""),
]:
    ws1.write(r, 0, label, norm); ws1.write(r, 1, s, num_blue); ws1.write(r, 2, g, num_blue); ws1.write(r, 3, e, num_blue); ws1.write(r, 4, n, norm); r+=1

for label, s, g, e, n in [
    ("AI Dialect Engine", "No", "Yes", "Yes", "Claude API powered"),
    ("API Access", "No", "No", "Yes", "REST API + Webhooks"),
    ("WhatsApp Templates", "Yes", "Yes", "Yes", "Included"),
    ("Shipping Integration", "Yes", "Yes", "Yes", "Aramex/DHL/Fetchr"),
    ("Chatbot Flow Builder", "Basic", "Full", "Full", "Visual editor"),
    ("Campaigns / Broadcasts", "3/mo", "Unlimited", "Unlimited", "Bulk WhatsApp"),
    ("Data Export (CSV)", "No", "Yes", "Yes", "Contacts/Deals/Convos"),
    ("Custom Reports", "No", "No", "Yes", "Report builder"),
    ("Support Level", "Email", "Email+Chat", "Priority+Phone", ""),
]:
    ws1.write(r, 0, label, norm)
    for ci, v in enumerate([s, g, e], 1):
        fmt = green_bg if v == "Yes" else (red_bg if v == "No" else norm)
        ws1.write(r, ci, v, fmt)
    ws1.write(r, 4, n, norm); r+=1


# ═══ SHEET 2: Infrastructure Cost ════════════════════════════════════
ws2 = wb.add_worksheet("Infrastructure Cost")
ws2.set_tab_color("#FF5722")
ws2.set_column("A:A", 38); ws2.set_column("B:D", 16); ws2.set_column("E:E", 32)
ws2.set_row(0, 35)

t2 = wb.add_format({"bold": True, "bg_color": "#FF5722", "font_color": "white", "font_size": 14, "align": "center", "font_name": "Arial"})
ws2.merge_range("A1:E1", "MONTHLY INFRASTRUCTURE COST PER CUSTOMER (KWD)", t2)
ws2.merge_range("A2:E2", "Assumptions: AWS me-south-1 (Bahrain) | 1 KWD = 3.26 USD | Shared infra allocated by tier", note)
ws2.write_row(3, 0, ["Cost Component", "Starter", "Growth", "Enterprise", "Source / Notes"], hdr_fmt)

r = 4
ws2.write(r, 0, "ASSUMPTIONS", section); ws2.write(r, 1, "", section); ws2.write(r, 2, "", section); ws2.write(r, 3, "", section); ws2.write(r, 4, "", section); r+=1
ws2.write(r, 0, "Assumed Customers per Tier", bold); ws2.write(r, 1, 100, num_blue); ws2.write(r, 2, 30, num_blue); ws2.write(r, 3, 5, num_blue); ws2.write(r, 4, "Editable assumption (blue)", norm); r+=1
r+=1

ws2.write(r, 0, "AWS INFRASTRUCTURE (shared)", section); ws2.write(r, 1, "", section); ws2.write(r, 2, "", section); ws2.write(r, 3, "", section); ws2.write(r, 4, "", section); r+=1
infra = [
    ("EC2 (2x t3.medium API + 2x worker)", 0.450, 0.900, 1.800, "$97/mo total, allocated by tier weight"),
    ("RDS PostgreSQL 16 (db.t3.medium multi-AZ)", 0.250, 0.500, 1.000, "$163/mo total, 14-day backup"),
    ("ElastiCache Redis (cache.t3.medium x2)", 0.100, 0.200, 0.400, "$65/mo total"),
    ("S3 Storage (media files)", 0.020, 0.100, 0.500, "$0.023/GB stored"),
    ("ALB + Data Transfer", 0.050, 0.100, 0.300, "$25/mo ALB + $0.09/GB out"),
]
infra_start = r
for label, s, g, e, n in infra:
    ws2.write(r, 0, label, norm); ws2.write(r, 1, s, kwd_blue); ws2.write(r, 2, g, kwd_blue); ws2.write(r, 3, e, kwd_blue); ws2.write(r, 4, n, norm); r+=1
infra_end = r - 1

ws2.write(r, 0, "Total AWS per Customer", bold)
ws2.write_formula(r, 1, f"=SUM(B{infra_start+1}:B{infra_end+1})", kwd_yellow)
ws2.write_formula(r, 2, f"=SUM(C{infra_start+1}:C{infra_end+1})", kwd_yellow)
ws2.write_formula(r, 3, f"=SUM(D{infra_start+1}:D{infra_end+1})", kwd_yellow)
ws2.write(r, 4, "Formula: sum of AWS costs", norm)
aws_total = r; r+=2

ws2.write(r, 0, "WHATSAPP API (Meta 2026 pricing)", section); ws2.write(r, 1, "", section); ws2.write(r, 2, "", section); ws2.write(r, 3, "", section); ws2.write(r, 4, "", section); r+=1
wa = [
    ("Service Convos (24h free window)", 0.000, 0.000, 0.000, "Free: customer-initiated replies"),
    ("Marketing Messages (~10-20% of convos)", 0.200, 1.500, 10.000, "~$0.065/msg avg, varies by country"),
    ("Utility Messages (~5% of convos)", 0.050, 0.300, 2.000, "~$0.025/msg avg (order updates, tracking)"),
]
wa_start = r
for label, s, g, e, n in wa:
    ws2.write(r, 0, label, norm); ws2.write(r, 1, s, kwd_blue); ws2.write(r, 2, g, kwd_blue); ws2.write(r, 3, e, kwd_blue); ws2.write(r, 4, n, norm); r+=1
wa_end = r - 1

ws2.write(r, 0, "Total WhatsApp API per Customer", bold)
ws2.write_formula(r, 1, f"=SUM(B{wa_start+1}:B{wa_end+1})", kwd_yellow)
ws2.write_formula(r, 2, f"=SUM(C{wa_start+1}:C{wa_end+1})", kwd_yellow)
ws2.write_formula(r, 3, f"=SUM(D{wa_start+1}:D{wa_end+1})", kwd_yellow)
ws2.write(r, 4, "Formula: sum of WA costs", norm)
wa_total = r; r+=2

ws2.write(r, 0, "AI ENGINE (Anthropic Claude Haiku)", section); ws2.write(r, 1, "", section); ws2.write(r, 2, "", section); ws2.write(r, 3, "", section); ws2.write(r, 4, "", section); r+=1
ws2.write(r, 0, "Claude API calls/month", norm); ws2.write(r, 1, 0.000, kwd_blue); ws2.write(r, 2, 0.150, kwd_blue); ws2.write(r, 3, 0.800, kwd_blue); ws2.write(r, 4, "Starter: no AI. $0.25/1M input tokens", norm)
ai_row = r; r+=2

ws2.write(r, 0, "PAYMENT PROCESSING (Tap)", section); ws2.write(r, 1, "", section); ws2.write(r, 2, "", section); ws2.write(r, 3, "", section); ws2.write(r, 4, "", section); r+=1
ws2.write(r, 0, "Tap fee on subscription (2.65%)", norm)
ws2.write_formula(r, 1, f"='Plan Pricing'!B4*0.0265", kwd)
ws2.write_formula(r, 2, f"='Plan Pricing'!C4*0.0265", kwd)
ws2.write_formula(r, 3, f"='Plan Pricing'!D4*0.0265", kwd)
ws2.write(r, 4, "K-Net ~1.5%, Visa/MC ~2.65%", norm)
tap_row = r; r+=2

ws2.write(r, 0, "OTHER COSTS", section); ws2.write(r, 1, "", section); ws2.write(r, 2, "", section); ws2.write(r, 3, "", section); ws2.write(r, 4, "", section); r+=1
others = [
    ("Domain + SSL Certificate", 0.005, 0.005, 0.005, "$15/yr shared"),
    ("Sentry Error Tracking", 0.010, 0.010, 0.010, "$26/mo team plan shared"),
    ("Email (AWS SES)", 0.002, 0.010, 0.050, "$0.10/1000 emails"),
]
other_start = r
for label, s, g, e, n in others:
    ws2.write(r, 0, label, norm); ws2.write(r, 1, s, kwd_blue); ws2.write(r, 2, g, kwd_blue); ws2.write(r, 3, e, kwd_blue); ws2.write(r, 4, n, norm); r+=1
other_end = r - 1; r+=1

ws2.write(r, 0, "TOTAL COST PER CUSTOMER / MONTH", bold)
for ci, col in enumerate(["B", "C", "D"], 1):
    ws2.write_formula(r, ci, f"={col}{aws_total+1}+{col}{wa_total+1}+{col}{ai_row+1}+{col}{tap_row+1}+SUM({col}{other_start+1}:{col}{other_end+1})", kwd_yellow)
ws2.write(r, 4, "Sum: AWS + WhatsApp + AI + Tap + Other", norm)
total_cost_row = r


# ═══ SHEET 3: Profit Analysis ════════════════════════════════════════
ws3 = wb.add_worksheet("Profit Analysis")
ws3.set_tab_color("#4CAF50")
ws3.set_column("A:A", 38); ws3.set_column("B:D", 18); ws3.set_column("E:E", 28)
ws3.set_row(0, 35)

t3 = wb.add_format({"bold": True, "bg_color": "#4CAF50", "font_color": "white", "font_size": 14, "align": "center", "font_name": "Arial"})
ws3.merge_range("A1:E1", "PROFIT & MARGIN ANALYSIS PER CUSTOMER (KWD/MONTH)", t3)
ws3.write_row(2, 0, ["Metric", "Starter", "Growth", "Enterprise", "Calculation"], hdr_fmt)

r = 3
ws3.write(r, 0, "Monthly Revenue (Plan Price)", bold)
for ci, col in enumerate(["B", "C", "D"], 1):
    ws3.write_formula(r, ci, f"='Plan Pricing'!{col}4", kwd); r_rev = r
ws3.write(r, 4, "From Plan Pricing sheet", norm); r+=1

ws3.write(r, 0, "Total Cost per Customer", bold)
for ci, col in enumerate(["B", "C", "D"], 1):
    ws3.write_formula(r, ci, f"='Infrastructure Cost'!{col}{total_cost_row+1}", kwd); r_cost = r
ws3.write(r, 4, "From Infrastructure Cost sheet", norm); r+=2

ws3.write(r, 0, "GROSS PROFIT / MONTH", bold)
for ci, col in enumerate(["B", "C", "D"], 1):
    ws3.write_formula(r, ci, f"={col}{r_rev+1}-{col}{r_cost+1}", kwd_green); r_profit = r
ws3.write(r, 4, "Revenue - Cost", norm); r+=1

ws3.write(r, 0, "GROSS MARGIN %", bold)
for ci, col in enumerate(["B", "C", "D"], 1):
    ws3.write_formula(r, ci, f"=IF({col}{r_rev+1}>0,{col}{r_profit+1}/{col}{r_rev+1},0)", pct_bold); r_margin = r
ws3.write(r, 4, "Profit / Revenue", norm); r+=2

ws3.write(r, 0, "ANNUAL METRICS", section); ws3.write(r, 1, "", section); ws3.write(r, 2, "", section); ws3.write(r, 3, "", section); ws3.write(r, 4, "", section); r+=1

ws3.write(r, 0, "Annual Revenue (monthly billing)", norm)
for ci, col in enumerate(["B", "C", "D"], 1):
    ws3.write_formula(r, ci, f"={col}{r_rev+1}*12", kwd_bold); r+=1

ws3.write(r, 0, "Annual Revenue (yearly billing)", norm)
for ci, col in enumerate(["B", "C", "D"], 1):
    ws3.write_formula(r, ci, f"='Plan Pricing'!{col}5", kwd); r+=1

ws3.write(r, 0, "Annual Cost", norm)
for ci, col in enumerate(["B", "C", "D"], 1):
    ws3.write_formula(r, ci, f"={col}{r_cost+1}*12", kwd); r_annual_cost = r; r+=1

ws3.write(r, 0, "Annual Profit (monthly billing)", bold)
for ci, col in enumerate(["B", "C", "D"], 1):
    ws3.write_formula(r, ci, f"={col}{r_rev+1}*12-{col}{r_annual_cost+1}", kwd_green); r+=1

ws3.write(r, 0, "Annual Profit (yearly billing)", bold)
for ci, col in enumerate(["B", "C", "D"], 1):
    ws3.write_formula(r, ci, f"='Plan Pricing'!{col}5-{col}{r_annual_cost+1}", kwd_green); r+=2

ws3.write(r, 0, "FLEET ECONOMICS (all customers)", section); ws3.write(r, 1, "", section); ws3.write(r, 2, "", section); ws3.write(r, 3, "", section); ws3.write(r, 4, "", section); r+=1

ws3.write(r, 0, "Customers per Tier", norm)
for ci, col in enumerate(["B", "C", "D"], 1):
    ws3.write_formula(r, ci, f"='Infrastructure Cost'!{col}6", num); r_cust = r; r+=1

ws3.write(r, 0, "Monthly Fleet Revenue", bold)
for ci, col in enumerate(["B", "C", "D"], 1):
    ws3.write_formula(r, ci, f"={col}{r_rev+1}*{col}{r_cust+1}", kwd_bold); r_fleet_rev = r; r+=1

ws3.write(r, 0, "Monthly Fleet Cost", norm)
for ci, col in enumerate(["B", "C", "D"], 1):
    ws3.write_formula(r, ci, f"={col}{r_cost+1}*{col}{r_cust+1}", kwd); r_fleet_cost = r; r+=1

ws3.write(r, 0, "MONTHLY FLEET PROFIT", bold)
for ci, col in enumerate(["B", "C", "D"], 1):
    ws3.write_formula(r, ci, f"={col}{r_fleet_rev+1}-{col}{r_fleet_cost+1}", kwd_green); r_fleet_profit = r; r+=1

ws3.write(r, 0, "ANNUAL FLEET PROFIT", bold)
for ci, col in enumerate(["B", "C", "D"], 1):
    ws3.write_formula(r, ci, f"={col}{r_fleet_profit+1}*12", kwd_green); r+=2

ws3.write(r, 0, "TOTAL ANNUAL PROFIT (ALL TIERS)", bold)
ws3.write_formula(r, 1, f"=B{r}+C{r}+D{r}", kwd_green)
ws3.write(r, 4, "Combined profit from all tiers", norm)
# Actually the formula should sum from the row above
ws3.write_formula(r, 1, f"=B{r_fleet_profit+1}*12+C{r_fleet_profit+1}*12+D{r_fleet_profit+1}*12", kwd_green)


# ═══ SHEET 4: Competitor Comparison ══════════════════════════════════
ws4 = wb.add_worksheet("Competitor Comparison")
ws4.set_tab_color("#9C27B0")
ws4.set_column("A:A", 28); ws4.set_column("B:F", 16)
ws4.set_row(0, 35)

t4 = wb.add_format({"bold": True, "bg_color": "#9C27B0", "font_color": "white", "font_size": 14, "align": "center", "font_name": "Arial"})
ws4.merge_range("A1:F1", "COMPETITOR PRICING COMPARISON (Monthly)", t4)
ws4.write_row(2, 0, ["Plan Tier", "KW Growth (KWD)", "KW Growth (USD)", "Respond.io (USD)", "WATI (USD)", "SleekFlow (USD)"], hdr_fmt)

ws4.write(3, 0, "Entry / Starter", bold); ws4.write(3, 1, 9.900, kwd_blue); ws4.write_formula(3, 2, "=B4*3.26", usd_int); ws4.write(3, 3, 99, usd_int); ws4.write(3, 4, 49, usd_int); ws4.write(3, 5, 79, usd_int)
ws4.write(4, 0, "Mid / Growth", bold); ws4.write(4, 1, 29.900, kwd_blue); ws4.write_formula(4, 2, "=B5*3.26", usd_int); ws4.write(4, 3, 299, usd_int); ws4.write(4, 4, 99, usd_int); ws4.write(4, 5, 299, usd_int)
ws4.write(5, 0, "High / Enterprise", bold); ws4.write(5, 1, 79.900, kwd_blue); ws4.write_formula(5, 2, "=B6*3.26", usd_int); ws4.write(5, 3, 699, usd_int); ws4.write(5, 4, "Custom", norm); ws4.write(5, 5, 599, usd_int)

r = 7
ws4.write(r, 0, "PRICE ADVANTAGE", section); ws4.write(r, 1, "", section); ws4.write(r, 2, "", section); ws4.write(r, 3, "", section); ws4.write(r, 4, "", section); ws4.write(r, 5, "", section); r+=1
ws4.write(r, 0, "vs Respond.io Starter", norm); ws4.write_formula(r, 1, "=C4-D4", usd_int); ws4.write(r, 2, "savings", norm); r+=1
ws4.write(r, 0, "vs Respond.io Growth", norm); ws4.write_formula(r, 1, "=C5-D5", usd_int); ws4.write(r, 2, "savings", norm); r+=1
ws4.write(r, 0, "vs Respond.io Enterprise", norm); ws4.write_formula(r, 1, "=C6-D6", usd_int); ws4.write(r, 2, "savings", norm); r+=2

ws4.write(r, 0, "UNIQUE FEATURES (included)", section); ws4.write(r, 1, "", section); ws4.write(r, 2, "", section); ws4.write(r, 3, "", section); ws4.write(r, 4, "", section); ws4.write(r, 5, "", section); r+=1
features = [
    ("Kuwait K-Net Payments", "Yes", "Yes", "No", "No", "No"),
    ("Kuwaiti Dialect AI", "Yes", "Yes", "No", "No", "No"),
    ("Shipping + WhatsApp Tracking", "Yes", "Yes", "No", "No", "No"),
    ("Landing Page Builder", "Yes", "Yes", "No", "No", "No"),
    ("GCC Data Residency (Bahrain)", "Yes", "Yes", "Partial", "No", "No"),
    ("Sales Pipeline / Kanban", "Yes", "Yes", "Yes", "No", "Yes"),
    ("Instagram + Facebook DM", "Yes", "Yes", "Yes", "Yes", "Yes"),
    ("Visual Chatbot Builder", "Yes", "Yes", "Yes", "Yes", "Yes"),
    ("Broadcast Campaigns", "Yes", "Yes", "Yes", "Yes", "Yes"),
]
for label, *vals in features:
    ws4.write(r, 0, label, norm)
    for ci, v in enumerate(vals, 1):
        fmt = green_bg if v == "Yes" else (red_bg if v == "No" else norm)
        ws4.write(r, ci, v, fmt)
    r += 1


wb.close()
print(f"Saved: {output}")
