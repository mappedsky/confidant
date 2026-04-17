export const baseDataGridSx = {
  border: 'none',
  '& .MuiDataGrid-columnHeader': {
    bgcolor: 'primary.main',
    color: 'primary.contrastText',
  },
  '& .MuiDataGrid-columnHeader:focus, & .MuiDataGrid-columnHeader:focus-within': {
    outline: 'none',
  },
  '& .MuiDataGrid-columnHeaderTitle': {
    fontWeight: 600,
  },
  '& .MuiDataGrid-sortIcon': {
    color: 'primary.contrastText',
    opacity: '1 !important',
  },
  '& .MuiDataGrid-menuIconButton': {
    color: 'primary.contrastText',
  },
  '& .MuiDataGrid-columnSeparator': {
    color: 'rgba(255,255,255,0.35)',
  },
  '& .MuiDataGrid-filler': {
    bgcolor: 'primary.main',
  },
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
  '& .MuiDataGrid-cell': {
    display: 'flex',
    alignItems: 'center',
  },
  '& .MuiDataGrid-cell:focus, & .MuiDataGrid-cell:focus-within': {
    outline: 'none',
  },
};
