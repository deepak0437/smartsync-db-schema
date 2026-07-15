-- Updates the platform.plans / platform.expansion_addons catalog to a real
-- price list: `price` is the FLAT total for that entire row's user count —
-- e.g. the 500-user Core Entry tier's price is what all 500 users cost
-- together, not a per-user rate to be multiplied by 500. Per-user cost is
-- purely a frontend-derived comparison figure (basePrice / users), never
-- stored here. `discount_percentage` follows the tenure ladder (0/5/10/15/
-- 22/30% for 1/3/6/12/24/36 months), constant across a tier's 6 tenure rows.
-- Matches smartsync-website's src/features/pricing/config/{plans,tenure}
-- .config.ts exactly, so the live API and the frontend's static fallback
-- agree.
--
-- Larger tiers cost more in absolute (flat) terms but less per user — that's
-- the volume discount, and it's entirely implied by how these flat numbers
-- were chosen, not a separately stored percentage.
--
-- Updates existing rows in place (matched by type/variant/user_count/tenure)
-- rather than re-inserting — run against a DB that already has the 66 plan
-- rows + 2 addon rows from the initial schema's expected shape.
--
-- Usage: psql -h <host> -p <port> -U <user> -d <db> -f scripts/seed_pricing.sql

BEGIN;

-- Core Entry (500 users, fixed) — ₹9,000/month flat
UPDATE platform.plans SET price = 9000.00, discount_price = NULL,
  discount_percentage = CASE tenure
    WHEN 'ONE_MONTH' THEN 0.00 WHEN 'THREE_MONTHS' THEN 5.00 WHEN 'SIX_MONTHS' THEN 10.00
    WHEN 'TWELVE_MONTHS' THEN 15.00 WHEN 'TWENTY_FOUR' THEN 22.00 WHEN 'THIRTY_SIX' THEN 30.00
  END
WHERE type = 'CORE' AND variant = 'ENTRY' AND user_count = 'USERS_500';

-- Core Scalable tiers — flat totals, ₹24,000 -> ₹60,500 as the tier grows
UPDATE platform.plans SET price = 24000.00, discount_price = NULL,
  discount_percentage = CASE tenure
    WHEN 'ONE_MONTH' THEN 0.00 WHEN 'THREE_MONTHS' THEN 5.00 WHEN 'SIX_MONTHS' THEN 10.00
    WHEN 'TWELVE_MONTHS' THEN 15.00 WHEN 'TWENTY_FOUR' THEN 22.00 WHEN 'THIRTY_SIX' THEN 30.00
  END
WHERE type = 'CORE' AND variant = 'SCALABLE' AND user_count = 'USERS_1500';

UPDATE platform.plans SET price = 35000.00, discount_price = NULL,
  discount_percentage = CASE tenure
    WHEN 'ONE_MONTH' THEN 0.00 WHEN 'THREE_MONTHS' THEN 5.00 WHEN 'SIX_MONTHS' THEN 10.00
    WHEN 'TWELVE_MONTHS' THEN 15.00 WHEN 'TWENTY_FOUR' THEN 22.00 WHEN 'THIRTY_SIX' THEN 30.00
  END
WHERE type = 'CORE' AND variant = 'SCALABLE' AND user_count = 'USERS_2500';

UPDATE platform.plans SET price = 45500.00, discount_price = NULL,
  discount_percentage = CASE tenure
    WHEN 'ONE_MONTH' THEN 0.00 WHEN 'THREE_MONTHS' THEN 5.00 WHEN 'SIX_MONTHS' THEN 10.00
    WHEN 'TWELVE_MONTHS' THEN 15.00 WHEN 'TWENTY_FOUR' THEN 22.00 WHEN 'THIRTY_SIX' THEN 30.00
  END
WHERE type = 'CORE' AND variant = 'SCALABLE' AND user_count = 'USERS_3500';

UPDATE platform.plans SET price = 54000.00, discount_price = NULL,
  discount_percentage = CASE tenure
    WHEN 'ONE_MONTH' THEN 0.00 WHEN 'THREE_MONTHS' THEN 5.00 WHEN 'SIX_MONTHS' THEN 10.00
    WHEN 'TWELVE_MONTHS' THEN 15.00 WHEN 'TWENTY_FOUR' THEN 22.00 WHEN 'THIRTY_SIX' THEN 30.00
  END
WHERE type = 'CORE' AND variant = 'SCALABLE' AND user_count = 'USERS_4500';

UPDATE platform.plans SET price = 60500.00, discount_price = NULL,
  discount_percentage = CASE tenure
    WHEN 'ONE_MONTH' THEN 0.00 WHEN 'THREE_MONTHS' THEN 5.00 WHEN 'SIX_MONTHS' THEN 10.00
    WHEN 'TWELVE_MONTHS' THEN 15.00 WHEN 'TWENTY_FOUR' THEN 22.00 WHEN 'THIRTY_SIX' THEN 30.00
  END
WHERE type = 'CORE' AND variant = 'SCALABLE' AND user_count = 'USERS_5500';

-- Growth Entry (1,000 users, fixed) — ₹22,000/month flat
UPDATE platform.plans SET price = 22000.00, discount_price = NULL,
  discount_percentage = CASE tenure
    WHEN 'ONE_MONTH' THEN 0.00 WHEN 'THREE_MONTHS' THEN 5.00 WHEN 'SIX_MONTHS' THEN 10.00
    WHEN 'TWELVE_MONTHS' THEN 15.00 WHEN 'TWENTY_FOUR' THEN 22.00 WHEN 'THIRTY_SIX' THEN 30.00
  END
WHERE type = 'GROWTH' AND variant = 'ENTRY' AND user_count = 'USERS_1000';

-- Growth Scalable tiers — flat totals, ₹40,000 -> ₹85,000 as the tier grows
UPDATE platform.plans SET price = 40000.00, discount_price = NULL,
  discount_percentage = CASE tenure
    WHEN 'ONE_MONTH' THEN 0.00 WHEN 'THREE_MONTHS' THEN 5.00 WHEN 'SIX_MONTHS' THEN 10.00
    WHEN 'TWELVE_MONTHS' THEN 15.00 WHEN 'TWENTY_FOUR' THEN 22.00 WHEN 'THIRTY_SIX' THEN 30.00
  END
WHERE type = 'GROWTH' AND variant = 'SCALABLE' AND user_count = 'USERS_2000';

UPDATE platform.plans SET price = 57000.00, discount_price = NULL,
  discount_percentage = CASE tenure
    WHEN 'ONE_MONTH' THEN 0.00 WHEN 'THREE_MONTHS' THEN 5.00 WHEN 'SIX_MONTHS' THEN 10.00
    WHEN 'TWELVE_MONTHS' THEN 15.00 WHEN 'TWENTY_FOUR' THEN 22.00 WHEN 'THIRTY_SIX' THEN 30.00
  END
WHERE type = 'GROWTH' AND variant = 'SCALABLE' AND user_count = 'USERS_3000';

UPDATE platform.plans SET price = 72000.00, discount_price = NULL,
  discount_percentage = CASE tenure
    WHEN 'ONE_MONTH' THEN 0.00 WHEN 'THREE_MONTHS' THEN 5.00 WHEN 'SIX_MONTHS' THEN 10.00
    WHEN 'TWELVE_MONTHS' THEN 15.00 WHEN 'TWENTY_FOUR' THEN 22.00 WHEN 'THIRTY_SIX' THEN 30.00
  END
WHERE type = 'GROWTH' AND variant = 'SCALABLE' AND user_count = 'USERS_4000';

UPDATE platform.plans SET price = 85000.00, discount_price = NULL,
  discount_percentage = CASE tenure
    WHEN 'ONE_MONTH' THEN 0.00 WHEN 'THREE_MONTHS' THEN 5.00 WHEN 'SIX_MONTHS' THEN 10.00
    WHEN 'TWELVE_MONTHS' THEN 15.00 WHEN 'TWENTY_FOUR' THEN 22.00 WHEN 'THIRTY_SIX' THEN 30.00
  END
WHERE type = 'GROWTH' AND variant = 'SCALABLE' AND user_count = 'USERS_5000';

-- Capacity add-on packs — each tenure has its own directly-authored flat
-- price (cheaper for a longer commitment, same idea as Plans), not a
-- percentage discount applied to a base rate: discount/discount_percentage
-- stay NULL on every row, `price` itself IS the final number for that row.
-- A real row exists for each of the 6 tenures so the frontend can look up
-- "the addon price for whatever plan tenure is currently selected" and
-- always find a match, instead of only ever having a 12-month row.
INSERT INTO platform.expansion_addons (code, expansion_type, user_count, tenure, price, storage, description)
VALUES
  ('ADDON_USER_500_1M', 'USER_CAPACITY_EXPANSION', 'PLUS_500', 'ONE_MONTH', 4500.00, 'GB_20', 'Capacity pack adding 500 users and 20GB storage for 1 month'),
  ('ADDON_USER_500_3M', 'USER_CAPACITY_EXPANSION', 'PLUS_500', 'THREE_MONTHS', 4275.00, 'GB_20', 'Capacity pack adding 500 users and 20GB storage for 3 months'),
  ('ADDON_USER_500_6M', 'USER_CAPACITY_EXPANSION', 'PLUS_500', 'SIX_MONTHS', 4050.00, 'GB_20', 'Capacity pack adding 500 users and 20GB storage for 6 months'),
  ('ADDON_USER_500_12M', 'USER_CAPACITY_EXPANSION', 'PLUS_500', 'TWELVE_MONTHS', 3825.00, 'GB_20', 'Capacity pack adding 500 users and 20GB storage for 12 months'),
  ('ADDON_USER_500_24M', 'USER_CAPACITY_EXPANSION', 'PLUS_500', 'TWENTY_FOUR', 3510.00, 'GB_20', 'Capacity pack adding 500 users and 20GB storage for 24 months'),
  ('ADDON_USER_500_36M', 'USER_CAPACITY_EXPANSION', 'PLUS_500', 'THIRTY_SIX', 3150.00, 'GB_20', 'Capacity pack adding 500 users and 20GB storage for 36 months'),
  ('ADDON_USER_1000_1M', 'USER_CAPACITY_EXPANSION', 'PLUS_1000', 'ONE_MONTH', 8000.00, 'GB_20', 'Capacity pack adding 1000 users and 20GB storage for 1 month'),
  ('ADDON_USER_1000_3M', 'USER_CAPACITY_EXPANSION', 'PLUS_1000', 'THREE_MONTHS', 7600.00, 'GB_20', 'Capacity pack adding 1000 users and 20GB storage for 3 months'),
  ('ADDON_USER_1000_6M', 'USER_CAPACITY_EXPANSION', 'PLUS_1000', 'SIX_MONTHS', 7200.00, 'GB_20', 'Capacity pack adding 1000 users and 20GB storage for 6 months'),
  ('ADDON_USER_1000_12M', 'USER_CAPACITY_EXPANSION', 'PLUS_1000', 'TWELVE_MONTHS', 6800.00, 'GB_20', 'Capacity pack adding 1000 users and 20GB storage for 12 months'),
  ('ADDON_USER_1000_24M', 'USER_CAPACITY_EXPANSION', 'PLUS_1000', 'TWENTY_FOUR', 6240.00, 'GB_20', 'Capacity pack adding 1000 users and 20GB storage for 24 months'),
  ('ADDON_USER_1000_36M', 'USER_CAPACITY_EXPANSION', 'PLUS_1000', 'THIRTY_SIX', 5600.00, 'GB_20', 'Capacity pack adding 1000 users and 20GB storage for 36 months')
ON CONFLICT (code) WHERE deleted_at IS NULL DO NOTHING;

-- In case this script runs against a DB where these rows already existed
-- with different values (e.g. from an earlier flat-price version of this
-- script), force them to the tenure-specific prices above.
UPDATE platform.expansion_addons SET discount = NULL, discount_percentage = NULL,
  price = CASE tenure
    WHEN 'ONE_MONTH' THEN 4500.00 WHEN 'THREE_MONTHS' THEN 4275.00 WHEN 'SIX_MONTHS' THEN 4050.00
    WHEN 'TWELVE_MONTHS' THEN 3825.00 WHEN 'TWENTY_FOUR' THEN 3510.00 WHEN 'THIRTY_SIX' THEN 3150.00
  END
WHERE user_count = 'PLUS_500';

UPDATE platform.expansion_addons SET discount = NULL, discount_percentage = NULL,
  price = CASE tenure
    WHEN 'ONE_MONTH' THEN 8000.00 WHEN 'THREE_MONTHS' THEN 7600.00 WHEN 'SIX_MONTHS' THEN 7200.00
    WHEN 'TWELVE_MONTHS' THEN 6800.00 WHEN 'TWENTY_FOUR' THEN 6240.00 WHEN 'THIRTY_SIX' THEN 5600.00
  END
WHERE user_count = 'PLUS_1000';

COMMIT;
