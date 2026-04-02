import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, Database, Layers, RefreshCw, Zap, TrendingUp, ChevronRight, Activity } from 'lucide-react';
import { fetchStats, fetchTrending, fetchArticles, triggerFullScrape, triggerScrape, fetchPipelineStatus } from '../api';

export default function Dashboard() {
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const { data, isLoading: loading, isError, error } = useQuery({
    queryKey: ['dashboardData'],
    queryFn: async () => {
      const [statsData, latestData, trendingData, pipelineData] = await Promise.all([
        fetchStats(),
        fetchArticles({ page: 1 }),
        fetchTrending(10),
        fetchPipelineStatus()
      ]);
      return { 
        stats: statsData, 
        latest: latestData?.articles || [], 
        trending: trendingData?.articles || [],
        pipeline: pipelineData
      };
    },
    retry: 1,
    refetchInterval: 5000 // Refetch every 5s to sync with the new pipeline ticker
  });

  const stats = data?.stats;
  const latest = data?.latest || [];
  const trending = data?.trending || [];
  const pipeline = data?.pipeline;

  const handleScrape = async (source: string) => {
    setActionLoading(source);
    try {
      if (source === 'all') {
        await triggerFullScrape();
      } else {
        await triggerScrape(source);
      }
      setTimeout(() => window.location.reload(), 1000); // Give it a second to reflect
    } catch (err) {
      alert(`Error running scrape for ${source}: \n${err}`);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
      <div className="loader" style={{ width: 40, height: 40, borderWidth: 3 }}></div>
    </div>
  );

  if (isError) return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh', flexDirection: 'column' }}>
      <h3 style={{ color: 'var(--danger)', marginBottom: '1rem' }}>Connection Error</h3>
      <p className="text-muted" style={{ maxWidth: '400px', textAlign: 'center' }}>
        Failed to fetch dashboard data. Please ensure the backend server is running and accessible.
      </p>
      <pre style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(0,0,0,0.5)', borderRadius: '8px', fontSize: '0.8rem', color: 'var(--danger-light)' }}>
        {error instanceof Error ? error.message : 'Unknown error occurred'}
      </pre>
    </div>
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '2.5rem' }}>
        <div>
          <h1>Tech News Intelligence</h1>
          <p className="text-muted">Real-time aggregated industry signals and trends.</p>
        </div>
        
        {/* Auto Scrape Status Banner */}
        {pipeline?.is_running && (
          <div style={{ 
            display: 'flex', alignItems: 'center', gap: '0.75rem', 
            background: 'rgba(99, 102, 241, 0.1)', border: '1px solid var(--primary)', 
            padding: '0.5rem 1rem', borderRadius: 'var(--radius-md)',
            animation: 'pulse 2s infinite'
          }}>
            <div className="loader" style={{ width: '16px', height: '16px', borderWidth: '2px', borderColor: 'rgba(255,255,255,0.2)', borderTopColor: 'var(--primary)' }}></div>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--primary)' }}>Automated Pipeline Live (Queue: {pipeline?.queue_size})</span>
          </div>
        )}
      </div>
      
      {/* KPI Cards */}
      <div className="grid-4" style={{ marginBottom: '2.5rem' }}>
        <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <div style={{ padding: '1rem', background: 'rgba(99, 102, 241, 0.15)', borderRadius: 'var(--radius-lg)', color: 'var(--primary)' }}>
            <Database size={24} />
          </div>
          <div>
            <div className="text-muted" style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>Total Articles</div>
            <div style={{ fontSize: '1.875rem', fontWeight: 700, color: 'white' }}>{stats?.total_articles?.toLocaleString()}</div>
          </div>
        </div>
        
        <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <div style={{ padding: '1rem', background: 'var(--success-glow)', borderRadius: 'var(--radius-lg)', color: 'var(--success)' }}>
            <BarChart3 size={24} />
          </div>
          <div>
            <div className="text-muted" style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>Active Sources</div>
            <div style={{ fontSize: '1.875rem', fontWeight: 700, color: 'white' }}>{Object.keys(stats?.by_source || {}).length}</div>
          </div>
        </div>
        
        <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <div style={{ padding: '1rem', background: 'var(--warning-glow)', borderRadius: 'var(--radius-lg)', color: 'var(--warning)' }}>
            <Layers size={24} />
          </div>
          <div>
            <div className="text-muted" style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>Categories</div>
            <div style={{ fontSize: '1.875rem', fontWeight: 700, color: 'white' }}>{Object.keys(stats?.by_category || {}).length}</div>
          </div>
        </div>
        
        <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <div style={{ padding: '1rem', background: 'rgba(168, 85, 247, 0.15)', borderRadius: 'var(--radius-lg)', color: '#a855f7' }}>
            <Activity size={24} />
          </div>
          <div>
            <div className="text-muted" style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>Pipeline Gen</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 600, color: 'white', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ color: 'var(--primary-light)' }}>+{pipeline?.stats?.articles_generated || 0}</span> 
              <span style={{ fontSize: '0.8rem', color: 'var(--text-light)', fontWeight: 400 }}>(/5s)</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid-2">
        {/* Latest Articles */}
        <div className="glass-panel" style={{ padding: '0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1.5rem', borderBottom: '1px solid var(--card-border)' }}>
            <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Zap size={20} className="text-gradient" /> Latest Signals
            </h2>
            <Link to="/articles" className="btn btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem' }}>
              View All <ChevronRight size={14} />
            </Link>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', padding: '1rem' }}>
            {latest.slice(0, 6).map((article: any) => (
              <div key={article.id} className="list-item">
                <Link to={`/article/${article.id}`} className="list-item-title" style={{ fontSize: '1.05rem', lineHeight: '1.4' }}>
                  {article.title}
                </Link>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginTop: '0.5rem' }}>
                  <span className="badge badge-source">{article.source}</span>
                  {article.category && <span className="badge badge-category">{article.category}</span>}
                  <span className="text-light" style={{ marginLeft: 'auto', fontSize: '0.8rem' }}>
                    {article.published_at ? new Date(article.published_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : ''}
                  </span>
                </div>
              </div>
            ))}
            {latest.length === 0 && (
              <div className="text-muted" style={{ padding: '2rem', textAlign: 'center' }}>No signals yet. Run the scrapers to fetch data.</div>
            )}
          </div>
        </div>

        {/* Right Column: Action Panel & Trending */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          <div className="glass-panel" style={{ background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%)', position: 'relative', overflow: 'hidden' }}>
            {/* Decorative background circle */}
            <div style={{ position: 'absolute', top: '-10%', right: '-10%', width: '150px', height: '150px', background: 'var(--primary-glow)', borderRadius: '50%', filter: 'blur(40px)', zIndex: 0 }}></div>
            
            <div style={{ padding: '1.5rem', position: 'relative', zIndex: 1 }}>
              <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Activity size={20} className="text-gradient" /> 
                Data Pipelines
              </h2>
              <p className="text-muted" style={{ marginBottom: '1.5rem', fontSize: '0.9rem' }}>Trigger on-demand data extraction layer.</p>
              
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
                <button 
                  onClick={() => handleScrape('hackernews')} 
                  disabled={!!actionLoading}
                  className="btn btn-secondary" style={{ flexGrow: 1 }}
                >
                  {actionLoading === 'hackernews' ? <div className="loader" /> : 'Scrape HN'}
                </button>
                <button 
                  onClick={() => handleScrape('techcrunch')} 
                  disabled={!!actionLoading}
                  className="btn btn-secondary" style={{ flexGrow: 1 }}
                >
                  {actionLoading === 'techcrunch' ? <div className="loader" /> : 'Scrape TC'}
                </button>
                <button 
                  onClick={() => handleScrape('all')} 
                  disabled={!!actionLoading}
                  className="btn btn-primary" style={{ width: '100%', marginTop: '0.5rem' }}
                >
                  {actionLoading === 'all' ? (
                    <><div className="loader" style={{ borderColor: 'rgba(255,255,255,0.2)', borderTopColor: 'white'}} /> Executing Pipeline...</>
                  ) : (
                    <><RefreshCw size={16} /> Run All Scrapers</>
                  )}
                </button>
              </div>
            </div>
          </div>

          <div className="glass-panel" style={{ flexGrow: 1, padding: 0 }}>
            <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--card-border)' }}>
              <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <TrendingUp size={20} className="text-gradient" /> Trending
              </h2>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', padding: '1rem' }}>
              {trending.slice(0, 5).map((article: any, index: number) => (
                <Link to={`/article/${article.id}`} key={article.id} className="list-item" style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                  <div style={{ fontWeight: 700, color: 'var(--primary)', opacity: 0.8, marginTop: '2px' }}>0{index + 1}</div>
                  <div>
                    <div className="list-item-title" style={{ margin: 0, fontSize: '0.95rem' }}>{article.title}</div>
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.3rem', fontSize: '0.75rem', color: 'var(--text-light)' }}>
                      <span style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>{article.source}</span>
                      {article.extra_data?.score && (
                        <span style={{ color: 'var(--warning)', display: 'flex', alignItems: 'center', gap: '2px' }}>
                          ★ {article.extra_data.score}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              ))}
              {trending.length === 0 && (
                <div className="text-muted" style={{ padding: '2rem', textAlign: 'center', fontSize: '0.9rem' }}>Not enough data for trending analysis.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
