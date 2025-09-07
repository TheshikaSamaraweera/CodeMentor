// src/components/IssueList.js
import React, { useContext } from 'react';
import { Box, Checkbox, FormControlLabel, Typography } from '@mui/material';
import { AppContext } from '../context/AppContext';

const IssueList = ({ issuesData }) => {
  const { handleIssueSelection, selectedIssues } = useContext(AppContext);

  return (
    <Box>
      {Object.entries(issuesData.issues_by_category || {}).map(([category, issues]) => (
        <div key={category}>
          <Typography variant="h6">{category.toUpperCase()} ({issues.length} issues)</Typography>
          <Box sx={{ pl: 2 }}>
            {issues.map((issue, idx) => {
              const issueKey = `${category}-${issue.line}-${issue.description}`;
              return (
                <FormControlLabel
                  key={idx}
                  control={
                    <Checkbox
                      checked={selectedIssues.includes(issueKey)}
                      onChange={() => handleIssueSelection(issue, category)}
                    />
                  }
                  label={
                    <div>
                      <Typography>Line {issue.line}: {issue.description}</Typography>
                      <Typography color="textSecondary">Suggestion: {issue.suggestion}</Typography>
                      <Typography color="error">Severity: {issue.severity}</Typography>
                    </div>
                  }
                />
              );
            })}
          </Box>
        </div>
      ))}
    </Box>
  );
};

export default IssueList;