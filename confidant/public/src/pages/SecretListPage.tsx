import React from 'react';
import { Box, Typography, Button, Alert, Link } from '@mui/material';
import {
  DataGrid,
  GridToolbar,
  GridColDef,
  GridRenderCellParams,
} from '@mui/x-data-grid';
import AddIcon from '@mui/icons-material/Add';
import HistoryIcon from '@mui/icons-material/History';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { SecretSummary } from '../types/api';
import ActionsMenu from '../components/ActionsMenu';
import { baseDataGridSx } from '../components/dataGridStyles';
import { useAllCursorPages } from '../hooks/useAllCursorPages';
import {
  secretDetailPath,
  secretHistoryPath,
} from '../utils/resourceIds';

export default function SecretListPage() {
  const navigate = useNavigate();
  const {
    rows: secrets,
    loading,
    error,
  } = useAllCursorPages<SecretSummary, { secrets: SecretSummary[]; next_page?: string | null }>({
    fetchPage: (page) => api.getSecrets({ page }),
    getRows: (response) => response.secrets || [],
  });

  const columns: GridColDef<SecretSummary>[] = [
    {
      field: 'name',
      headerName: 'Name',
      flex: 1,
      minWidth: 220,
      renderCell: (params: GridRenderCellParams<SecretSummary, string>) => (
        <Link
          component={RouterLink}
          to={secretDetailPath(params.row.id)}
          underline="hover"
          onClick={(event) => event.stopPropagation()}
        >
          {params.value || params.row.id}
        </Link>
      ),
    },
    {
      field: 'id',
      headerName: 'ID',
      flex: 1,
      minWidth: 220,
      renderCell: (params: GridRenderCellParams<SecretSummary, string>) => (
        <Typography variant="body2" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
          {params.value}
        </Typography>
      ),
    },
    {
      field: 'revision',
      headerName: 'Revision',
      type: 'number',
      width: 105,
      headerAlign: 'left',
      align: 'left',
    },
    {
      field: 'modified_date',
      headerName: 'Modified',
      width: 190,
      renderCell: (params: GridRenderCellParams<SecretSummary, string>) => (
        <Typography variant="body2" color="text.secondary">
          {params.value ? new Date(params.value).toLocaleString() : '—'}
        </Typography>
      ),
    },
    {
      field: 'modified_by',
      headerName: 'Modified By',
      flex: 1,
      minWidth: 160,
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
      renderCell: (params: GridRenderCellParams<SecretSummary>) => (
        <ActionsMenu
          items={[
            {
              label: 'View',
              icon: <VisibilityIcon fontSize="small" />,
              onClick: () => navigate(secretDetailPath(params.row.id)),
            },
            {
              label: 'History',
              icon: <HistoryIcon fontSize="small" />,
              onClick: () => navigate(secretHistoryPath(params.row.id)),
            },
          ]}
        />
      ),
    },
  ];

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h5" fontWeight={600}>
          Secrets
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/secrets/new')}
          sx={{ bgcolor: '#6bdfab', color: '#424554', '&:hover': { bgcolor: '#229B65', color: '#F4F5F5' } }}
        >
          New Secret
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Box sx={{ flex: 1, minHeight: 420 }}>
        <DataGrid
          rows={secrets}
          columns={columns}
          loading={loading}
          density="compact"
          pagination
          pageSizeOptions={[25, 50, 100]}
          disableRowSelectionOnClick
          slots={{ toolbar: GridToolbar }}
          slotProps={{ toolbar: { showQuickFilter: true } }}
          initialState={{
            pagination: {
              paginationModel: {
                page: 0,
                pageSize: 25,
              },
            },
          }}
          sx={baseDataGridSx}
        />
      </Box>
    </Box>
  );
}
