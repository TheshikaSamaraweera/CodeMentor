import React, { useContext } from 'react';
import { TextField, Box } from '@mui/material';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { solarizedlight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { AppContext } from '../context/AppContext';

const CodeUploader = () => {
  const { code, setCode, handleFileUpload } = useContext(AppContext);

  return (
    <Box>
      <input
        type="file"
        onChange={handleFileUpload}
        style={{ marginBottom: 16, display: 'block' }}
      />
      <Box sx={{ position: 'relative', bgcolor: 'background.paper', borderRadius: 2, overflow: 'hidden' }}>
        <SyntaxHighlighter
          language="python"
          style={solarizedlight}
          customStyle={{ margin: 0, padding: 16, minHeight: 200 }}
        >
          {code || '// Paste or upload your code here'}
        </SyntaxHighlighter>
        <TextField
          value={code}
          onChange={(e) => setCode(e.target.value)}
          multiline
          fullWidth
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            opacity: 0,
            '& textarea': { fontFamily: 'monospace', fontSize: '14px' },
          }}
        />
      </Box>
    </Box>
  );
};

export default CodeUploader;