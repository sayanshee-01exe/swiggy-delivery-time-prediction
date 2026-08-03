// The SPA and the API are served from one CloudFront distribution, so these
// paths are same-origin in production. In development the Vite proxy forwards
// /api to the local FastAPI process. Never hardcode a host here: an absolute
// http:// URL would be blocked as mixed content on the HTTPS site.

/** Turn a FastAPI error body into something worth showing a person. */
function describeError(status, body) {
  const detail = body?.detail;

  // 422 from pydantic: a list of per-field problems
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = item.loc?.filter((part) => part !== 'body').join('.');
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .join('; ');
  }

  if (typeof detail === 'string') return detail;

  return `Request failed (${status}).`;
}

async function request(path, options) {
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    // fetch only rejects on network-level failure, never on an HTTP error
    throw new Error(
      'Could not reach the prediction service. Check your connection and try again.'
    );
  }

  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    throw new Error(describeError(response.status, body));
  }

  return body;
}

export function predict(order) {
  return request('/api/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(order),
  });
}

export function health() {
  return request('/api/health', { method: 'GET' });
}
