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
import { useAppContext } from '../contexts/AppContext';
import { GroupSummary } from '../types/api';
import ActionsMenu from '../components/ActionsMenu';
import { baseDataGridSx } from '../components/dataGridStyles';
import { useAllCursorPages } from '../hooks/useAllCursorPages';

export default function GroupListPage() {
  const navigate = useNavigate();
  const { clientConfig } = useAppContext();
  const permissions = clientConfig?.generated?.permissions;
  const maintenanceMode = clientConfig?.generated?.maintenance_mode ?? false;
  const {
    rows: groups,
    loading,
    error,
  } = useAllCursorPages<GroupSummary, { groups: GroupSummary[]; next_page?: string | null }>({
    fetchPage: (page) => api.getGroups({ page }),
    getRows: (response) => response.groups || [],
  });

  const columns: GridColDef<GroupSummary>[] = [
    {
      field: 'id',
      headerName: 'Group ID',
      flex: 1,
      minWidth: 240,
      renderCell: (params: GridRenderCellParams<GroupSummary, string>) => (
        <Link
          component={RouterLink}
          to={`/groups/${params.row.id}`}
          underline="hover"
          sx={{ fontFamily: 'monospace' }}
          onClick={(event) => event.stopPropagation()}
        >
          {params.value}
        </Link>
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
      field: 'policies',
      headerName: 'Policies',
      width: 120,
      sortable: false,
      renderCell: (
        params: GridRenderCellParams<GroupSummary, GroupSummary['policies']>,
      ) => (
        <Typography variant="body2" color="text.secondary">
          {params.value ? Object.keys(params.value).length : 0}
        </Typography>
      ),
    },
    {
      field: 'modified_date',
      headerName: 'Modified',
      width: 190,
      renderCell: (params: GridRenderCellParams<GroupSummary, string>) => (
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
      renderCell: (params: GridRenderCellParams<GroupSummary>) => (
        <ActionsMenu
          items={[
            {
              label: 'View',
              icon: <VisibilityIcon fontSize="small" />,
              onClick: () => navigate(`/groups/${params.row.id}`),
            },
            {
              label: 'History',
              icon: <HistoryIcon fontSize="small" />,
              onClick: () => navigate(`/groups/${params.row.id}/history`),
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
          Groups
        </Typography>
        {permissions?.groups?.create && !maintenanceMode && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/groups/new')}
            sx={{ bgcolor: '#6bdfab', color: '#424554', '&:hover': { bgcolor: '#229B65', color: '#F4F5F5' } }}
          >
            New Group
          </Button>
        )}
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Box sx={{ flex: 1, minHeight: 420 }}>
        <DataGrid
          rows={groups}
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
