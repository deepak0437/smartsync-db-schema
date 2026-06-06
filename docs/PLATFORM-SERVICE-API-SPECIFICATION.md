# Platform Service - API Specification

**Version:** 1.0  
**Last Updated:** 2024-01-15  
**Service:** Platform Service  
**Purpose:** Subscription management, tenant/school lifecycle, billing, and access control

---

## Table of Contents

1. [Tenant Management APIs](#1-tenant-management-apis)
2. [School Management APIs](#2-school-management-apis)
3. [School Domain Management APIs](#3-school-domain-management-apis)
4. [Subscription Plan Management APIs](#4-subscription-plan-management-apis)
5. [School Subscription APIs](#5-school-subscription-apis)
6. [Subscription Pricing APIs](#6-subscription-pricing-apis)
7. [Subscription History APIs](#7-subscription-history-apis)
8. [Free Trial Management APIs](#8-free-trial-management-apis)
9. [Analytics & Reporting APIs](#9-analytics--reporting-apis)

---

## 1. Tenant Management APIs

Manage customer organizations (tenants) in the SmartSync platform.

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/api/v1/tenants` | Create new tenant organization (onboarding) | Platform Admin |
| GET | `/api/v1/tenants/{tenant_id}` | Get tenant details | Platform Admin, Tenant Admin |
| GET | `/api/v1/tenants` | List all tenants (with pagination, filters) | Platform Admin |
| PUT | `/api/v1/tenants/{tenant_id}` | Update tenant information | Platform Admin, Tenant Admin |
| PATCH | `/api/v1/tenants/{tenant_id}/status` | Change tenant status (ACTIVE/INACTIVE/ARCHIVED) | Platform Admin |
| DELETE | `/api/v1/tenants/{tenant_id}` | Soft delete tenant | Platform Admin |

### Example Request: Create Tenant

```http
POST /api/v1/tenants
Content-Type: application/json
Authorization: Bearer <platform_admin_token>

{
  "name": "Green Valley Education Group",
  "code": "GVEG",
  "type": "SCHOOL_GROUP",
  "slug": "green-valley",
  "website": "https://greenvalley.edu",
  "status": "ACTIVE"
}
```

### Example Response:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Green Valley Education Group",
  "code": "GVEG",
  "type": "SCHOOL_GROUP",
  "slug": "green-valley",
  "website": "https://greenvalley.edu",
  "status": "ACTIVE",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

## 2. School Management APIs

Manage individual schools within tenant organizations.

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/api/v1/tenants/{tenant_id}/schools` | Create new school under tenant | Platform Admin |
| GET | `/api/v1/schools/{school_id}` | Get school details | Platform Admin, School Admin |
| GET | `/api/v1/tenants/{tenant_id}/schools` | List schools under a tenant | Platform Admin, Tenant Admin |
| PUT | `/api/v1/schools/{school_id}` | Update school information | Platform Admin, School Admin |
| PATCH | `/api/v1/schools/{school_id}/status` | Change school status (TRIAL/ACTIVE/SUSPENDED/etc) | Platform Admin |
| DELETE | `/api/v1/schools/{school_id}` | Soft delete school | Platform Admin |
| GET | `/api/v1/schools/subdomain/{subdomain}` | Get school by subdomain (for login routing) | Public |

### Example Request: Create School

```http
POST /api/v1/tenants/550e8400-e29b-41d4-a716-446655440000/schools
Content-Type: application/json
Authorization: Bearer <platform_admin_token>

{
  "name": "Green Valley Bangalore",
  "code": "GVB",
  "subdomain": "greenvalley-bangalore",
  "board": "CBSE",
  "email": "admin@greenvalley-bangalore.edu",
  "phone_number": "+91-80-12345678",
  "address": "123 School Street",
  "city": "Bangalore",
  "state": "Karnataka",
  "country": "India",
  "pincode": "560001",
  "timezone": "Asia/Kolkata",
  "academic_year_start_month": 4,
  "status": "TRIAL"
}
```

### Example Response:

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Green Valley Bangalore",
  "code": "GVB",
  "subdomain": "greenvalley-bangalore",
  "board": "CBSE",
  "email": "admin@greenvalley-bangalore.edu",
  "phone_number": "+91-80-12345678",
  "address": "123 School Street",
  "city": "Bangalore",
  "state": "Karnataka",
  "country": "India",
  "pincode": "560001",
  "timezone": "Asia/Kolkata",
  "status": "TRIAL",
  "academic_year_start_month": 4,
  "created_at": "2024-01-15T10:35:00Z"
}
```

---

## 3. School Domain Management APIs

Manage custom domains and subdomains for schools.

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/api/v1/schools/{school_id}/domain` | Add/update custom domain for school | Platform Admin, School Admin |
| GET | `/api/v1/schools/{school_id}/domain` | Get domain configuration | Platform Admin, School Admin |
| POST | `/api/v1/schools/{school_id}/domain/verify` | Trigger domain verification (DNS check) | Platform Admin, School Admin |
| DELETE | `/api/v1/schools/{school_id}/domain` | Remove custom domain | Platform Admin |

### Example Request: Add Custom Domain

```http
POST /api/v1/schools/660e8400-e29b-41d4-a716-446655440001/domain
Content-Type: application/json
Authorization: Bearer <school_admin_token>

{
  "domain": "erp.greenvalley.edu",
  "is_custom_domain": true
}
```

### Example Response:

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "school_id": "660e8400-e29b-41d4-a716-446655440001",
  "domain": "erp.greenvalley.edu",
  "is_custom_domain": true,
  "status": "PENDING_VERIFICATION",
  "verified_at": null,
  "dns_instructions": {
    "type": "CNAME",
    "name": "erp",
    "value": "greenvalley-bangalore.smartsync.ai",
    "verification_token": "abc123def456"
  },
  "created_at": "2024-01-15T11:00:00Z"
}
```

---

## 4. Subscription Plan Management APIs

Platform admin manages subscription plans (product catalog).

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/api/v1/subscription-plans` | Create new subscription plan (A1, A2, B1, B2) | Platform Admin |
| GET | `/api/v1/subscription-plans` | List all plans (public + internal) | Platform Admin |
| GET | `/api/v1/subscription-plans/public` | List publicly available plans (for pricing page) | Public |
| GET | `/api/v1/subscription-plans/{plan_id}` | Get plan details | Public |
| PUT | `/api/v1/subscription-plans/{plan_id}` | Update plan configuration | Platform Admin |
| PATCH | `/api/v1/subscription-plans/{plan_id}/active` | Enable/disable plan | Platform Admin |

### Example Request: Create Subscription Plan

```http
POST /api/v1/subscription-plans
Content-Type: application/json
Authorization: Bearer <platform_admin_token>

{
  "name": "Core Entry",
  "code": "A1",
  "family": "CORE",
  "variant": "ENTRY",
  "description": "Entry-level plan for small schools",
  "is_publicly_listed": true,
  "is_active": true,
  "display_order": 1,
  "fixed_max_users": 500,
  "pricing_model": "FLAT",
  "base_price_paise": 49900,
  "currency": "INR",
  "tenure_discounts": {
    "1": 0.00,
    "3": 5.00,
    "6": 10.00,
    "12": 15.00,
    "24": 20.00,
    "36": 25.00
  },
  "tax_percent": 18.00,
  "tax_label": "GST",
  "hsn_sac_code": "9984",
  "max_storage_gb": 100,
  "included_modules": ["ACADEMICS", "FINANCE", "COMMUNICATION", "ADMIN"],
  "features": {
    "api_access": false,
    "custom_reports": false,
    "white_label": false,
    "priority_support": false
  },
  "trial_days": 30
}
```

### Example Response: List Public Plans

```http
GET /api/v1/subscription-plans/public
```

```json
{
  "plans": [
    {
      "id": "plan-uuid-1",
      "name": "Core Entry",
      "code": "A1",
      "family": "CORE",
      "variant": "ENTRY",
      "fixed_max_users": 500,
      "base_price": 499.00,
      "currency": "INR",
      "billing_cycle": "MONTHLY",
      "max_storage_gb": 100,
      "included_modules": ["ACADEMICS", "FINANCE", "COMMUNICATION", "ADMIN"],
      "features": {
        "api_access": false,
        "custom_reports": false,
        "priority_support": false
      },
      "trial_days": 30,
      "highlight_text": null
    },
    {
      "id": "plan-uuid-2",
      "name": "Core Scalable",
      "code": "A2",
      "family": "CORE",
      "variant": "SCALABLE",
      "allowed_user_counts": [1500, 2500, 3500, 4500, 5500],
      "base_price": 999.00,
      "currency": "INR",
      "max_storage_gb": 500,
      "highlight_text": "Most Popular"
    }
  ]
}
```

---

## 5. School Subscription APIs

Core billing and subscription management for schools.

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/api/v1/schools/{school_id}/subscriptions` | Create new subscription (purchase/upgrade) | Platform Admin |
| GET | `/api/v1/schools/{school_id}/subscriptions/current` | Get current active subscription | School Admin |
| GET | `/api/v1/schools/{school_id}/subscriptions` | List all subscriptions (history) | Platform Admin, School Admin |
| GET | `/api/v1/schools/{school_id}/subscriptions/{subscription_id}` | Get specific subscription details | School Admin |
| POST | `/api/v1/schools/{school_id}/subscriptions/{subscription_id}/renew` | Renew subscription | Platform Admin |
| POST | `/api/v1/schools/{school_id}/subscriptions/{subscription_id}/upgrade` | Upgrade plan or user count | Platform Admin |
| POST | `/api/v1/schools/{school_id}/subscriptions/{subscription_id}/downgrade` | Downgrade plan or user count | Platform Admin |
| POST | `/api/v1/schools/{school_id}/subscriptions/{subscription_id}/cancel` | Cancel subscription | Platform Admin, School Admin |
| PATCH | `/api/v1/schools/{school_id}/subscriptions/{subscription_id}/suspend` | Suspend subscription (payment failure) | Platform Admin |
| PATCH | `/api/v1/schools/{school_id}/subscriptions/{subscription_id}/reactivate` | Reactivate suspended subscription | Platform Admin |
| POST | `/api/v1/schools/{school_id}/subscriptions/{subscription_id}/extend` | Extend end date (goodwill) | Platform Admin |
| GET | `/api/v1/schools/{school_id}/subscription/limits` | Get subscription limits (for quota enforcement) | Internal Services |
| GET | `/api/v1/schools/{school_id}/subscription/usage` | Get usage vs limits with Auth Service data | School Admin |

### Example Request: Create Subscription

```http
POST /api/v1/schools/660e8400-e29b-41d4-a716-446655440001/subscriptions
Content-Type: application/json
Authorization: Bearer <platform_admin_token>

{
  "plan_id": "plan-uuid-2",
  "selected_max_users": 2500,
  "tenure_months": 12,
  "auto_renewal": true,
  "active_add_ons": [
    {
      "module": "HOSTEL",
      "monthly_price_paise": 20000
    }
  ],
  "payment_method": "RAZORPAY",
  "payment_reference": "pay_abc123def456",
  "po_number": "PO-2024-001"
}
```

### Example Response:

```json
{
  "subscription": {
    "id": "sub-uuid-123",
    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "school_id": "660e8400-e29b-41d4-a716-446655440001",
    "plan_id": "plan-uuid-2",
    "status": "ACTIVE",
    "selected_max_users": 2500,
    "effective_max_users": 2500,
    "tenure_months": 12,
    "start_date": "2024-01-15",
    "end_date": "2025-01-14",
    "grace_period_end_date": "2025-01-29",
    "auto_renewal": true,
    "active_modules": ["ACADEMICS", "FINANCE", "HR", "COMMUNICATION", "LMS", "HOSTEL"],
    "active_add_ons": [
      {
        "module": "HOSTEL",
        "monthly_price_paise": 20000
      }
    ],
    "payment_method": "RAZORPAY",
    "payment_reference": "pay_abc123def456",
    "po_number": "PO-2024-001",
    "created_at": "2024-01-15T12:00:00Z"
  },
  "pricing": {
    "base_price_paise": 99900,
    "tenure_discount_percent": 15.00,
    "discount_amount_paise": 14985,
    "subtotal_paise": 84915,
    "tax_percent": 18.00,
    "tax_amount_paise": 15285,
    "final_amount_paise": 100200,
    "currency": "INR",
    "final_amount_inr": 1002.00
  }
}
```

### Example: Get Subscription Limits (Internal API)

```http
GET /api/v1/schools/660e8400-e29b-41d4-a716-446655440001/subscription/limits
Authorization: Bearer <service_api_key>
```

```json
{
  "school_id": "660e8400-e29b-41d4-a716-446655440001",
  "purchased_user_count": 2500,
  "purchased_storage_gb": 500,
  "plan_code": "A2",
  "plan_name": "Core Scalable",
  "status": "ACTIVE",
  "start_date": "2024-01-15",
  "end_date": "2025-01-14"
}
```

### Example: Get Subscription Usage (with Auth Service data)

```http
GET /api/v1/schools/660e8400-e29b-41d4-a716-446655440001/subscription/usage
Authorization: Bearer <school_admin_token>
```

```json
{
  "subscription": {
    "plan_name": "Core Scalable",
    "status": "ACTIVE",
    "start_date": "2024-01-15",
    "end_date": "2025-01-14",
    "days_remaining": 335,
    "purchased_limits": {
      "users": 2500,
      "storage_gb": 500
    }
  },
  "current_usage": {
    "users": {
      "total_active": 1847,
      "percentage": 73.88,
      "status": "ok",
      "breakdown_by_role": {
        "students": 1650,
        "teachers": 85,
        "parents": 1500,
        "admin_staff": 12
      }
    },
    "storage": {
      "used_gb": 234,
      "percentage": 46.8,
      "status": "ok"
    }
  },
  "alerts": []
}
```

### Example: Upgrade Subscription

```http
POST /api/v1/schools/660e8400-e29b-41d4-a716-446655440001/subscriptions/sub-uuid-123/upgrade
Content-Type: application/json
Authorization: Bearer <platform_admin_token>

{
  "new_plan_id": "plan-uuid-4",
  "new_max_users": 3500,
  "upgrade_reason": "School reached 2400 users, needs higher capacity",
  "prorated_payment": true
}
```

---

## 6. Subscription Pricing APIs

Price calculation and invoice generation.

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/api/v1/subscriptions/{subscription_id}/pricing` | Get complete price breakdown | School Admin |
| POST | `/api/v1/subscription-plans/{plan_id}/calculate-price` | Calculate price for given user count + tenure | Public |
| GET | `/api/v1/subscriptions/{subscription_id}/invoice` | Generate invoice PDF/JSON | School Admin |

### Example: Calculate Price

```http
POST /api/v1/subscription-plans/plan-uuid-2/calculate-price
Content-Type: application/json

{
  "selected_max_users": 3500,
  "tenure_months": 12,
  "add_ons": [
    {
      "module": "HOSTEL",
      "monthly_price_paise": 20000
    }
  ]
}
```

```json
{
  "plan_code": "A2",
  "plan_name": "Core Scalable",
  "user_count": 3500,
  "tenure_months": 12,
  "breakdown": {
    "base_price_monthly": 1499.00,
    "base_price_total": 17988.00,
    "add_ons_total": 2400.00,
    "subtotal_before_discount": 20388.00,
    "tenure_discount_percent": 15.00,
    "tenure_discount_amount": 3058.20,
    "subtotal_after_discount": 17329.80,
    "tax_percent": 18.00,
    "tax_amount": 3119.36,
    "final_amount": 20449.16
  },
  "currency": "INR"
}
```

---

## 7. Subscription History APIs

Audit trail and change history for subscriptions.

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/api/v1/schools/{school_id}/subscription-history` | Get complete subscription change history | School Admin |
| GET | `/api/v1/subscriptions/{subscription_id}/history` | Get history for specific subscription | School Admin |
| GET | `/api/v1/subscription-history/changes` | Platform-wide subscription changes (analytics) | Platform Admin |

### Example Response: Subscription History

```http
GET /api/v1/schools/660e8400-e29b-41d4-a716-446655440001/subscription-history
```

```json
{
  "school_id": "660e8400-e29b-41d4-a716-446655440001",
  "history": [
    {
      "id": "hist-001",
      "change_type": "TRIAL_STARTED",
      "changed_at": "2023-12-01T10:00:00Z",
      "new_status": "FREE_TRIAL",
      "new_plan_code": "FREE_TRIAL",
      "new_max_users": 50,
      "changed_by_type": "SYSTEM"
    },
    {
      "id": "hist-002",
      "change_type": "TRIAL_CONVERTED",
      "changed_at": "2023-12-15T14:30:00Z",
      "previous_status": "FREE_TRIAL",
      "new_status": "ACTIVE",
      "previous_plan_code": "FREE_TRIAL",
      "new_plan_code": "A1",
      "new_max_users": 500,
      "new_final_amount_paise": 50000,
      "changed_by_type": "PLATFORM_ADMIN",
      "change_reason": "School purchased Core Entry plan"
    },
    {
      "id": "hist-003",
      "change_type": "UPGRADED",
      "changed_at": "2024-01-15T12:00:00Z",
      "previous_status": "ACTIVE",
      "new_status": "ACTIVE",
      "previous_plan_code": "A1",
      "new_plan_code": "A2",
      "previous_max_users": 500,
      "new_max_users": 2500,
      "previous_final_amount_paise": 50000,
      "new_final_amount_paise": 100200,
      "changed_by_type": "PLATFORM_ADMIN",
      "change_reason": "School reached user capacity, upgraded to A2"
    }
  ]
}
```

---

## 8. Free Trial Management APIs

Manage free trial periods for schools.

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/api/v1/schools/{school_id}/trial/start` | Start free trial for school | Platform Admin |
| GET | `/api/v1/schools/{school_id}/trial` | Get trial status and details | School Admin |
| POST | `/api/v1/schools/{school_id}/trial/extend` | Extend trial period | Platform Admin |
| POST | `/api/v1/schools/{school_id}/trial/convert` | Convert trial to paid subscription | Platform Admin |
| GET | `/api/v1/trials/expiring` | List trials expiring soon (for reminders) | Platform Admin |

### Example: Start Trial

```http
POST /api/v1/schools/660e8400-e29b-41d4-a716-446655440001/trial/start
Content-Type: application/json
Authorization: Bearer <platform_admin_token>

{
  "trial_days": 30,
  "trial_max_users": 50,
  "trial_modules": ["ACADEMICS", "COMMUNICATION"]
}
```

### Example Response:

```json
{
  "trial": {
    "id": "trial-uuid-001",
    "school_id": "660e8400-e29b-41d4-a716-446655440001",
    "subscription_id": "sub-trial-001",
    "trial_days_granted": 30,
    "trial_start_date": "2024-01-15",
    "trial_end_date": "2024-02-14",
    "trial_max_users": 50,
    "trial_modules": ["ACADEMICS", "COMMUNICATION"],
    "status": "ACTIVE"
  }
}
```

---

## 9. Analytics & Reporting APIs

Platform-wide analytics for business intelligence.

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/api/v1/analytics/subscriptions/summary` | MRR, ARR, active subscriptions count | Platform Admin |
| GET | `/api/v1/analytics/subscriptions/by-plan` | Subscription distribution by plan | Platform Admin |
| GET | `/api/v1/analytics/trials/conversion-rate` | Trial to paid conversion metrics | Platform Admin |
| GET | `/api/v1/analytics/churn` | Cancellation and churn data | Platform Admin |
| GET | `/api/v1/analytics/revenue/monthly` | Monthly revenue breakdown | Platform Admin |

### Example: Subscription Summary

```http
GET /api/v1/analytics/subscriptions/summary
Authorization: Bearer <platform_admin_token>
```

```json
{
  "summary": {
    "total_active_subscriptions": 342,
    "total_trial_subscriptions": 28,
    "mrr": 4250000,
    "arr": 51000000,
    "average_revenue_per_school": 12427
  },
  "by_plan": {
    "A1": {
      "count": 120,
      "mrr": 600000
    },
    "A2": {
      "count": 150,
      "mrr": 2250000
    },
    "B1": {
      "count": 50,
      "mrr": 1000000
    },
    "B2": {
      "count": 22,
      "mrr": 400000
    }
  },
  "currency": "INR"
}
```

---

## Event Publishing

Platform Service publishes events to Message Queue (Kafka/RabbitMQ) for other services to consume:

### Events Published:

| Event Type | Triggered When | Consumed By |
|------------|----------------|-------------|
| `TenantCreated` | New tenant created | All services |
| `TenantStatusChanged` | Tenant status updated | All services |
| `SchoolCreated` | New school created | Auth, Admin, Finance services |
| `SchoolStatusChanged` | School status updated | Auth, Admin services |
| `SubscriptionCreated` | New subscription purchased | Auth, Finance, Media services |
| `SubscriptionUpgraded` | Plan or user count upgraded | Auth, Finance services |
| `SubscriptionDowngraded` | Plan or user count downgraded | Auth, Finance services |
| `SubscriptionRenewed` | Subscription renewed | Finance service |
| `SubscriptionCancelled` | Subscription cancelled | Auth, Finance services |
| `SubscriptionSuspended` | Payment failure/manual suspension | Auth service |
| `TrialStarted` | Free trial activated | Auth, Admin services |
| `TrialConverted` | Trial converted to paid | Finance service |

---

## Authentication & Authorization

### Authentication:
- **JWT Bearer Token** in `Authorization` header
- Token contains: `user_id`, `school_id`, `tenant_id`, `roles`, `permissions`

### Authorization Levels:
1. **Platform Admin** - Full access to all APIs
2. **Tenant Admin** - Access to tenant and all schools under tenant
3. **School Admin** - Access to specific school data only
4. **Internal Service** - Service-to-service API keys for cross-service calls

---

## Error Responses

Standard error format:

```json
{
  "error": {
    "code": "SUBSCRIPTION_LIMIT_EXCEEDED",
    "message": "Cannot add more users. Current: 2480/2500. Please upgrade your plan.",
    "details": {
      "current_users": 2480,
      "purchased_limit": 2500,
      "available": 20
    }
  }
}
```

### Common Error Codes:
- `TENANT_NOT_FOUND`
- `SCHOOL_NOT_FOUND`
- `SUBSCRIPTION_NOT_FOUND`
- `SUBSCRIPTION_EXPIRED`
- `SUBSCRIPTION_SUSPENDED`
- `SUBSCRIPTION_LIMIT_EXCEEDED`
- `PAYMENT_FAILED`
- `INVALID_PLAN_SELECTION`
- `TRIAL_ALREADY_USED`
- `DOMAIN_VERIFICATION_FAILED`

---

## Rate Limiting

- **Public APIs**: 100 requests/minute
- **Authenticated APIs**: 1000 requests/minute per school
- **Internal Service APIs**: 10,000 requests/minute

---

## Pagination

List APIs support pagination:

```http
GET /api/v1/tenants?page=1&page_size=20&sort_by=created_at&sort_order=desc
```

Response includes pagination metadata:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_pages": 15,
    "total_items": 300,
    "has_next": true,
    "has_previous": false
  }
}
```

---

## Webhook Support (Future)

Platform Service will support webhooks for external integrations:

- `subscription.created`
- `subscription.upgraded`
- `subscription.cancelled`
- `trial.started`
- `trial.expired`
- `payment.received`

---

**End of Platform Service API Specification**
