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
import { GroupDetail, GroupSummary } from '../types/api';

type RouteParams = {
  id?: string;
};

export default function GroupHistoryPage() {
  const { id } = useParams<RouteParams>();
  const navigate = useNavigate();
  const [versions, setVersions] = useState<GroupSummary[]>([]);
  const [currentGroup, setCurrentGroup] = useState<GroupDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [restoringRevision, setRestoringRevision] = useState<number | null>(null);

  useEffect(() => {
    if (!id) {
      setError('Missing group ID.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    Promise.all([
      api.getGroupVersions(id),
      api.getGroup(id),
    ])
      .then(([history, current]) => {
        const sorted = [...(history.versions || [])].sort((a, b) => b.revision - a.revision);
        setVersions(sorted);
        setCurrentGroup(current);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  const latestRevision = currentGroup?.revision ?? versions[0]?.revision;
  const canRestore = currentGroup?.permissions?.update ?? false;

  const handleRestore = async (revision: number) => {
    if (!id) {
      return;
    }

    setRestoreError(null);
    setRestoringRevision(revision);
    try {
      await api.restoreGroupVersion(id, revision);
      navigate(`/groups/${id}`);
    } catch (err) {
      setRestoreError((err as Error).message);
    } finally {
      setRestoringRevision(null);
    }
  };

  const columns: GridColDef<GroupSummary>[] = [
    {
      field: 'revision',
      headerName: 'Version',
      width: 150,
      renderCell: (params: GridRenderCellParams<GroupSummary, number>) => {
        const isCurrent = params.row.revision === latestRevision;
        return (
          <Stack direction="row" spacing={1} alignItems="center">
            <Link
              component={RouterLink}
              to={`/groups/${id}/versions/${params.row.revision}`}
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
      field: 'secrets',
      headerName: 'Secrets',
      width: 140,
      sortable: false,
      renderCell: (params: GridRenderCellParams<GroupSummary, string[]>) => (
        <Typography variant="body2" color="text.secondary">
          {params.value?.length ?? 0}
        </Typography>
      ),
    },
    {
      field: 'modified_date',
      headerName: 'Saved',
      width: 190,
      renderCell: (params: GridRenderCellParams<GroupSummary, string>) => (
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
      renderCell: (params: GridRenderCellParams<GroupSummary, string>) => (
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
      renderCell: (params: GridRenderCellParams<GroupSummary>) => {
        const isCurrent = params.row.revision === latestRevision;
        const restoreDisabled = restoringRevision !== null || isCurrent || !canRestore;
        const restoreTooltip = isCurrent
          ? 'This is already the current version.'
          : !canRestore
            ? 'You do not have permission to restore this group.'
            : '';

        return (
          <ActionsMenu
            items={[
              {
                label: 'View',
                icon: <VisibilityIcon fontSize="small" />,
                onClick: () => navigate(`/groups/${id}/versions/${params.row.revision}`),
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
        onClick={() => navigate(`/groups/${id}`)}
        sx={{ mb: 2 }}
      >
        Back to Group
      </Button>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
        <HistoryIcon color="action" />
        <Typography variant="h5" fontWeight={600}>
          Group History{currentGroup?.id ? ` · ${currentGroup.id}` : ''}
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
