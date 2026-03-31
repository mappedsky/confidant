import { createTheme } from '@mui/material/styles';

export function createAppTheme(mode) {
  const isDark = mode === 'dark';

  // Light mode link/accent: #3d40b8 — ~8:1 on white (AAA)
  // Dark mode link/accent:  #c0c2ff — ~9:1 on #21232e (AAA)
  const linkColor = isDark ? '#c0c2ff' : '#3d40b8';
  // secondary.main is the high-contrast accent (#c0c2ff dark / #3d40b8 light).
  // We use it as the default color for all interactive form controls so that
  // focus rings, checked state, etc. are visible against both backgrounds.
  const formControlColor = 'secondary';

  return createTheme({
    palette: {
      mode,
      primary: {
        // Dark: darker so #F4F5F5 contrastText achieves ~9:1 on AppBar bg
        main: isDark ? '#2e3154' : '#585C70',
        contrastText: '#F4F5F5',
      },
      secondary: {
        // Dark: bright accent — ~9:1 on paper bg #21232e
        main: isDark ? '#c0c2ff' : '#3d40b8',
        contrastText: isDark ? '#16171f' : '#F4F5F5',
      },
      background: {
        default: isDark ? '#16171f' : '#F4F5F5',
        paper: isDark ? '#21232e' : '#ffffff',
      },
      text: {
        primary: isDark ? '#f0f1f8' : '#1a1c2a',
        secondary: isDark ? '#a8abcc' : '#4a4d65',
      },
      action: {
        active: linkColor,
      },
    },
    components: {
      MuiListItemButton: {
        styleOverrides: {
          root: {
            '&.Mui-selected': {
              backgroundColor: isDark ? 'rgba(192, 194, 255, 0.15)' : 'rgba(61, 64, 184, 0.10)',
            },
            '&.Mui-selected:hover': {
              backgroundColor: isDark ? 'rgba(192, 194, 255, 0.22)' : 'rgba(61, 64, 184, 0.16)',
            },
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: ({ ownerState, theme }) => ({
            // Default (primary) text and outlined buttons inherit primary.main,
            // which is near-invisible in dark mode. Use text.primary instead.
            ...(ownerState.color === 'primary' && ownerState.variant !== 'contained' && {
              color: theme.palette.text.primary,
              ...(ownerState.variant === 'outlined' && {
                borderColor: theme.palette.text.secondary,
                '&:hover': { borderColor: theme.palette.text.primary },
              }),
            }),
          }),
        },
      },
      MuiLink: {
        styleOverrides: {
          root: {
            color: linkColor,
          },
        },
      },
      // Use the high-contrast accent color for all interactive form controls so
      // that focus rings, checked/selected indicators, and input labels remain
      // visible in both light and dark mode. primary.main is intentionally dark
      // (matches the AppBar) and has near-zero contrast on dark paper.
      MuiCheckbox: { defaultProps: { color: formControlColor } },
      MuiRadio: { defaultProps: { color: formControlColor } },
      MuiSwitch: { defaultProps: { color: formControlColor } },
      MuiTextField: { defaultProps: { color: formControlColor } },
      MuiFormControl: { defaultProps: { color: formControlColor } },
    },
    typography: {
      fontFamily: '"Helvetica Neue", Arial, sans-serif',
    },
  });
}
