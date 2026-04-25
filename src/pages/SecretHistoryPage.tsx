import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Link,
  Stack,
  Typography,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import HistoryIcon from '@mui/icons-material/History';
import RestoreIcon from '@mui/icons-material/Restore';
import VisibilityIcon from '@mui/icons-material/Visibility';
import {
  DataGrid,
  GridColDef,
  GridRenderCellParams,
  GridToolbar,
} from '@mui/x-data-grid';
import { Link as RouterLink, useNavigate, useSearchParams } from 'react-router-dom';
import ActionsMenu from '../components/ActionsMenu';
import CenteredSpinner from '../components/CenteredSpinner';
import { baseDataGridSx } from '../components/dataGridStyles';
import { api } from '../api';
import { SecretDetail, SecretSummary } from '../types/api';
import {
  secretDetailPath,
  secretVersionPath,
} from '../utils/resourceIds';

export default function SecretHistoryPage() {
  const [searchParams] = useSearchParams();
  const id = searchParams.get('id');
  const navigate = useNavigate();
  const [versions, setVersions] = useState<SecretSummary[]>([]);
  const [currentSecret, setCurrentSecret] = useState<SecretDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [restoringRevision, setRestoringRevision] = useState<number | null>(null);

  useEffect(() => {
    if (!id) {
      setError('Missing secret ID.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    Promise.all([
      api.getSecretVersions(id),
      api.getSecret(id),
    ])
      .then(([history, current]) => {
        const sorted = [...(history.versions || [])].sort((a, b) => b.revision - a.revision);
        setVersions(sorted);
        setCurrentSecret(current);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  const latestRevision = currentSecret?.revision ?? versions[0]?.revision;
  const canRestore =
    currentSecret?.permissions?.revert
    ?? currentSecret?.permissions?.update
    ?? false;

  const handleRestore = async (revision: number) => {
    if (!id) {
      return;
    }

    setRestoreError(null);
    setRestoringRevision(revision);
    try {
      await api.restoreSecretVersion(id, revision);
      navigate(secretDetailPath(id!));
    } catch (err) {
      setRestoreError((err as Error).message);
    } finally {
      setRestoringRevision(null);
    }
  };

  const columns: GridColDef<SecretSummary>[] = [
    {
      field: 'revision',
      headerName: 'Version',
      width: 150,
      renderCell: (params: GridRenderCellParams<SecretSummary, number>) => {
        const isCurrent = params.row.revision === latestRevision;
        return (
          <Stack direction="row" spacing={1} alignItems="center">
            <Link
              component={RouterLink}
              to={secretVersionPath(id!, params.row.revision)}
              underline="hover"
              onClick={(event) => event.stopPropagation()}
            >
              v{params.row.revision}
            </Link>
            {isCurrent && <Chip label="Current" size="small" color="primary" variant="outlined" />}
          </Stack>
        );
      },
    },
    {
      field: 'name',
      headerName: 'Name',
      flex: 1,
      minWidth: 220,
      renderCell: (params: GridRenderCellParams<SecretSummary, string>) => (
        <Typography variant="body2">{params.value || params.row.id}</Typography>
      ),
    },
    {
      field: 'modified_date',
      headerName: 'Saved',
      width: 190,
      renderCell: (params: GridRenderCellParams<SecretSummary, string>) => (
        <Typography variant="body2" color="text.secondary">
          {params.value ? new Date(params.value).toLocaleString() : '—'}
        </Typography>
      ),
    },
    {
      field: 'modified_by',
      headerName: 'Author',
      flex: 1,
      minWidth: 180,
      renderCell: (params: GridRenderCellParams<SecretSummary, string>) => (
        <Typography variant="body2" color="text.secondary">
          {params.value || '—'}
        </Typography>
      ),
    },
    {
      field: '__actions',
      headerName: '',
      width: 60,
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
      align: 'right',
      renderCell: (params: GridRenderCellParams<SecretSummary>) => {
        const isCurrent = params.row.revision === latestRevision;
        const restoreDisabled = restoringRevision !== null || isCurrent || !canRestore;
        const restoreTooltip = isCurrent
          ? 'This is already the current version.'
          : !canRestore
            ? 'You do not have permission to restore this secret.'
            : '';

        return (
          <ActionsMenu
            items={[
              {
                label: 'View',
                icon: <VisibilityIcon fontSize="small" />,
                onClick: () =>
                  navigate(secretVersionPath(id!, params.row.revision)),
              },
              {
                label: restoringRevision === params.row.revision ? 'Restoring…' : 'Restore',
                icon: <RestoreIcon fontSize="small" />,
                onClick: () => handleRestore(params.row.revision),
                disabled: restoreDisabled,
                tooltip: restoreTooltip,
              },
            ]}
          />
        );
      },
    },
  ];

  return (
    <Box>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate(secretDetailPath(id!))}
        sx={{ mb: 2 }}
      >
        Back to Secret
      </Button>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
        <HistoryIcon color="action" />
        <Typography variant="h5" fontWeight={600}>
          Secret History{currentSecret?.name ? ` · ${currentSecret.name}` : ''}
        </Typography>
      </Box>

      {restoreError && <Alert severity="error" sx={{ mb: 2 }}>{restoreError}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading ? (
        <CenteredSpinner minHeight={320} />
      ) : (
        <DataGrid
          rows={versions}
          columns={columns}
          getRowId={(row) => row.revision}
          autoHeight
          density="compact"
          disableRowSelectionOnClick
          slots={{ toolbar: GridToolbar }}
          slotProps={{ toolbar: { showQuickFilter: true } }}
          sx={baseDataGridSx}
        />
      )}
    </Box>
  );
}
