import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  FaRightFromBracket, FaHeart, FaHeartPulse, FaCommentDots, FaFileLines,
  FaChartColumn, FaBars, FaXmark, FaShieldHalved,
} from 'react-icons/fa6';

export default function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isAuthPage = ['/login', '/register'].includes(location.pathname);

  if (!user || isAuthPage) return null;

  const links = [
    { to: '/', label: 'Assessment', icon: <FaHeart size={16} /> },
    { to: '/dashboard', label: 'Dashboard', icon: <FaHeartPulse size={16} /> },
    { to: '/simulator', label: 'Simulator', icon: <FaChartColumn size={16} /> },
    { to: '/chat', label: 'Diet Chat', icon: <FaCommentDots size={16} /> },
    { to: '/reports', label: 'Reports', icon: <FaFileLines size={16} /> },
  ];
  if (user.role === 'admin' || user.role === 'manager') {
    links.push({ to: '/admin', label: 'Admin', icon: <FaShieldHalved size={16} /> });
  }

  const linkClass = (to) =>
    `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
      location.pathname === to
        ? 'bg-primary-500/20 text-primary-300'
        : 'text-gray-400 hover:text-white hover:bg-white/5'
    }`;

  const handleNav = () => setOpen(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-300 flex items-center justify-center">
              <FaHeart className="text-white" size={18} />
            </div>
            <span className="font-display font-bold text-lg text-white group-hover:text-primary-300 transition-colors">
              VitaLens
            </span>
          </Link>

          {/* Desktop Nav Links */}
          <div className="hidden md:flex items-center gap-1">
            {links.map((link) => (
              <Link key={link.to} to={link.to} className={linkClass(link.to)}>
                {link.icon}
                {link.label}
              </Link>
            ))}
          </div>

          {/* User + Logout */}
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400 hidden sm:block">{user.name}</span>
            <button
              onClick={handleLogout}
              aria-label="Logout"
              className="hidden md:flex items-center gap-2 text-gray-400 hover:text-red-400 transition-colors p-2 rounded-lg hover:bg-white/5"
              title="Logout"
            >
              <FaRightFromBracket size={18} />
            </button>
            {/* Mobile hamburger */}
            <button
              onClick={() => setOpen((o) => !o)}
              aria-label="Toggle navigation menu"
              aria-expanded={open}
              className="md:hidden text-gray-300 hover:text-white p-2 rounded-lg hover:bg-white/5"
            >
              {open ? <FaXmark size={22} /> : <FaBars size={22} />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {open && (
        <div className="md:hidden border-t border-white/5 bg-surface-50/95 backdrop-blur px-4 py-3 space-y-1">
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              onClick={handleNav}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium ${
                location.pathname === link.to
                  ? 'bg-primary-500/20 text-primary-300'
                  : 'text-gray-300 hover:text-white hover:bg-white/5'
              }`}
            >
              {link.icon}
              {link.label}
            </Link>
          ))}
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-gray-300 hover:text-red-400 hover:bg-white/5"
          >
            <FaRightFromBracket size={16} /> Logout
          </button>
        </div>
      )}
    </nav>
  );
}
