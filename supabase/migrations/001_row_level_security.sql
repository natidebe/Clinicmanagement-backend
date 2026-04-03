-- =============================================================================
-- Row Level Security (RLS) — Clinic Isolation
-- =============================================================================
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New query).
--
-- WHY a helper function instead of auth.jwt() ->> 'clinic_id':
--   clinic_id is NOT a default Supabase JWT claim. Reading it from the JWT
--   would require a custom Auth Hook. Instead, we use a SECURITY DEFINER
--   function that reads the current user's clinic_id from the profiles table,
--   bypassing RLS on that one read so there is no circular dependency.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Helper: returns the clinic_id of the currently authenticated user
-- SECURITY DEFINER + explicit search_path = runs as the function owner
-- (postgres), which bypasses RLS on profiles — no circular dependency.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.current_clinic_id()
RETURNS uuid
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT clinic_id
  FROM public.profiles
  WHERE id = auth.uid()
$$;


-- =============================================================================
-- profiles
-- =============================================================================
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Users can read any profile in their own clinic
CREATE POLICY "profiles: clinic members can read"
ON public.profiles
FOR SELECT
USING (clinic_id = public.current_clinic_id());

-- Users can update only their own profile row
CREATE POLICY "profiles: users can update own row"
ON public.profiles
FOR UPDATE
USING (id = auth.uid())
WITH CHECK (id = auth.uid());

-- Only service-role (Django backend) can INSERT / DELETE profiles
-- (no authenticated-role policies for INSERT/DELETE = those are blocked)


-- =============================================================================
-- patients
-- =============================================================================
ALTER TABLE public.patients ENABLE ROW LEVEL SECURITY;

CREATE POLICY "patients: clinic isolation"
ON public.patients
FOR ALL
USING (clinic_id = public.current_clinic_id())
WITH CHECK (clinic_id = public.current_clinic_id());


-- =============================================================================
-- visits
-- =============================================================================
ALTER TABLE public.visits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "visits: clinic isolation"
ON public.visits
FOR ALL
USING (clinic_id = public.current_clinic_id())
WITH CHECK (clinic_id = public.current_clinic_id());


-- =============================================================================
-- consultations  (no clinic_id — resolved via visit)
-- =============================================================================
ALTER TABLE public.consultations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "consultations: clinic isolation"
ON public.consultations
FOR ALL
USING (
  visit_id IN (
    SELECT id FROM public.visits
    WHERE clinic_id = public.current_clinic_id()
  )
)
WITH CHECK (
  visit_id IN (
    SELECT id FROM public.visits
    WHERE clinic_id = public.current_clinic_id()
  )
);


-- =============================================================================
-- lab_tests
-- =============================================================================
ALTER TABLE public.lab_tests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "lab_tests: clinic isolation"
ON public.lab_tests
FOR ALL
USING (clinic_id = public.current_clinic_id())
WITH CHECK (clinic_id = public.current_clinic_id());


-- =============================================================================
-- test_orders  (no clinic_id — resolved via visit)
-- =============================================================================
ALTER TABLE public.test_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "test_orders: clinic isolation"
ON public.test_orders
FOR ALL
USING (
  visit_id IN (
    SELECT id FROM public.visits
    WHERE clinic_id = public.current_clinic_id()
  )
)
WITH CHECK (
  visit_id IN (
    SELECT id FROM public.visits
    WHERE clinic_id = public.current_clinic_id()
  )
);


-- =============================================================================
-- test_results  (no clinic_id — resolved via test_order → visit)
-- =============================================================================
ALTER TABLE public.test_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "test_results: clinic isolation"
ON public.test_results
FOR ALL
USING (
  test_order_id IN (
    SELECT o.id FROM public.test_orders o
    JOIN public.visits v ON v.id = o.visit_id
    WHERE v.clinic_id = public.current_clinic_id()
  )
)
WITH CHECK (
  test_order_id IN (
    SELECT o.id FROM public.test_orders o
    JOIN public.visits v ON v.id = o.visit_id
    WHERE v.clinic_id = public.current_clinic_id()
  )
);


-- =============================================================================
-- audit_logs
-- =============================================================================
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "audit_logs: clinic isolation"
ON public.audit_logs
FOR ALL
USING (clinic_id = public.current_clinic_id())
WITH CHECK (clinic_id = public.current_clinic_id());


-- =============================================================================
-- Verification — run this after applying to confirm RLS is active
-- =============================================================================
-- SELECT tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public'
-- ORDER BY tablename;
