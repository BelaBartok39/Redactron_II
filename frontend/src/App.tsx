import { Routes, Route, NavLink } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import BatchDetailPage from './pages/BatchDetailPage';
import DocumentPage from './pages/DocumentPage';
import ReportsPage from './pages/ReportsPage';

function App() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>RedactQC</h1>
          <span className="sidebar-subtitle">PII Quality Assurance</span>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            <span className="nav-icon">&#9632;</span>
            Dashboard
          </NavLink>
          <NavLink to="/reports" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            <span className="nav-icon">&#9776;</span>
            Reports
          </NavLink>
        </nav>
      </aside>
      <div className="main-area">
        <header className="top-header">
          <h2>RedactQC Dashboard</h2>
        </header>
        <main className="content">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/batches/:id" element={<BatchDetailPage />} />
            <Route path="/documents/:id" element={<DocumentPage />} />
            <Route path="/reports" element={<ReportsPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;
