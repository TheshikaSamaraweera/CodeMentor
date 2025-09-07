import React, { useContext } from 'react';
import { Box, Button, Typography, Card, CardContent, CircularProgress, TextField, Select, MenuItem } from '@mui/material';
import CodeUploader from '../components/CodeUploader';
import ScoreSummary from '../components/ScoreSummary';
import { AppContext } from '../context/AppContext';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

const Home = () => {
  const { code, apiKey, setApiKey, mode, setMode, handleAnalyze, results, error, loading } = useContext(AppContext);
  const navigate = useNavigate();

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
      <Box sx={{ maxWidth: 1200, mx: 'auto', p: 3 }}>
        <Typography variant="h3" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          CodeMenter
        </Typography>
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h5" gutterBottom>
              Upload and Analyze Code
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
              disabled={loading || !code || !apiKey}
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