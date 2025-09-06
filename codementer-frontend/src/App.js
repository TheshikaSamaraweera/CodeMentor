import React, { useState } from 'react';

function App() {
  const [code, setCode] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [mode, setMode] = useState('full_scan');
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [finalCode, setFinalCode] = useState(null);
  const [feedback, setFeedback] = useState(null);

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => setCode(ev.target.result);
      reader.readAsText(file);
    }
  };

  const handleAnalyze = async () => {
    setError(null);
    setResults(null);
    setFinalCode(null);
    setFeedback(null);
    try {
      const response = await fetch('http://127.0.0.1:8000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, api_key: apiKey, mode }),
      });
      if (!response.ok) {
        throw new Error('Analysis failed');
      }
      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleFix = async () => {
    setError(null);
    try {
      const response = await fetch('http://127.0.0.1:8000/fix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code,
          issues: results.final_issues,
          api_key: apiKey,
          mode,
          context: {},
        }),
      });
      if (!response.ok) {
        throw new Error('Fix failed');
      }
      const data = await response.json();
      setFinalCode(data.final_code);
      setFeedback(data.feedback);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h1>codeMenter</h1>
      <input type="file" onChange={handleFileUpload} style={{ marginBottom: '10px' }} />
      <textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="Paste your code here or upload a file"
        rows={10}
        style={{ width: '100%' }}
      />
      <br />
      <input
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
        placeholder="Gemini API Key"
        style={{ width: '100%', marginBottom: '10px' }}
      />
      <select value={mode} onChange={(e) => setMode(e.target.value)} style={{ marginBottom: '10px' }}>
        <option value="full_scan">Full Scan</option>
        <option value="quality">Quality</option>
        <option value="security">Security</option>
        <option value="code_smell">Code Smell</option>
      </select>
      <button onClick={handleAnalyze}>Analyze</button>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {results && (
        <div>
          <h2>Analysis Report</h2>
          <p>Overall Score: {results.overall_score}</p>
          <p>Total Issues: {results.total_unique_issues}</p>
          {Object.entries(results.issues_by_category || {}).map(([category, issues]) => (
            <div key={category}>
              <h3>{category.toUpperCase()} ({issues.length} issues)</h3>
              <ul>
                {issues.map((issue, idx) => (
                  <li key={idx}>
                    Line {issue.line}: {issue.description}<br />
                    Suggestion: {issue.suggestion}<br />
                    Severity: {issue.severity}
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {results.total_unique_issues > 0 && (
            <button onClick={handleFix} style={{ marginTop: '10px' }}>
              Fix (Automatic)
            </button>
          )}
        </div>
      )}
      {finalCode && (
        <div>
          <h2>Fixed Code</h2>
          <textarea value={finalCode} readOnly rows={10} style={{ width: '100%' }} />
          <h3>Feedback</h3>
          <pre>{JSON.stringify(feedback, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default App;