import React from 'react';
import { Link } from 'react-router-dom';
import { FaCompass } from 'react-icons/fa6';

export default function NotFound() {
  return (
    <div className="pt-24 pb-12 px-4 min-h-screen flex items-center justify-center">
      <div className="text-center animate-slide-up">
        <FaCompass size={48} className="mx-auto mb-4 text-primary-300" />
        <h1 className="font-display text-5xl font-bold text-white mb-2">404</h1>
        <p className="text-gray-400 mb-6">This page could not be found.</p>
        <Link to="/" className="btn-primary inline-block">Back to Assessment</Link>
      </div>
    </div>
  );
}
