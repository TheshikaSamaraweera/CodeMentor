import React, { useContext } from 'react';
import { Box, Button, Typography, Card, CardContent, CircularProgress, TextField, Select, MenuItem, List, ListItem, ListItemText } from '@mui/material';
import { useDropzone } from 'react-dropzone';
import { toast } from 'react-toastify'; // Added import
import CodeUploader from '../components/CodeUploader';
import ScoreSummary from '../components/ScoreSummary';
import { AppContext } from '../context/AppContext';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

const Home = () => {
  const { apiKey, setApiKey, mode, setMode, handleAnalyze, results, error, loading, handleFileUpload, uploadedFiles, repoUrl, setRepoUrl, handleFetchRepo } = useContext(AppContext);
  const navigate = useNavigate();

  const onDrop = async (acceptedFiles) => {
    if (acceptedFiles?.length) {
      await handleFileUpload(acceptedFiles);
    } else {
      toast.error('No valid files selected');
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    accept: { 'text/*': ['.py', '.js', '.zip'] },
  });

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
      <Box sx={{ maxWidth: 1200, mx: 'auto', p: 3 }}>
        <Typography variant="h3" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          CodeMenter
        </Typography>
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h5" gutterBottom>
              Upload Project or Files
            </Typography>
            <Box {...getRootProps()} sx={{ border: '2px dashed #ccc', p: 3, textAlign: 'center', mb: 2, bgcolor: isDragActive ? 'action.hover' : 'background.paper' }}>
              <input {...getInputProps()} />
              <Typography>{isDragActive ? 'Drop files here...' : 'Drag and drop files or zip (multiple supported)'}</Typography>
            </Box>
            <TextField
              label="GitHub Repo URL (Public)"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              fullWidth
              sx={{ mb: 2 }}
            />
            <Button
              variant="outlined"
              onClick={handleFetchRepo}
              disabled={loading || !repoUrl}
              fullWidth
              sx={{ mb: 2 }}
            >
              {loading ? <CircularProgress size={24} color="inherit" /> : 'Fetch GitHub Repo'}
            </Button>
            {uploadedFiles.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="h6">Uploaded Files:</Typography>
                <List dense>
                  {uploadedFiles.map((file, index) => (
                    <ListItem key={index}>
                      <ListItemText primary={file} />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}
            <Typography variant="subtitle1" gutterBottom>
              Preview First File:
            </Typography>
            <CodeUploader />
            <TextField
              label="Gemini API Key"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              fullWidth
              sx={{ mb: 2 }}
            />
            <Select
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              fullWidth
              sx={{ mb: 2 }}
            >
              <MenuItem value="full_scan">Full Scan</MenuItem>
              <MenuItem value="quality">Quality</MenuItem>
              <MenuItem value="security">Security</MenuItem>
              <MenuItem value="code_smell">Code Smell</MenuItem>
            </Select>
            <Button
              variant="contained"
              onClick={handleAnalyze}
              disabled={loading || !apiKey}
              fullWidth
              size="large"
              sx={{ mt: 2 }}
            >
              {loading ? <CircularProgress size={24} color="inherit" /> : 'Analyze Code'}
            </Button>
            {error && (
              <Typography color="error" sx={{ mt: 2 }}>
                {error}
              </Typography>
            )}
          </CardContent>
        </Card>
        {results && (
          <Card>
            <CardContent>
              <ScoreSummary />
              <Button
                variant="outlined"
                onClick={() => navigate('/issues')}
                size="large"
                sx={{ mt: 2 }}
              >
                View Issues
              </Button>
            </CardContent>
          </Card>
        )}
      </Box>
    </motion.div>
  );
};

export default Home;