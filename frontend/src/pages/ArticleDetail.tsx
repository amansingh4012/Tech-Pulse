import { useParams, Link } from 'react-router-dom';
import DOMPurify from 'dompurify';
import { useQuery } from '@tanstack/react-query';
import { fetchArticle } from '../api';
import { ArrowLeft, ExternalLink, Share2, ThumbsUp, Bookmark } from 'lucide-react';
import './ArticleDetail.css';

export default function ArticleDetail() {
  const { id } = useParams<{ id: string }>();
  
  const { data: article, isLoading } = useQuery({
    queryKey: ['article', id],
    queryFn: () => fetchArticle(id as string),
    enabled: !!id,
  });

  if (isLoading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '10rem 0' }}>
      <div className="loader" style={{ width: 40, height: 40, borderWidth: '3px' }}></div>
    </div>
  );

  if (!article) return (
    <div className="glass-panel" style={{ textAlign: 'center', padding: '6rem 2rem', maxWidth: '600px', margin: '4rem auto' }}>
      <h2 style={{ color: 'white' }}>Signal Not Found</h2>
      <p className="text-muted" style={{ marginTop: '0.5rem', marginBottom: '2rem' }}>The requested intelligence payload does not exist.</p>
      <Link to="/articles" className="btn btn-primary">Back to Feed</Link>
    </div>
  );

  const authorName = article.author && article.author !== 'Unknown' ? article.author : 'Tech Pulse Intel';
  const authorInitials = authorName.substring(0, 2).toUpperCase();

  return (
    <div className="article-detail-container">
      <div className="back-btn-wrapper">
        <Link to="/articles" className="back-btn">
          <ArrowLeft size={18} /> Back to Intelligence Feed
        </Link>
      </div>

      {/* Article Header */}
      <section className="article-header">
        <div className="article-meta-top">
          <span className="badge badge-source">{article.source_name || article.source}</span>
          {article.category && <span className="badge badge-category">{article.category}</span>}
          <span className="text-muted" style={{ fontSize: '0.75rem', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            INTEL REPORT
          </span>
        </div>
        
        <h1 className="article-title">{article.title}</h1>
        
        <div className="article-meta-bottom">
          <div className="author-info">
            <div className="author-avatar">{authorInitials}</div>
            <div>
              <div className="author-name">{authorName}</div>
              <div className="author-role">{article.author && article.author !== 'Unknown' ? 'Contributing Analyst' : 'Automated Extraction'}</div>
            </div>
          </div>
          
          <div className="meta-stats">
            <div className="meta-stat-group">
              <span className="meta-label">Source</span>
              <span className="meta-value">{article.source_name || article.source}</span>
            </div>
            {article.published_at && (
              <div className="meta-stat-group">
                <span className="meta-label">Published</span>
                <span className="meta-value">{new Date(article.published_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</span>
              </div>
            )}
            <div className="meta-stat-group">
              <span className="meta-label">Original</span>
              <a href={article.url} target="_blank" rel="noreferrer" style={{ color: 'var(--primary)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.875rem', fontWeight: 600 }}>
                <ExternalLink size={14} /> View Payload
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Featured Image Area placeholder if available */}
      {article.image_url && (
         <div className="article-featured-image">
           <img src={article.image_url} alt="Article visual" />
         </div>
      )}

      {/* Article Content */}
      <article className="article-content-card">
        {/* Glows */}
        <div className="content-glow-primary"></div>
        <div className="content-glow-secondary"></div>
        
        <div 
          className="article-body"
          dangerouslySetInnerHTML={{ 
            __html: DOMPurify.sanitize(article.content || article.summary || '<p>No payload content extracted.</p>') 
          }} 
        />
        
        {article.tags && article.tags.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '2.5rem', flexWrap: 'wrap', position: 'relative', zIndex: 10 }}>
            {article.tags.map((tag: string) => (
              <span key={tag} className="badge" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)' }}>#{tag}</span>
            ))}
          </div>
        )}

        <div className="article-footer relative z-10">
          <div className="footer-actions">
            <button className="action-btn">
              <ThumbsUp size={16} /> <span>Useful</span>
            </button>
            <button className="action-btn">
              <Share2 size={16} /> <span>Share</span>
            </button>
          </div>
          <button className="action-btn" style={{ color: 'var(--text-light)', background: 'transparent' }}>
            <Bookmark size={16} /> <span style={{ color: 'var(--text-light)'}}>Save</span>
          </button>
        </div>
      </article>
    </div>
  );
}
