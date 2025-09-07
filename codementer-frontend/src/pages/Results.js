import React, { useContext } from 'react';
import { Box, Typography, Card, CardContent, Button } from '@mui/material';
import DiffViewer from '../components/DiffViewer';
import Analytics from '../components/Analytics';
import { AppContext } from '../context/AppContext';
import { motion } from 'framer-motion';

const Results = () => {
  const { finalCode, feedback, handleDownload } = useContext(AppContext);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
      <Box sx={{ maxWidth: 1200, mx: 'auto', p: 3 }}>
        <Typography variant="h3" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          Results
        </Typography>
        {finalCode && (
          <Box>
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Analytics />
              </CardContent>
            </Card>
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h5" gutterBottom>
                  Code Comparison
                </Typography>
                <DiffViewer />
                <Button
                  variant="contained"
                  onClick={handleDownload}
                  size="large"
                  sx={{ mt: 2 }}
                >
                  Download Fixed Code
                </Button>
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <Typography variant="h5" gutterBottom>
                  Feedback
                </Typography>
                <pre style={{ backgroundColor: 'background.paper', p: 2, borderRadius: 4, overflow: 'auto' }}>
                  {JSON.stringify(feedback, null, 2)}
                </pre>
              </CardContent>
            </Card>
          </Box>
        )}
      </Box>
    </motion.div>
  );
};

export default Results;