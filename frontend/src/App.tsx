import { Routes, Route } from 'react-router-dom';
import Layout from './layouts/Layout';
import Dashboard from './pages/Dashboard';
import Articles from './pages/Articles';
import ArticleDetail from './pages/ArticleDetail';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="articles" element={<Articles />} />
        <Route path="article/:id" element={<ArticleDetail />} />
      </Route>
    </Routes>
  );
}

export default App;
