import React from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  Chip,
  Link,
} from '@mui/material';
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
import { useAppContext } from '../contexts/AppContext';
import { ServiceSummary } from '../types/api';
import ActionsMenu from '../components/ActionsMenu';
import { baseDataGridSx } from '../components/dataGridStyles';
import { useAllCursorPages } from '../hooks/useAllCursorPages';

export default function ServiceListPage() {
  const navigate = useNavigate();
  const { clientConfig } = useAppContext();

  const permissions = clientConfig?.generated?.permissions;
  const {
    rows: services,
    loading,
    error,
  } = useAllCursorPages<ServiceSummary, { services: ServiceSummary[]; next_page?: string | null }>({
    fetchPage: (page) => api.getServices({ page }),
    getRows: (response) => response.services || [],
  });

  const columns: GridColDef<ServiceSummary>[] = [
    {
      field: 'id',
      headerName: 'Service ID',
      flex: 1,
      minWidth: 240,
      renderCell: (params: GridRenderCellParams<ServiceSummary, string>) => (
        <Link
          component={RouterLink}
          to={`/services/${params.row.id}`}
          underline="hover"
          sx={{ fontFamily: 'monospace' }}
          onClick={(event) => event.stopPropagation()}
        >
          {params.value}
        </Link>
      ),
    },
    {
      field: 'enabled',
      headerName: 'Status',
      type: 'boolean',
      width: 120,
      headerAlign: 'left',
      align: 'left',
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
      field: 'revision',
      headerName: 'Revision',
      type: 'number',
      width: 105,
      headerAlign: 'left',
      align: 'left',
    },
    {
      field: 'credentials',
      headerName: 'Credentials',
      width: 120,
      sortable: false,
      renderCell: (params: GridRenderCellParams<ServiceSummary, string[]>) => (
        <Typography variant="body2" color="text.secondary">
          {params.value?.length ?? 0}
        </Typography>
      ),
    },
    {
      field: 'modified_date',
      headerName: 'Modified',
      width: 190,
      renderCell: (params: GridRenderCellParams<ServiceSummary, string>) => (
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
      renderCell: (params: GridRenderCellParams<ServiceSummary>) => (
        <ActionsMenu
          items={[
            {
              label: 'View',
              icon: <VisibilityIcon fontSize="small" />,
              onClick: () => navigate(`/services/${params.row.id}`),
            },
            {
              label: 'History',
              icon: <HistoryIcon fontSize="small" />,
              onClick: () => navigate(`/services/${params.row.id}/history`),
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
          Services
        </Typography>
        {permissions?.services?.create && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/services/new')}
            sx={{ bgcolor: '#6bdfab', color: '#424554', '&:hover': { bgcolor: '#229B65', color: '#F4F5F5' } }}
          >
            New Service
          </Button>
        )}
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Box sx={{ flex: 1, minHeight: 420 }}>
        <DataGrid
          rows={services}
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
            filter: {
              filterModel: {
                items: [{ field: 'enabled', operator: 'is', value: 'true' }],
              },
            },
          }}
          sx={baseDataGridSx}
        />
      </Box>
    </Box>
  );
}
