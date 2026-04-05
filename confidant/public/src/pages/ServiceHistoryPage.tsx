import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
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
import { Link as RouterLink, useNavigate, useParams } from 'react-router-dom';
import ActionsMenu from '../components/ActionsMenu';
import { baseDataGridSx } from '../components/dataGridStyles';
import { api } from '../api';
import { ServiceDetail, ServiceSummary } from '../types/api';

type RouteParams = {
  id?: string;
};

export default function ServiceHistoryPage() {
  const { id } = useParams<RouteParams>();
  const navigate = useNavigate();
  const [versions, setVersions] = useState<ServiceSummary[]>([]);
  const [currentService, setCurrentService] = useState<ServiceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [restoringRevision, setRestoringRevision] = useState<number | null>(null);

  useEffect(() => {
    if (!id) {
      setError('Missing service ID.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    Promise.all([
      api.getServiceVersions(id),
      api.getService(id),
    ])
      .then(([history, current]) => {
        const sorted = [...(history.versions || [])].sort((a, b) => b.revision - a.revision);
        setVersions(sorted);
        setCurrentService(current);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  const latestRevision = currentService?.revision ?? versions[0]?.revision;
  const canRestore = currentService?.permissions?.update ?? false;

  const handleRestore = async (revision: number) => {
    if (!id) {
      return;
    }

    setRestoreError(null);
    setRestoringRevision(revision);
    try {
      await api.restoreServiceVersion(id, revision);
      navigate(`/services/${id}`);
    } catch (err) {
      setRestoreError((err as Error).message);
    } finally {
      setRestoringRevision(null);
    }
  };

  const columns: GridColDef<ServiceSummary>[] = [
    {
      field: 'revision',
      headerName: 'Version',
      width: 150,
      renderCell: (params: GridRenderCellParams<ServiceSummary, number>) => {
        const isCurrent = params.row.revision === latestRevision;
        return (
          <Stack direction="row" spacing={1} alignItems="center">
            <Link
              component={RouterLink}
              to={`/services/${id}/versions/${params.row.revision}`}
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
      field: 'enabled',
      headerName: 'Status',
      width: 120,
      renderCell: (params) => (
        <Chip
          label={params.value ? 'Enabled' : 'Disabled'}
          size="small"
          color={params.value ? 'success' : 'default'}
          variant="outlined"
        />
      ),
    },
    {
      field: 'credentials',
      headerName: 'Credentials',
      width: 140,
      sortable: false,
      renderCell: (params: GridRenderCellParams<ServiceSummary, string[]>) => (
        <Typography variant="body2" color="text.secondary">
          {params.value?.length ?? 0}
        </Typography>
      ),
    },
    {
      field: 'modified_date',
      headerName: 'Saved',
      width: 190,
      renderCell: (params: GridRenderCellParams<ServiceSummary, string>) => (
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
      renderCell: (params: GridRenderCellParams<ServiceSummary, string>) => (
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
      renderCell: (params: GridRenderCellParams<ServiceSummary>) => {
        const isCurrent = params.row.revision === latestRevision;
        const restoreDisabled = restoringRevision !== null || isCurrent || !canRestore;
        const restoreTooltip = isCurrent
          ? 'This is already the current version.'
          : !canRestore
            ? 'You do not have permission to restore this service.'
            : '';

        return (
          <ActionsMenu
            items={[
              {
                label: 'View',
                icon: <VisibilityIcon fontSize="small" />,
                onClick: () => navigate(`/services/${id}/versions/${params.row.revision}`),
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
        onClick={() => navigate(`/services/${id}`)}
        sx={{ mb: 2 }}
      >
        Back to Service
      </Button>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
        <HistoryIcon color="action" />
        <Typography variant="h5" fontWeight={600}>
          Service History{currentService?.id ? ` · ${currentService.id}` : ''}
        </Typography>
      </Box>

      {restoreError && <Alert severity="error" sx={{ mb: 2 }}>{restoreError}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', pt: 8 }}>
          <CircularProgress />
        </Box>
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
