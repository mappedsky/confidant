import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Button,
  TextField,
  FormControlLabel,
  Checkbox,
  Card,
  CardContent,
  CardActions,
  CircularProgress,
  Alert,
  Divider,
  IconButton,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Link,
  Chip,
  Stack,
  Autocomplete,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import RefreshIcon from '@mui/icons-material/Refresh';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import { api } from '../api';
import { useAppContext } from '../contexts/AppContext';

function SectionLabel({ children }) {
  return (
    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
      {children}
    </Typography>
  );
}

function ReadOnlyField({ label, value, sx: sxProp, valueSx }) {
  return (
    <Box sx={sxProp}>
      <Typography variant="caption" color="text.secondary" display="block" mb={0.25}>
        {label}
      </Typography>
      <Typography variant="body2" sx={valueSx}>{value ?? '—'}</Typography>
    </Box>
  );
}

export default function ServiceDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { clientConfig } = useAppContext();
  const isNew = !id;

  const permissions = clientConfig?.generated?.permissions ?? {};
  const awsAccounts = clientConfig?.generated?.aws_accounts ?? [];
  const showGrants = clientConfig?.generated?.kms_auth_manage_grants ?? false;

  const [service, setService] = useState(null);
  const [allCredentials, setAllCredentials] = useState([]);
  const [roles, setRoles] = useState([]);
  const [grants, setGrants] = useState(null);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(isNew);
  const [error, setError] = useState(null);
  const [saveError, setSaveError] = useState(null);
  const [conflicts, setConflicts] = useState(null);
  const [grantError, setGrantError] = useState(null);

  const [formId, setFormId] = useState('');
  const [formEnabled, setFormEnabled] = useState(true);
  const [formAccount, setFormAccount] = useState('');
  const [formCredentials, setFormCredentials] = useState([]);

  const populateForm = useCallback((svc) => {
    setFormId(svc.id ?? '');
    setFormEnabled(svc.enabled ?? true);
    setFormAccount(svc.account ?? '');
    setFormCredentials(
      (svc.credentials ?? []).map((c) => ({
        id: c.id,
        name: c.name || c.id,
        revision: c.revision,
        enabled: c.enabled,
      }))
    );
  }, []);

  useEffect(() => {
    api.getCredentials()
      .then((data) => setAllCredentials(data.credentials || []))
      .catch(() => {});

    api.getRoles()
      .then((data) => setRoles(data.roles || []))
      .catch(() => {});

    if (isNew) {
      setService({ id: '', enabled: true, credentials: [], account: null });
      return;
    }

    setLoading(true);
    const promises = [api.getService(id)];
    if (showGrants) promises.push(api.getGrants(id).catch(() => null));

    Promise.all(promises)
      .then(([svc, grantData]) => {
        setService(svc);
        populateForm(svc);
        if (grantData) setGrants(grantData.grants);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id, isNew, showGrants, populateForm]);

  const handleCancel = () => {
    if (isNew) { navigate('/services'); return; }
    populateForm(service);
    setSaveError(null);
    setConflicts(null);
    setEditing(false);
  };

  const handleAddCredential = () => {
    setFormCredentials((prev) => [...prev, { id: '', name: '', isNew: true }]);
  };

  const handleRemoveCredential = (idx) => {
    setFormCredentials((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleCredentialChange = (idx, credId) => {
    const cred = allCredentials.find((c) => c.id === credId);
    setFormCredentials((prev) =>
      prev.map((c, i) => i === idx ? { id: credId, name: cred?.name || credId, enabled: cred?.enabled } : c)
    );
  };

  const handleEnsureGrants = async () => {
    setGrantError(null);
    try {
      const data = await api.updateGrants(id);
      setGrants(data.grants);
    } catch (err) {
      setGrantError(err.message);
    }
  };

  const handleSave = async () => {
    setSaveError(null);
    setConflicts(null);

    const credIds = formCredentials.map((c) => c.id);
    if (new Set(credIds).size !== credIds.length) {
      setSaveError('Credentials must be unique.');
      return;
    }

    if (isNew) {
      try {
        await api.getService(formId);
        setSaveError(`Service with id ${formId} already exists.`);
        return;
      } catch (err) {
        if (err.status !== 404) {
          setSaveError('Failed to check if service already exists.');
          return;
        }
      }
    }

    const payload = {
      id: formId,
      enabled: formEnabled,
      account: formAccount || null,
      credentials: credIds,
    };

    setSaving(true);
    try {
      let saved;
      if (isNew) {
        saved = await api.createService(payload);
        navigate(`/services/${saved.id}`, { replace: true });
      } else {
        saved = await api.updateService(id, payload);
        setService(saved);
        populateForm(saved);
        setEditing(false);
      }
    } catch (err) {
      setSaveError(err.message);
      if (err.data?.conflicts) setConflicts(err.data.conflicts);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', pt: 8 }}><CircularProgress /></Box>;
  }

  if (error) {
    return (
      <Box>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/services')} sx={{ mb: 2 }}>
          Back to Services
        </Button>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  const canEdit = isNew ? permissions.services?.create : service?.permissions?.update;

  return (
    <Box>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/services')} sx={{ mb: 2 }}>
        Back to Services
      </Button>

      <Typography variant="h5" fontWeight={600} mb={3}>
        {isNew ? 'New Service' : (service?.id || id)}
      </Typography>

      {grantError && <Alert severity="warning" sx={{ mb: 2 }}>{grantError}</Alert>}

      {saveError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {saveError}
          {conflicts && (
            <Box mt={1}>
              <Typography variant="body2">Conflicting credential pair keys:</Typography>
              {Object.entries(conflicts).map(([key, info]) => (
                <Box key={key} ml={2}>
                  <Typography variant="body2"><strong>{key}</strong></Typography>
                  {info.credentials?.map((cid) => (
                    <Typography key={cid} variant="body2" ml={2}>
                      Credential: <Link component={RouterLink} to={`/credentials/${cid}`}>{cid}</Link>
                    </Typography>
                  ))}
                </Box>
              ))}
              <Typography variant="body2" mt={1}>
                Please ensure credential pair keys are unique, then try again.
              </Typography>
            </Box>
          )}
        </Alert>
      )}

      <Card elevation={1}>
        <CardContent sx={{ p: 3 }}>
          <Stack spacing={3}>

            {/* Service ID */}
            {isNew ? (
              <Autocomplete
                freeSolo
                options={roles}
                value={formId}
                onInputChange={(_, val) => setFormId(val)}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Service ID"
                    size="small"
                    required
                    placeholder="Enter or select IAM role"
                  />
                )}
              />
            ) : (
              <ReadOnlyField
                label="Service ID"
                value={service?.id}
                valueSx={{ fontFamily: 'monospace' }}
              />
            )}

            {/* AWS Account */}
            {awsAccounts.length > 0 && (
              editing ? (
                <FormControl size="small" fullWidth>
                  <InputLabel>AWS Account</InputLabel>
                  <Select
                    label="AWS Account"
                    value={formAccount}
                    onChange={(e) => setFormAccount(e.target.value)}
                    displayEmpty
                  >
                    <MenuItem value=""><em>No account scoping</em></MenuItem>
                    {awsAccounts.filter(Boolean).map((acct) => (
                      <MenuItem key={acct} value={acct}>{acct}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              ) : (
                <ReadOnlyField label="AWS Account" value={service?.account || 'No account scoping'} />
              )
            )}

            {/* Enabled — existing services only */}
            {!isNew && (
              editing ? (
                <FormControlLabel
                  control={<Checkbox checked={formEnabled} onChange={(e) => setFormEnabled(e.target.checked)} />}
                  label="Enabled"
                />
              ) : (
                <Box>
                  <SectionLabel>Status</SectionLabel>
                  <Chip
                    label={service?.enabled ? 'Enabled' : 'Disabled'}
                    size="small"
                    color={service?.enabled ? 'success' : 'default'}
                    variant="outlined"
                  />
                </Box>
              )
            )}

            {/* Credentials */}
            <Box>
              <SectionLabel>Credentials</SectionLabel>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Credential</TableCell>
                    {!editing && <TableCell sx={{ fontWeight: 600 }}>Revision</TableCell>}
                    {editing && <TableCell sx={{ width: 60 }} />}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {formCredentials.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={3} sx={{ color: 'text.secondary', fontStyle: 'italic' }}>
                        No credentials assigned.
                      </TableCell>
                    </TableRow>
                  ) : (
                    formCredentials.map((cred, idx) => (
                      <TableRow key={idx}>
                        <TableCell>
                          {editing ? (
                            <FormControl size="small" fullWidth>
                              <Select
                                value={cred.id}
                                onChange={(e) => handleCredentialChange(idx, e.target.value)}
                                displayEmpty
                              >
                                <MenuItem value=""><em>Select credential</em></MenuItem>
                                {allCredentials
                                  .filter((c) => c.enabled || c.id === cred.id)
                                  .map((c) => (
                                    <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>
                                  ))}
                              </Select>
                            </FormControl>
                          ) : (
                            <Box>
                              <Link component={RouterLink} to={`/credentials/${cred.id}`}>
                                {cred.name || cred.id}
                              </Link>
                              {!cred.enabled && (
                                <Typography component="span" color="text.secondary" ml={1}>(disabled)</Typography>
                              )}
                            </Box>
                          )}
                        </TableCell>
                        {!editing && (
                          <TableCell>
                            <Typography color="text.secondary">{cred.revision}</Typography>
                          </TableCell>
                        )}
                        {editing && (
                          <TableCell>
                            <IconButton size="small" color="error" onClick={() => handleRemoveCredential(idx)}>
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </TableCell>
                        )}
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
              {editing && (
                <Button size="small" startIcon={<AddIcon />} onClick={handleAddCredential} sx={{ mt: 1 }}>
                  Add credential
                </Button>
              )}
            </Box>

            {/* Grants */}
            {!isNew && showGrants && (
              <Box>
                <Stack direction="row" alignItems="center" spacing={1} mb={1}>
                  <SectionLabel>Service Grants</SectionLabel>
                  {!editing && (
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<RefreshIcon />}
                      onClick={handleEnsureGrants}
                      sx={{ mb: '2px' }}
                    >
                      Update Grants
                    </Button>
                  )}
                </Stack>
                {grants ? (
                  <Stack spacing={1.5}>
                    <ReadOnlyField label="Decrypt Grant" value={grants.decrypt_grant || 'none'} />
                    <ReadOnlyField label="Encrypt Grant" value={grants.encrypt_grant || 'none'} />
                  </Stack>
                ) : (
                  <Typography color="text.secondary" variant="body2">No grants information available.</Typography>
                )}
              </Box>
            )}

            {/* Read-only audit metadata */}
            {!isNew && (
              <>
                <Divider />
                <Stack direction="row" flexWrap="wrap" gap={2}>
                  <ReadOnlyField label="Revision" value={service?.revision?.toString()} sx={{ flex: '0 1 100px' }} />
                  <ReadOnlyField
                    label="Modified"
                    value={service?.modified_date ? new Date(service.modified_date).toLocaleString() : '—'}
                    sx={{ flex: '1 1 200px' }}
                  />
                  <ReadOnlyField
                    label="Modified By"
                    value={service?.modified_by}
                    sx={{ flex: '1 1 180px' }}
                  />
                </Stack>
              </>
            )}

          </Stack>
        </CardContent>

        <CardActions sx={{ px: 3, pb: 3, pt: 0, gap: 1 }}>
          {!editing ? (
            canEdit ? (
              <Button
                variant="contained"
                onClick={() => { setSaveError(null); setConflicts(null); setEditing(true); }}
                sx={{ bgcolor: '#6bdfab', color: '#424554', '&:hover': { bgcolor: '#229B65', color: '#F4F5F5' } }}
              >
                Edit
              </Button>
            ) : (
              <Tooltip title="You do not have edit permission for this service.">
                <span>
                  <Button variant="outlined" disabled>Edit</Button>
                </span>
              </Tooltip>
            )
          ) : (
            <>
              <Button
                variant="contained"
                onClick={handleSave}
                disabled={saving}
                sx={{ bgcolor: '#6bdfab', color: '#424554', '&:hover': { bgcolor: '#229B65', color: '#F4F5F5' } }}
              >
                {saving ? <CircularProgress size={18} /> : 'Save'}
              </Button>
              <Button variant="outlined" onClick={handleCancel} disabled={saving}>
                Cancel
              </Button>
            </>
          )}
        </CardActions>
      </Card>
    </Box>
  );
}
