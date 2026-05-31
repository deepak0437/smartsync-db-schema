# Platform Service Models Architecture Documentation

## Overview
Five interdependent models implementing a multi-tenant SaaS subscription platform for educational institutions.

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    TENANT (Organization)                │
│  - organization_name, organization_code, tenant_type   │
│  - website, status, slug                               │
│  - Types: SINGLE_SCHOOL, SCHOOL_GROUP, GOVT_BLOCK      │
└────────────────┬────────────────────────────────────────┘
                 │ 1-to-many
                 ├─────────────────┐
                 │                 │
      ┌──────────▼─────────┐  ┌─────▼──────────────────┐
      │    SCHOOL          │  │ SchoolSubscription     │
      │ (Campus/Location)  │  │ (Billing Instance)     │
      │                    │  │                        │
      │ - school_name      │  │ - start_date/end_date  │
      │ - subdomain        │  │ - status               │
      │ - address          │  │ - usage limits         │
      │ - timezone         │  │ - purchased counts     │
      │ - board_type       │  │ - active counts        │
      │ - email/phone      │  │ - billing amounts      │
      └──────────┬─────────┘  └─────────────────────────┘
                 │
                 │ 1-to-many
                 │
      ┌──────────▼──────────────┐
      │   SCHOOL_DOMAIN         │
      │ (Domain/Portal Access)  │
      │                         │
      │ - domain (URL)          │
      │ - is_primary            │
      │ - is_custom_domain      │
      │ - ssl_enabled           │
      │ - verification_status   │
      │ - ssl_provider          │
      └─────────────────────────┘

      ┌──────────────────────────┐
      │ SUBSCRIPTION_PLAN        │
      │ (Product Catalog)        │
      │                          │
      │ - name, code, tier       │
      │ - billing_cycle          │
      │ - pricing_model          │
      │ - base_price/per_student │
      │ - limits & features      │
      │ - modules/add-ons        │
      │ - display_order          │
      └──────────────────────────┘
            ▲
            │ Referenced by
            │
      SchoolSubscription
```

---

## 2. Entity Relationships

### Tenant (Parent Entity)
**Role:** Customer organization that owns one or more schools

**Relationships:**
- `schools` (1-to-many) → School instances
- `subscriptions` (1-to-many) → SchoolSubscriptions for reporting

**Key Enums:**
- `TenantStatus`: TRIAL → ACTIVE → SUSPENDED/CANCELLED → ARCHIVED
- `TenantType`: SINGLE_SCHOOL, SCHOOL_GROUP, GOVERNMENT_BLOCK, UNIVERSITY

**Columns:** 14 indexed fields (organization_name, code, slug, status, type)

---

### School (Child Entity)
**Role:** Physical campus or school location within a tenant

**Relationships:**
- `tenant` (many-to-1) → Parent Tenant [CASCADE delete]
- `subscriptions` (1-to-many) → SchoolSubscriptions
- `domains` (1-to-many) → SchoolDomains [CASCADE delete]

**Key Constraints:**
- Unique: `subdomain` (portal URL identifier)
- Compound Unique: `(tenant_id, school_code)` - code unique per tenant

**Key Enums:**
- `SchoolStatus`: ACTIVE, INACTIVE, ARCHIVED
- `BoardType`: CBSE, ICSE, STATE, IB, IGCSE, OTHER

**Columns:** 17 fields including address, contact, timezone, academic year

---

### SchoolSubscription (Bridge Entity)
**Role:** Links School → SubscriptionPlan, tracks usage and billing

**Relationships:**
- `tenant` (many-to-1) → Tenant [indexed, for reporting]
- `school` (many-to-1) → School
- `plan` (many-to-1) → SubscriptionPlan

**Key Enums:**
- `SubscriptionStatus`: TRIAL → ACTIVE → EXPIRED/SUSPENDED/CANCELLED

**Column Groups:**
1. **Purchased Limits** (what school bought):
   - purchased_student_count
   - purchased_user_count
   - purchased_role_count
   - purchased_storage_gb

2. **Active Counters** (current usage):
   - active_student_count
   - active_user_count
   - active_role_count
   - used_storage_gb

3. **Billing** (financial):
   - start_date, end_date, trial_ends_at
   - plan_amount, discount_amount, tax_amount, final_amount
   - amount_paid, currency (INR)
   - auto_renew flag

---

### SchoolDomain (Portal Access)
**Role:** Manages custom domains and subdomains for school portals

**Relationships:**
- `school` (many-to-1) → School [CASCADE delete]

**Key Features:**
- Primary domain indicator (one per school)
- Custom domain support (e.g., erp.greenvalleyschool.com)
- SSL/TLS provisioning tracking
- Domain verification with token-based validation
- Status: PENDING_VERIFICATION → VERIFIED or FAILED → DISABLED

**Key Enums:**
- `DomainStatus`: PENDING_VERIFICATION, VERIFIED, FAILED, DISABLED

**Columns:** 9 fields with SSL provider and verification tracking

---

### SubscriptionPlan (Master Catalog)
**Role:** Product definition - independent of tenant/school hierarchy

**Relationships:**
- `subscriptions` (1-to-many) → SchoolSubscriptions (reverse lookup)

**Key Enums:**
- `BillingCycle`: MONTHLY, QUARTERLY, ANNUAL
- `PlanTier`: FREE_TRIAL, STARTER, PROFESSIONAL, ENTERPRISE, GOVERNMENT, CUSTOM
- `PricingModel`: FLAT, PER_STUDENT, PER_USER, HYBRID

**Column Groups:**
1. **Identity**: name, code, tier, description, is_publicly_listed
2. **Billing**: billing_cycle, pricing_model
3. **Pricing**: base_price_paise, per_student_price_paise, per_user_price_paise, currency
4. **Limits**: max_students, max_teachers, max_total_users, max_roles, max_storage_gb, max_schools
5. **Features**: included_modules (JSON), module_add_ons (JSON), features (JSON)
6. **Trial & Display**: trial_days, display_order, is_active, highlight_text

---

## 3. Data Flow Examples

### Scenario 1: Single School Organization
```
Tenant: "ABC Public School" (SINGLE_SCHOOL)
  └─ School: "ABC Public School, Mumbai"
      ├─ SchoolSubscription: Professional tier, Rs 50,000/year
      ├─ SchoolDomain: abc.smartsync.ai (primary)
      └─ SchoolDomain: erp.abcschool.edu.in (custom)
```

### Scenario 2: Multi-School Organization
```
Tenant: "Green Valley Education" (SCHOOL_GROUP)
  ├─ School: "Green Valley, Bangalore"
  │   ├─ SchoolSubscription: Enterprise, Rs 2,00,000/year
  │   └─ SchoolDomain: gv-blr.smartsync.ai
  │
  └─ School: "Green Valley, Hyderabad"
      ├─ SchoolSubscription: Professional, Rs 50,000/year
      └─ SchoolDomain: gv-hyd.smartsync.ai
```

### Scenario 3: Billing Calculation
```
SubscriptionPlan "Enterprise": 
  - Base: Rs 1,00,000
  - Per-student: Rs 100
  - Per-user: Rs 500

School 1 purchases Enterprise for 500 students, 50 users:
SchoolSubscription calculation:
  plan_amount = 1,00,000 + (500 × 100) + (50 × 500) = 1,75,000
  discount_amount = 8,750 (5% promo)
  tax_amount = 26,587.50 (18% GST)
  final_amount = 1,93,837.50
```

---

## 4. Modifications Applied

### ✅ 1. Added Module-Level Docstrings

**Files Enhanced:**
- `tenant.py` - Multi-tenancy boundary explanation
- `school.py` - Billing per-school architecture
- `school_domain.py` - Portal access & SSL management
- `school_subscription.py` - Billing instance tracking
- `subscription_plan.py` - Product catalog design

**Content Includes:**
- Module purpose
- Architecture relationships (1-to-many, many-to-1)
- Usage patterns
- Key features

### ✅ 2. Fixed Missing Imports

**school.py:**
- ✅ Added `Integer` (for academic_year_start_month)
- ✅ Added `UniqueConstraint` (for compound unique constraint)

**school_domain.py:**
- ✅ Fixed `DateTime` import (was mixed with String)
- ✅ Added `UniqueConstraint` import
- ✅ Organized imports with proper grouping

**school_subscription.py:**
- ✅ All imports already correct

### ✅ 3. Fixed Code Organization Issues

**school_domain.py:**
- ❌ OLD: `__repr__` method placed BEFORE `__table_args__`
- ✅ NEW: Proper ordering: columns → relationships → __table_args__ → __repr__

**school_subscription.py:**
- ❌ OLD: Columns (plan_amount, discount_amount, etc.) placed AFTER __repr__
- ✅ NEW: All columns grouped together BEFORE relationships
- ✅ NEW: Relationships grouped together BEFORE __repr__
- ✅ Organized: Purchased Limits → Active Counters → Billing → Relationships → Methods

### ✅ 4. Fixed Data Type Issues

**school_domain.py - verified_at column:**
- ❌ OLD: `verified_at = Column(String(100), DateTime(timezone=True), nullable=True)`
- ✅ NEW: `verified_at = Column(DateTime(timezone=True), nullable=True)`
- **Reason:** Column accepts single type, not two mixed types

### ✅ 5. Enhanced Enum Classes

**All 9 Enums now have docstrings:**

| Enum | File | States | Documentation |
|------|------|--------|---------------|
| TenantStatus | tenant.py | 5 | Lifecycle: TRIAL → ACTIVE → (SUSPENDED/CANCELLED) → ARCHIVED |
| TenantType | tenant.py | 4 | Org types: SINGLE_SCHOOL, SCHOOL_GROUP, GOVT_BLOCK, UNIVERSITY |
| SchoolStatus | school.py | 3 | States: ACTIVE, INACTIVE, ARCHIVED |
| BoardType | school.py | 6 | Curriculum: CBSE, ICSE, STATE, IB, IGCSE, OTHER |
| DomainStatus | school_domain.py | 4 | Verification: PENDING → VERIFIED or FAILED → DISABLED |
| SubscriptionStatus | school_subscription.py | 5 | Billing: TRIAL → ACTIVE → (EXPIRED/SUSPENDED/CANCELLED) |
| BillingCycle | subscription_plan.py | 3 | Frequency: MONTHLY, QUARTERLY, ANNUAL |
| PlanTier | subscription_plan.py | 6 | Tier: FREE_TRIAL, STARTER, PROFESSIONAL, ENTERPRISE, GOVERNMENT, CUSTOM |
| PricingModel | subscription_plan.py | 4 | Model: FLAT, PER_STUDENT, PER_USER, HYBRID |

### ✅ 6. Enhanced __repr__ Methods

All 5 model classes now have:
- **Type hints:** `-> str`
- **Docstrings:** Explaining format and return value
- **Consistent format:** Key fields with appropriate representation

```python
# Example from School
def __repr__(self) -> str:
    """String representation of School."""
    return f"<School(id={self.id}, school_name={self.school_name})>"
```

### ✅ 7. Verified Relationships

**Bidirectional Relationships:**
- ✅ Tenant ←→ School (via `back_populates`)
- ✅ Tenant ←→ SchoolSubscription (via `back_populates`)
- ✅ School ←→ SchoolSubscription (via `back_populates`)
- ✅ School ←→ SchoolDomain (via `back_populates`)
- ✅ SubscriptionPlan ←→ SchoolSubscription (via `back_populates`)

**Cascade Behavior:**
- ✅ School → Tenant: `CASCADE delete` (delete school if tenant deleted)
- ✅ SchoolDomain → School: `CASCADE delete` (delete domain if school deleted)

---

## 5. Architecture Verification Checklist

### ✅ Database Design
- [x] Multi-tenancy: Tenant → Schools (1-to-many)
- [x] Billing boundary: Per-school (not per-tenant)
- [x] Subdomain isolation: Unique subdomains per school
- [x] Domain management: Custom domains with SSL
- [x] Usage tracking: Purchased vs. Active counters
- [x] Financial tracking: Base price + per-unit + discounts + tax

### ✅ Code Quality
- [x] All classes have docstrings
- [x] All enums documented
- [x] All __repr__ methods typed and documented
- [x] Consistent import organization
- [x] Proper column grouping (identity, billing, limits)
- [x] No orphaned columns
- [x] No duplicate imports

### ✅ Relationships
- [x] All many-to-1 relationships have indexes
- [x] All bidirectional relationships use `back_populates`
- [x] Cascade delete policies appropriate
- [x] No circular dependencies

### ✅ Constraints
- [x] Unique constraints documented
- [x] Compound unique constraints used appropriately
- [x] Foreign key constraints with CASCADE

---

## 6. Usage Examples

### Query a School with Related Data
```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Get school with eager-loaded relationships
stmt = (
    select(School)
    .where(School.subdomain == "gv-blr")
    .options(
        selectinload(School.tenant),
        selectinload(School.subscriptions).selectinload(SchoolSubscription.plan),
        selectinload(School.domains),
    )
)
school = session.execute(stmt).scalar_one()

print(f"School: {school.school_name}")
print(f"Tenant: {school.tenant.organization_name}")
print(f"Subscriptions: {len(school.subscriptions)}")
for sub in school.subscriptions:
    print(f"  - {sub.plan.name}: {sub.final_amount} {sub.currency}")
```

### Check Subscription Limits
```python
subscription = school.subscriptions[0]

# Usage percentage
student_usage = (subscription.active_student_count / 
                 subscription.purchased_student_count * 100)
storage_usage = (subscription.used_storage_gb / 
                 subscription.purchased_storage_gb * 100)

print(f"Student usage: {student_usage:.1f}%")
print(f"Storage usage: {storage_usage:.1f}%")
```

### Create Multi-School Tenant
```python
from datetime import date, timedelta

# Create tenant
tenant = Tenant(
    organization_name="Green Valley Education Group",
    organization_code="GVE-001",
    tenant_type=TenantType.SCHOOL_GROUP,
    slug="green-valley",
    status=TenantStatus.ACTIVE,
)
session.add(tenant)
session.flush()

# Create school 1
school1 = School(
    tenant_id=tenant.id,
    school_name="Green Valley Bangalore",
    school_code="GVB",
    subdomain="gv-blr",
    status=SchoolStatus.ACTIVE,
    timezone="Asia/Kolkata",
    board_type=BoardType.CBSE,
)
session.add(school1)
session.flush()

# Get Enterprise plan
plan = session.execute(
    select(SubscriptionPlan).where(SubscriptionPlan.code == "ENTERPRISE")
).scalar_one()

# Create subscription
subscription = SchoolSubscription(
    tenant_id=tenant.id,
    school_id=school1.id,
    subscription_plan_id=plan.id,
    status=SubscriptionStatus.ACTIVE,
    start_date=date.today(),
    end_date=date.today() + timedelta(days=365),
    purchased_student_count=500,
    purchased_user_count=50,
    plan_amount=175000,
    final_amount=206750,  # with tax
    currency="INR",
)
session.add(subscription)
session.commit()
```

---

## 7. Best Practices Applied

✅ **Enum Documentation:**
- Every state/value documented with business meaning
- Examples provided where applicable

✅ **Model Documentation:**
- Purpose statement at top
- Architecture relationships explained
- Real-world examples

✅ **Code Organization:**
- Imports: Standard → SQLAlchemy → Dialects → ORM → Local
- Columns: Grouped by semantic meaning (Identity, Billing, Limits)
- Relationships: After columns, before methods
- Methods: __repr__ last

✅ **Type Hints:**
- __repr__ methods include return type
- Proper Python conventions

✅ **Naming Conventions:**
- Enums: PascalCase + (str, enum.Enum)
- Tables: snake_case plural (school_subscriptions)
- Constraints: Descriptive names (uq_school_domain, uq_school_tenant_code)

✅ **Database Design:**
- Logical primary keys (UUID from BaseModel)
- Indexes on frequently queried columns (status, code, slug)
- Compound unique constraints for multi-field uniqueness
- Appropriate cascade delete policies

---

## 8. Summary Statistics

| Metric | Count |
|--------|-------|
| Total Models | 5 |
| Total Enums | 9 |
| Total Relationships | 7 (bidirectional) |
| Total Columns | ~60 |
| Unique Constraints | 5 |
| Cascade Delete Policies | 2 |
| Docstrings Added | 20+ |
| Code Fixes Applied | 7 |

---

## 9. Files Modified

1. ✅ [tenant.py](tenant.py) - Added module docstring, enum docstrings, __repr__ docstring
2. ✅ [school.py](school.py) - Fixed imports, added module & enum docstrings, __repr__ docstring
3. ✅ [school_domain.py](school_domain.py) - Fixed data type, imports, docstrings, code organization
4. ✅ [school_subscription.py](school_subscription.py) - Reorganized columns/relationships, added docstrings
5. ✅ [subscription_plan.py](subscription_plan.py) - Added module & enum docstrings, __repr__ docstring

---

**Status:** ✅ All models reviewed, documented, and optimized for best practices.
