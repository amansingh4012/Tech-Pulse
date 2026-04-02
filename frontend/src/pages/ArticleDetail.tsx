import { useParams, Link } from 'react-router-dom';
import DOMPurify from 'dompurify';
import { useQuery } from '@tanstack/react-query';
import { fetchArticle } from '../api';
import { ArrowLeft, ExternalLink, Calendar, User, Tag } from 'lucide-react';

export default function ArticleDetail() {
  const { id } = useParams<{ id: string }>();
  
  const { data: article, isLoading } = useQuery({
    queryKey: ['article', id],
    queryFn: () => fetchArticle(id as string),
    enabled: !!id,
  });

  if (isLoading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
      <div className="loader"></div>
    </div>
  );

  if (!article) return (
    <div style={{ textAlign: 'center', padding: '4rem' }}>
      <h2>Signal Not Found</h2>
      <Link to="/articles" className="btn btn-secondary" style={{ marginTop: '1rem' }}>Back to Feed</Link>
    </div>
  );

  return (
    <div>
      <Link to="/articles" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', textDecoration: 'none', color: 'var(--text-muted)', marginBottom: '2rem', fontWeight: 500 }}>
        <ArrowLeft size={18} /> Back to Feed
      </Link>

      <div className="card glass-panel" style={{ padding: '3rem', maxWidth: '900px', margin: '0 auto' }}>
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <span className="badge badge-source">{article.source_name}</span>
          {article.category && <span className="badge badge-category">{article.category}</span>}
        </div>
        
        <h1 style={{ fontSize: '2.5rem', marginBottom: '1.5rem', lineHeight: 1.2 }}>{article.title}</h1>
        
        <div style={{ display: 'flex', gap: '2rem', color: 'var(--text-muted)', borderBottom: '1px solid var(--card-border)', paddingBottom: '1.5rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
          {article.author && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <User size={16} /> {article.author}
            </div>
          )}
          {article.published_at && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Calendar size={16} /> {new Date(article.published_at).toLocaleString()}
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ExternalLink size={16} /> 
            <a href={article.url} target="_blank" rel="noreferrer" style={{ color: 'var(--primary)', textDecoration: 'none' }}>
              View Original Payload
            </a>
          </div>
        </div>

        {article.tags && article.tags.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
            <Tag size={16} className="text-muted" />
            {article.tags.map((tag: string) => (
              <span key={tag} className="tag">{tag}</span>
            ))}
          </div>
        )}

        <div 
          style={{ fontSize: '1.125rem', lineHeight: 1.8, color: 'var(--text-main)', whiteSpace: 'pre-wrap' }}
          dangerouslySetInnerHTML={{ 
            __html: DOMPurify.sanitize(article.content || article.summary || 'No content extracted.') 
          }} 
        />
      </div>
    </div>
  );
}
