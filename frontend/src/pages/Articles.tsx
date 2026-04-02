import { Link, useSearchParams } from 'react-router-dom';
import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import { fetchArticles, fetchStats } from '../api';
import { Filter, Search, ChevronRight, ArrowRight } from 'lucide-react';
import DOMPurify from 'dompurify';
import './Articles.css';

export default function Articles() {
  const [searchParams, setSearchParams] = useSearchParams();
  const sourceParam = searchParams.get('source') || '';
  const categoryParam = searchParams.get('category') || '';
  
  const { data: statsData } = useQuery({
    queryKey: ['stats'],
    queryFn: fetchStats,
  });

  const sources = Object.keys(statsData?.by_source || {});
  const categories = Object.keys(statsData?.by_category || {});

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isLoading: loading,
    isError,
    error,
  } = useInfiniteQuery({
    queryKey: ['articles', sourceParam, categoryParam],
    queryFn: ({ pageParam = 1 }) => fetchArticles({ source: sourceParam, category: categoryParam, page: pageParam }),
    getNextPageParam: (lastPage) => lastPage.has_more ? lastPage.page + 1 : undefined,
    initialPageParam: 1,
    retry: 1,
  });

  const articles = data ? data.pages.flatMap(page => page.articles) : [];

  const handleSourceChange = (source: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (source === '') newParams.delete('source');
    else newParams.set('source', source);
    setSearchParams(newParams);
  };

  const handleCategoryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newParams = new URLSearchParams(searchParams);
    if (e.target.value) newParams.set('category', e.target.value);
    else newParams.delete('category');
    setSearchParams(newParams);
  };

  const formatSummary = (text: string) => {
    if (!text) return '';
    // Split by whitespace to accurately count words
    const words = text.split(/\s+/);
    if (words.length <= 100) return text;
    // Truncate to 100 words and append ellipsis
    return words.slice(0, 100).join(' ') + '...';
  };

  return (
    <div className="articles-container">
      {/* Page Header */}
      <header className="page-header">
        <div className="page-header-label">
          <span className="page-header-line"></span>
          <span className="page-header-text">Content Hub</span>
        </div>
        <h3 className="page-title">Intelligence Feed</h3>
        <p className="page-description">
          The central feed for cross-sector innovation. Aggregate insights from global sources filtered through the lens of enterprise intelligence.
        </p>
      </header>

      {/* Filters Section */}
      <section className="filters-section">
        <div className="filters-group">
          <button 
            className={`filter-btn ${sourceParam === '' ? 'active' : ''}`}
            onClick={() => handleSourceChange('')}
          >
            <Filter size={16} /> All Sources
          </button>
          
          {sources.map(s => (
            <button 
              key={s} 
              className={`filter-btn ${sourceParam === s ? 'active' : ''}`}
              onClick={() => handleSourceChange(s)}
            >
              {s}
            </button>
          ))}
        </div>
        
        <div className="filters-group">
          <div className="select-filter-wrapper group">
            <select 
              className="select-filter"
              value={categoryParam} 
              onChange={handleCategoryChange}
            >
              <option value="">Category: All</option>
              {categories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            <Filter className="select-icon" size={16} />
          </div>
        </div>
      </section>

      {/* Articles Feed */}
      <div className="feed-grid">
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '10rem 0' }}>
            <div className="loader" style={{ width: 40, height: 40, borderWidth: '3px' }}></div>
          </div>
        ) : isError ? (
          <div className="empty-state" style={{ minHeight: '40vh' }}>
            <div style={{ display: 'inline-block', padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '50%', marginBottom: '1rem', color: 'var(--danger)' }}>
              <Search size={32} />
            </div>
            <h3 style={{ color: 'var(--danger)' }}>Failed to load signals</h3>
            <p style={{ maxWidth: '400px', margin: '0 auto 1rem' }}>We couldn't connect to the Tech Pulse API. Please verify the backend is running.</p>
            <pre style={{ padding: '1rem', background: 'rgba(0,0,0,0.5)', borderRadius: '8px', fontSize: '0.8rem', color: 'var(--danger-light)', maxWidth: '500px', margin: '0 auto', textAlign: 'left', overflowX: 'auto' }}>
              {error instanceof Error ? error.message : 'Unknown network error'}
            </pre>
          </div>
        ) : articles.length === 0 ? (
          <div className="empty-state">
            <Search size={48} style={{ opacity: 0.2, margin: '0 auto 1.5rem', color: 'var(--primary)' }} />
            <h3>No signals found</h3>
            <p>Try adjusting your data filters or running scrapers.</p>
          </div>
        ) : (
          articles.map((article: any) => (
            <article key={article.id} className="feed-card group">
              <div className="feed-card-bg-gradient"></div>
              
              <div className="feed-card-image">
                <img 
                  src={article.image_url || 'https://images.unsplash.com/photo-1518770660439-4636190af475?ixlib=rb-4.0.3&auto=format&fit=crop&w=1000&q=80'} 
                  alt="Article visual" 
                />
              </div>
              
              <div className="feed-card-content">
                <div className="feed-card-meta">
                  <span className="badge badge-source">{article.source_name || article.source}</span>
                  {article.category && <span className="badge badge-category">{article.category}</span>}
                  <span className="feed-card-time">
                    {article.published_at ? new Date(article.published_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''}
                  </span>
                </div>
                
                <h4 className="feed-card-title">{article.title}</h4>
                
                {article.summary && (
                  <div 
                    className="feed-card-excerpt" 
                    dangerouslySetInnerHTML={{ 
                      __html: DOMPurify.sanitize(formatSummary(article.summary), { ALLOWED_TAGS: ['p', 'br', 'b', 'strong', 'i', 'em', 'ul', 'ol', 'li'] }) 
                    }}
                  />
                )}
                
                <div className="feed-card-footer">
                  <div className="signal-live">
                    <div className="signal-dot"></div>
                    <span className="signal-text">Live Signal</span>
                  </div>
                  
                  <Link to={`/article/${article.id}`} style={{ textDecoration: 'none' }}>
                    <button className="read-btn group/btn">
                      Read Analysis
                      <ChevronRight className="read-btn-icon group-hover/btn:translate-x-1" size={18} />
                    </button>
                  </Link>
                </div>
              </div>
            </article>
          ))
        )}
      </div>

      {/* Pagination */}
      {hasNextPage && !loading && articles.length > 0 && (
         <div className="pagination">
           <button onClick={() => fetchNextPage()} className="pagination-btn" style={{ margin: '0 auto' }}>
            Load More Signals
            <ArrowRight size={18} className="group-hover:translate-x-1" />
           </button>
         </div>
      )}
    </div>
  );
}
