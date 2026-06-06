# School Data Storage Architecture

**Document Purpose:** Define where different types of school-related data should be stored across microservices

**Version:** 1.0  
**Last Updated:** 2024-01-15

---

## Problem Statement

After a school purchases a subscription through Platform Service, we need to store various types of school-related information:

- Basic info (name, address, contact)
- Branding (logo, colors, motto)
- Configuration (language, timezone, settings)
- Operational data (announcements, events, news)
- Media assets (images, documents, files)

**Question:** Which service should own which data?

---

## Solution: Data Distribution Across Services

### **Principle: Separate Concerns by Domain**

Different services own different aspects of school data based on their domain responsibility:

```
┌─────────────────────────────────────────────────────────────────┐
│                    School Data Distribution                      │
└─────────────────────────────────────────────────────────────────┘

Platform Service      ──────►  Subscription & Access Control
Admin Service         ──────►  School Operations & Configuration
Media Service         ──────►  Files, Images, Documents
Academic Service      ──────►  Academic Structure
Finance Service       ──────►  Fee Structure
HR Service            ──────►  Staff Details
```

---

## 1. Platform Service (Subscription & Identity)

### **Purpose:**
Controls WHO can access the system, WHAT they can access, and billing.

### **Data Stored:**

#### **Table: `schools`**

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | School identifier |
| `tenant_id` | UUID | Parent organization |
| `name` | String | Official school name |
| `code` | String | Short code (e.g., "GVB") |
| `subdomain` | String | URL subdomain (greenvalley-bangalore) |
| `board` | Enum | Educational board (CBSE, ICSE, etc.) |
| `email` | String | Primary contact email |
| `phone_number` | String | Primary phone |
| `address` | String | Physical address |
| `city` | String | City |
| `state` | String | State |
| `country` | String | Country |
| `pincode` | String | Postal code |
| `timezone` | String | Timezone (Asia/Kolkata) |
| `academic_year_start_month` | Integer | Academic year start (4 = April) |
| `status` | Enum | TRIAL, ACTIVE, SUSPENDED, etc. |

#### **Table: `school_subscriptions`**
- Purchased user limits
- Purchased storage limits
- Subscription status
- Start/end dates
- Pricing details

#### **Table: `school_domains`**
- Custom domain mapping
- SSL configuration
- Domain verification status

### **What Platform Service DOES NOT Store:**
- ❌ School logo, images
- ❌ School motto, vision, mission
- ❌ School announcements, news
- ❌ Detailed staff information
- ❌ Academic class structure
- ❌ Fee structure details

---

## 2. Admin Service (School Operations & Configuration)

### **Purpose:**
Manages day-to-day operational data and school-specific configurations.

### **Recommended Tables:**

#### **Table: `school_profiles`**

Stores branding and presentation details.

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `school_id` | UUID | FK → platform.schools.id |
| `tenant_id` | UUID | Soft FK for multi-tenancy |
| `logo_url` | String | URL to logo (stored in Media Service) |
| `banner_url` | String | URL to banner image |
| `favicon_url` | String | URL to favicon |
| `motto` | String | School motto/tagline |
| `vision` | Text | Vision statement |
| `mission` | Text | Mission statement |
| `about` | Text | About us / description |
| `establishment_year` | Integer | Year founded |
| `affiliation_number` | String | Board affiliation number |
| `school_code_board` | String | Board-issued school code |
| `principal_name` | String | Current principal name |
| `principal_message` | Text | Principal's message |
| `website` | String | Official website URL |
| `social_media` | JSONB | Links to social media profiles |

**Example Data:**
```json
{
  "school_id": "660e8400-...",
  "logo_url": "https://cdn.smartsync.ai/schools/gvb/logo.png",
  "motto": "Knowledge is Power",
  "vision": "To be a center of excellence in education...",
  "mission": "Provide quality education to all students...",
  "establishment_year": 1995,
  "affiliation_number": "CBSE/DEL/1234567",
  "social_media": {
    "facebook": "https://facebook.com/greenvalley",
    "twitter": "https://twitter.com/greenvalley",
    "instagram": "https://instagram.com/greenvalley"
  }
}
```

---

#### **Table: `school_settings`**

Application-level configuration and preferences.

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `school_id` | UUID | FK → platform.schools.id |
| `language` | String | Default UI language (en, hi, ta, etc.) |
| `locale` | String | Locale (en-IN, en-US) |
| `currency` | String | Display currency (INR, USD) |
| `date_format` | String | DD/MM/YYYY or MM/DD/YYYY |
| `time_format` | String | 12-hour or 24-hour |
| `week_start_day` | String | SUNDAY or MONDAY |
| `theme_primary_color` | String | Hex color code |
| `theme_secondary_color` | String | Hex color code |
| `enable_dark_mode` | Boolean | Dark mode support |
| `enable_parent_portal` | Boolean | Parent login enabled |
| `enable_student_portal` | Boolean | Student login enabled |
| `enable_public_website` | Boolean | Public-facing website |
| `session_timeout_minutes` | Integer | Auto-logout time |
| `working_days` | JSONB | Array of working days |
| `school_timings` | JSONB | Opening and closing times |

**Example Data:**
```json
{
  "school_id": "660e8400-...",
  "language": "en",
  "currency": "INR",
  "date_format": "DD/MM/YYYY",
  "theme_primary_color": "#1E88E5",
  "working_days": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"],
  "school_timings": {
    "morning_assembly": "08:00",
    "school_start": "08:30",
    "lunch_break": "12:30-13:15",
    "school_end": "15:30"
  }
}
```

---

#### **Table: `school_announcements`**

News, updates, and notices for the school community.

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `school_id` | UUID | FK → platform.schools.id |
| `title` | String | Announcement title |
| `content` | Text | Full content (HTML/Markdown) |
| `category` | Enum | NEWS, EVENT, HOLIDAY, EXAM, GENERAL |
| `priority` | Enum | LOW, MEDIUM, HIGH, URGENT |
| `target_audience` | JSONB | Array: [STUDENTS, PARENTS, TEACHERS, STAFF] |
| `published_at` | DateTime | When published |
| `expires_at` | DateTime | When to remove from display |
| `is_pinned` | Boolean | Show at top |
| `attachments` | JSONB | Array of file URLs |
| `created_by` | UUID | User who created |

**Example Data:**
```json
{
  "title": "Annual Day Celebration - Jan 25th",
  "content": "We are excited to announce our Annual Day...",
  "category": "EVENT",
  "priority": "HIGH",
  "target_audience": ["STUDENTS", "PARENTS"],
  "published_at": "2024-01-10T10:00:00Z",
  "expires_at": "2024-01-26T00:00:00Z",
  "is_pinned": true,
  "attachments": [
    {
      "name": "Event_Schedule.pdf",
      "url": "https://cdn.smartsync.ai/schools/gvb/announcements/schedule.pdf"
    }
  ]
}
```

---

#### **Table: `school_contacts`**

Multiple contact persons with different roles.

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `school_id` | UUID | FK → platform.schools.id |
| `contact_type` | Enum | PRINCIPAL, ADMIN, ACCOUNTS, ADMISSIONS, SUPPORT |
| `name` | String | Contact person name |
| `designation` | String | Job title |
| `email` | String | Email address |
| `phone` | String | Phone number |
| `mobile` | String | Mobile number |
| `extension` | String | Office extension |
| `is_primary` | Boolean | Main contact for this type |
| `display_order` | Integer | Sort order on contact page |

---

#### **Table: `school_documents`**

Policy documents, handbooks, certificates.

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `school_id` | UUID | FK → platform.schools.id |
| `document_type` | Enum | PROSPECTUS, HANDBOOK, POLICY, CERTIFICATE, OTHER |
| `title` | String | Document name |
| `description` | Text | Document description |
| `file_url` | String | URL to file (Media Service) |
| `file_size_bytes` | Integer | File size |
| `file_type` | String | MIME type (application/pdf) |
| `version` | String | Version number (v1.0, v2.0) |
| `is_public` | Boolean | Show on public website |
| `uploaded_at` | DateTime | Upload timestamp |
| `uploaded_by` | UUID | User who uploaded |

---

#### **Table: `school_holidays`**

Academic calendar holidays and breaks.

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `school_id` | UUID | FK → platform.schools.id |
| `holiday_name` | String | Name of holiday |
| `holiday_type` | Enum | PUBLIC_HOLIDAY, SCHOOL_HOLIDAY, OPTIONAL |
| `start_date` | Date | Holiday start date |
| `end_date` | Date | Holiday end date |
| `description` | Text | Additional details |
| `applies_to` | JSONB | Array: [STUDENTS, TEACHERS, STAFF] |

---

## 3. Media Service (Files & Images)

### **Purpose:**
Centralized storage for all media assets (images, documents, videos).

### **Tables:**

#### **Table: `media_files`**

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `school_id` | UUID | Soft FK → platform.schools.id |
| `tenant_id` | UUID | Soft FK for multi-tenancy |
| `file_name` | String | Original filename |
| `file_path` | String | S3/CDN path |
| `file_url` | String | Public CDN URL |
| `file_size_bytes` | Integer | Size in bytes |
| `mime_type` | String | application/pdf, image/png, etc. |
| `file_category` | Enum | SCHOOL_LOGO, BANNER, DOCUMENT, GALLERY, PROFILE_PHOTO |
| `uploaded_by` | UUID | User who uploaded |
| `is_public` | Boolean | Publicly accessible |

#### **Storage Structure:**
```
s3://smartsync-media-prod/
  └── schools/
      └── {school_id}/
          ├── branding/
          │   ├── logo.png
          │   ├── banner.jpg
          │   └── favicon.ico
          ├── announcements/
          │   └── event_schedule.pdf
          ├── documents/
          │   ├── prospectus_2024.pdf
          │   └── handbook.pdf
          ├── gallery/
          │   ├── annual_day_2023/
          │   │   ├── photo1.jpg
          │   │   └── photo2.jpg
          └── profiles/
              ├── students/
              └── staff/
```

---

## 4. Other Services (Domain-Specific Data)

### **Academic Service**
- Class structure (grades, sections)
- Subjects and curriculum
- Exam schedules
- Student enrollment data

### **Finance Service**
- Fee structure
- Fee categories
- Payment plans
- Invoice templates

### **HR Service**
- Staff directory
- Department structure
- Salary structure
- Employee details

### **Hostel Service**
- Hostel building details
- Room allocation
- Mess menu

### **Transport Service**
- Bus routes
- Vehicle details
- Driver information

---

## Data Flow: School Onboarding

### **Step 1: Platform Service (After Subscription Purchase)**

```http
POST /api/v1/tenants/{tenant_id}/schools
{
  "name": "Green Valley Bangalore",
  "code": "GVB",
  "subdomain": "greenvalley-bangalore",
  "email": "admin@greenvalley.edu",
  "phone_number": "+91-80-12345678",
  "address": "123 School Street",
  "city": "Bangalore",
  "timezone": "Asia/Kolkata"
}
```

**Platform Service:**
1. Creates school in `schools` table
2. Creates subscription in `school_subscriptions`
3. Publishes `SchoolCreated` event

---

### **Step 2: Admin Service (Event Consumer)**

**Listens to `SchoolCreated` event:**

```python
@event_handler("SchoolCreated")
async def handle_school_created(event):
    school_id = event["school_id"]
    
    # Create school profile with defaults
    school_profile = SchoolProfile(
        school_id=school_id,
        tenant_id=event["tenant_id"],
        motto="",
        vision="",
        mission="",
        establishment_year=None
    )
    db.add(school_profile)
    
    # Create default settings
    school_settings = SchoolSettings(
        school_id=school_id,
        language="en",
        currency="INR",
        date_format="DD/MM/YYYY",
        theme_primary_color="#1E88E5"
    )
    db.add(school_settings)
    
    db.commit()
```

---

### **Step 3: School Admin Updates Profile**

```http
PUT /api/v1/admin/schools/{school_id}/profile
{
  "motto": "Knowledge is Power",
  "vision": "To be a center of excellence...",
  "mission": "Provide quality education...",
  "establishment_year": 1995,
  "principal_name": "Dr. Rajesh Kumar"
}
```

```http
POST /api/v1/media/upload
Content-Type: multipart/form-data

{
  "school_id": "660e8400-...",
  "file": <logo.png>,
  "category": "SCHOOL_LOGO"
}

Response:
{
  "file_url": "https://cdn.smartsync.ai/schools/gvb/branding/logo.png"
}
```

```http
PUT /api/v1/admin/schools/{school_id}/profile
{
  "logo_url": "https://cdn.smartsync.ai/schools/gvb/branding/logo.png"
}
```

---

## API Design: School Profile Management

### **Admin Service APIs:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/schools/{school_id}/profile` | Get school profile |
| PUT | `/api/v1/admin/schools/{school_id}/profile` | Update school profile |
| GET | `/api/v1/admin/schools/{school_id}/settings` | Get school settings |
| PUT | `/api/v1/admin/schools/{school_id}/settings` | Update school settings |
| POST | `/api/v1/admin/schools/{school_id}/announcements` | Create announcement |
| GET | `/api/v1/admin/schools/{school_id}/announcements` | List announcements |
| POST | `/api/v1/admin/schools/{school_id}/contacts` | Add contact person |
| GET | `/api/v1/admin/schools/{school_id}/contacts` | List contact persons |
| POST | `/api/v1/admin/schools/{school_id}/documents` | Upload document |
| GET | `/api/v1/admin/schools/{school_id}/documents` | List documents |

---

## Summary: Who Owns What?

| Data Type | Service | Reason |
|-----------|---------|--------|
| **Subscription limits** | Platform Service | Billing & access control |
| **School basic info** | Platform Service | Identity & routing |
| **School branding** | Admin Service | Operations & presentation |
| **School settings** | Admin Service | Configuration management |
| **Announcements** | Admin Service | Operational communication |
| **Contact persons** | Admin Service | School directory |
| **Policy documents** | Admin Service | Operational docs |
| **Logo/images (files)** | Media Service | Centralized media storage |
| **Academic structure** | Academic Service | Domain-specific |
| **Fee structure** | Finance Service | Domain-specific |
| **Staff details** | HR Service | Domain-specific |

---

## Key Principles

1. ✅ **Platform Service** = Subscription, billing, access control
2. ✅ **Admin Service** = School operations, configuration, presentation
3. ✅ **Media Service** = Files, images, documents (actual storage)
4. ✅ **Domain Services** = Domain-specific operational data
5. ✅ **No data duplication** - Each service owns its domain
6. ✅ **Event-driven sync** - Services communicate via events
7. ✅ **Soft FKs** - Cross-service references use soft foreign keys

---

**End of Document**


Key Recommendation:
Store in-depth school details (logo, motto, vision, announcements, settings) in Admin Service , not Platform Service. Platform Service only handles subscription and basic identity info.

Both documents are production-ready and follow best practices! 🎉

Compact c