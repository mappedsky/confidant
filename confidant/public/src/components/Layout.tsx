import React from 'react';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  AppBar,
  Toolbar,
  CircularProgress,
  Alert,
  Button,
} from '@mui/material';
import LockIcon from '@mui/icons-material/Lock';
import SettingsIcon from '@mui/icons-material/Settings';
import LogoutIcon from '@mui/icons-material/Logout';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAppContext } from '../contexts/AppContext';

const DRAWER_WIDTH = 220;
const APPBAR_HEIGHT = 80;

const navItems = [
  { label: 'Credentials', path: '/credentials', icon: <LockIcon /> },
  { label: 'Services', path: '/services', icon: <SettingsIcon /> },
];

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { userEmail, loading, error } = useAppContext();

  return (
    <Box sx={{ display: 'flex', height: '100vh', bgcolor: 'background.default' }}>
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
            bgcolor: 'background.paper',
            top: APPBAR_HEIGHT,
            height: `calc(100% - ${APPBAR_HEIGHT}px)`,
          },
        }}
      >
        <List sx={{ flexGrow: 1, pt: 1 }}>
          {navItems.map(({ label, path, icon }) => {
            const active = location.pathname.startsWith(path);
            return (
              <ListItem key={path} disablePadding>
                <ListItemButton
                  selected={active}
                  onClick={() => navigate(path)}
                  sx={{
                    borderRadius: 1,
                    mx: 1,
                    mb: 0.5,
                    '&.Mui-selected': { color: 'secondary.main' },
                    '&.Mui-selected .MuiListItemIcon-root': { color: 'secondary.main' },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={label}
                    primaryTypographyProps={{ fontWeight: active ? 600 : 400 }}
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Drawer>

      <AppBar
        position="fixed"
        elevation={1}
        sx={{
          bgcolor: 'primary.main',
          zIndex: (theme) => theme.zIndex.drawer + 1,
          height: APPBAR_HEIGHT,
        }}
      >
        <Toolbar sx={{ height: APPBAR_HEIGHT, minHeight: `${APPBAR_HEIGHT}px !important` }}>
          <Box sx={{ display: 'flex', alignItems: 'center', width: DRAWER_WIDTH - 24 }}>
            <Box
              component="img"
              src="/images/logo.svg"
              alt="Confidant"
              sx={{ height: 72, width: 'auto' }}
              onError={(event) => {
                event.currentTarget.style.display = 'none';
              }}
            />
          </Box>

          <Box sx={{ flexGrow: 1 }} />

          {userEmail && (
            <Typography
              variant="body2"
              sx={{ color: 'primary.contrastText', mr: 2, display: { xs: 'none', sm: 'block' } }}
            >
              {userEmail}
            </Typography>
          )}

          <Button
            href="/loggedout"
            size="small"
            startIcon={<LogoutIcon fontSize="small" />}
            sx={{
              color: 'primary.contrastText',
              textTransform: 'none',
              border: '1px solid rgba(244,245,245,0.5)',
              '&:hover': { bgcolor: 'rgba(244,245,245,0.1)' },
            }}
          >
            Log Out
          </Button>
        </Toolbar>
      </AppBar>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          mt: `${APPBAR_HEIGHT}px`,
        }}
      >
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Box sx={{ p: 3 }}>
            <Alert severity="error">{error}</Alert>
          </Box>
        ) : (
          <Box sx={{ flexGrow: 1, overflow: 'auto', p: 3 }}>
            {children}
          </Box>
        )}
      </Box>
    </Box>
  );
}
