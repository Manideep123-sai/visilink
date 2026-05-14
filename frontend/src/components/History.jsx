// Manideep Sai C
// Reg.no 23BCE0737

import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config';

function History({ onSelectResult }) {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchHistory();
    }, []);

    const fetchHistory = async () => {
        try {
            setLoading(true);
            const res = await fetch(`${API_BASE_URL}/api/history`);
            if (!res.ok) throw new Error('Failed to fetch history');
            const data = await res.json();
            setHistory(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (e, id) => {
        e.stopPropagation(); // prevent triggering the container's onClick
        if (!window.confirm("Are you sure you want to delete this analysis?")) return;

        try {
            const res = await fetch(`${API_BASE_URL}/api/analyses/${id}`, {
                method: 'DELETE',
            });
            if (!res.ok) throw new Error('Failed to delete history item');
            // Remove from local state
            setHistory(history.filter(item => item.id !== id));
        } catch (err) {
            alert(err.message);
        }
    };

    if (loading) return <div className="loader-container"><div className="spinner"></div></div>;
    if (error) return <div className="error-message">{error}</div>;

    return (
        <div className="card">
            <h2>Analysis History</h2>
            {history.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)' }}>No queries analyzed yet.</p>
            ) : (
                <div className="history-list">
                    {history.map((item) => (
                        <div
                            key={item.id}
                            className="history-item"
                            onClick={() => onSelectResult(item)}
                        >
                            <div className="history-item-content">
                                <div className="history-title">{item.video_title || 'Untitled Video'}</div>
                                <div className="history-url">{item.youtube_url}</div>
                                <div className="history-date">{new Date(item.created_at).toLocaleString()}</div>
                            </div>
                            <button
                                className="delete-btn"
                                onClick={(e) => handleDelete(e, item.id)}
                                title="Delete this analysis"
                            >
                                Delete
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default History;
