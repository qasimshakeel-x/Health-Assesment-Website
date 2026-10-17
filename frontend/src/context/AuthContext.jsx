import React, { createContext, useContext, useState, useEffect } from 'react';
import { getMe, logout as logoutApi } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const savedUser = localStorage.getItem('user');
    if (token && savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch {
        localStorage.removeItem('user');
      }
      // Boot pe server se validate karo — sirf localStorage pe trust karne se stale
      // user/role chalta rehta tha (getMe pehle se import tha, kabhi call hi nahi hota tha) (BUG-8)
      getMe()
        .then((res) => {
          const fresh = res.data?.user || res.data;
          if (fresh && typeof fresh === 'object') {
            localStorage.setItem('user', JSON.stringify(fresh));
            setUser(fresh);
          }
        })
        .catch((err) => {
          // 401/403 = refresh interceptor already ek baar retry kar chuka → session khatam
          const status = err?.response?.status;
          if (status === 401 || status === 403) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            setUser(null);
          }
          // Network error pe cached user rehne do (backend down ho sakta hai)
        });
    }
    setLoading(false);
  }, []);

  const loginUser = (userData, tokens) => {
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
  };

  const logout = () => {
    // Server-side logout call (best-effort — JWT stateless hai, failure pe bhi local clear)
    logoutApi().catch(() => {});
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, loginUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
