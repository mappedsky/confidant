import { Box, CircularProgress } from '@mui/material';

interface CenteredSpinnerProps {
  minHeight?: number | string;
}

export default function CenteredSpinner({
  minHeight = '100%',
}: CenteredSpinnerProps) {
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '100%',
        minHeight,
      }}
    >
      <CircularProgress />
    </Box>
  );
}
