export function formatDateTime(isoString) {
  if (!isoString) return '';
  const dt = new Date(isoString);
  if (Number.isNaN(dt.getTime())) return isoString;

  // Use the user's locale by leaving the locale undefined.
  const parts = new Intl.DateTimeFormat(undefined, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  }).formatToParts(dt);

  const lookup = {};
  for (const p of parts) {
    if (p.type && p.type !== 'literal') lookup[p.type] = p.value;
  }

  // Build string like: 04 Jul 2026, 03:34 PM
  const day = lookup.day || '';
  const month = lookup.month || '';
  const year = lookup.year || '';
  const hour = lookup.hour || '';
  const minute = lookup.minute || '';
  const dayPeriod = lookup.dayPeriod || '';

  return `${day} ${month} ${year}, ${hour}:${minute} ${dayPeriod}`.trim();
}
