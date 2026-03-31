import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  Chip,
} from '@mui/material';
import { DataGrid, GridToolbar } from '@mui/x-data-grid';
import AddIcon from '@mui/icons-material/Add';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAppContext } from '../contexts/AppContext';

const columns = [
  { field: 'id', headerName: 'Service ID', flex: 1, minWidth: 220 },
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
  { field: 'revision', headerName: 'Revision', type: 'number', width: 105, headerAlign: 'left', align: 'left' },
  {
    field: 'modified_date',
    headerName: 'Modified',
    width: 180,
    valueFormatter: (value) => value ? new Date(value).toLocaleString() : '—',
  },
  { field: 'modified_by', headerName: 'Modified By', flex: 1, minWidth: 160 },
  {
    field: '__action',
    headerName: '',
    width: 50,
    sortable: false,
    filterable: false,
    renderCell: () => <ChevronRightIcon fontSize="small" sx={{ color: 'text.secondary' }} />,
  },
];

const dataGridSx = {
  border: 'none',
  '& .MuiDataGrid-row': { cursor: 'pointer' },
  // Header
  '& .MuiDataGrid-columnHeader': {
    bgcolor: 'primary.main',
    color: 'primary.contrastText',
  },
  '& .MuiDataGrid-columnHeader:focus, & .MuiDataGrid-columnHeader:focus-within': {
    outline: 'none',
  },
  '& .MuiDataGrid-columnHeaderTitle': { fontWeight: 600 },
  '& .MuiDataGrid-sortIcon': { color: 'primary.contrastText', opacity: '1 !important' },
  '& .MuiDataGrid-menuIconButton': { color: 'primary.contrastText' },
  '& .MuiDataGrid-columnSeparator': { color: 'rgba(255,255,255,0.35)' },
  // Fill the empty header area to the right of the last column
  '& .MuiDataGrid-filler': { bgcolor: 'primary.main' },
  // Icon-only toolbar buttons: fontSize 0 hides text nodes (which inherit font size),
  // while MUI icons keep their size via absolute rem-based classes.
  '& .MuiDataGrid-toolbarContainer': {
    px: 1,
    py: 0.5,
    gap: 0.5,
    borderBottom: '1px solid',
    borderColor: 'divider',
  },
  '& .MuiDataGrid-toolbarContainer .MuiButton-root': {
    minWidth: 'unset',
    px: 1,
    fontSize: 0,
    color: 'text.primary',
  },
  '& .MuiDataGrid-toolbarContainer .MuiButton-root .MuiButton-startIcon': {
    mr: 0,
    ml: 0,
  },
  // Chip cells — vertically centre
  '& .MuiDataGrid-cell': {
    display: 'flex',
    alignItems: 'center',
  },
  '& .MuiDataGrid-cell:focus, & .MuiDataGrid-cell:focus-within': {
    outline: 'none',
  },
};

export default function ServiceListPage() {
  const navigate = useNavigate();
  const { clientConfig } = useAppContext();
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const permissions = clientConfig?.generated?.permissions ?? {};

  useEffect(() => {
    api.getServices()
      .then((data) => setServices(data.services || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h5" fontWeight={600}>
          Services
        </Typography>
        {permissions.services?.create && (
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

      <DataGrid
        rows={services}
        columns={columns}
        loading={loading}
        autoHeight
        density="compact"
        onRowClick={(params) => navigate(`/services/${params.row.id}`)}
        slots={{ toolbar: GridToolbar }}
        slotProps={{ toolbar: { showQuickFilter: true } }}
        initialState={{
          filter: {
            filterModel: {
              items: [{ field: 'enabled', operator: 'is', value: 'true' }],
            },
          },
        }}
        sx={dataGridSx}
      />
    </Box>
  );
}
