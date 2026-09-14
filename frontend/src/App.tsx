import { useState } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { Menu, Braces } from 'lucide-react';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Explorer from './pages/Explorer';
import SearchPage from './pages/Search';
import Chat from './pages/Chat';
import Review from './pages/Review';
import Investigate from './pages/Investigate';
import Tests from './pages/Tests';
import Git from './pages/Git';
import SettingsPage from './pages/Settings';

function AppLayout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const getPageTitle = (path: string) => {
    switch (path) {
      case '/': return 'Dashboard';
      case '/explorer': return 'Repository Explorer';
      case '/search': return 'Semantic Search';
      case '/chat': return 'AI Chat';
      case '/review': return 'Code Review';
      case '/investigate': return 'Investigate';
      case '/tests': return 'Tests';
      case '/git': return 'Git';
      case '/settings': return 'Settings';
      default: return 'AI Assistant';
    }
  };

  return (
    <div className="app-layout">
      {/* Mobile Top Navigation Bar (visible on <= 768px) */}
      <header className="mobile-topbar">
        <div className="mobile-topbar-left">
          <button
            type="button"
            className="mobile-menu-btn"
            onClick={() => setMobileMenuOpen(true)}
            aria-label="Open navigation menu"
          >
            <Menu size={20} />
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div
              style={{
                width: 26,
                height: 26,
                borderRadius: 'var(--radius-sm)',
                background: 'var(--gradient-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Braces size={14} color="#fff" />
            </div>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
              {getPageTitle(location.pathname)}
            </span>
          </div>
        </div>

        <div style={{ fontSize: 11, color: 'var(--accent-blue)', fontWeight: 600 }}>
          AI Ready
        </div>
      </header>

      {/* Sidebar (Desktop dock / Mobile slide-over drawer) */}
      <Sidebar
        isOpen={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/explorer" element={<Explorer />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/review" element={<Review />} />
          <Route path="/investigate" element={<Investigate />} />
          <Route path="/tests" element={<Tests />} />
          <Route path="/git" element={<Git />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}

