import React, { useState } from 'react';
import { API_BASE_URL } from '../config';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Calendar, Clock, ExternalLink, FileText, MessageSquare, Play, Video } from 'lucide-react';

const MarkdownRenderer = ({ content }) => {
    return (
        <ReactMarkdown 
            remarkPlugins={[remarkGfm]}
            components={{
                h1: ({node, ...props}) => <h1 style={{ color: 'var(--text-primary)', marginBottom: '1.2rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }} {...props} />,
                h2: ({node, ...props}) => <h2 style={{ color: 'var(--text-primary)', marginTop: '1.8rem', marginBottom: '0.8rem' }} {...props} />,
                h3: ({node, ...props}) => <h3 style={{ color: 'var(--text-primary)', marginTop: '1.4rem', marginBottom: '0.6rem' }} {...props} />,
                table: ({node, ...props}) => (
                    <div style={{ overflowX: 'auto', marginBottom: '1.5rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }} {...props} />
                    </div>
                ),
                thead: ({node, ...props}) => <thead style={{ backgroundColor: 'rgba(255,255,255,0.05)' }} {...props} />,
                th: ({node, ...props}) => <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid var(--border-color)', color: 'var(--primary-color)' }} {...props} />,
                td: ({node, ...props}) => <td style={{ padding: '0.75rem', borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }} {...props} />,
                ul: ({node, ...props}) => <ul style={{ paddingLeft: '1.5rem', marginBottom: '1rem' }} {...props} />,
                li: ({node, ...props}) => <li style={{ marginBottom: '0.4rem', color: 'var(--text-secondary)' }} {...props} />,
                p: ({node, ...props}) => <p style={{ marginBottom: '1rem', lineHeight: '1.6', color: 'var(--text-secondary)' }} {...props} />,
            }}
        >
            {content}
        </ReactMarkdown>
    );
};

const formatTime = (seconds) => {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `[${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}]`;
};

const renderTranscript = (transcriptData) => {
    if (!transcriptData) return 'No transcript available.';

    try {
        const parsed = JSON.parse(transcriptData);
        if (Array.isArray(parsed)) {
            return (
                <div className="transcript-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {parsed.map((chunk, idx) => (
                        <div key={idx} style={{ display: 'flex', gap: '1rem', lineHeight: '1.5' }}>
                            <span style={{ color: 'var(--primary-color)', fontWeight: '500', flexShrink: 0 }}>
                                {formatTime(chunk.start_time_in_seconds || 0)}
                            </span>
                            <span style={{ color: 'var(--text-secondary)' }}>
                                {chunk.text}
                            </span>
                        </div>
                    ))}
                </div>
            );
        }
    } catch (e) {
        // Fallback for older string transcripts
    }

    return <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>{transcriptData}</div>;
};

function ResultDetail({ result }) {
    const [showTranscript, setShowTranscript] = useState(false);

    // Q&A State
    const [question, setQuestion] = useState('');
    const [qaHistory, setQaHistory] = useState([]);
    const [asking, setAsking] = useState(false);
    const [qaError, setQaError] = useState('');

    const handleAskQuestion = async (e) => {
        e.preventDefault();
        if (!question.trim()) return;

        setAsking(true);
        setQaError('');

        const currentQuestion = question;
        setQuestion(''); // clear input immediately

        // Optimistically add to history
        const tempId = Date.now();
        setQaHistory(prev => [...prev, { id: tempId, q: currentQuestion, a: null, loading: true }]);

        try {
            const res = await fetch(`${API_BASE_URL}/api/analyses/${result.id}/question`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: currentQuestion }),
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Failed to get answer');
            }

            const data = await res.json();

            setQaHistory(prev => prev.map(item =>
                item.id === tempId ? { ...item, a: data.answer, loading: false } : item
            ));
        } catch (err) {
            setQaHistory(prev => prev.filter(item => item.id !== tempId));
            setQaError(err.message);
        } finally {
            setAsking(false);
        }
    };

    if (!result) return null;

    return (
        <div className="card result-section">
            <h2>Results for: {result.video_title || 'Unknown Video'}</h2>
            <a
                href={result.youtube_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'var(--primary-color)', fontSize: '0.9rem', marginBottom: '1.5rem', display: 'block' }}
            >
                {result.youtube_url}
            </a>

            <div className="summary-content">
                <h3>AI Summary</h3>
                {/* Render summary safely without full markdown parser for simplicity, 
            interpreting lists properly if generated by LLM */}
                <div style={{ marginTop: '1rem', backgroundColor: 'rgba(0,0,0,0.1)', padding: '1.5rem', borderRadius: '8px' }}>
                    <MarkdownRenderer content={result.summary} />
                </div>
            </div>

            <div className="transcript-section">
                <div
                    className="collapsible-header"
                    onClick={() => setShowTranscript(!showTranscript)}
                >
                    <span style={{ fontWeight: '600' }}>Full Transcript</span>
                    <span>{showTranscript ? '▲' : '▼'}</span>
                </div>

                <div className={`collapsible-content ${!showTranscript ? 'hidden' : ''}`}>
                    {renderTranscript(result.transcript)}
                </div>
            </div>

            <div className="qa-section">
                <hr className="divider" />
                <h3>Ask Questions About This Video</h3>

                <div className="qa-history">
                    {qaHistory.map((item) => (
                        <div key={item.id} className="qa-item">
                            <div className="qa-bubble user-bubble">
                                <strong>You:</strong> {item.q}
                            </div>
                            {item.loading ? (
                                <div className="qa-bubble ai-bubble loading-bubble">
                                    <div className="typing-dot"></div>
                                    <div className="typing-dot"></div>
                                    <div className="typing-dot"></div>
                                </div>
                            ) : (
                                <div className="qa-bubble ai-bubble plain-text-container-small">
                                    <strong>AI:</strong>
                                    <div style={{ marginTop: '0.5rem' }}><MarkdownRenderer content={item.a} /></div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                <form onSubmit={handleAskQuestion} className="qa-form">
                    <input
                        type="text"
                        placeholder="e.g., What did the speaker say about X?"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        disabled={asking}
                    />
                    <button type="submit" disabled={asking || !question.trim()}>
                        Ask
                    </button>
                </form>
                {qaError && (
                    <div className="error-message">
                        <strong>Error:</strong> {qaError}
                    </div>
                )}
            </div>
        </div>
    );
}

export default ResultDetail;
