const API_BASE = import.meta.env.PROD ? '/api/v1' : 'http://localhost:8000/api/v1';

export async function fetchStats() {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function fetchTrending(limit = 10) {
  const res = await fetch(`${API_BASE}/articles/trending?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch trending');
  return res.json();
}

export async function fetchArticles(params: { source?: string, category?: string, page?: number } = {}) {
  const query = new URLSearchParams();
  if (params.source) query.append('source', params.source);
  if (params.category) query.append('category', params.category);
  if (params.page) query.append('page', params.page.toString());
  
  const res = await fetch(`${API_BASE}/articles?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch articles');
  return res.json();
}

export async function fetchArticle(id: number | string) {
  const res = await fetch(`${API_BASE}/articles/${id}`);
  if (!res.ok) throw new Error('Failed to fetch article');
  return res.json();
}

export async function triggerScrape(source: string) {
  const res = await fetch(`${API_BASE}/scrape/${source}`, { method: 'POST' });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || 'Failed to scrape');
  }
  return res.json();
}

export async function triggerFullScrape() {
  const res = await fetch(`${API_BASE}/scrape`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to run full scrape');
  return res.json();
}

export async function fetchPipelineStatus() {
  const res = await fetch(`${API_BASE}/pipeline/status`);
  if (!res.ok) throw new Error('Failed to fetch pipeline status');
  return res.json();
}
