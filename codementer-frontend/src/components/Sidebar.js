import React from 'react';
import { Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, IconButton, Box, Typography } from '@mui/material';
import { Home, BugReport, Assessment, LightMode, DarkMode } from '@mui/icons-material';
import { Link } from 'react-router-dom';

const Sidebar = ({ themeMode, setThemeMode }) => {
  return (
    <Drawer variant="permanent" sx={{ width: 240, flexShrink: 0, '& .MuiDrawer-paper': { width: 240, boxSizing: 'border-box' } }}>
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h6">CodeMenter</Typography>
        <IconButton onClick={() => setThemeMode(themeMode === 'light' ? 'dark' : 'light')}>
          {themeMode === 'light' ? <DarkMode /> : <LightMode />}
        </IconButton>
      </Box>
      <List>
        <ListItem disablePadding>
          <ListItemButton component={Link} to="/">
            <ListItemIcon><Home /></ListItemIcon>
            <ListItemText primary="Home" />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton component={Link} to="/issues">
            <ListItemIcon><BugReport /></ListItemIcon>
            <ListItemText primary="Issues" />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton component={Link} to="/results">
            <ListItemIcon><Assessment /></ListItemIcon>
            <ListItemText primary="Results" />
          </ListItemButton>
        </ListItem>
      </List>
    </Drawer>
  );
};

export default Sidebar;