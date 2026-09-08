import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { FiLogOut, FiHeart, FiActivity, FiMessageCircle, FiFileText, FiBarChart2 } from 'react-icons/fi';

export default function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isAuthPage = ['/login', '/register'].includes(location.pathname);

  if (!user || isAuthPage) return null;

  const links = [
    { to: '/', label: 'Assessment', icon: <FiHeart size={16} /> },
    { to: '/dashboard', label: 'Dashboard', icon: <FiActivity size={16} /> },
    { to: '/simulator', label: 'Simulator', icon: <FiBarChart2 size={16} /> },
    { to: '/chat', label: 'Diet Chat', icon: <FiMessageCircle size={16} /> },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-300 flex items-center justify-center">
              <FiHeart className="text-white" size={18} />
            </div>
            <span className="font-display font-bold text-lg text-white group-hover:text-primary-300 transition-colors">
              VitaLens
            </span>
          </Link>

          {/* Nav Links */}
          <div className="hidden md:flex items-center gap-1">
            {links.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  location.pathname === link.to
                    ? 'bg-primary-500/20 text-primary-300'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
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
              className="flex items-center gap-2 text-gray-400 hover:text-red-400 transition-colors p-2 rounded-lg hover:bg-white/5"
              title="Logout"
            >
              <FiLogOut size={18} />
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
