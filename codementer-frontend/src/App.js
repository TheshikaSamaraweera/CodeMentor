import React, { useState } from 'react';
import ReactDiffViewer from 'react-diff-viewer-continued';

function App() {
  const [code, setCode] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [mode, setMode] = useState('full_scan');
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [finalCode, setFinalCode] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [selectedIssues, setSelectedIssues] = useState([]);
  const [initialScore, setInitialScore] = useState(null);
  const [initialIssuesCount, setInitialIssuesCount] = useState(0);
  const [remainingResults, setRemainingResults] = useState(null);

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
    setSelectedIssues([]);
    setRemainingResults(null);
    setInitialScore(null);
    setInitialIssuesCount(0);
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
      setInitialScore(data.overall_score);
      setInitialIssuesCount(data.total_unique_issues);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleIssueSelection = (issue, category) => {
    const issueKey = `${category}-${issue.line}-${issue.description}`;
    setSelectedIssues((prev) =>
      prev.includes(issueKey)
        ? prev.filter((key) => key !== issueKey)
        : [...prev, issueKey]
    );
  };

  const handleFix = async () => {
    setError(null);
    const issuesToFix = (results.final_issues || []).filter((issue) =>
      Object.entries(results.issues_by_category || {}).some(([category, issues]) =>
        issues.some(
          (i) =>
            `${category}-${i.line}-${i.description}` ===
            `${category}-${issue.line}-${issue.description}` &&
            selectedIssues.includes(`${category}-${i.line}-${i.description}`)
        )
      )
    );
    if (issuesToFix.length === 0) {
      setError('No issues selected for fixing');
      return;
    }
    try {
      const response = await fetch('http://127.0.0.1:8000/fix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code,
          issues: issuesToFix,
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
      await handleReAnalyze(data.final_code);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleReAnalyze = async (newCode) => {
    try {
      const response = await fetch('http://127.0.0.1:8000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: newCode, api_key: apiKey, mode }),
      });
      if (!response.ok) {
        throw new Error('Re-analysis failed');
      }
      const data = await response.json();
      setRemainingResults(data);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.header}>codeMenter</h1>
      <div style={styles.inputSection}>
        <input
          type="file"
          onChange={handleFileUpload}
          style={styles.fileInput}
        />
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Paste your code here or upload a file"
          style={styles.textarea}
        />
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="Gemini API Key"
          style={styles.input}
        />
        <select value={mode} onChange={(e) => setMode(e.target.value)} style={styles.select}>
          <option value="full_scan">Full Scan</option>
          <option value="quality">Quality</option>
          <option value="security">Security</option>
          <option value="code_smell">Code Smell</option>
        </select>
        <button onClick={handleAnalyze} style={styles.button}>Analyze</button>
      </div>
      {error && <p style={styles.error}>{error}</p>}
      {results && (
        <div style={styles.resultsSection}>
          <h2 style={styles.subHeader}>Analysis Report</h2>
          <p style={styles.info}>Overall Score: {results.overall_score}</p>
          <p style={styles.info}>Total Issues: {results.total_unique_issues}</p>
          {Object.entries(results.issues_by_category || {}).map(([category, issues]) => (
            <div key={category} style={styles.category}>
              <h3 style={styles.categoryHeader}>{category.toUpperCase()} ({issues.length} issues)</h3>
              <ul style={styles.issueList}>
                {issues.map((issue, idx) => {
                  const issueKey = `${category}-${issue.line}-${issue.description}`;
                  return (
                    <li key={idx} style={styles.issueItem}>
                      <label style={styles.checkboxLabel}>
                        <input
                          type="checkbox"
                          checked={selectedIssues.includes(issueKey)}
                          onChange={() => handleIssueSelection(issue, category)}
                          style={styles.checkbox}
                        />
                        <span style={styles.issueLine}>Line {issue.line}</span>: {issue.description}<br />
                        <span style={styles.suggestion}>Suggestion: {issue.suggestion}</span><br />
                        <span style={styles.severity}>Severity: {issue.severity}</span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
          {results.total_unique_issues > 0 && (
            <button onClick={handleFix} style={styles.button}>Fix Selected Issues</button>
          )}
        </div>
      )}
      {finalCode && (
        <div style={styles.resultsSection}>
          <h2 style={styles.subHeader}>Fixed Code</h2>
          <ReactDiffViewer
            oldValue={code}
            newValue={finalCode}
            splitView={true}
            leftTitle="Original Code"
            rightTitle="Fixed Code"
            styles={diffStyles}
          />
          <h3 style={styles.subHeader}>Feedback</h3>
          <pre style={styles.feedback}>{JSON.stringify(feedback, null, 2)}</pre>
        </div>
      )}
      {remainingResults && (
        <div style={styles.resultsSection}>
          <h2 style={styles.subHeader}>Remaining Issues Report</h2>
          <p style={styles.info}>Updated Score: {remainingResults.overall_score}</p>
          <p style={styles.info}>Score Improvement: {remainingResults.overall_score - initialScore}</p>
          <p style={styles.info}>Initial Issues: {initialIssuesCount}</p>
          <p style={styles.info}>Issues Fixed: {selectedIssues.length}</p>
          <p style={styles.info}>Remaining Issues: {remainingResults.total_unique_issues}</p>
          {Object.entries(remainingResults.issues_by_category || {}).map(([category, issues]) => (
            <div key={category} style={styles.category}>
              <h3 style={styles.categoryHeader}>{category.toUpperCase()} ({issues.length} issues)</h3>
              <ul style={styles.issueList}>
                {issues.map((issue, idx) => (
                  <li key={idx} style={styles.issueItem}>
                    <span style={styles.issueLine}>Line {issue.line}</span>: {issue.description}<br />
                    <span style={styles.suggestion}>Suggestion: {issue.suggestion}</span><br />
                    <span style={styles.severity}>Severity: {issue.severity}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    maxWidth: '800px',
    margin: '0 auto',
    padding: '20px',
    fontFamily: 'Arial, sans-serif',
    backgroundColor: '#f5f5f5',
    minHeight: '100vh',
  },
  header: {
    color: '#333',
    textAlign: 'center',
    marginBottom: '20px',
  },
  inputSection: {
    backgroundColor: '#fff',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    marginBottom: '20px',
  },
  fileInput: {
    marginBottom: '10px',
    display: 'block',
  },
  textarea: {
    width: '100%',
    minHeight: '150px',
    marginBottom: '10px',
    padding: '10px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    fontFamily: 'monospace',
    fontSize: '14px',
    resize: 'vertical',
  },
  input: {
    width: '100%',
    padding: '10px',
    marginBottom: '10px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    fontSize: '14px',
  },
  select: {
    width: '100%',
    padding: '10px',
    marginBottom: '10px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    fontSize: '14px',
  },
  button: {
    backgroundColor: '#007bff',
    color: '#fff',
    padding: '10px 20px',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '16px',
    marginRight: '10px',
  },
  error: {
    color: '#d32f2f',
    backgroundColor: '#ffebee',
    padding: '10px',
    borderRadius: '4px',
    marginBottom: '20px',
  },
  resultsSection: {
    backgroundColor: '#fff',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    marginBottom: '20px',
  },
  subHeader: {
    color: '#333',
    marginBottom: '10px',
  },
  info: {
    color: '#555',
    margin: '5px 0',
  },
  category: {
    marginBottom: '15px',
  },
  categoryHeader: {
    color: '#007bff',
    marginBottom: '10px',
  },
  issueList: {
    listStyle: 'none',
    padding: 0,
  },
  issueItem: {
    backgroundColor: '#f9f9f9',
    padding: '10px',
    borderRadius: '4px',
    marginBottom: '10px',
    borderLeft: '4px solid #007bff',
  },
  issueLine: {
    fontWeight: 'bold',
  },
  suggestion: {
    color: '#388e3c',
  },
  severity: {
    color: '#d81b60',
  },
  feedback: {
    backgroundColor: '#f9f9f9',
    padding: '10px',
    borderRadius: '4px',
    fontFamily: 'monospace',
    fontSize: '14px',
    maxHeight: '300px',
    overflowY: 'auto',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'flex-start',
  },
  checkbox: {
    marginRight: '10px',
    marginTop: '3px',
  },
};

const diffStyles = {
  diffContainer: {
    fontSize: '14px',
    fontFamily: 'monospace',
  },
  title: {
    fontWeight: 'bold',
    color: '#333',
  },
  line: {
    lineHeight: '1.5',
  },
};

export default App;