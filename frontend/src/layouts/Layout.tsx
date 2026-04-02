import { Outlet, NavLink } from 'react-router-dom';
import { Activity, BookOpen, LayoutDashboard, Settings } from 'lucide-react';

export default function Layout() {
  return (
    <div className="page-wrapper">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <NavLink to="/" className="brand">
          <Activity className="brand-icon" size={24} />
          <span>Tech<span className="text-muted">Pulse</span></span>
        </NavLink>
        
        <nav className="nav-links">
          <NavLink to="/" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
            <LayoutDashboard size={18} />
            Dashboard
          </NavLink>
          <NavLink to="/articles" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
            <BookOpen size={18} />
            All Articles
          </NavLink>
        </nav>

        <div style={{ marginTop: 'auto' }}>
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="nav-link" style={{ opacity: 0.7 }}>
            <Settings size={18} />
            API Docs
          </a>
        </div>
      </aside>
      
      {/* Top and Main Content area */}
      <div className="main-content-wrapper">
        <main className="container animate-fade-in">
          <Outlet />
        </main>
        
        <footer className="footer">
          <div className="container" style={{ display: 'flex', justifyContent: 'space-between', padding: '1rem 2.5rem' }}>
            <span>Tech Pulse Intelligence Platform</span>
            <span>v2.0.0 — Enterprise Edition</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
