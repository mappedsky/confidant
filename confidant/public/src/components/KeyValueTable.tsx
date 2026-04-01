import React from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableContainer,
  TableRow,
  TextField,
  IconButton,
  Button,
  Tooltip,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import AutorenewIcon from '@mui/icons-material/Autorenew';

export interface KeyValueRow {
  key: string;
  value: string;
}

interface KeyValueTableProps {
  rows: KeyValueRow[];
  onChange: (newRows: KeyValueRow[]) => void;
  showValues?: boolean;
  editable?: boolean;
  onGenerate?: (idx: number) => void;
  isCredentialPairs?: boolean;
}

/**
 * Reusable key/value pair table used for credential pairs and metadata.
 *
 * Props:
 *   rows         – array of { key, value }
 *   onChange     – (newRows) => void
 *   showValues   – whether to show value column as plain text (vs masked)
 *   editable     – whether rows can be added/edited/deleted
 *   onGenerate   – optional (idx) => void — shows a generate button per row
 *   isCredentialPairs – if true, use "Key" / "Value" headers and mask values
 */
export default function KeyValueTable({
  rows,
  onChange,
  showValues = false,
  editable = false,
  onGenerate,
  isCredentialPairs = false,
}: KeyValueTableProps) {
  const handleKeyChange = (idx: number, key: string) => {
    onChange(rows.map((r, i) => (i === idx ? { ...r, key } : r)));
  };

  const handleValueChange = (idx: number, value: string) => {
    onChange(rows.map((r, i) => (i === idx ? { ...r, value } : r)));
  };

  const handleAdd = () => {
    onChange([...rows, { key: '', value: '' }]);
  };

  const handleRemove = (idx: number) => {
    onChange(rows.filter((_, i) => i !== idx));
  };

  const maskValue = (val: string) => {
    if (showValues || !isCredentialPairs) return val;
    return '••••••••';
  };

  if (!editable && rows.length === 0) {
    return null;
  }

  return (
    <Box>
      <TableContainer
        component={Paper}
        variant="outlined"
        sx={{ borderColor: 'divider', borderRadius: 1, overflowX: 'auto' }}
      >
        <Table size="small" sx={{ minWidth: 640 }}>
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600, width: '40%' }}>Key</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Value</TableCell>
              {editable && <TableCell sx={{ fontWeight: 600, width: 60 }} />}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row, idx) => (
              <TableRow key={idx}>
                <TableCell sx={{ verticalAlign: 'top' }}>
                  {editable ? (
                    <TextField
                      size="small"
                      fullWidth
                      value={row.key}
                      onChange={(e) => handleKeyChange(idx, e.target.value)}
                      placeholder="key"
                      variant="outlined"
                    />
                  ) : (
                    row.key
                  )}
                </TableCell>
                <TableCell sx={{ verticalAlign: 'top' }}>
                  {editable ? (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <TextField
                        size="small"
                        fullWidth
                        value={row.value}
                        onChange={(e) => handleValueChange(idx, e.target.value)}
                        placeholder="value"
                        type={isCredentialPairs && !showValues ? 'password' : 'text'}
                        variant="outlined"
                      />
                      {onGenerate && (
                        <Tooltip title="Generate random value">
                          <IconButton size="small" onClick={() => onGenerate(idx)}>
                            <AutorenewIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  ) : (
                    <Box component="span" sx={{ fontFamily: isCredentialPairs ? 'monospace' : undefined }}>
                      {maskValue(row.value)}
                    </Box>
                  )}
                </TableCell>
                {editable && (
                  <TableCell sx={{ verticalAlign: 'top' }}>
                    <IconButton size="small" color="error" onClick={() => handleRemove(idx)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                )}
              </TableRow>
            ))}
            {rows.length === 0 && !editable && (
              <TableRow>
                <TableCell colSpan={2} sx={{ color: 'text.secondary', fontStyle: 'italic' }}>
                  None
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      {editable && (
        <Button size="small" startIcon={<AddIcon />} onClick={handleAdd} sx={{ mt: 1 }}>
          Add row
        </Button>
      )}
    </Box>
  );
}
