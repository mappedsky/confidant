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
  Link,
  Chip,
  Stack,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableContainer,
  TableRow,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import HistoryIcon from '@mui/icons-material/History';
import RestoreIcon from '@mui/icons-material/Restore';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import { api } from '../api';
import { useAppContext } from '../contexts/AppContext';
import {
  ConflictMap,
  CredentialSummary,
  ServiceDetail,
} from '../types/api';

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
      {children}
    </Typography>
  );
}

interface ReadOnlyFieldProps {
  label: string;
  value?: string | null;
  sx?: React.ComponentProps<typeof Box>['sx'];
  valueSx?: React.ComponentProps<typeof Typography>['sx'];
}

function ReadOnlyField({ label, value, sx: sxProp, valueSx }: ReadOnlyFieldProps) {
  return (
    <Box sx={sxProp}>
      <Typography variant="caption" color="text.secondary" display="block" mb={0.25}>
        {label}
      </Typography>
      <Typography variant="body2" sx={valueSx}>{value ?? '—'}</Typography>
    </Box>
  );
}

function credentialDisplayLabel(credential: Pick<CredentialSummary, 'name' | 'id'>) {
  return `${credential.name} (${credential.id})`;
}

interface ServiceFormCredential {
  id: string;
  name: string;
  revision?: number;
  enabled?: boolean;
  isNew?: boolean;
}

type ServiceDetailParams = { id?: string; version?: string };

export default function ServiceDetailPage() {
  const { id, version } = useParams<ServiceDetailParams>();
  const navigate = useNavigate();
  const { clientConfig } = useAppContext();
  const isNew = !id;
  const versionNumber = version ? Number(version) : null;
  const isVersionView = versionNumber !== null && !Number.isNaN(versionNumber);

  const permissions = clientConfig?.generated?.permissions;

  const [service, setService] = useState<ServiceDetail | null>(null);
  const [allCredentials, setAllCredentials] = useState<CredentialSummary[]>([]);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(isNew);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [conflicts, setConflicts] = useState<ConflictMap | null>(null);
  const [latestRevision, setLatestRevision] = useState<number | null>(null);
  const [canRestore, setCanRestore] = useState(false);
  const [restoring, setRestoring] = useState(false);

  const [formId, setFormId] = useState('');
  const [formEnabled, setFormEnabled] = useState(true);
  const [formCredentials, setFormCredentials] = useState<ServiceFormCredential[]>([]);

  const populateForm = useCallback((svc: ServiceDetail) => {
    setFormId(svc.id ?? '');
    setFormEnabled(svc.enabled ?? true);
    setFormCredentials(
      (svc.credentials ?? []).map((credential) => ({
        id: credential,
        name: credential,
        isNew: false,
      })),
    );
  }, []);

  useEffect(() => {
    api.getCredentials()
      .then((data) => setAllCredentials(data.credentials ?? []))
      .catch(() => {});

    if (isNew) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    setLatestRevision(null);
    setCanRestore(false);

    if (isVersionView && id && versionNumber !== null) {
      Promise.all([api.getServiceVersion(id, versionNumber), api.getService(id)])
        .then(([svc, current]) => {
          setService(svc);
          populateForm(svc);
          setLatestRevision(current.revision);
          setCanRestore(current.permissions?.update ?? false);
        })
        .catch((err: Error) => setError(err.message))
        .finally(() => setLoading(false));
      return;
    }

    api.getService(id)
      .then((svc) => {
        setService(svc);
        populateForm(svc);
        setLatestRevision(svc.revision);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id, isNew, isVersionView, populateForm, versionNumber]);

  useEffect(() => {
    if (allCredentials.length === 0) {
      return;
    }

    setFormCredentials((previous) => previous.map((credential) => {
      const match = allCredentials.find((item) => item.id === credential.id);
      if (!match) {
        return credential;
      }
      return {
        ...credential,
        name: match.name,
        revision: credential.revision ?? match.revision,
        enabled: credential.enabled ?? match.enabled,
      };
    }));
  }, [allCredentials]);

  const handleAddCredential = () => {
    setFormCredentials((prev) => [...prev, { id: '', name: '', isNew: true }]);
  };

  const handleRemoveCredential = (idx: number) => {
    setFormCredentials((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleCredentialChange = (idx: number, credId: string) => {
    const cred = allCredentials.find((c) => c.id === credId);
    setFormCredentials((prev) =>
      prev.map((c, i) =>
        i === idx
          ? {
              id: credId,
              name: cred?.name ?? credId,
              revision: cred?.revision,
              enabled: cred?.enabled,
            }
          : c,
      ),
    );
  };

  const handleSave = async () => {
    setSaveError(null);
    setConflicts(null);

    const credIds = formCredentials.map((c) => c.id).filter(Boolean);
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
        const error = err as { status?: number };
        if (error.status !== 404) {
          setSaveError('Failed to check if service already exists.');
          return;
        }
      }
    }

    const payload = {
      id: formId,
      enabled: formEnabled,
      credentials: credIds,
    };

    setSaving(true);
    try {
      let saved: ServiceDetail;
      if (isNew) {
        saved = await api.createService(formId, payload);
        if (!saved.id) {
          throw new Error('Service was created, but no service ID was returned.');
        }
        window.location.replace(`/services/${saved.id}`);
        return;
      } else if (id) {
        saved = await api.updateService(id, payload);
        setService(saved);
        populateForm(saved);
        setEditing(false);
      } else {
        throw new Error('Missing service ID');
      }
    } catch (err: unknown) {
      const error = err as { message: string; data?: { conflicts?: ConflictMap } };
      setSaveError(error.message);
      if (error.data?.conflicts) {
        setConflicts(error.data.conflicts);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (isNew) {
      navigate('/services');
      return;
    }
    if (service) {
      populateForm(service);
    }
    setSaveError(null);
    setConflicts(null);
    setEditing(false);
  };

  const handleRestoreVersion = async () => {
    if (!id || versionNumber === null) {
      return;
    }

    setSaveError(null);
    setRestoring(true);
    try {
      const restored = await api.restoreServiceVersion(id, versionNumber);
      navigate(`/services/${restored.id}`);
    } catch (err) {
      setSaveError((err as Error).message);
    } finally {
      setRestoring(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', pt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate('/services')}
          sx={{ mb: 2 }}
        >
          Back to Services
        </Button>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  const canEdit = !isVersionView && (isNew
    ? permissions?.services?.create
    : service?.permissions?.update);
  const restoreDisabled = versionNumber === latestRevision || !canRestore || restoring;
  const restoreTooltip = versionNumber === latestRevision
    ? 'This is already the current version.'
    : !canRestore
      ? 'You do not have permission to restore this service.'
      : '';

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <Box>
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate(isVersionView ? `/services/${id}/history` : '/services')}
            sx={{ mb: 2 }}
          >
            {isVersionView ? 'Back to History' : 'Back to Services'}
          </Button>

          <Typography variant="h5" fontWeight={600}>
            {isNew ? 'New Service' : service?.id || id}
          </Typography>
        </Box>

        {!isNew && (
          <Stack direction="row" spacing={1} alignItems="flex-start" flexWrap="wrap">
            {isVersionView ? (
              <>
                <Button variant="outlined" onClick={() => navigate(`/services/${id}`)}>
                  View Current
                </Button>
                <Tooltip title={restoreTooltip}>
                  <span>
                    <Button
                      variant="outlined"
                      startIcon={<RestoreIcon />}
                      onClick={handleRestoreVersion}
                      disabled={restoreDisabled}
                    >
                      {restoring ? 'Restoring…' : 'Restore'}
                    </Button>
                  </span>
                </Tooltip>
              </>
            ) : (
              <Button
                variant="outlined"
                startIcon={<HistoryIcon />}
                onClick={() => navigate(`/services/${id}/history`)}
              >
                History
              </Button>
            )}
          </Stack>
        )}
      </Box>

      {isVersionView && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Viewing service version v{versionNumber}
          {latestRevision === versionNumber ? ' (current)' : ''}
        </Alert>
      )}
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
                      Credential:
                      <Link component={RouterLink} to={`/credentials/${cid}`}>
                        {cid}
                      </Link>
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
            {isNew ? (
              <TextField
                label="Service ID"
                size="small"
                required
                value={formId}
                onChange={(event) => setFormId(event.target.value)}
                placeholder="Enter a service ID"
              />
            ) : (
              <ReadOnlyField label="Service ID" value={service?.id} valueSx={{ fontFamily: 'monospace' }} />
            )}

            {!isNew && (
              editing ? (
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={formEnabled}
                      onChange={(e) => setFormEnabled(e.target.checked)}
                    />
                  }
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

            <Box>
              <SectionLabel>Credentials</SectionLabel>
              <TableContainer
                component={Paper}
                variant="outlined"
                sx={{ borderColor: 'divider', borderRadius: 1, overflowX: 'auto' }}
              >
                <Table size="small" sx={{ minWidth: 640 }}>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600, width: editing ? '48%' : '40%' }}>Credential</TableCell>
                      <TableCell sx={{ fontWeight: 600, width: '32%' }}>Credential ID</TableCell>
                      {!editing && <TableCell sx={{ fontWeight: 600, width: '14%' }}>Revision</TableCell>}
                      {editing && <TableCell sx={{ fontWeight: 600, width: 60 }} />}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {formCredentials.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={editing ? 4 : 3} sx={{ color: 'text.secondary', fontStyle: 'italic' }}>
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
                                  onChange={(event: SelectChangeEvent<string>) =>
                                    handleCredentialChange(idx, event.target.value)
                                  }
                                  displayEmpty
                                >
                                  <MenuItem value="">
                                    <em>Select credential</em>
                                  </MenuItem>
                                  {allCredentials
                                    .filter((c) => c.enabled || c.id === cred.id)
                                    .map((c) => (
                                      <MenuItem key={c.id} value={c.id}>
                                        {credentialDisplayLabel(c)}
                                      </MenuItem>
                                    ))}
                                </Select>
                              </FormControl>
                            ) : (
                              <Box>
                                <Link component={RouterLink} to={`/credentials/${cred.id}`}>
                                  {cred.name || cred.id}
                                </Link>
                                {!cred.enabled && (
                                  <Typography component="span" color="text.secondary" ml={1}>
                                    (disabled)
                                  </Typography>
                                )}
                              </Box>
                            )}
                          </TableCell>
                          <TableCell>
                            <Typography color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                              {cred.id || '—'}
                            </Typography>
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
              </TableContainer>
              {editing && (
                <Button
                  size="small"
                  startIcon={<AddIcon />}
                  onClick={handleAddCredential}
                  sx={{ mt: 1 }}
                >
                  Add credential
                </Button>
              )}
            </Box>

            {!isNew && (
              <>
                <Divider />
                <Stack direction="row" flexWrap="wrap" gap={2}>
                  <ReadOnlyField
                    label="Revision"
                    value={service?.revision?.toString() ?? '—'}
                    sx={{ flex: '0 1 100px' }}
                  />
                  <ReadOnlyField
                    label="Modified"
                    value={
                      service?.modified_date
                        ? new Date(service.modified_date).toLocaleString()
                        : '—'
                    }
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
                onClick={() => {
                  setSaveError(null);
                  setConflicts(null);
                  setEditing(true);
                }}
                sx={{
                  bgcolor: '#6bdfab',
                  color: '#424554',
                  '&:hover': { bgcolor: '#229B65', color: '#F4F5F5' },
                }}
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
                sx={{
                  bgcolor: '#6bdfab',
                  color: '#424554',
                  '&:hover': { bgcolor: '#229B65', color: '#F4F5F5' },
                }}
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
