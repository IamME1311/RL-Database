/**
 * Mirrors settings.ALLOWED_DOMAINS in backend/app/core/config.py.
 *
 * This is purely for fast inline feedback in the login form — the backend must
 * enforce it independently, for both password and Google sign-in. (Today it does
 * neither: `WorkEmail` in backend/app/models/auth.py is defined but never applied
 * to User.email.)
 */
export const ALLOWED_EMAIL_DOMAINS = ['ripplelinks.com'];

export function emailDomain(email: string): string {
  return email.split('@').pop()?.toLowerCase().trim() ?? '';
}

export function isAllowedDomain(email: string): boolean {
  return ALLOWED_EMAIL_DOMAINS.includes(emailDomain(email));
}

export function looksLikeEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

/** Returns a message when the email is unusable, or null when it's fine. */
export function validateWorkEmail(email: string): string | null {
  const trimmed = email.trim();
  if (!trimmed) return null;
  if (!looksLikeEmail(trimmed)) return 'Enter a valid email address.';
  if (!isAllowedDomain(trimmed)) {
    return `Only ${ALLOWED_EMAIL_DOMAINS.map((d) => `@${d}`).join(' or ')} addresses can sign in.`;
  }
  return null;
}
