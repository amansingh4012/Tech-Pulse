import { Link, useSearchParams } from 'react-router-dom';
import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import { fetchArticles, fetchStats } from '../api';
import { Filter, Search } from 'lucide-react';
import DOMPurify from 'dompurify';

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
  } = useInfiniteQuery({
    queryKey: ['articles', sourceParam, categoryParam],
    queryFn: ({ pageParam = 1 }) => fetchArticles({ source: sourceParam, category: categoryParam, page: pageParam }),
    getNextPageParam: (lastPage) => lastPage.has_more ? lastPage.page + 1 : undefined,
    initialPageParam: 1,
  });

  const articles = data ? data.pages.flatMap(page => page.articles) : [];

  const loadMore = () => fetchNextPage();

  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>, type: 'source' | 'category') => {
    const newParams = new URLSearchParams(searchParams);
    if (e.target.value) {
      newParams.set(type, e.target.value);
    } else {
      newParams.delete(type);
    }
    setSearchParams(newParams);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1>Intelligence Feed</h1>
          <p className="text-muted">Explore and filter all extracted insights.</p>
        </div>
        
        <div className="filters card glass-panel" style={{ padding: '0.75rem 1.5rem', marginBottom: 0, display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <Filter size={18} className="text-muted" />
          <select 
            className="form-select" 
            value={sourceParam} 
            onChange={e => handleFilterChange(e, 'source')}
          >
            <option value="">All Sources</option>
            {sources.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          
          <select 
            className="form-select" 
            value={categoryParam} 
            onChange={e => handleFilterChange(e, 'category')}
          >
            <option value="">All Categories</option>
            {categories.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      </div>

      <div className="card glass-panel">
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
            <div className="loader"></div>
          </div>
        ) : articles.length === 0 ? (
          <div style={{ padding: '4rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Search size={48} style={{ opacity: 0.2, margin: '0 auto 1rem' }} />
            <h3>No articles found</h3>
            <p>Try adjusting your data filters.</p>
          </div>
        ) : (
          <div>
            <div className="grid-3">
              {articles.map((article: any) => (
                <Link to={`/article/${article.id}`} key={article.id} style={{ textDecoration: 'none', color: 'inherit' }}>
                  <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ flexGrow: 1 }}>
                      <h3 style={{ fontSize: '1.1rem', marginBottom: '0.75rem', lineHeight: 1.4 }}>{article.title}</h3>
                      {article.summary && (
                        <p 
                          className="text-muted" 
                          style={{ fontSize: '0.875rem', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}
                          dangerouslySetInnerHTML={{ 
                            __html: DOMPurify.sanitize(article.summary, { ALLOWED_TAGS: [] }) 
                          }}
                        />
                      )}
                    </div>
                    <div style={{ marginTop: '1.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem', borderTop: '1px solid var(--card-border)', paddingTop: '1rem' }}>
                      <span className="badge badge-source">{article.source}</span>
                      {article.category && <span className="badge badge-category">{article.category}</span>}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
            
            {hasNextPage && (
              <div style={{ textAlign: 'center', marginTop: '2.5rem' }}>
                <button onClick={loadMore} className="btn btn-secondary">
                  Load More Signals
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
