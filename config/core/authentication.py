import jwt
from jwt import PyJWKClient
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

# Fetches and caches Supabase's public keys (ES256).
# Falls back to HS256 with SUPABASE_JWT_SECRET if the JWKS fetch fails.
_jwks_client = None


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        from django.conf import settings as s
        supabase_url = s.SUPABASE_URL
        if supabase_url:
            jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
            _jwks_client = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
    return _jwks_client


class SupabaseJWTAuthentication(BaseAuthentication):
    """
    Validates Supabase-issued JWTs.
    Supports ES256 (asymmetric, via JWKS) and HS256 (symmetric, via SUPABASE_JWT_SECRET).
    Sets request.user to the matching Profile instance.
    """

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]

        try:
            header = jwt.get_unverified_header(token)
            alg = header.get("alg", "HS256")

            if alg == "ES256":
                client = _get_jwks_client()
                if client is None:
                    raise AuthenticationFailed("JWKS client unavailable — SUPABASE_URL is not configured.")
                signing_key = client.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["ES256"],
                    audience="authenticated",
                )
            else:
                payload = jwt.decode(
                    token,
                    settings.SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    audience="authenticated",
                )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token expired.")
        except jwt.InvalidAudienceError:
            raise AuthenticationFailed("Invalid token audience.")
        except jwt.InvalidTokenError as exc:
            raise AuthenticationFailed(f"Invalid token: {exc}")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationFailed("Token missing sub claim.")

        from users.models import Profile

        try:
            profile = Profile.objects.get(id=user_id)
        except Profile.DoesNotExist:
            raise AuthenticationFailed("No profile found for this user.")

        return (profile, token)

    def authenticate_header(self, request):
        return "Bearer"
