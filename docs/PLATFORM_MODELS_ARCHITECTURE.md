# Platform Service Models Architecture Documentation

## Overview
Comprehensive multi-tenant SaaS subscription platform for educational institutions with 9 interconnected models supporting multi-family plans, usage tracking, billing, and audit trails.

---

## 1. Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                    TENANT (Organization)                           │
│    - name, code, type, slug, website, status                      │
│    - Types: SINGLE_SCHOOL, SCHOOL_GROUP, GOVERNMENT_BLOCK         │
└────────────────┬─────────────────────────────────────────────────┘
                 │ 1-to-many
                 ├──────────────────┐
                 │                  │
      ┌──────────▼─────────┐    ┌────▼──────────────────┐
      │    SCHOOL          │    │ SchoolSubscription    │
      │ (Campus/Location)  │    │ (Purchase Record)     │
      │                    │    │                       │
      │ - name, code       │    │ - plan_id, status     │
      │ - subdomain        │    │ - selected_max_users  │
      │ - address, city    │    │ - effective_max_users │
      │ - timezone         │    │ - tenure_months       │
      │ - board_type       │    │ - start/end_date      │
      │ - academic_year    │    │ - active_modules      │
      │                    │    │ - auto_renewal        │
      └──────────┬─────────┘    └────┬──────────────────┘
                 │                   │ 1-to-1
                 │ 1-to-many         │
                 │ 1-to-1    ┌───────▼──────────────────────┐
      ┌──────────▼──────────┐│ SchoolSubscriptionPricing    │
      │   SCHOOL_DOMAIN     ││ (Financial Breakdown)        │
      │ (Domain/Portal)     ││                              │
      │                     ││ - base_price_paise           │
      │ - domain (URL)      ││ - discount_amount_paise      │
      │ - is_custom_domain  ││ - tax_amount_paise           │
      │ - status            ││ - final_amount_paise         │
      │ - verified_at       ││ - tenure_discount_percent    │
      └─────────────────────┘└──────────────────────────────┘
                                      │
                                      │ 1-to-many
                                      │
              ┌───────────────────────▼─────────────────┐
              │ SchoolSubscriptionHistory               │
              │ (Immutable Audit Log)                   │
              │                                         │
              │ - change_type (enum)                   │
              │ - previous_* & new_* (snapshots)       │
              │ - changed_by_user_id, changed_by_type  │
              │ - change_reason, changed_at            │
              └─────────────────────────────────────────┘

      ┌─────────────────────────────┐
      │ SUBSCRIPTION_PLAN           │
      │ (Product Catalog - 4-5 rows)│
      │                             │
      │ - name, code, family        │
      │ - variant (ENTRY/SCALABLE)  │
      │ - fixed_max_users           │
      │ - base_price_paise          │
      │ - per_user_increment        │
      │ - tenure_discounts (JSONB)  │
      │ - included_modules (JSONB)  │
      │ - tax_percent               │
      └──────────────┬──────────────┘
                     │ Referenced by
                     │
              SchoolSubscription

      ┌──────────────────────────────┐
      │ BillingInvoice               │
      │ (Formal Invoice)             │
      │                              │
      │ - invoice_number             │
      │ - billing_period_start/end   │
      │ - subtotal, discount, tax    │
      │ - total_amount_paise         │
      │ - status, paid_at            │
      └──────────────────────────────┘

      ┌──────────────────────────────────┐
      │ SubscriptionUsageSnapshot        │
      │ (Monthly Usage Tracking)         │
      │                                  │
      │ - subscription_id                │
      │ - snapshot_date                  │
      │ - student_count, user_count      │
      │ - used_storage_gb                │
      └──────────────────────────────────┘

      ┌────────────────────────────────┐
      │ TenantFeatureFlag              │
      │ (Granular Feature Toggles)     │
      │                                │
      │ - tenant_id                    │
      │ - feature_key                  │
      │ - is_enabled                   │
      │ - metadata (JSONB)             │
      └────────────────────────────────┘
```

---

## 2. Entity Relationships & Model Details

### Tenant (Parent Organization)
**Role:** Customer organization that owns one or more schools

**Relationships:**
- `schools` (1-to-many) → School instances [CASCADE delete]
- `subscriptions` (1-to-many) → SchoolSubscriptions (denormalized for reporting)
- `feature_flags` (1-to-many) → TenantFeatureFlags (feature toggles)

**Key Enums:**
- `TenantStatus`: ACTIVE, INACTIVE, ARCHIVED
- `TenantType`: SINGLE_SCHOOL, SCHOOL_GROUP, GOVERNMENT_BLOCK

**Key Fields:**
- `name` (String, 255): Organization name, indexed
- `code` (String, 50): Unique code identifier, indexed
- `type` (Enum): Organizational structure type
- `slug` (String, 100): URL-friendly identifier, unique, indexed
- `website` (String, 255): Organization website URL
- `status` (Enum, indexed): Operational status

---

### School (Physical Campus/Location)
**Role:** Individual school location within tenant; billing boundary

**Relationships:**
- `tenant` (many-to-1) → Parent Tenant [CASCADE delete]
- `subscriptions` (1-to-many) → SchoolSubscriptions
- `domain` (1-to-1) → SchoolDomain [CASCADE delete]

**Key Enums:**
- `SchoolStatus`: TRIAL, ACTIVE, INACTIVE, SUSPENDED, CANCELLED, ARCHIVED
- `BoardType`: CBSE, ICSE, STATE, IB, IGCSE, OTHER

**Key Fields:**
- `tenant_id` (UUID): Foreign key to parent tenant, indexed
- `name` (String, 255): School name, indexed
- `code` (String, 50): School identifier within tenant
- `subdomain` (String, 100): Unique portal subdomain, indexed
- `board` (Enum): Educational board/curriculum type
- `email`, `phone_number`, `address`, `city`, `state`, `country`: Contact info
- `pincode` (String, 20): Postal code
- `timezone` (String): Default Asia/Kolkata
- `academic_year_start_month` (Integer): Month 1-12 when academic year starts
- `status` (Enum, indexed): Operational status

**Constraints:**
- Unique: `subdomain`
- Compound Unique: `(tenant_id, code)` - code unique per tenant

---

### SchoolSubscription (Purchase/Billing Record)
**Role:** Represents one subscription period for a school; snapshot of what was purchased

**Relationships:**
- `tenant_id` (denormalized, indexed): Tenant for efficient billing queries
- `school_id` (indexed): Which school (billing boundary at school level)
- `plan` (many-to-1) → SubscriptionPlan [RESTRICT delete]
- `pricing` (1-to-1) → SchoolSubscriptionPricing (separated for audit trail)
- `history` (1-to-many) → SchoolSubscriptionHistory (append-only event log)
- `previous_subscription_id`: Links to prior subscription (for chaining)

**Key Enums:**
- `SubscriptionStatus`: FREE_TRIAL, ACTIVE, GRACE, EXPIRED, SUSPENDED, CANCELLED, ARCHIVED
- `TenureMonths`: 1, 3, 6, 12, 24, 36 months
- `SubscriptionChangeType`: TRIAL_STARTED, TRIAL_CONVERTED, ACTIVATED, RENEWED, UPGRADED, DOWNGRADED, SUSPENDED, CANCELLED, etc.

**Key Column Groups:**

1. **Plan Selection:**
   - `plan_id` (UUID): Reference to subscription plan
   - `selected_max_users` (Integer): User count chosen by platform team (scalable plans only)
   - `effective_max_users` (Integer): Computed = selected_max_users OR plan.fixed_max_users
   - `tenure_months` (Enum): Subscription duration (1/3/6/12/24/36 months)

2. **Validity Period:**
   - `start_date`, `end_date` (Date): Subscription validity
   - `grace_period_end_date` (Date): Extra access after end_date (typically +15 days)
   - `auto_renewal` (Boolean): Auto-renew at end_date if payment collected
   - `next_renewal_date` (Date): When renewal should be initiated

3. **Module & Add-ons:**
   - `active_modules` (JSONB): Snapshot of included modules for this period
   - `active_add_ons` (JSONB): Optional purchased add-on modules

4. **Payment & Contract:**
   - `contract_file_id`, `po_number`: Contract documentation
   - `payment_reference`, `payment_method`: Payment tracking
   - `account_manager_user_id`: Internal owner of this deal

5. **Suspension/Cancellation:**
   - `suspended_at`, `suspension_reason`
   - `cancelled_at`

**State Machine:**
```
FREE_TRIAL ──[on payment]──► ACTIVE
   │
   └──[trial expires]───► EXPIRED
   
ACTIVE ──[end_date reached]──► GRACE ──[grace expires]──► EXPIRED
   │                            │
   │                            └──[payment received]──► ACTIVE
   │
   ├──[payment fails]──► GRACE
   │
   ├──[manual action]──► SUSPENDED ──[payment received]──► ACTIVE
   │
   └──[cancellation]──► CANCELLED ──[after retention]──► ARCHIVED
```

---

### SchoolSubscriptionPricing (Financial Breakdown)
**Role:** Immutable snapshot of pricing calculation for a subscription

**Relationships:**
- `subscription_id` (1-to-1) → SchoolSubscription (can't be modified once created)

**Key Fields:**
- `base_price_at_selection_paise` (Numeric): Base price at selected user count
- `tenure_discount_percent` (Numeric): Discount applied for tenure length
- `discount_amount_paise`: Calculated discount
- `subtotal_paise`: Price after discount
- `tax_amount_paise`: GST/tax
- `final_amount_paise`: Total invoice amount
- `currency`: INR (default)

**Pricing Calculation Flow:**
```
base_price = plan.base_price_paise 
           + (selected_users - min_users) / step × plan.per_user_increment_paise

discount = base_price × (tenure_discount % / 100)
subtotal = base_price - discount
tax = subtotal × (plan.tax_percent / 100)
final_amount = subtotal + tax
```

---

### SchoolSubscriptionHistory (Immutable Audit Log)
**Role:** Complete event log of every subscription state transition

**Relationships:**
- `school_id` (indexed): Soft FK to school (for per-school history queries)
- `tenant_id` (indexed): Denormalized for tenant-level reporting
- `subscription_id` (ForeignKey): The NEW subscription row created by this change
- `previous_subscription_id`: The OLD subscription row before this change

**Change Events Logged:**
- TRIAL_STARTED, TRIAL_CONVERTED, TRIAL_EXPIRED
- ACTIVATED, RENEWED, UPGRADED, DOWNGRADED
- TENURE_CHANGED, EXTENDED
- SUSPENDED, REACTIVATED, CANCELLED, EXPIRED

**Snapshot Fields (Before/After):**
- `previous_plan_code`, `new_plan_code`
- `previous_status`, `new_status`
- `previous_max_users`, `new_max_users`
- `previous_tenure_months`, `new_tenure_months`
- `previous_end_date`, `new_end_date`
- `previous_final_amount_paise`, `new_final_amount_paise`

**Audit Trail:**
- `changed_by_user_id`: SmartSync user who made the change (NULL for system)
- `changed_by_type`: PLATFORM_ADMIN, SYSTEM, SCHOOL_ADMIN
- `change_reason`: Human-readable reason for the change
- `changed_at` (DateTime, indexed): Exact UTC timestamp

**Key Property:** Append-only (never updated/deleted), enables point-in-time state reconstruction

---

### SchoolDomain (Portal Access & SSL)
**Role:** Manages custom domains and subdomains for school portals

**Relationships:**
- `school_id` (many-to-1) → School [CASCADE delete]

**Key Enums:**
- `DomainStatus`: PENDING_VERIFICATION, VERIFIED, FAILED, DISABLED

**Key Fields:**
- `domain` (String, 255): Fully qualified domain, unique, indexed
- `is_custom_domain` (Boolean): True for custom domains, False for smartsync subdomains
- `status` (Enum, indexed): Domain verification status
- `verified_at` (DateTime): Timestamp of verification

**Constraints:**
- Unique `domain`
- Compound Unique: `(school_id)` - only one domain per school

**Status Flow:**
```
PENDING_VERIFICATION ──[DNS verified]──► VERIFIED
                   ──[verification failed]──► FAILED ──[retry]──► PENDING_VERIFICATION
                   
VERIFIED ──[expiry or manual]──► DISABLED
```

---

### SubscriptionPlan (Product Catalog)
**Role:** Master product definition; created by platform team (4-5 rows total)

**Relationships:**
- `subscriptions` (1-to-many, inverse) ← SchoolSubscription

**Key Enums:**
- `PlanFamily`: CORE (A-series), GROWTH (B-series)
- `PlanVariant`: ENTRY (fixed users), SCALABLE (selected users)
- `Currency`: INR (default)

**Plan Family Breakdown:**
```
CORE Family (A-series) — Smaller schools (up to ~5500 users)
├── A1: ENTRY    → fixed_max_users = 500 (no selection)
└── A2: SCALABLE → selected from: 1500, 2500, 3500, 4500, 5500

GROWTH Family (B-series) — Larger schools (up to ~5000 users)
├── B1: ENTRY    → fixed_max_users = 1000 (no selection)
└── B2: SCALABLE → selected from: 2000, 3000, 4000, 5000
```

**Key Fields:**

1. **Plan Identity:**
   - `name`, `code` (unique): Display name and machine identifier
   - `family` (Enum): CORE or GROWTH
   - `variant` (Enum): ENTRY or SCALABLE
   - `description`, `is_publicly_listed`: Marketing info

2. **User Count Configuration:**
   - `fixed_max_users` (Integer): For ENTRY plans (A1=500, B1=1000), NULL for SCALABLE
   - Allowed user counts defined in `plan_constants.py` (enums)

3. **Pricing:**
   - `base_price_paise` (Numeric): Base price at minimum user tier
   - `per_user_increment_paise` (Numeric): Incremental price per user step
   - `tenure_discounts` (JSONB): Discount % for each tenure ({"1": 0, "12": 15.00, "24": 20.00})
   - `tax_percent` (Numeric): Default 18% for India GST

4. **Features & Limits:**
   - `included_modules` (JSONB): Modules included in plan
   - `module_add_ons` (JSONB): Optional paid add-ons
   - `trial_days` (Integer): Free trial duration

**Constraints:**
- Unique: `code`, `name`
- Compound Unique: `(family, variant)` - only one plan per family+variant combination
- CheckConstraint: ENTRY plans must have fixed_max_users; SCALABLE must have NULL

---

### BillingInvoice (Formal Invoice Record)
**Role:** Formal invoice raised for tenant's subscription

**Relationships:**
- `tenant_id`: Which tenant/organization
- `subscription_id`: Which subscription this invoice covers

**Key Enums:**
- `InvoiceStatus`: DRAFT, SENT, PAID, OVERDUE, PARTIALLY_PAID, WAIVED, REFUNDED, VOID

**Key Fields:**
- `invoice_number` (String, unique): Human-readable identifier (e.g., SS-INV-2024-00001)
- `invoice_date`, `due_date`: Invoice and payment due dates
- `billing_period_start`, `billing_period_end`: Period covered
- `subtotal_paise`, `discount_paise`, `tax_amount_paise`, `total_amount_paise`: Amount breakdown
- `tax_rate_percent`: GST rate (default 18%)
- `status`: Payment status
- `paid_at`, `paid_amount_paise`: Payment tracking
- `billed_student_count`, `billed_user_count`: Usage snapshot

**GST Fields (India-specific):**
- `gstin_of_tenant`: Tenant's GST ID
- `hsn_sac_code`: Service classification (default 9984 for software services)
- `place_of_supply`: State for GST calculation

---

### SubscriptionUsageSnapshot (Monthly Usage Tracking)
**Role:** Records actual usage (student count, user count, storage) for billing calculations

**Key Fields:**
- `subscription_id`: Which subscription
- `snapshot_date` (Date): Month for which usage is recorded
- `student_count`, `user_count`: Active users/students
- `used_storage_gb`: Storage consumed
- `notes`: Optional notes

**Purpose:** Used for per-student/per-user billing and quota enforcement

---

### TenantFeatureFlag (Granular Feature Toggles)
**Role:** Enable/disable specific features per tenant independently

**Key Fields:**
- `tenant_id`: Which tenant
- `feature_key` (String): Feature identifier (e.g., "ADVANCED_REPORTING")
- `is_enabled` (Boolean): Feature enabled state
- `metadata` (JSONB): Additional configuration
- `valid_from`, `valid_until` (DateTime): Temporal validity

**Use Cases:**
- Early access features for specific tenants
- Temporary overrides during support
- A/B testing
- Custom enterprise features

---

## 3. Data Flow & Scenario Examples

### Scenario 1: Single School Organization with Trial → Paid Conversion
```
1. Tenant Creation:
   - Tenant: "ABC Public School" (SINGLE_SCHOOL, ACTIVE)

2. School Creation:
   - School: "ABC Public School, Mumbai"
   - Status: TRIAL
   - Subdomain: abc-ps
   - Board: CBSE

3. Free Trial Starts:
   - SchoolSubscription created:
     * Plan: FREE_TRIAL (no pricing)
     * Status: FREE_TRIAL
     * start_date: Today
     * end_date: Today + 14 days
     * tenure_months: NULL (trial duration from plan)
   
   - SchoolSubscriptionHistory entry:
     * change_type: TRIAL_STARTED
     * new_status: FREE_TRIAL

4. Trial Conversion (after 10 days):
   - Platform team selects: Plan A2 (Core Scalable), 2500 users, 12 months
   
   - SchoolSubscriptionPricing calculated:
     * base_price = plan.base_price (1,00,000)
                  + (2500 - 1500) / 1000 × plan.per_user_increment (50,000)
                  = 1,50,000 paise
     * tenure_discount = 15% (for 12 months)
     * discount_amount = 1,50,000 × 15% = 22,500
     * subtotal = 1,27,500
     * tax (18%) = 22,950
     * final_amount = 1,50,450
   
   - New SchoolSubscription row created:
     * Plan: A2
     * Status: ACTIVE
     * selected_max_users: 2500
     * effective_max_users: 2500
     * tenure_months: 12
     * start_date: Today
     * end_date: Today + 365 days
     * previous_subscription_id: (old trial row)
   
   - Old trial subscription row status → EXPIRED
   
   - SchoolSubscriptionHistory entry:
     * change_type: TRIAL_CONVERTED
     * previous_status: FREE_TRIAL
     * new_status: ACTIVE
     * previous_plan_code: NULL
     * new_plan_code: A2
     * new_final_amount_paise: 1,50,450

5. Domain Setup:
   - SchoolDomain created:
     * domain: abc-ps.smartsync.ai
     * is_custom_domain: False
     * status: VERIFIED
```

### Scenario 2: Multi-School Organization (School Group)
```
Tenant: "Green Valley Education Group" (SCHOOL_GROUP)
├── School 1: "Green Valley, Bangalore"
│   ├── SchoolSubscription: Plan B2, 4000 users, 24 months, ACTIVE
│   ├── Pricing: Base 2,50,000 + (3×50,000) = 4,00,000
│   │          - Discount (20% for 24mo): 80,000
│   │          - Subtotal: 3,20,000
│   │          - Tax (18%): 57,600
│   │          - Final: 3,77,600
│   └── SchoolDomain: gv-blr.smartsync.ai
│
└── School 2: "Green Valley, Hyderabad"
    ├── SchoolSubscription: Plan A2, 1500 users, 12 months, ACTIVE
    ├── Pricing: Base 1,00,000 + (0×50,000) = 1,00,000
    │          - Discount (15% for 12mo): 15,000
    │          - Subtotal: 85,000
    │          - Tax (18%): 15,300
    │          - Final: 1,00,300
    └── SchoolDomain: gv-hyd.smartsync.ai
```

### Scenario 3: Subscription Upgrade
```
1. Current State:
   - SchoolSubscription: Plan A2, 2500 users, ACTIVE
   - end_date: Jan 31, 2025
   - final_amount: 1,50,450

2. School Requests Upgrade (mid-term):
   - Decision: Upgrade to Plan B2, 3500 users
   
3. Platform Creates New Row:
   - New SchoolSubscription:
     * Plan: B2
     * selected_max_users: 3500
     * start_date: Today (Oct 15, 2024)
     * end_date: Jan 31, 2025 (original end date preserved)
     * tenure_months: 3 (pro-rated remainder)
   
4. Proration Calculation:
   - Months remaining: 3.5 (Oct 15 - Jan 31)
   - New plan monthly price: (2,50,000 - 15,000) / 12 = 19,583
   - Credit from old plan: (remaining days × old daily rate)
   - Charge for upgrade: New plan - credit
   
5. Old Subscription Status → EXPIRED
   
6. History Entry:
   - change_type: UPGRADED
   - previous_plan_code: A2
   - new_plan_code: B2
   - previous_max_users: 2500
   - new_max_users: 3500

7. History shows complete upgrade chain:
   OLD → UPGRADED → NEW
```

### Scenario 4: Payment Failure & Grace Period
```
1. Subscription Ends:
   - SchoolSubscription.end_date: Aug 31, 2024
   - Status: ACTIVE
   - auto_renewal: True
   - grace_period_end_date: Sep 15, 2024

2. Renewal Initiated (30 days before end_date):
   - next_renewal_date: Aug 1, 2024
   - Invoice generated
   - Payment reminder sent

3. Aug 31: Auto-renewal triggered, payment fails:
   - Status → GRACE
   - grace_period_end_date: Sep 15, 2024
   - School retains full access
   
   - History entry:
     * change_type: (internal state change, not added to history)

4. Sep 5: Manual payment received:
   - Payment webhook received
   - Status → ACTIVE (back to normal)
   - New SchoolSubscription row created for new period
   - Old row status → EXPIRED
   
   - History entries:
     * change_type: RENEWED
     * changed_by_type: SYSTEM (payment webhook)

5. Sep 15 would have been suspension if no payment

6. Current History Log:
   - TRIAL_STARTED (Day 1)
   - TRIAL_CONVERTED (Day 14)
   - RENEWED (Aug 31)
   - RENEWED (Sep 5)
```

### Scenario 5: Billing Calculation with Add-ons
```
1. Base Plan: A2, 2500 users, 12 months
   - Base: 1,50,000
   - Discount (15%): -22,500
   - Subtotal: 1,27,500

2. Add-on: Hostel Module, 50,000/month
   - 12 months: 6,00,000
   - Total add-on: 6,00,000

3. Grand Total Before Tax:
   - Plan: 1,27,500
   - Add-ons: 6,00,000
   - Subtotal: 7,27,500

4. Tax (18%):
   - Tax: 1,30,950

5. Final Invoice:
   - total_amount_paise: 8,58,450
   - monthly_effective_charge: 8,58,450 / 12 = 71,537.50

6. SchoolSubscriptionPricing records:
   - base_price_at_selection_paise: 1,50,000
   - discount_amount_paise: 22,500
   - add_ons_total_paise: 6,00,000
   - subtotal_paise: 7,27,500
   - tax_amount_paise: 1,30,950
   - final_amount_paise: 8,58,450
```

---

## 4. Database Design Details

### Plan Constants & Selection Options (`plan_constants.py`)

**Plan Family Structure:**
```python
PlanFamily (Enum):
  - CORE   = "CORE"    # A-series plans
  - GROWTH = "GROWTH"  # B-series plans

PlanVariant (Enum):
  - ENTRY    = "ENTRY"      # Fixed user count
  - SCALABLE = "SCALABLE"   # User count selected from list
```

**Selectable User Counts:**
```python
CoreScalableUserCount:
  USERS_1500 = 1500
  USERS_2500 = 2500
  USERS_3500 = 3500
  USERS_4500 = 4500
  USERS_5500 = 5500

GrowthScalableUserCount:
  USERS_2000 = 2000
  USERS_3000 = 3000
  USERS_4000 = 4000
  USERS_5000 = 5000

CoreEntryUserCount: 500 (A1, fixed)
GrowthEntryUserCount: 1000 (B1, fixed)
```

**Selectable Tenures:**
```python
TenureMonths (Enum):
  ONE_MONTH     = 1
  THREE_MONTHS  = 3
  SIX_MONTHS    = 6
  TWELVE_MONTHS = 12
  TWENTY_FOUR   = 24
  THIRTY_SIX    = 36
```

---

### Database Schema Summary

| Model | Table Name | Primary Key | Key Indexes |
|-------|-----------|------------|-----------|
| Tenant | tenants | id (UUID) | name, code, slug, status, type |
| School | schools | id (UUID) | tenant_id, code, subdomain, status |
| SchoolSubscription | school_subscriptions | id (UUID) | school_id, plan_id, status, start_date, end_date |
| SchoolSubscriptionPricing | school_subscription_pricing | id (UUID) | subscription_id |
| SchoolSubscriptionHistory | school_subscription_history | id (UUID) | school_id, tenant_id, subscription_id, change_type, changed_at |
| SchoolDomain | school_domains | id (UUID) | school_id, domain, status |
| SubscriptionPlan | subscription_plans | id (UUID) | code, name, family, variant, is_active |
| BillingInvoice | billing_invoices | id (UUID) | tenant_id, subscription_id, invoice_number, status |
| SubscriptionUsageSnapshot | subscription_usage_snapshots | id (UUID) | subscription_id, snapshot_date |
| TenantFeatureFlag | tenant_feature_flags | id (UUID) | tenant_id, feature_key |

---

### Soft Delete & Audit Trail

**All Models Inherit from BaseModel:**
- `id`: UUID primary key (client-side generated)
- `is_deleted`: Soft delete flag (default False)
- `deleted_at`: Timestamp of soft delete
- `deleted_by`: user_id who performed delete
- `created_at`: Server-side timestamp
- `updated_at`: Auto-update on row changes
- `created_by`: user_id who created row
- `updated_by`: user_id who last modified row

**Query Pattern:**
```python
# Always filter active records
select(School).where(School.is_deleted == False)

# To recover deleted records
select(School).where(School.is_deleted == True)
```

---

## 5. Key Features & Constraints

### Unique Constraints
1. `tenants.code` — Tenant organization code
2. `tenants.slug` — Tenant URL slug
3. `schools.subdomain` — Portal subdomain (globally unique)
4. `schools.(tenant_id, code)` — School code unique per tenant
5. `school_domains.domain` — Domain globally unique
6. `school_domains.(school_id)` — One domain per school
7. `subscription_plans.(family, variant)` — Plan uniqueness
8. `subscription_plans.code` — Plan machine identifier
9. `billing_invoices.invoice_number` — Invoice document number
10. `tenant_feature_flags.(tenant_id, feature_key)` — One flag per tenant per feature

### Foreign Key Constraints
1. `schools.tenant_id` → `tenants.id` [CASCADE delete]
2. `school_subscriptions.plan_id` → `subscription_plans.id` [RESTRICT delete]
3. `school_subscriptions.previous_subscription_id` → `school_subscriptions.id` [SET NULL]
4. `school_subscription_pricing.subscription_id` → `school_subscriptions.id`
5. `school_subscription_history.subscription_id` → `school_subscriptions.id` [SET NULL]
6. `school_domains.school_id` → `schools.id` [CASCADE delete]
7. `billing_invoices.tenant_id` → `tenants.id`
8. `billing_invoices.subscription_id` → `school_subscriptions.id`
9. `subscription_usage_snapshots.subscription_id` → `school_subscriptions.id`
10. `tenant_feature_flags.tenant_id` → `tenants.id`

### Check Constraints
1. **subscription_plans**: 
   - ENTRY plans MUST have `fixed_max_users` NOT NULL
   - SCALABLE plans MUST have `fixed_max_users` NULL
2. **school_subscriptions**: User count validation handled in application layer with enums

### Partial Unique Indexes (Application-Enforced)
- Only ONE active subscription (status IN FREE_TRIAL, ACTIVE, GRACE, SUSPENDED) per school at a time
- Enforced by application logic during subscription creation

---

## 6. API & Service Integration Patterns

### Getting a School's Current Subscription
```python
from sqlalchemy import select, and_

# Get active subscription
stmt = (
    select(SchoolSubscription)
    .where(
        and_(
            SchoolSubscription.school_id == school_id,
            SchoolSubscription.status.in_([
                SubscriptionStatus.FREE_TRIAL,
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.GRACE,
                SubscriptionStatus.SUSPENDED,
            ])
        )
    )
    .limit(1)
)
current_sub = session.execute(stmt).scalar()
```

### Checking Subscription Status & Quota
```python
def check_quota(subscription):
    """Verify if school is within usage limits"""
    return {
        "student_usage_percent": (
            subscription.active_student_count / 
            subscription.effective_max_users * 100
        ),
        "is_within_quota": (
            subscription.active_student_count <= 
            subscription.effective_max_users
        ),
        "days_until_expiry": (
            subscription.end_date - date.today()
        ).days,
        "grace_active": (
            subscription.status == SubscriptionStatus.GRACE
        ),
    }
```

### Creating Subscription with Pricing
```python
from decimal import Decimal
from datetime import date, timedelta

plan = session.execute(
    select(SubscriptionPlan).where(SubscriptionPlan.code == "A2")
).scalar_one()

selected_users = 2500
tenure_months = 12

# Calculate pricing
base_price = plan.base_price_paise + (
    (selected_users - 1500) // 1000 * plan.per_user_increment_paise
)
tenure_discount_percent = plan.tenure_discounts[str(tenure_months)]
discount_amount = base_price * tenure_discount_percent / 100
subtotal = base_price - discount_amount
tax_amount = subtotal * plan.tax_percent / 100
final_amount = subtotal + tax_amount

# Create subscription
subscription = SchoolSubscription(
    tenant_id=tenant_id,
    school_id=school_id,
    plan_id=plan.id,
    selected_max_users=selected_users,
    effective_max_users=selected_users,
    tenure_months=tenure_months,
    status=SubscriptionStatus.ACTIVE,
    start_date=date.today(),
    end_date=date.today() + timedelta(days=365),
    auto_renewal=True,
)
session.add(subscription)
session.flush()

# Create pricing snapshot
pricing = SchoolSubscriptionPricing(
    subscription_id=subscription.id,
    base_price_at_selection_paise=base_price,
    tenure_discount_percent=tenure_discount_percent,
    discount_amount_paise=discount_amount,
    subtotal_paise=subtotal,
    tax_amount_paise=tax_amount,
    final_amount_paise=final_amount,
    currency="INR",
)
session.add(pricing)

# Log history
history = SchoolSubscriptionHistory(
    school_id=school_id,
    tenant_id=tenant_id,
    subscription_id=subscription.id,
    change_type=SubscriptionChangeType.ACTIVATED,
    new_plan_code=plan.code,
    new_plan_name=plan.name,
    new_status=SubscriptionStatus.ACTIVE,
    new_max_users=selected_users,
    new_tenure_months=tenure_months,
    new_start_date=subscription.start_date,
    new_end_date=subscription.end_date,
    new_final_amount_paise=final_amount,
    changed_by_user_id=current_user_id,
    changed_by_type="PLATFORM_ADMIN",
    change_reason="New subscription activated",
)
session.add(history)
session.commit()
```

### Querying Subscription History
```python
# Get all changes for a school
stmt = (
    select(SchoolSubscriptionHistory)
    .where(SchoolSubscriptionHistory.school_id == school_id)
    .order_by(SchoolSubscriptionHistory.changed_at.asc())
)
history = session.execute(stmt).scalars()

# Get state at specific date
specific_date = date(2024, 8, 15)
stmt = (
    select(SchoolSubscriptionHistory)
    .where(
        and_(
            SchoolSubscriptionHistory.school_id == school_id,
            SchoolSubscriptionHistory.changed_at <= specific_date,
        )
    )
    .order_by(SchoolSubscriptionHistory.changed_at.desc())
    .limit(1)
)
snapshot = session.execute(stmt).scalar()
```

---

## 7. Summary & Model Statistics

### Total Models: 9

| Model | Purpose | Typical Record Count | Key Relationship |
|-------|---------|-------|-----------|
| Tenant | Customer organization | 100s | Parent of all schools |
| School | Physical campus/location | 1,000s | Billing boundary |
| SchoolSubscription | Active/historical subscription | 10,000s | One per period per school |
| SchoolSubscriptionPricing | Financial snapshot | 10,000s | 1-to-1 with subscription |
| SchoolSubscriptionHistory | Immutable audit log | 100,000s | 1-to-many with subscription |
| SchoolDomain | Domain mapping & SSL | 10,000s | 1-to-1 with school |
| SubscriptionPlan | Product catalog | 4-5 | Master reference (never deleted) |
| BillingInvoice | Formal invoice | 100,000s | Per-billing-cycle |
| SubscriptionUsageSnapshot | Monthly usage snapshot | 1,000,000s | Per-month per-subscription |
| TenantFeatureFlag | Feature toggles | 1,000s | Per-tenant per-feature |

### Enums Defined: 12

| Enum | Values | Location |
|------|--------|----------|
| TenantStatus | ACTIVE, INACTIVE, ARCHIVED | tenant.py |
| TenantType | SINGLE_SCHOOL, SCHOOL_GROUP, GOVERNMENT_BLOCK | tenant.py |
| SchoolStatus | TRIAL, ACTIVE, INACTIVE, SUSPENDED, CANCELLED, ARCHIVED | school.py |
| BoardType | CBSE, ICSE, STATE, IB, IGCSE, OTHER | school.py |
| DomainStatus | PENDING_VERIFICATION, VERIFIED, FAILED, DISABLED | school_domain.py |
| SubscriptionStatus | FREE_TRIAL, ACTIVE, GRACE, EXPIRED, SUSPENDED, CANCELLED, ARCHIVED | school_subscription.py |
| SubscriptionChangeType | 14 event types (TRIAL_STARTED, TRIAL_CONVERTED, ACTIVATED, RENEWED, UPGRADED, etc.) | school_subscription.py |
| InvoiceStatus | DRAFT, SENT, PAID, OVERDUE, PARTIALLY_PAID, WAIVED, REFUNDED, VOID | billing_and_flags.py |
| PlanFamily | CORE, GROWTH | plan_constants.py |
| PlanVariant | ENTRY, SCALABLE | plan_constants.py |
| CoreScalableUserCount | 1500, 2500, 3500, 4500, 5500 | plan_constants.py |
| GrowthScalableUserCount | 2000, 3000, 4000, 5000 | plan_constants.py |

### Key Metrics

- **Total Tables**: 10 (plus BaseModel)
- **Total Indexed Columns**: 40+
- **Total Unique Constraints**: 10+
- **Total Foreign Keys**: 10
- **Total Enums**: 12 with 70+ distinct values
- **Pricing Fields**: 6 (base, discount, subtotal, tax, total, currency)
- **Audit Trail Fields**: 8 per model (created_at/by, updated_at/by, deleted_at/by, is_deleted)

---

## 8. Performance Considerations

### Critical Indexes
- `schools(tenant_id, status)` — For finding active schools per tenant
- `school_subscriptions(school_id, status)` — For finding active subscription
- `school_subscriptions(plan_id)` — For finding subscribers to a plan
- `school_subscription_history(school_id, changed_at DESC)` — For history queries
- `billing_invoices(tenant_id, status)` — For invoice retrieval
- `subscription_usage_snapshots(subscription_id, snapshot_date DESC)` — For usage trends

### Query Optimization
1. **Subscription lookup**: Use partial unique index on (school_id) where status IN (FREE_TRIAL, ACTIVE, GRACE, SUSPENDED)
2. **History queries**: Always filter on `changed_at` range for date-based queries
3. **Billing reports**: Denormalize tenant_id on history & invoices to avoid multi-level joins
4. **Usage aggregation**: Snapshot table enables efficient monthly/yearly reporting without computing on-the-fly

### Archival Strategy
- SchoolSubscriptionHistory entries: Keep indefinitely (audit trail)
- BillingInvoice entries: Archive after 7 years (legal/tax requirement)
- SubscriptionUsageSnapshot entries: Aggregate after 3 years, keep summary tables

---

## 9. Security & Data Privacy

### Tenant Isolation
- Every query MUST filter by tenant_id (except for plans, which are global)
- No cross-tenant data queries allowed
- Hard FK constraints prevent orphaned rows

### Soft Deletion Strategy
- Records are never hard-deleted; soft delete with retention period
- Data can be recovered within retention period
- Automated purge job removes after retention expires (configurable)

### Audit Trail
- SchoolSubscriptionHistory is immutable (append-only)
- All user actions recorded with changed_by_user_id, changed_by_type, change_reason
- Timestamp auditing via created_at, updated_at fields

### PII Handling
- School contact info (email, phone) needs encryption at-rest
- Tenant info (name, website) may be public or private per org type
- Feature flags allow per-tenant privacy controls

---

## 10. Files in Platform Service

```
platform-service/
├── app/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                      # BaseModel (UUID, soft delete, audit trail)
│   │   ├── tenant.py                    # Tenant, TenantStatus, TenantType
│   │   ├── school.py                    # School, SchoolStatus, BoardType
│   │   ├── school_domain.py             # SchoolDomain, DomainStatus
│   │   ├── school_subscription.py       # SchoolSubscription, SubscriptionStatus, SubscriptionChangeType
│   │   ├── school_subscription_pricing.py  # SchoolSubscriptionPricing (separated from subscription)
│   │   ├── subscription_history.py      # SchoolSubscriptionHistory (immutable audit log)
│   │   ├── subscription_plan.py         # SubscriptionPlan
│   │   ├── billing_and_flags.py         # BillingInvoice, SubscriptionUsageSnapshot, TenantFeatureFlag
│   │   └── plan_constants.py            # PlanFamily, PlanVariant, user count options, tenure options
│   ├── db/
│   │   ├── __init__.py
│   │   └── ... (database connection, session management)
│   └── ... (services, routes, etc.)
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
└── requirements.txt
```

---

## 11. Related Documentation

- **[01-DOMAIN-ANALYSIS.md](01-DOMAIN-ANALYSIS.md)** — Business domain overview
- **[AUTH_USER_MODEL_ARCHITECTURE.md](AUTH_USER_MODEL_ARCHITECTURE.md)** — User/auth service integration
- **[PLATFORM-SERVICE-API-SPECIFICATION.md](PLATFORM-SERVICE-API-SPECIFICATION.md)** — API endpoints
- **[SCHOOL-DATA-STORAGE-ARCHITECTURE.md](SCHOOL-DATA-STORAGE-ARCHITECTURE.md)** — School data models

---

**Last Updated**: 2024-06-06  
**Schema Version**: 2.0  
**Status**: Active & Maintained
