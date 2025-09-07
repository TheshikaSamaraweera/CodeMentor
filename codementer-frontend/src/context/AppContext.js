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
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [repoUrl, setRepoUrl] = useState('');

  const handleFileUpload = async (files) => {
    setLoading(true);
    setError(null);
    try {
      const fileArray = Array.from(files || []);
      if (!fileArray.length) {
        throw new Error('No files selected');
      }
      const formData = new FormData();
      fileArray.forEach(file => formData.append('files', file));
      const response = await fetch('http://127.0.0.1:8000/upload-project', {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Upload failed');
      }
      const data = await response.json();
      setUploadedFiles(fileArray.map(file => file.name));
      if (fileArray.length > 0) {
        const reader = new FileReader();
        reader.onload = (e) => setCode(e.target.result);
        reader.readAsText(fileArray[0]);
      }
      toast.success(`Uploaded ${data.file_count} files`);
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFetchRepo = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://127.0.0.1:8000/fetch-repo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Repo fetch failed');
      }
      const data = await response.json();
      setUploadedFiles([repoUrl]);
      setCode('');
      toast.success(`Fetched ${data.file_count} files from repo`);
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
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
        const errorData = await response.json();
        throw new Error(errorData.error || 'Analysis failed');
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
    if (!results || !results.issues_by_category || !apiKey) {
      setError('Missing analysis results or API key');
      toast.error('Missing analysis results or API key');
      setLoading(false);
      return;
    }
    const allCode = results.context?.combined_code || code;
    const issuesToFix = Object.entries(results.issues_by_category || {})
      .flatMap(([category, issues]) =>
        issues.filter((issue) =>
          selectedIssues.includes(`${category}-${issue.line}-${issue.description}`)
        )
      );
    if (!issuesToFix.length) {
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
          code: allCode,
          issues: issuesToFix,
          api_key: apiKey,
          mode,
          context: results.context || {},
        }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Fix failed');
      }
      const data = await response.json();
      setFinalCode(data.final_code);
      setFeedback(data.feedback); // Array of {file_path, feedback}
      await handleReAnalyze(data.final_code);
      toast.success('Issues fixed successfully!');
    } catch (err) {
      setError(err.message);
      toast.error(`Fix failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateBestCode = async () => {
    setLoading(true);
    setError(null);
    if (!results || !results.issues_by_category || !apiKey) {
      setError('Missing analysis results or API key');
      toast.error('Missing analysis results or API key');
      setLoading(false);
      return;
    }
    const allCode = results.context?.combined_code || code;
    const allIssues = Object.entries(results.issues_by_category || {}).flatMap(
      ([_, issues]) => issues
    );
    try {
      const response = await fetch('http://127.0.0.1:8000/fix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: allCode,
          issues: allIssues,
          api_key: apiKey,
          mode,
          context: results.context || {},
        }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Generate best code failed');
      }
      const data = await response.json();
      setFinalCode(data.final_code);
      setFeedback(data.feedback);
      await handleReAnalyze(data.final_code);
      toast.success('Best code generated successfully!');
    } catch (err) {
      setError(err.message);
      toast.error(`Generate best code failed: ${err.message}`);
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
        const errorData = await response.json();
        throw new Error(errorData.error || 'Re-analysis failed');
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
        uploadedFiles,
        repoUrl,
        setRepoUrl,
        handleFetchRepo,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};