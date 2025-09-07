import React, { useContext } from 'react';
import { Typography, Card, CardContent, Grid } from '@mui/material';
import { AppContext } from '../context/AppContext';

const Analytics = () => {
  const { initialIssuesCount, selectedIssues, remainingResults, initialScore } = useContext(AppContext);

  return (
    <Card>
      <CardContent>
        <Typography variant="h5" gutterBottom>
          Analysis Summary
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <Typography>Initial Issues: {initialIssuesCount}</Typography>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Typography>Issues Fixed: {selectedIssues.length}</Typography>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Typography>Remaining Issues: {remainingResults ? remainingResults.total_unique_issues : initialIssuesCount - selectedIssues.length}</Typography>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Typography>Initial Score: {initialScore}</Typography>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Typography>Updated Score: {remainingResults ? remainingResults.overall_score : initialScore}</Typography>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Typography>Score Improvement: {remainingResults ? remainingResults.overall_score - initialScore : 0}</Typography>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default Analytics;