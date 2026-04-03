-- =============================================================================
-- Custom JWT Claims Hook
-- =============================================================================
-- Injects clinic_id and user_role into every Supabase-issued access token.
--
-- After running this SQL you must enable the hook in the Supabase Dashboard:
--   Authentication → Hooks → Customize Access Token (JWT Claims)
--   → Select "Postgres function" → choose public.custom_access_token_hook
--
-- Claim names:
--   clinic_id  — UUID of the user's clinic (as text in JWT)
--   user_role  — application role: admin | doctor | lab_tech | receptionist
--
-- We intentionally do NOT override the built-in "role" claim — that one is
-- set to "authenticated" by Supabase and is used internally by RLS policies.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.custom_access_token_hook(event jsonb)
RETURNS jsonb
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  claims      jsonb;
  user_clinic_id  uuid;
  user_app_role   text;
BEGIN
  -- Read clinic_id and role from profiles (this runs as the function owner,
  -- bypassing RLS — safe because the hook only fires for authenticated users
  -- whose token has already been issued by Supabase Auth).
  SELECT clinic_id, role
  INTO user_clinic_id, user_app_role
  FROM public.profiles
  WHERE id = (event ->> 'user_id')::uuid;

  claims := event -> 'claims';

  -- If the profile row doesn't exist yet (race condition during signup),
  -- return the token without custom claims — Django auth will reject it.
  IF user_clinic_id IS NULL THEN
    RETURN event;
  END IF;

  -- Inject our custom claims
  claims := jsonb_set(claims, '{clinic_id}', to_jsonb(user_clinic_id::text));
  claims := jsonb_set(claims, '{user_role}', to_jsonb(user_app_role));

  RETURN jsonb_set(event, '{claims}', claims);
END;
$$;

-- Grant the auth system permission to call this function
GRANT EXECUTE ON FUNCTION public.custom_access_token_hook TO supabase_auth_admin;

-- Revoke from public so nothing else can call it directly
REVOKE EXECUTE ON FUNCTION public.custom_access_token_hook FROM PUBLIC;
