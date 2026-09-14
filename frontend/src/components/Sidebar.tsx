/**
 * Sidebar navigation component with IDE-style layout.
 */

import { NavLink } from 'react-router-dom';
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

export default function Sidebar() {
  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">
            <Braces size={18} color="#fff" />
          </div>
          <div>
            <div className="sidebar-logo-text">Code Intelligence</div>
            <div className="sidebar-logo-sub">AI-Powered • 100% Local</div>
          </div>
        </div>
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
      <div style={{
        padding: '12px 16px',
        borderTop: '1px solid var(--border-default)',
        fontSize: '11px',
        color: 'var(--text-tertiary)',
        textAlign: 'center',
      }}>
        100% Local • $0 API Cost
      </div>
    </aside>
  );
}
