/**
 * Main application component with routing and layout.
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
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

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
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
    </BrowserRouter>
  );
}
