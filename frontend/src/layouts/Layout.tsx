import { Outlet, NavLink } from 'react-router-dom';
import { Activity, BookOpen, FileText } from 'lucide-react';

export default function Layout() {
  return (
    <div className="page-wrapper">
      <header className="header">
        <div className="container header-inner">
          <NavLink to="/" className="brand">
            <Activity className="brand-icon" size={28} />
            Tech<span className="text-muted">Pulse</span>
          </NavLink>
          
          <nav className="nav-links">
            <NavLink to="/" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Activity size={18} /> Dashboard
              </span>
            </NavLink>
            <NavLink to="/articles" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <BookOpen size={18} /> Articles
              </span>
            </NavLink>
            <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="nav-link">
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileText size={18} /> API Docs
              </span>
            </a>
          </nav>
        </div>
      </header>
      
      <main className="main-content container animate-fade-in">
        <Outlet />
      </main>
      
      <footer className="footer">
        <div className="container">
          <p className="text-muted">Tech Pulse — B2B Tech News Intelligence Platform</p>
          <p className="text-light" style={{ marginTop: '0.5rem' }}>Powered by React, FastAPI, and PostgreSQL</p>
        </div>
      </footer>
    </div>
  );
}
