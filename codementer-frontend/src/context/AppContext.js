import React, { createContext, useState } from 'react';
import { toast } from 'react-toastify';

export const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [code, setCode] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [mode, setMode] = useState('full_scan');
  const [results, setResults] = useState(null);
  const [remainingResults, setRemainingResults] = useState(null);
  const [error, setError] = useState(null);
  const [finalCode, setFinalCode] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [selectedIssues, setSelectedIssues] = useState([]);
  const [loading, setLoading] = useState(false);
  const [initialScore, setInitialScore] = useState(null);
  const [initialIssuesCount, setInitialIssuesCount] = useState(0);

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => setCode(ev.target.result);
      reader.readAsText(file);
    }
  };

  const handleAnalyze = async () => {
    setLoading(true);
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
      toast.success('Analysis completed!');
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFix = async () => {
    setLoading(true);
    setError(null);
    const issuesToFix = (results.final_issues || []).filter((issue) =>
      Object.entries(results.issues_by_category || {}).some(([category, issues]) =>
        issues.some(
          (i) =>
            `${category}-${i.line}-${i.description}` ===
            `${category}-${issue.line}-${i.description}` &&
            selectedIssues.includes(`${category}-${i.line}-${i.description}`)
        )
      )
    );
    if (issuesToFix.length === 0) {
      setError('No issues selected for fixing');
      toast.error('No issues selected for fixing');
      setLoading(false);
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
      toast.success('Issues fixed successfully!');
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateBestCode = async () => {
    setLoading(true);
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
        throw new Error('Generate best code failed');
      }
      const data = await response.json();
      setFinalCode(data.final_code);
      setFeedback(data.feedback);
      await handleReAnalyze(data.final_code);
      toast.success('Best code generated successfully!');
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReAnalyze = async (newCode) => {
    setLoading(true);
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
      setResults(data);
      setSelectedIssues([]);
      toast.success('Re-analysis completed!');
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
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

  const handleDownload = () => {
    if (!finalCode) return;
    const blob = new Blob([finalCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'fixed_code.py';
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Fixed code downloaded!');
  };

  return (
    <AppContext.Provider
      value={{
        code,
        setCode,
        apiKey,
        setApiKey,
        mode,
        setMode,
        handleAnalyze,
        results,
        error,
        loading,
        finalCode,
        feedback,
        selectedIssues,
        handleIssueSelection,
        handleFix,
        handleGenerateBestCode,
        remainingResults,
        initialScore,
        initialIssuesCount,
        handleFileUpload,
        handleDownload,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};