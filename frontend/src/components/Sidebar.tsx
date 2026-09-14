/**
 * Sidebar navigation component with IDE-style layout.
 */

import { useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderTree,
  Search,
  MessageSquare,
  ShieldCheck,
  Bug,
  TestTube,
  GitBranch,
  Settings,
  Braces,
  X,
} from 'lucide-react';

const navItems = [
  { section: 'Overview', items: [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  ]},
  { section: 'Repository', items: [
    { to: '/explorer', icon: FolderTree, label: 'Explorer' },
    { to: '/search', icon: Search, label: 'Semantic Search' },
    { to: '/git', icon: GitBranch, label: 'Git' },
  ]},
  { section: 'AI Tools', items: [
    { to: '/chat', icon: MessageSquare, label: 'AI Chat' },
    { to: '/review', icon: ShieldCheck, label: 'Code Review' },
    { to: '/investigate', icon: Bug, label: 'Investigate' },
    { to: '/tests', icon: TestTube, label: 'Tests' },
  ]},
  { section: 'System', items: [
    { to: '/settings', icon: Settings, label: 'Settings' },
  ]},
];

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export default function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const location = useLocation();

  // Close sidebar drawer automatically on navigation change
  useEffect(() => {
    onClose?.();
  }, [location.pathname]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="sidebar-backdrop"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        {/* Logo & Header */}
        <div
          className="sidebar-header"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div className="sidebar-logo">
            <div className="sidebar-logo-icon">
              <Braces size={18} color="#fff" />
            </div>
            <div>
              <div className="sidebar-logo-text">Code Intelligence</div>
              <div className="sidebar-logo-sub">AI-Powered • Local & Cloud</div>
            </div>
          </div>

          {/* Close button on mobile */}
          <button
            type="button"
            className="sidebar-close-btn"
            onClick={onClose}
            aria-label="Close navigation menu"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          {navItems.map((section) => (
            <div key={section.section} className="sidebar-section">
              <div className="sidebar-section-title">{section.section}</div>
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  onClick={() => onClose?.()}
                  className={({ isActive }) =>
                    `sidebar-link ${isActive ? 'active' : ''}`
                  }
                >
                  <item.icon className="sidebar-link-icon" />
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div
          style={{
            padding: '12px 16px',
            borderTop: '1px solid var(--border-default)',
            fontSize: '11px',
            color: 'var(--text-tertiary)',
            textAlign: 'center',
          }}
        >
          AI Code Intelligence • v1.0
        </div>
      </aside>
    </>
  );
}

