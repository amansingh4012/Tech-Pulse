import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, Clock, Database, Layers, RefreshCw, Zap } from 'lucide-react';
import { fetchStats, fetchTrending, fetchArticles, triggerFullScrape, triggerScrape } from '../api';
import { formatDistanceToNow } from 'date-fns';

export default function Dashboard() {
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const { data, isLoading: loading } = useQuery({
    queryKey: ['dashboardData'],
    queryFn: async () => {
      const [statsData, latestData, trendingData] = await Promise.all([
        fetchStats(),
        fetchArticles({ page: 1 }),
        fetchTrending(10)
      ]);
      return { 
        stats: statsData, 
        latest: latestData?.articles || [], 
        trending: trendingData?.articles || [] 
      };
    }
  });

  const stats = data?.stats;
  const latest = data?.latest || [];
  const trending = data?.trending || [];

  const handleScrape = async (source: string) => {
    setActionLoading(source);
    try {
      if (source === 'all') {
        await triggerFullScrape();
      } else {
        await triggerScrape(source);
      }
      // Refresh
      window.location.reload();
    } catch (err) {
      alert(`Error running scrape for ${source}: \n${err}`);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
      <div className="loader"></div>
    </div>
  );

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1>Tech News Intelligence</h1>
        <p className="text-muted">Real-time aggregated industry signals and trends.</p>
      </div>
      
      {/* KPI Cards */}
      <div className="grid-4" style={{ marginBottom: '2.5rem' }}>
        <div className="card glass-panel" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ padding: '1rem', background: 'var(--primary-glow)', borderRadius: 'var(--radius-md)', color: 'var(--primary)' }}>
            <Database size={24} />
          </div>
          <div>
            <div className="text-muted" style={{ fontSize: '0.875rem' }}>Total Articles</div>
            <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>{stats?.total_articles}</div>
          </div>
        </div>
        <div className="card glass-panel" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ padding: '1rem', background: 'rgba(16, 185, 129, 0.1)', borderRadius: 'var(--radius-md)', color: 'var(--success)' }}>
            <BarChart3 size={24} />
          </div>
          <div>
            <div className="text-muted" style={{ fontSize: '0.875rem' }}>Active Sources</div>
            <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>{Object.keys(stats?.by_source || {}).length}</div>
          </div>
        </div>
        <div className="card glass-panel" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ padding: '1rem', background: 'rgba(245, 158, 11, 0.1)', borderRadius: 'var(--radius-md)', color: 'var(--warning)' }}>
            <Layers size={24} />
          </div>
          <div>
            <div className="text-muted" style={{ fontSize: '0.875rem' }}>Categories</div>
            <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>{Object.keys(stats?.by_category || {}).length}</div>
          </div>
        </div>
        <div className="card glass-panel" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ padding: '1rem', background: 'rgba(99, 102, 241, 0.1)', borderRadius: 'var(--radius-md)', color: '#6366f1' }}>
            <Clock size={24} />
          </div>
          <div>
            <div className="text-muted" style={{ fontSize: '0.875rem' }}>Last Scrape</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>
              {stats?.last_scraped ? formatDistanceToNow(new Date(stats.last_scraped), { addSuffix: true }) : 'N/A'}
            </div>
          </div>
        </div>
      </div>

      <div className="grid-2">
        {/* Latest Articles */}
        <div className="card glass-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h2>Latest Signals</h2>
            <Link to="/articles" className="btn btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem' }}>
              View All
            </Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {latest.slice(0, 6).map((article: any) => (
              <div key={article.id} style={{ paddingBottom: '1rem', borderBottom: '1px solid var(--card-border)' }}>
                <Link to={`/article/${article.id}`} style={{ textDecoration: 'none', color: 'var(--text-main)', fontWeight: 500, display: 'block', marginBottom: '0.5rem' }}>
                  {article.title}
                </Link>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span className="badge badge-source">{article.source}</span>
                  {article.category && <span className="badge badge-category">{article.category}</span>}
                  <span className="text-light" style={{ fontSize: '0.75rem' }}>
                    {article.published_at ? new Date(article.published_at).toLocaleDateString() : ''}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Action Panel & Trending */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="card glass-panel" style={{ background: 'linear-gradient(to right bottom, #1e293b, #0f172a)', color: 'white' }}>
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'white' }}><Zap size={20} /> Data Pipelines</h2>
            <p style={{ color: '#94a3b8', marginBottom: '1.5rem', fontSize: '0.875rem' }}>Trigger on-demand data extraction.</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
              <button 
                onClick={() => handleScrape('hackernews')} 
                disabled={!!actionLoading}
                className="btn btn-secondary" style={{ background: 'rgba(255,255,255,0.1)', color: 'white', borderColor: 'rgba(255,255,255,0.2)' }}
              >
                {actionLoading === 'hackernews' ? <RefreshCw size={16} className="loader" style={{width: 16, height: 16, border: '2px solid white', borderTopColor: 'transparent'}} /> : 'Scrape HN'}
              </button>
              <button 
                onClick={() => handleScrape('techcrunch')} 
                disabled={!!actionLoading}
                className="btn btn-secondary" style={{ background: 'rgba(255,255,255,0.1)', color: 'white', borderColor: 'rgba(255,255,255,0.2)' }}
              >
                {actionLoading === 'techcrunch' ? '...' : 'Scrape TechCrunch'}
              </button>
              <button 
                onClick={() => handleScrape('all')} 
                disabled={!!actionLoading}
                className="btn btn-primary" style={{ flexGrow: 1 }}
              >
                {actionLoading === 'all' ? 'Running Pipeline...' : 'Run All Scrapers'}
              </button>
            </div>
          </div>

          <div className="card glass-panel" style={{ flexGrow: 1 }}>
            <h2>🔥 Trending</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {trending.map((article: any) => (
                <div key={article.id}>
                  <Link to={`/article/${article.id}`} style={{ textDecoration: 'none', color: 'var(--text-main)', fontWeight: 500, display: 'block', fontSize: '0.875rem' }}>
                    {article.title}
                  </Link>
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.3rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <span>{article.source}</span>
                    {article.extra_data?.score && <span>⭐ {article.extra_data.score}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
