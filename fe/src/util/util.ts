export function parseDuration(cssValue: string): number {
  const val = cssValue.trim();
  if (val.endsWith("ms")) {
    return parseFloat(val) / 1000;
  }
  return parseFloat(val) || 0;
}
