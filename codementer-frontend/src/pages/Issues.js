import React, { useContext, useMemo } from 'react';
import { Box, Button, Typography, Card, CardContent, CircularProgress } from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import Analytics from '../components/Analytics';
import { AppContext } from '../context/AppContext';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

const Issues = () => {
  const { results, remainingResults, handleFix, handleGenerateBestCode, loading, selectedIssues, handleIssueSelection } = useContext(AppContext);
  const navigate = useNavigate();

  const columns = useMemo(
    () => [
      {
        field: 'selection',
        headerName: '',
        width: 50,
        renderCell: (params) => (
          <input
            type="checkbox"
            checked={selectedIssues.includes(params.row.id)}
            onChange={() => handleIssueSelection(params.row.issue, params.row.category)}
          />
        ),
      },
      { field: 'line', headerName: 'Line', width: 80 },
      { field: 'description', headerName: 'Description', width: 300 },
      { field: 'suggestion', headerName: 'Suggestion', width: 300 },
      { field: 'severity', headerName: 'Severity', width: 120 },
      { field: 'category', headerName: 'Category', width: 150 },
    ],
    [selectedIssues, handleIssueSelection]
  );

  const rows = useMemo(() => {
    const issuesData = remainingResults || results;
    return Object.entries(issuesData?.issues_by_category || {}).flatMap(([category, issues]) =>
      issues.map((issue, idx) => ({
        id: `${category}-${issue.line}-${issue.description}`,
        line: issue.line,
        description: issue.description,
        suggestion: issue.suggestion,
        severity: issue.severity,
        category,
        issue,
      }))
    );
  }, [remainingResults, results]);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
      <Box sx={{ maxWidth: 1200, mx: 'auto', p: 3 }}>
        <Typography variant="h3" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          Issues
        </Typography>
        {results && (
          <Box>
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Analytics />
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <Typography variant="h5" gutterBottom>
                  Code Issues
                </Typography>
                <Box sx={{ height: 400, width: '100%' }}>
                  <DataGrid
                    rows={rows}
                    columns={columns}
                    pageSize={10}
                    rowsPerPageOptions={[10, 20, 50]}
                    checkboxSelection={false}
                    disableSelectionOnClick
                    sx={{ '& .MuiDataGrid-cell': { py: 2 } }}
                  />
                </Box>
                <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
                  <Button
                    variant="contained"
                    onClick={handleFix}
                    disabled={loading || selectedIssues.length === 0}
                    size="large"
                  >
                    {loading ? <CircularProgress size={24} color="inherit" /> : 'Apply Fixes'}
                  </Button>
                  <Button
                    variant="contained"
                    onClick={handleGenerateBestCode}
                    disabled={loading}
                    size="large"
                  >
                    {loading ? <CircularProgress size={24} color="inherit" /> : 'Generate Best Code'}
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={() => navigate('/results')}
                    size="large"
                  >
                    View Results
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Box>
        )}
      </Box>
    </motion.div>
  );
};

export default Issues;