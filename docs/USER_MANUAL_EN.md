# Kuwait WhatsApp Growth Engine — Enterprise User Manual

**Version 1.0 | April 2026**
**Platform:** Enterprise WhatsApp CRM SaaS for Kuwait & GCC
**URL:** app.kwgrowth.com

---

## Table of Contents

1. [Introduction & Value Proposition](#1-introduction--value-proposition)
2. [Getting Started](#2-getting-started)
3. [Dashboard Overview](#3-dashboard-overview)
4. [Contacts & CRM Management](#4-contacts--crm-management)
5. [WhatsApp Shared Inbox](#5-whatsapp-shared-inbox)
6. [Campaigns & Broadcasts](#6-campaigns--broadcasts)
7. [Chatbot Flow Builder](#7-chatbot-flow-builder)
8. [Automation Engine](#8-automation-engine)
9. [Kuwaiti Dialect AI Engine](#9-kuwaiti-dialect-ai-engine)
10. [Sales Pipeline & Kanban](#10-sales-pipeline--kanban)
11. [Landing Page Builder](#11-landing-page-builder)
12. [Message Templates](#12-message-templates)
13. [Shipping & Delivery Tracking](#13-shipping--delivery-tracking)
14. [Payments & Billing](#14-payments--billing)
15. [Product Catalog & Commerce](#15-product-catalog--commerce)
16. [Analytics & Performance](#16-analytics--performance)
17. [Settings & Administration](#17-settings--administration)
18. [Compliance & Data Security](#18-compliance--data-security)
19. [API Reference](#19-api-reference)
20. [Conclusion](#20-conclusion)

---

## 1. Introduction & Value Proposition

The **Kuwait WhatsApp Growth Engine** is the most comprehensive enterprise WhatsApp CRM platform purpose-built for the Kuwaiti and GCC market. Unlike international competitors that treat the Middle East as an afterthought, every component of this platform — from AI dialect understanding to K-Net payment processing — has been engineered from the ground up for Kuwait.

### Why Choose Us Over Respond.io, WATI, or SleekFlow?

| Capability | KW Growth Engine | International Competitors |
|---|---|---|
| **Kuwaiti Dialect AI** | 133+ dialect markers, code-switching, auto-responses | No Arabic dialect support |
| **K-Net Payments** | Native Tap Payments (K-Net, Visa, MC) | Stripe only (no K-Net) |
| **Local Shipping** | Aramex integration with WhatsApp tracking | No shipping integration |
| **Data Residency** | AWS Bahrain (GCC), CITRA tier classification | US/EU hosting only |
| **Landing Pages** | Built-in page builder with WhatsApp CTA | Not available |
| **Self-Hosted** | Can deploy on-premise for banks & government | SaaS only |
| **Cost** | Starting 9.900 KWD/mo (~$32 USD) | Starting $99-299 USD/mo |

### Platform at a Glance

- **145 API Endpoints** across 31 modules
- **42 Database Tables** with PostgreSQL Row-Level Security
- **23 User-Facing Pages** with Arabic RTL support
- **133+ Kuwaiti Dialect Markers** for AI understanding
- **5 Messaging Channels** (WhatsApp, Instagram, Facebook, Snapchat, Web Chat)
- **9 Chatbot Node Types** including in-chat payments and shipping queries

---

## 2. Getting Started

### 2.1 Registration

Visit **app.kwgrowth.com/register** and provide:
- Company name
- First and last name
- Email address
- Username
- Password (minimum 8 characters)

Upon registration, you are automatically assigned the **Owner** role with full platform access. A JWT access token (15 minutes) is issued and refreshes automatically.

### 2.2 System Requirements

| Component | Requirement |
|---|---|
| Browser | Chrome 90+, Firefox 88+, Safari 14+, Edge 90+ |
| WhatsApp | Meta Business Account with Cloud API access |
| Payments | Tap Payments account (for K-Net acceptance) |
| Mobile | Fully responsive — all features work on phone and tablet |

### 2.3 First Steps After Registration

1. **Connect WhatsApp** — Go to Settings > Channels and enter your WhatsApp Cloud API credentials
2. **Import Contacts** — Upload a CSV file or add contacts manually
3. **Create Your First Automation** — Set up an auto-reply for incoming messages
4. **Set Up Your Pipeline** — Create sales stages and start tracking deals

---

## 3. Dashboard Overview

The dashboard provides a real-time snapshot of your entire business:

### KPI Cards (4 Primary Metrics)
- **Total Contacts** — Contacts in your CRM with trend indicator
- **Open Conversations** — Active WhatsApp conversations requiring attention
- **Messages (Period)** — Inbound and outbound message volume
- **Revenue (Won)** — Total deal value in KWD (3 decimal places)

### Navigation Sidebar
The dark navy sidebar (available on all pages) provides quick access to all 10 modules. Active page is highlighted with a green indicator bar. Each module uses a professional Lucide icon.

### Header Features
- **Breadcrumb navigation** — Always know where you are
- **Global search** — Quick search across contacts and conversations
- **Notification bell** — Real-time alerts for new messages
- **Dark mode toggle** — Switch between light and dark themes

---

## 4. Contacts & CRM Management

### 4.1 Contact List (`/contacts`)

The contacts page displays all your customers in a powerful data table supporting:

- **Real-time search** — Type to search by name, phone, or email (debounced 300ms)
- **Multi-filter** — Filter by status (Active/Inactive/Blocked), source (Manual/WhatsApp/Import/Landing Page/API), and tags
- **Column sorting** — Click any header to sort ascending/descending
- **Bulk actions** — Select multiple contacts to delete, add tag, or change status
- **Pagination** — Navigate through pages with 20 contacts per page

### 4.2 Contact Detail (`/contacts/{id}`)

Click any contact to view their full profile:
- Contact information (phone, email, name)
- Status and source
- Lead score
- WhatsApp opt-in status
- Assigned tags (color-coded)
- Custom field values
- Notes
- Edit mode with inline saving

### 4.3 Tags

Tags are color-coded labels for organizing contacts. Manage them in Settings > Tags:
- Create tags with custom name, color, and description
- 10 preset colors available
- Tags are company-unique (no duplicates)

### 4.4 Custom Fields

Create additional fields per contact beyond the defaults:
- **5 field types**: Text, Number, Date, Select (dropdown), Boolean (Yes/No)
- Sortable display order
- Required field option

### 4.5 CSV Import

Upload contacts in bulk:
- **Flexible column mapping** — Automatically maps common column names (phone, first_name, email, etc.)
- **Upsert logic** — Duplicate phone numbers are updated, new ones are created
- **Async processing** — Large files processed via Celery background task
- **Error reporting** — Failed rows reported with line numbers

### 4.6 Unified Timeline (`/timeline/{contact_id}`)

View all interactions with a contact across every channel in one chronological feed:
- WhatsApp messages
- Conversation open/close events
- Deal activities and stage changes
- Shipment tracking updates

**API:** `GET /v1/timeline/{contact_id}`

---

## 5. WhatsApp Shared Inbox

### 5.1 Conversation List (`/inbox`)

The left panel displays all conversations sorted by last message time:
- **Avatar circles** with contact initials
- **Status dot** — Green (open), Yellow (pending), Blue (snoozed), Gray (closed)
- **Unread badge** — Green counter for unread messages
- **Last message preview** — Truncated preview text
- **Relative time** — "2m ago", "1h ago", etc.
- **Search & filter pills** — Filter by status with one click

### 5.2 Message Thread

The right panel shows the full conversation:
- **Gradient chat bubbles** — Green for outbound, white for inbound
- **Delivery status icons** — Clock (pending), Check (sent), Double-check (delivered), Blue double-check (read), X (failed)
- **Timestamp** on every message
- **Auto-scroll** to latest message
- **Enter to send** (Shift+Enter for new line)

### 5.3 Real-Time Updates

Conversations refresh automatically every 3 seconds. The platform uses WebSocket connections for instant message delivery:

```
wss://app.kwgrowth.com/ws?token=<jwt_access_token>
```

Events pushed via WebSocket:
- `message.new` — New inbound/outbound message
- `conversation.updated` — Status or assignment change
- `message.status` — Delivery status update

### 5.4 WhatsApp Cloud API Integration

Messages are sent and received via Meta's WhatsApp Cloud API:

**Supported message types:**
- Text
- Image, Video, Audio, Document
- Template (pre-approved by Meta)
- Interactive (buttons, lists)
- Location
- Product & Product List (WhatsApp Catalog)

**Webhook handling:**
- `GET /v1/webhooks/whatsapp` — Meta subscription verification
- `POST /v1/webhooks/whatsapp` — Incoming messages and status updates

---

## 6. Campaigns & Broadcasts

### 6.1 Campaign Management (`/campaigns`)

Send bulk WhatsApp messages to your entire contact base or targeted segments.

**Features:**
- **Template or text messages** — Use Meta-approved templates for broadcast
- **Audience targeting** — All contacts, by tag, by segment, or custom filter
- **Scheduling** — Send immediately or schedule for a future date
- **Delivery tracking** — Real-time counters for sent, delivered, read, and failed
- **Pause/Resume** — Pause a running campaign and resume later
- **Rate limiting** — Respects WhatsApp's 80 msg/sec limit

**API Endpoints (8):**
- `GET /v1/campaigns` — List campaigns
- `POST /v1/campaigns` — Create campaign
- `GET /v1/campaigns/{id}` — Campaign detail
- `PATCH /v1/campaigns/{id}` — Update campaign
- `DELETE /v1/campaigns/{id}` — Delete campaign
- `POST /v1/campaigns/{id}/send` — Start sending
- `POST /v1/campaigns/{id}/pause` — Pause sending
- `GET /v1/campaigns/{id}/stats` — Delivery statistics

---

## 7. Chatbot Flow Builder

### 7.1 Flow List (`/chatbots`)

Create automated conversation flows with a visual node-based editor.

**Trigger Types:**
- **Keyword Match** — Activates when message contains specific keywords
- **Any Message** — Activates on every inbound message
- **New Conversation** — Activates when a conversation starts
- **Webhook** — Triggered by external API call

### 7.2 Flow Editor (`/chatbots/{id}`)

Build flows by adding and connecting nodes:

| Node Type | Description | Use Case |
|---|---|---|
| **Send Message** | Send text to customer | Welcome message, info reply |
| **Ask Question** | Ask and wait for response | Qualification, data collection |
| **Condition** | Branch based on content | Route by language or intent |
| **Delay** | Wait N seconds | Timed follow-up |
| **Assign Agent** | Hand off to human | Complex queries |
| **Action** | Tag, update field, score | CRM automation |
| **Payment Link** | Generate Tap charge URL | In-chat purchase |
| **Check Shipping** | Query shipment status | "Where is my order?" |
| **API Call** | External HTTP request | Third-party integration |

### 7.3 Payment Link Node (Gap 8)

The payment link node generates a Tap Payments charge and sends the payment URL directly in the WhatsApp conversation:

```json
{
  "type": "payment_link",
  "data": {
    "amount": 29.900,
    "currency": "KWD",
    "description": "Monthly Subscription"
  }
}
```

The customer receives: "Please complete your payment of 29.900 KWD for: Monthly Subscription. Pay here: https://tap.company/pay/..."

### 7.4 Shipping Query Node (Gap 9)

When a customer asks "Where is my order?", the check_shipping node automatically:
1. Finds the customer's most recent shipment
2. Retrieves tracking status from the carrier
3. Sends a formatted status message with tracking number, carrier, and estimated delivery

---

## 8. Automation Engine

### 8.1 Rule Builder (`/automations`)

Create automated actions that trigger on system events.

**Triggers (5):**
- Message Received
- Contact Created
- Contact Updated
- Conversation Created
- Deal Stage Changed

**Conditions (7 operators):**
- Equals, Not Equals, Contains, Starts With, Greater Than, Less Than, In List

**Actions (8 types):**

| Action | Description |
|---|---|
| Auto Reply | Send a text message immediately |
| Send Template | Send a Meta-approved template |
| Add Tag | Automatically tag the contact |
| Remove Tag | Remove a tag |
| Change Status | Update contact status |
| Update Lead Score | Increase or decrease score |
| Assign Agent | Route via smart routing engine |
| Webhook Call | HTTP request to external service |

### 8.2 Execution & Logging

Automations execute asynchronously via Celery. Each execution is logged:
- Status (success/failed)
- Actions executed count
- Duration in milliseconds
- Error details if failed

---

## 9. Kuwaiti Dialect AI Engine

### 9.1 Overview

The AI engine is the platform's most unique differentiator. No competitor offers native Kuwaiti Arabic dialect understanding.

### 9.2 Dialect Detection

**133+ Kuwaiti dialect markers** organized into 9 categories:
- Greetings (شلونك, هلا والله, يا بعد قلبي)
- Pronouns (شنو, ليش, وين, هالحين)
- Intensifiers (وايد, مرة, خلاص, بس)
- Verbs (أبي, أسوي, أدري, خلنا)
- Nouns (فلوس, هدوم, سيارة, ديوانية)
- Expressions (الله يبارك, ما عليك, عسى بس)
- Business terms (كم السعر, خصم, عرض, توصيل)

**Dialect categories detected:** Kuwaiti, Gulf, MSA (Modern Standard Arabic), English, Mixed

### 9.3 Code-Switching Support

The engine understands messages mixing Arabic and English — extremely common in Kuwait:

Example: "hala shlonik, aby delivery for the new offer please"
- Detects: `kuwaiti` dialect
- Transliterations found: `shlonik` → شلونك, `aby` → أبي
- Intent: `purchase`

**27 transliteration mappings** including: shlonik, inshallah, mashallah, yallah, khalas, habibi, zain, wallah, etc.

### 9.4 Intent Classification (10 Categories)

Each inbound message is classified into one of 10 intents with confidence scores:

| Intent | Arabic Keywords | English Keywords |
|---|---|---|
| Pricing | كم, سعر, بكم, خصم | price, cost, discount, offer |
| Purchase | أبي, شراء, اشتري, أطلب | buy, order, want, checkout |
| Support | مساعدة, مشكلة, خربان | help, problem, issue, broken |
| Greeting | هلا, شلون, مرحبا | hi, hello, hey |
| Inquiry | أبي أعرف, استفسار, تفاصيل | info, details, tell me |
| Scheduling | موعد, حجز, متى | appointment, book, available |
| Shipping | وين طلبي, شحن, تتبع | tracking, delivery, where is my order |
| Complaint | شكوى, زعلان, سيء | complaint, angry, terrible |
| Feedback | شكرا, ممتاز, رائع | thanks, great, excellent |
| Cancellation | إلغاء, رجعوا فلوسي | cancel, refund, unsubscribe |

### 9.5 Sentiment Analysis

Every message receives a sentiment score:
- **Positive** (0 to +1.0): 36 indicator words (19 Arabic, 17 English)
- **Negative** (-1.0 to 0): 33 indicator words (18 Arabic, 15 English)
- **Neutral** (0.0)
- **Mixed** (both positive and negative detected)

### 9.6 Auto-Response Templates

When Kuwaiti dialect is detected, the AI suggests culturally appropriate responses:

| Intent | Response Template |
|---|---|
| Greeting | هلا والله! شلون أقدر أساعدك اليوم؟ |
| Pricing | تبي تعرف الأسعار؟ خلني أوريك التفاصيل |
| Purchase | ممتاز! تبي أسويلك الطلب الحين؟ |
| Support | ما عليك هم، خلني أساعدك بالمشكلة |
| Shipping | خلني أشيك على الطلب حقك |

### 9.7 Claude API Integration

When an Anthropic API key is configured, the engine uses **Claude Haiku** for advanced analysis:
- Full sentence-level understanding
- Contextual intent classification
- Natural response generation in customer's dialect
- Conversation summarization
- Customer insight extraction (needs, urgency, language preference)

**API Endpoints:**
- `POST /v1/ai/analyze` — Analyze a message
- `GET /v1/ai/context/{conversation_id}` — Get AI context for a conversation
- `POST /v1/ai/suggest/{conversation_id}` — Generate suggested response

### 9.8 Business Glossary

Add your own product names, services, and terminology to improve AI understanding:

**API Endpoints:**
- `GET /v1/glossary` — List terms
- `POST /v1/glossary` — Add term with definition and aliases
- `DELETE /v1/glossary/{id}` — Remove term

---

## 10. Sales Pipeline & Kanban

### 10.1 Pipeline View (`/pipeline`)

Manage your sales process with a visual Kanban board.

**Features:**
- **Colored stage columns** — New Lead, Contacted, Qualified, Proposal, Won, Lost
- **Deal cards** — Title, value (KWD 3 decimals), status badge
- **Drag-and-drop** — Move deals between stages
- **Create deal dialog** — Title, value, stage, contact link
- **Auto-create pipeline** — Default Sales Pipeline with 6 stages

### 10.2 Deal Management

Each deal tracks:
- Title and description
- Value in KWD (DECIMAL 12,3)
- Stage and status (Open, Won, Lost)
- Linked contact
- Assigned agent
- Expected close date
- Custom data (JSONB)

### 10.3 Activity Timeline

All changes are automatically logged:
- Stage changed (with old → new)
- Value changed (with amounts)
- Status changed (open/won/lost)
- Notes added
- Deal created

**API Endpoints (16):**
- Pipeline CRUD (4): list, create, get, update, delete
- Stage management (2): add stage, delete stage
- Kanban board (1): GET /pipelines/{id}/board
- Deal CRUD (5): list, create, get, update, delete
- Deal actions (3): move, activities, notes
- Deal notes (1): add note

---

## 11. Landing Page Builder

### 11.1 Page List (`/landing-pages`)

Create marketing pages with WhatsApp call-to-action buttons.

**Features:**
- Card grid view with status badges
- Visit and conversion counters
- Publish/unpublish toggle
- Conversion rate display

### 11.2 Page Editor (`/landing-pages/{id}`)

Build pages using 8 block types:

| Block | Description |
|---|---|
| Hero Section | Full-width header with heading, subheading, and CTA button |
| Text Block | Rich text content |
| Image | Image with optional caption |
| Features Grid | Feature cards with icons |
| Call to Action | CTA section with WhatsApp button |
| Testimonial | Customer quote with author |
| FAQ | Accordion-style questions and answers |
| Divider | Visual separator |

### 11.3 WhatsApp CTA

Configure per page:
- WhatsApp phone number
- Pre-filled message (e.g., "Hi! I'm interested in your Ramadan offer")

When visitors click the CTA, WhatsApp opens with your number and message pre-filled.

### 11.4 Public Access & Analytics

Published pages are accessible without authentication:
- `GET /v1/landing-pages/public/{slug}` — View page (auto-increments visit counter)
- `POST /v1/landing-pages/public/{slug}/convert` — Record CTA click conversion

---

## 12. Message Templates

WhatsApp requires pre-approved message templates for outbound conversations (outside 24-hour window).

### 12.1 Template Management (`/templates`)

- Create templates with variables ({{1}}, {{2}})
- Categories: Marketing, Utility, Authentication
- Languages: English, Arabic
- Header types: Text, Image, Video, Document
- Footer and button support

### 12.2 Template Sync

Request Meta template sync via `POST /v1/templates/sync` to pull approved templates from WhatsApp Cloud API.

---

## 13. Shipping & Delivery Tracking

### 13.1 Carrier Integration

Supported carriers:
- **Aramex Kuwait** (primary)
- DHL
- Fetchr
- Shipa Delivery

### 13.2 Shipment Management

Create and track shipments:
- Origin and destination addresses
- Recipient name and phone
- Weight and description
- **Cash on Delivery (COD)** support in KWD
- Automatic tracking number generation

### 13.3 Status Tracking (7 States)

| Status | Description |
|---|---|
| Created | Shipment created in system |
| Picked Up | Courier collected package |
| In Transit | Package moving to destination |
| Out for Delivery | Last-mile delivery in progress |
| Delivered | Successfully delivered |
| Failed | Delivery attempt failed |
| Returned | Package being returned |

### 13.4 WhatsApp Notifications

Automatic WhatsApp messages sent on every status change:
- "Your shipment has been created! Tracking: ARX..."
- "Your package is on its way!"
- "Great news! Your package is out for delivery today."
- "Your package has been delivered!"

### 13.5 Chatbot Integration

Customers can ask "Where is my order?" via WhatsApp chatbot. The check_shipping node automatically retrieves and sends tracking status.

---

## 14. Payments & Billing

### 14.1 Subscription Plans

| Feature | Starter (9.900 KWD/mo) | Growth (29.900 KWD/mo) | Enterprise (79.900 KWD/mo) |
|---|---|---|---|
| Contacts | 500 | 5,000 | 50,000 |
| Conversations/mo | 1,000 | 10,000 | 100,000 |
| Team Members | 3 | 10 | 50 |
| Automations | 5 | 25 | 100 |
| Pipelines | 1 | 3 | 10 |
| Landing Pages | 3 | 10 | 50 |
| AI Features | No | Yes | Yes |
| API Access | No | No | Yes |
| Yearly Discount | ~17% | ~17% | ~17% |

### 14.2 Payment Methods

Powered by **Tap Payments** (Kuwait Central Bank licensed):
- **K-Net** (Kuwait debit cards) — `src_kw.knet`
- **Visa** — `src_card`
- **Mastercard** — `src_card`
- **Apple Pay** — `src_apple_pay`

All amounts in **Kuwaiti Dinar (KWD)** with 3 decimal places.

### 14.3 Invoice System

- Auto-generated on subscription creation/renewal
- Sequential numbering: INV-YYYYMM-NNNN
- Line items with description and amount
- Status tracking: Draft, Pending, Paid, Failed, Void

### 14.4 Tap Webhook

Payment confirmations received via `POST /v1/payments/tap-webhook`:
- CAPTURED → Payment successful, invoice marked paid
- FAILED/DECLINED → Payment recorded as failed

---

## 15. Product Catalog & Commerce

### 15.1 Product Management

Create a product catalog for in-chat commerce:
- Product name, description, price (KWD)
- SKU and image URL
- Stock quantity tracking
- Category organization

### 15.2 WhatsApp Catalog Sync

Sync your products to Meta Commerce Manager:
- `POST /v1/catalog/sync-whatsapp` — Push all products to WhatsApp Business Catalog
- Products appear as browsable catalog within WhatsApp conversations
- Single-product and multi-product message support

### 15.3 In-Chat Purchase Flow

1. Customer browses catalog in WhatsApp
2. Selects product
3. Chatbot generates K-Net payment link
4. Customer pays via Tap Payments
5. Confirmation message sent automatically
6. Shipment created and tracked

---

## 16. Analytics & Performance

### 16.1 Dashboard (`/analytics`)

KPI cards with gradient borders and trend indicators:
- Total Contacts (with new count)
- Open Conversations
- Message Volume (inbound/outbound)
- Revenue from Won Deals

### 16.2 Pipeline Analytics

- Stage distribution chart with colored bars
- Win rate percentage
- Average deal value

### 16.3 Team Performance

Per-agent metrics table:
- Messages sent
- Conversations assigned
- Deals won
- Revenue generated
- Online status indicator

### 16.4 Landing Page Analytics

Per-page metrics:
- Visit count
- Conversion count
- Conversion rate

### 16.5 Localization Analytics

- Dialect distribution (% Kuwaiti, Gulf, MSA, English, Mixed)
- Average intent confidence score
- Sentiment distribution

### 16.6 Routing Analytics

- Same-agent routing rate
- Method distribution (relationship, scoring, round-robin, queue)

**API Endpoints (8):**
- `GET /v1/analytics/dashboard` — KPI summary
- `GET /v1/analytics/messages` — Message volume & delivery stats
- `GET /v1/analytics/pipeline` — Pipeline deal analytics
- `GET /v1/analytics/team` — Agent performance
- `GET /v1/analytics/landing-pages` — Page conversion stats
- `GET /v1/analytics/automations` — Automation execution stats
- `GET /v1/analytics/routing` — Routing continuity metrics
- `GET /v1/analytics/localization` — NLP effectiveness metrics

---

## 17. Settings & Administration

### 17.1 Team Management (`/settings/team`)

- **Invite members** by email with role assignment
- **5 roles**: Platform Admin, Owner, Admin, Manager, Agent
- **34 granular permissions** across 13 categories
- Activate/deactivate members
- Online status indicators

### 17.2 Channels (`/settings/channels`)

Connect messaging channels:
- WhatsApp (primary)
- Instagram DM
- Facebook Messenger
- Web Chat (embeddable widget)
- SMS
- Email

**Web Chat Widget:**
Generate an embed code for your website:
```html
<script src="https://app.kwgrowth.com/widget.js" data-token="your_token"></script>
```

### 17.3 Tags (`/settings/tags`)

Create, edit, and delete color-coded tags with 10 preset colors.

### 17.4 Billing (`/settings/billing`)

- Current plan display with status
- Plan comparison with monthly/yearly toggle
- Invoice history with status badges
- Payment method management

### 17.5 Compliance (`/settings/compliance`)

Detailed compliance dashboard (see Section 18).

### 17.6 Data Export (`/settings/export`)

Download your data as CSV:
- Contacts export
- Conversations export
- Deals export

### 17.7 QR Code Generator

Generate WhatsApp QR codes:
- `GET /v1/qr/whatsapp?phone=+96512345678&message=Hi` — Returns PNG QR code
- `GET /v1/qr/link?phone=+96512345678` — Returns click-to-chat URL

### 17.8 CSAT Surveys

Create customer satisfaction surveys:
- CSAT, NPS, or custom survey types
- Trigger on conversation close
- Score tracking and analytics

---

## 18. Compliance & Data Security

### 18.1 CITRA Data Classification

Data is classified per Kuwait CITRA regulations:

| Tier | Classification | Hosting Requirement | Platform Data |
|---|---|---|---|
| 1 | Public Data | Any region | Landing pages, product catalog |
| 2 | Internal Data | GCC recommended | Analytics, audit logs, deals |
| 3 | Confidential Data | Kuwait/CITRA-GCC required | Contacts, conversations, payments, AI contexts |
| 4 | Government/Restricted | Kuwait only | Government entity data (requires in-Kuwait DC) |

### 18.2 Compliance Checklist (8 Checks)

1. **Data Residency** — AWS me-south-1 (Bahrain, GCC)
2. **Encryption at Rest** — PostgreSQL AES-256 disk encryption
3. **Encryption in Transit** — TLS 1.3 for all connections
4. **Consent Tracking** — WhatsApp opt-in per contact
5. **Data Retention Policy** — Configurable (default 365 days)
6. **Audit Logging** — All actions recorded with timestamp, user, and changes
7. **Right to Deletion** — Soft delete with full purge capability
8. **Data Export** — CSV export for all data types

### 18.3 Security Measures

- **Authentication**: JWT (HS256), 15-minute access tokens, 7-day refresh
- **Password**: bcrypt with 12 rounds
- **Multi-Tenancy**: PostgreSQL Row-Level Security (company_id isolation)
- **RBAC**: 5 roles, 34 permissions, per-endpoint enforcement
- **Rate Limiting**: Redis sliding window (30/sec API, 5/sec auth, 100/sec webhooks)
- **Encryption**: Fernet (AES-128-CBC) for stored API keys and tokens

### 18.4 Audit Logs

Every significant action is logged:
- Who (user_id, email)
- What (action, resource_type, resource_id)
- Changes (before/after JSONB)
- Context (IP address, user agent)

**API:** `GET /v1/compliance/audit-logs`

### 18.5 CITRA Compliance Report

Generate a full compliance report:

**API:** `GET /v1/compliance/report`

Returns: data classification per table, retention policies, security measures, and compliance status per CITRA tier.

---

## 19. API Reference

### 19.1 Authentication

All API requests require a Bearer token:

```
Authorization: Bearer <access_token>
```

**Obtain tokens:**
```
POST /v1/auth/login
Body: {"email": "user@company.com", "password": "..."}
Response: {"access_token": "...", "refresh_token": "...", "expires_in": 900}
```

**Refresh tokens:**
```
POST /v1/auth/refresh
Body: {"refresh_token": "..."}
```

### 19.2 API Modules (31 Total, 145 Endpoints)

| Module | Prefix | Endpoints | Description |
|---|---|---|---|
| Authentication | /v1/auth | 4 | Register, login, refresh, profile |
| Contacts | /v1/contacts | 7 | CRUD, search, bulk, import |
| Tags | /v1/tags | 5 | Tag CRUD |
| Custom Fields | /v1/custom-fields | 4 | Field type CRUD |
| Timeline | /v1/timeline | 1 | Cross-channel contact timeline |
| Conversations | /v1/conversations | 6 | CRUD, send message, history |
| Webhooks | /v1/webhooks | 4 | WhatsApp + Instagram webhooks |
| Templates | /v1/templates | 4 | Template CRUD + Meta sync |
| Automations | /v1/automations | 7 | CRUD, toggle, execute, logs |
| Chatbot Flows | /v1/chatbots | 6 | CRUD, toggle |
| AI Engine | /v1/ai | 3 | Analyze, context, suggest |
| Glossary | /v1/glossary | 3 | Business term CRUD |
| Pipelines | /v1/pipelines | 16 | Pipeline, stage, deal, board |
| Campaigns | /v1/campaigns | 8 | CRUD, send, pause, stats |
| Landing Pages | /v1/landing-pages | 10 | CRUD, publish, public, convert |
| Product Catalog | /v1/catalog | 5 | Products, sync, send |
| Payments | /v1/payments | 10 | Plans, subscription, invoices, charges |
| Shipping | /v1/shipping | 9 | Providers, shipments, tracking |
| Analytics | /v1/analytics | 8 | Dashboard, messages, pipeline, team, LP, routing, localization |
| Compliance | /v1/compliance | 3 | Status, report, audit logs |
| Surveys | /v1/surveys | 3 | CSAT survey CRUD + stats |
| Users | /v1/users | 4 | Team invite, list, update, deactivate |
| Channels | /v1/channels | 4 | Channel CRUD + web chat widget |
| Media | /v1/media | 2 | Upload, presigned URL |
| Export | /v1/export | 3 | Contacts, conversations, deals CSV |
| QR Codes | /v1/qr | 2 | WhatsApp QR + link generator |

### 19.3 WebSocket API

```
wss://app.kwgrowth.com/ws?token=<jwt_access_token>
```

| Event | Direction | Payload |
|---|---|---|
| `message.new` | Server → Client | New message data |
| `conversation.updated` | Server → Client | Conversation status change |
| `message.status` | Server → Client | Delivery status update |
| `ping` | Client → Server | Heartbeat |
| `pong` | Server → Client | Heartbeat response |

### 19.4 Webhook Endpoints

| Endpoint | Source | Purpose |
|---|---|---|
| `POST /v1/webhooks/whatsapp` | Meta | Incoming WhatsApp messages & status |
| `POST /v1/webhooks/instagram` | Meta | Instagram DMs & comments |
| `POST /v1/payments/tap-webhook` | Tap | Payment confirmations |

### 19.5 Rate Limits

| Endpoint Category | Limit |
|---|---|
| API (general) | 30 requests/second |
| Authentication | 5 requests/second |
| Webhooks | 100 requests/second |
| WhatsApp sends | 80 messages/second (Meta tier) |

### 19.6 Error Format (RFC 7807)

```json
{
  "type": "about:blank",
  "title": "Contact with phone '+96512345678' already exists",
  "status": 409,
  "detail": null,
  "traceId": "abc-123-def"
}
```

---

## 20. Conclusion

The **Kuwait WhatsApp Growth Engine** delivers what no international CRM platform can: a complete enterprise solution built from the ground up for the Kuwaiti market.

### For Companies

- **Reduce customer response time** with AI-powered auto-replies in Kuwaiti dialect
- **Increase conversion rates** with in-chat payments and product catalogs
- **Streamline operations** with automated workflows and smart agent routing
- **Track everything** with real-time analytics across contacts, deals, and campaigns

### For Partners

- **White-label ready** — Self-hosted deployment option for banks and government
- **API-first architecture** — 145 endpoints for seamless integration
- **Multi-tenant** — Serve unlimited clients from a single deployment
- **GCC compliant** — CITRA data classification, Bahrain hosting, audit logging
- **Cost advantage** — 60-70% cheaper than Respond.io while offering more Kuwait-specific features

### Technology Foundation

- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Celery, Redis
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS v4, Lucide Icons
- **Database**: PostgreSQL 16 with Row-Level Security
- **Infrastructure**: Docker, Terraform (AWS), GitHub Actions CI/CD
- **AI**: Claude Haiku + 133-marker rule engine
- **Payments**: Tap Payments (K-Net, Visa, MC)
- **Shipping**: Aramex Kuwait with WhatsApp tracking

---

**Kuwait WhatsApp Growth Engine** — The enterprise WhatsApp CRM Kuwait deserves.

**app.kwgrowth.com** | **API Docs: app.kwgrowth.com/docs** | **Support: support@kwgrowth.com**

*Copyright 2026 Kuwait WhatsApp Growth Engine. All rights reserved.*
