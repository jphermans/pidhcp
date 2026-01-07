import { Link, useLocation } from 'react-router-dom'

export default function Header({ onLogout, currentPath }) {
  return (
    <header className="header">
      <div className="container header-content">
        <div className="logo">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 12.55a11 11 0 0 1 14.08 0"></path>
            <path d="M1.42 9a16 16 0 0 1 21.16 0"></path>
            <path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path>
            <line x1="12" y1="20" x2="12.01" y2="20"></line>
          </svg>
          Pi Router
        </div>
        <nav className="nav">
          <Link to="/dashboard" className={`nav-link ${currentPath === '/dashboard' ? 'active' : ''}`}>
            Dashboard
          </Link>
          <Link to="/network" className={`nav-link ${currentPath === '/network' ? 'active' : ''}`}>
            Network
          </Link>
          <Link to="/settings" className={`nav-link ${currentPath === '/settings' ? 'active' : ''}`}>
            Settings
          </Link>
          <Link to="/backup" className={`nav-link ${currentPath === '/backup' ? 'active' : ''}`}>
            Backup
          </Link>
          <button onClick={onLogout} className="btn btn-secondary btn-sm">
            Logout
          </button>
        </nav>
      </div>
    </header>
  )
}
