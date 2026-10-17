import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  adminListUsers, adminCreateUser, adminUpdateRole, adminDeleteUser,
  adminGetStats, adminRetrainModels, adminGetActions,
} from '../services/api';
import {
  FaUsers, FaUserPlus, FaTrash, FaArrowsRotate, FaHeartPulse, FaShieldHalved, FaCircleExclamation,
} from 'react-icons/fa6';

const ROLES = ['user', 'manager', 'admin'];

export default function Admin() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  const [tab, setTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState(null);
  const [actions, setActions] = useState([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(true);

  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'user' });

  const load = async () => {
    setLoading(true);
    try {
      const [usersRes, statsRes] = await Promise.all([adminListUsers(), adminGetStats()]);
      setUsers(usersRes.data || []);
      setStats(statsRes.data || null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  const loadActions = async () => {
    try {
      const res = await adminGetActions();
      setActions(res.data?.actions || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load actions');
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (tab === 'actions') loadActions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError('');
    setNotice('');
    try {
      await adminCreateUser(form);
      setNotice(`User ${form.email} created`);
      setForm({ name: '', email: '', password: '', role: 'user' });
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleRole = async (id, role) => {
    try {
      await adminUpdateRole(id, role);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update role');
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Delete user "${name}"? This cannot be undone.`)) return;
    try {
      await adminDeleteUser(id);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete user');
    }
  };

  const handleRetrain = async () => {
    setError('');
    setNotice('');
    try {
      await adminRetrainModels();
      setNotice('Model retraining started in background. This can take several minutes.');
      setTab('actions');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start retraining');
    }
  };

  return (
    <div className="pt-20 pb-12 px-4 max-w-6xl mx-auto">
      <div className="animate-slide-up">
        <h1 className="font-display text-3xl font-bold text-white mb-2 flex items-center gap-3">
          <FaShieldHalved className="text-primary-300" /> Admin
        </h1>
        <p className="text-gray-400 mb-6">
          {isAdmin ? 'Manage users, models and audit actions' : 'Read-only overview (manager)'}
        </p>

        {error && (
          <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-xl p-3 mb-4 text-red-400 text-sm">
            <FaCircleExclamation size={16} /> {error}
          </div>
        )}
        {notice && <div className="glass-light p-3 mb-4 text-sm text-primary-300" role="status">{notice}</div>}

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {[
              ['Total', stats.total], ['Admins', stats.admin],
              ['Managers', stats.manager], ['Users', stats.user],
            ].map(([label, value]) => (
              <div key={label} className="glass p-4">
                <p className="text-xs text-gray-400">{label}</p>
                <p className="text-2xl font-bold text-white">{value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Tabs */}
        <div className="flex items-center gap-2 mb-6">
          <button
            onClick={() => setTab('users')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
              tab === 'users' ? 'bg-primary-500/20 text-primary-300' : 'text-gray-400 hover:text-white'
            }`}
          >
            <FaUsers size={16} /> Users
          </button>
          <button
            onClick={() => setTab('actions')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
              tab === 'actions' ? 'bg-primary-500/20 text-primary-300' : 'text-gray-400 hover:text-white'
            }`}
          >
            <FaHeartPulse size={16} /> Actions
          </button>
          {isAdmin && (
            <button
              onClick={handleRetrain}
              className="ml-auto flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-yellow-500/10 text-yellow-400 hover:bg-yellow-500/20"
            >
              <FaArrowsRotate size={16} /> Retrain Models
            </button>
          )}
        </div>

        {loading ? (
          <div className="glass p-8 flex justify-center">
            <div className="w-10 h-10 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
          </div>
        ) : tab === 'users' ? (
          <>
            {isAdmin && (
              <form onSubmit={handleCreate} className="glass p-4 mb-6 grid grid-cols-1 md:grid-cols-5 gap-3">
                <input
                  className="input-field"
                  placeholder="Name"
                  aria-label="New user name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
                <input
                  type="email"
                  className="input-field"
                  placeholder="Email"
                  aria-label="New user email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                />
                <input
                  type="password"
                  className="input-field"
                  placeholder="Password (min 8)"
                  aria-label="New user password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  minLength={8}
                  required
                />
                <select
                  className="input-field"
                  aria-label="New user role"
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                >
                  {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
                <button type="submit" className="btn-primary flex items-center justify-center gap-2">
                  <FaUserPlus size={16} /> Create
                </button>
              </form>
            )}

            <div className="glass overflow-hidden overflow-x-auto">
              <table className="w-full text-sm min-w-[560px]">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-white/5">
                    <th className="px-4 py-3 font-medium">Name</th>
                    <th className="px-4 py-3 font-medium">Email</th>
                    <th className="px-4 py-3 font-medium">Role</th>
                    {isAdmin && <th className="px-4 py-3 font-medium text-right">Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-white/5 last:border-0">
                      <td className="px-4 py-3 text-white">{u.name}</td>
                      <td className="px-4 py-3 text-gray-400">{u.email}</td>
                      <td className="px-4 py-3">
                        {isAdmin && u.id !== user.id ? (
                          <select
                            className="input-field py-1"
                            aria-label={`Role for ${u.name}`}
                            value={u.role}
                            onChange={(e) => handleRole(u.id, e.target.value)}
                          >
                            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                          </select>
                        ) : (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 text-gray-300">{u.role}</span>
                        )}
                      </td>
                      {isAdmin && (
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => handleDelete(u.id, u.name)}
                            disabled={u.id === user.id}
                            aria-label={`Delete ${u.name}`}
                            className="text-gray-400 hover:text-red-400 disabled:text-gray-700 disabled:cursor-not-allowed"
                          >
                            <FaTrash size={16} />
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div className="glass overflow-hidden overflow-x-auto">
            {actions.length === 0 ? (
              <div className="p-8 text-center text-gray-400">No admin actions recorded yet.</div>
            ) : (
              <table className="w-full text-sm min-w-[560px]">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-white/5">
                    <th className="px-4 py-3 font-medium">When</th>
                    <th className="px-4 py-3 font-medium">Admin</th>
                    <th className="px-4 py-3 font-medium">Action</th>
                    <th className="px-4 py-3 font-medium">Target</th>
                    <th className="px-4 py-3 font-medium">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {actions.map((a) => (
                    <tr key={a.id} className="border-b border-white/5 last:border-0">
                      <td className="px-4 py-3 text-gray-400 whitespace-nowrap">
                        {a.created_at ? new Date(a.created_at).toLocaleString() : '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-300">{a.admin_email || a.admin_id || '—'}</td>
                      <td className="px-4 py-3 text-primary-300">{a.action}</td>
                      <td className="px-4 py-3 text-gray-400">{a.target || '—'}</td>
                      <td className="px-4 py-3 text-gray-500">{a.details || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
