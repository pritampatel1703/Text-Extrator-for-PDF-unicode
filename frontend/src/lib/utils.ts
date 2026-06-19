/**
 * Utility functions for the PDF Search Platform.
 */

/**
 * Format file size from bytes to human-readable string.
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Format date to localized string.
 */
export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return '—';
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format relative time (e.g., "2 hours ago").
 */
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(dateString);
}

/**
 * Get status color class for processing status.
 */
export function getStatusColor(status: string): string {
  switch (status) {
    case 'completed':
      return 'text-emerald-400 bg-emerald-400/10';
    case 'processing':
      return 'text-amber-400 bg-amber-400/10';
    case 'pending':
      return 'text-blue-400 bg-blue-400/10';
    case 'failed':
      return 'text-red-400 bg-red-400/10';
    default:
      return 'text-gray-400 bg-gray-400/10';
  }
}

/**
 * Get language display name from ISO code.
 */
export function getLanguageName(code: string | null): string {
  if (!code) return 'Unknown';
  const languages: Record<string, string> = {
    en: 'English',
    hi: 'Hindi',
    gu: 'Gujarati',
    ar: 'Arabic',
    zh: 'Chinese',
    'zh-cn': 'Chinese',
    ja: 'Japanese',
    ko: 'Korean',
    ru: 'Russian',
    fr: 'French',
    de: 'German',
    es: 'Spanish',
    pt: 'Portuguese',
    it: 'Italian',
  };
  return languages[code] || code.toUpperCase();
}

/**
 * Debounce function for search input.
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

/**
 * Truncate text with ellipsis.
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

/**
 * Generate a unique client-side ID.
 */
export function generateId(): string {
  return Math.random().toString(36).substring(2) + Date.now().toString(36);
}

/**
 * CN utility — Merge class names conditionally.
 */
export function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}
