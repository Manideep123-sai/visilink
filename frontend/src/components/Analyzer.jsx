// Manideep Sai C
// Reg.no 23BCE0737

import React, { useState } from 'react';
import { API_BASE_URL } from '../config';

function Analyzer({ onAnalyzeSuccess, engine }) {
    const [mode, setMode] = useState('url'); // 'url' or 'file'
    const [url, setUrl] = useState('');
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleAnalyze = async (e) => {
        e.preventDefault();
        if (mode === 'url' && !url) return;
        if (mode === 'file' && !file) return;

        setLoading(true);
        setError('');

        try {
            let response;
            if (mode === 'url') {
                response = await fetch(`${API_BASE_URL}/api/analyze`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url, engine }),
                });
            } else {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('engine_choice', engine);

                response = await fetch(`${API_BASE_URL}/api/analyze/upload`, {
                    method: 'POST',
                    body: formData,
                });
            }

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to analyze video');
            }

            const data = await response.json();
            onAnalyzeSuccess(data);
            setUrl('');
            setFile(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="card analyzer-section">
            <h2>Analyze New Video</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                Analyze a YouTube video or upload a local video file from your computer.
            </p>

            {/* Source Toggle: YouTube URL vs Local File */}
            <div style={{ marginBottom: '1.5rem', display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
                <button
                    type="button"
                    style={{
                        padding: '0.5rem 1.25rem',
                        borderRadius: '8px',
                        border: mode === 'url' ? '2px solid var(--primary-color)' : '2px solid transparent',
                        background: mode === 'url' ? 'var(--primary-color)' : 'rgba(255,255,255,0.05)',
                        color: mode === 'url' ? 'white' : 'var(--text-primary)',
                        cursor: 'pointer',
                        fontWeight: mode === 'url' ? '600' : '400',
                        transition: 'all 0.2s ease'
                    }}
                    onClick={() => setMode('url')}
                >
                    YouTube URL
                </button>
                <button
                    type="button"
                    style={{
                        padding: '0.5rem 1.25rem',
                        borderRadius: '8px',
                        border: mode === 'file' ? '2px solid var(--primary-color)' : '2px solid transparent',
                        background: mode === 'file' ? 'var(--primary-color)' : 'rgba(255,255,255,0.05)',
                        color: mode === 'file' ? 'white' : 'var(--text-primary)',
                        cursor: 'pointer',
                        fontWeight: mode === 'file' ? '600' : '400',
                        transition: 'all 0.2s ease'
                    }}
                    onClick={() => setMode('file')}
                >
                    Local File
                </button>
            </div>

            <form onSubmit={handleAnalyze} className="analyzer-form">
                {mode === 'url' ? (
                    <input
                        type="url"
                        placeholder="https://www.youtube.com/watch?v=..."
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        required
                        disabled={loading}
                    />
                ) : (
                    <input
                        type="file"
                        accept="video/*"
                        onChange={(e) => setFile(e.target.files[0])}
                        required
                        disabled={loading}
                    />
                )}
                <button type="submit" disabled={loading || (mode === 'url' && !url) || (mode === 'file' && !file)}>
                    {loading ? 'Analyzing...' : 'Analyze'}
                </button>
            </form>

            {error && (
                <div className="error-message">
                    <strong>Error:</strong> {error}
                </div>
            )}

            {loading && (
                <div className="loader-container">
                    <div className="spinner"></div>
                    <p style={{ color: 'var(--primary-color)' }}>
                        {engine === 'local'
                            ? 'Processing with local AI models (this may take longer)...'
                            : mode === 'file'
                                ? 'Uploading file and analyzing with Gemini...'
                                : 'Downloading audio, transcribing, and generating summary with Gemini...'}
                        <br />
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>This may take a few minutes depending on the video length.</span>
                    </p>
                </div>
            )}
        </div>
    );
}

export default Analyzer;
