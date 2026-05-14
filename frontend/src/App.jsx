// Manideep Sai C
// Reg.no 23BCE0737

import React, { useState } from 'react';
import Analyzer from './components/Analyzer';
import ResultDetail from './components/ResultDetail';
import History from './components/History';

function App() {
  const [activeTab, setActiveTab] = useState('analyze'); // 'analyze' or 'history'
  const [currentResult, setCurrentResult] = useState(null);
  const [engine, setEngine] = useState('gemini'); // 'gemini' or 'local'

  const handleAnalyzeSuccess = (data) => {
    setCurrentResult(data);
  };

  const handleSelectHistory = (item) => {
    setCurrentResult(item);
    setActiveTab('analyze');
  };

  return (
    <div className="container">
      <header className="header" style={{ position: 'relative' }}>
        <h1>Visilink</h1>
        <p style={{ color: 'var(--text-secondary)' }}>YouTube Audio Extractor & Analyzer</p>

        {/* Engine Toggle – top right */}
        <div style={{
          position: 'absolute',
          top: '1rem',
          right: '0',
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem',
        }}>
          <span style={{
            fontSize: '0.8rem',
            color: engine === 'gemini' ? '#4285f4' : 'var(--text-secondary)',
            fontWeight: engine === 'gemini' ? '600' : '400',
            transition: 'all 0.2s ease',
          }}>
            ☁️ Gemini
          </span>

          {/* Toggle Switch */}
          <div
            onClick={() => setEngine(engine === 'gemini' ? 'local' : 'gemini')}
            style={{
              width: '44px',
              height: '24px',
              borderRadius: '12px',
              background: engine === 'local' ? '#34a853' : '#4285f4',
              cursor: 'pointer',
              position: 'relative',
              transition: 'background 0.3s ease',
              flexShrink: 0,
            }}
          >
            <div style={{
              width: '18px',
              height: '18px',
              borderRadius: '50%',
              background: 'white',
              position: 'absolute',
              top: '3px',
              left: engine === 'local' ? '23px' : '3px',
              transition: 'left 0.3s ease',
              boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
            }} />
          </div>

          <span style={{
            fontSize: '0.8rem',
            color: engine === 'local' ? '#34a853' : 'var(--text-secondary)',
            fontWeight: engine === 'local' ? '600' : '400',
            transition: 'all 0.2s ease',
          }}>
            💻 Local
          </span>
        </div>
      </header>

      <div className="nav-tabs">
        <button
          className={`tab-btn ${activeTab === 'analyze' ? 'active' : ''}`}
          onClick={() => { setActiveTab('analyze'); setCurrentResult(null); }}
        >
          New Analysis
        </button>
        <button
          className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          History
        </button>
      </div>

      <main className="main-content">
        {activeTab === 'analyze' && (
          <>
            {!currentResult && <Analyzer onAnalyzeSuccess={handleAnalyzeSuccess} engine={engine} />}
            {currentResult && (
              <>
                <button
                  onClick={() => setCurrentResult(null)}
                  style={{ alignSelf: 'flex-start', marginBottom: '-1rem', backgroundColor: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
                >
                  ← Back to New Analysis
                </button>
                <ResultDetail result={currentResult} />
              </>
            )}
          </>
        )}

        {activeTab === 'history' && (
          <History onSelectResult={handleSelectHistory} />
        )}
      </main>
    </div>
  );
}

export default App;
