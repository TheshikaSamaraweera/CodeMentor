import React, { useContext } from 'react';
import { Typography, Card, CardContent, Grid } from '@mui/material';
import { AppContext } from '../context/AppContext';

const ScoreSummary = () => {
  const { results, mode } = useContext(AppContext);

  return (
    <Card>
      <CardContent>
        <Typography variant="h5" gutterBottom>
          Code Health
        </Typography>
        <Grid container spacing={2}>
          {mode !== 'full_scan' ? (
            <Grid item xs={12}>
              <Typography variant="h6">
                {mode.charAt(0).toUpperCase() + mode.slice(1)} Score: {results.category_scores?.[mode] || results.overall_score}
              </Typography>
            </Grid>
          ) : (
            <>
              <Grid item xs={12} sm={6}>
                <Typography variant="h6">Overall Score: {results.overall_score}</Typography>
              </Grid>
              {Object.entries(results.category_scores || {}).map(([cat, score]) => (
                <Grid item xs={12} sm={6} key={cat}>
                  <Typography variant="h6">
                    {cat.charAt(0).toUpperCase() + cat.slice(1)} Score: {score}
                  </Typography>
                </Grid>
              ))}
            </>
          )}
        </Grid>
      </CardContent>
    </Card>
  );
};

export default ScoreSummary;