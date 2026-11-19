/** Safe, bounded transport; no external hosts reachable from the browser. */
export async function getJson(path, options = {}) {
  if (!/^\/api\/[a-z]+(?:\?[a-z0-9=&%+._-]+)?$/i.test(path)) throw new Error('Invalid API path');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 25000);
  try {
    const response = await fetch(path, {
      ...options,
      headers: {...(options.body ? {'Content-Type': 'application/json'} : {}), ...(options.headers || {})},
      cache: 'no-store', credentials: 'same-origin', signal: controller.signal,
    });
    if (!response.ok) {
      let message = `HTTP ${response.status}`;
      try {const body = await response.json();message = body.detail || body.error || message;} catch { /* no body */ }
      throw new Error(typeof message === 'string' ? message.slice(0,250) : `HTTP ${response.status}`);
    }
    return response.json();
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('Request timed out. Retry when connectivity improves.');
    throw error;
  } finally {clearTimeout(timeout);}
}
