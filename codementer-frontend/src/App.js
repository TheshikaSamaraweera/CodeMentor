import React, { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { CssBaseline, ThemeProvider, Box } from '@mui/material';
import Home from './pages/Home';
import Issues from './pages/Issues';
import Results from './pages/Results';
import Sidebar from './components/Sidebar';
import { AppProvider } from './context/AppContext';
import { getTheme } from './theme';

function App() {
  const [themeMode, setThemeMode] = useState('light');
  const theme = getTheme(themeMode);

  return (
    <AppProvider>
      <BrowserRouter>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <Box sx={{ display: 'flex' }}>
            <Sidebar themeMode={themeMode} setThemeMode={setThemeMode} />
            <Box sx={{ flexGrow: 1, p: 3 }}>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/issues" element={<Issues />} />
                <Route path="/results" element={<Results />} />
              </Routes>
            </Box>
          </Box>
        </ThemeProvider>
      </BrowserRouter>
    </AppProvider>
  );
}

export default App;