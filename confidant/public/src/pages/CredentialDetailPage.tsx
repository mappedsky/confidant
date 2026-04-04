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
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import LockIcon from '@mui/icons-material/Lock';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import HistoryIcon from '@mui/icons-material/History';
import RestoreIcon from '@mui/icons-material/Restore';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import KeyValueTable, { KeyValueRow } from '../components/KeyValueTable';
import { api } from '../api';
import { useAppContext } from '../contexts/AppContext';
import {
  CredentialDetail,
  CredentialServicesResponse,
  ConflictMap,
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

type CredentialDetailParams = { id?: string; version?: string };

export default function CredentialDetailPage() {
  const { id, version } = useParams<CredentialDetailParams>();
  const navigate = useNavigate();
  const { clientConfig } = useAppContext();
  const isNew = !id;
  const versionNumber = version ? Number(version) : null;
  const isVersionView = versionNumber !== null && !Number.isNaN(versionNumber);

  const permissions = clientConfig?.generated?.permissions;
  const definedTags = clientConfig?.generated?.defined_tags ?? [];

  const [credential, setCredential] = useState<CredentialDetail | null>(null);
  const [credentialServices, setCredentialServices] = useState<
    CredentialServicesResponse['services']
  >([]);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(isNew);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [conflicts, setConflicts] = useState<ConflictMap | null>(null);
  const [showValues, setShowValues] = useState(false);
  const [decrypted, setDecrypted] = useState(false);
  const [latestRevision, setLatestRevision] = useState<number | null>(null);
  const [canRestore, setCanRestore] = useState(false);
  const [restoring, setRestoring] = useState(false);

  const [formName, setFormName] = useState('');
  const [formEnabled, setFormEnabled] = useState(true);
  const [formPairs, setFormPairs] = useState<KeyValueRow[]>([{ key: '', value: '' }]);
  const [formMetadata, setFormMetadata] = useState<KeyValueRow[]>([]);
  const [formTags, setFormTags] = useState<string[]>([]);
  const [formDocumentation, setFormDocumentation] = useState('');

  const populateForm = useCallback((cred: CredentialDetail) => {
    setFormName(cred.name ?? '');
    setFormEnabled(cred.enabled ?? true);
    const pairs = Object.entries(cred.credential_pairs ?? {}).map(([key, value]) => ({
      key,
      value,
    }));
    if (pairs.length) {
      setFormPairs(pairs);
    } else if ((cred.credential_keys ?? []).length) {
      setFormPairs(cred.credential_keys.map((key) => ({ key, value: '' })));
    } else {
      setFormPairs([{ key: '', value: '' }]);
    }
    setFormMetadata(
      Object.entries(cred.metadata ?? {}).map(([key, value]) => ({ key, value })),
    );
    setFormTags(cred.tags ?? []);
    setFormDocumentation(cred.documentation ?? '');
  }, []);

  useEffect(() => {
    if (isNew) {
      setLoading(false);
      return;
    }

    setShowValues(false);
    setDecrypted(isVersionView);
    setLatestRevision(null);
    setCanRestore(false);
    setLoading(true);
    setError(null);

    if (isVersionView && id && versionNumber !== null) {
      Promise.all([api.getCredentialVersion(id, versionNumber), api.getCredential(id, true)])
        .then(([cred, current]) => {
          setCredential(cred);
          populateForm(cred);
          setCredentialServices([]);
          setLatestRevision(current.revision);
          setCanRestore(current.permissions?.update ?? false);
        })
        .catch((err: Error) => setError(err.message))
        .finally(() => setLoading(false));
      return;
    }

    Promise.all([api.getCredential(id, true), api.getCredentialServices(id)])
      .then(([cred, svcData]) => {
        setCredential(cred);
        populateForm(cred);
        setCredentialServices(svcData.services ?? []);
        setLatestRevision(cred.revision);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id, isNew, isVersionView, populateForm, versionNumber]);

  const handleToggleShow = async () => {
    if (showValues) {
      setShowValues(false);
      return;
    }
    if (isVersionView) {
      setShowValues(true);
      return;
    }
    if (!decrypted && id) {
      try {
        const full = await api.getCredential(id, false);
        setCredential(full);
        populateForm(full);
        setDecrypted(true);
      } catch (err) {
        setError((err as Error).message);
        return;
      }
    }
    setShowValues(true);
  };

  const handleEdit = async () => {
    if (isVersionView) {
      return;
    }
    if (!decrypted && id) {
      try {
        const full = await api.getCredential(id, false);
        setCredential(full);
        populateForm(full);
        setDecrypted(true);
      } catch (err) {
        setError((err as Error).message);
        return;
      }
    }
    setSaveError(null);
    setConflicts(null);
    setEditing(true);
  };

  const handleRestoreVersion = async () => {
    if (!id || versionNumber === null) {
      return;
    }

    setSaveError(null);
    setRestoring(true);
    try {
      const restored = await api.restoreCredentialVersion(id, versionNumber);
      navigate(`/credentials/${restored.id}`);
    } catch (err) {
      setSaveError((err as Error).message);
    } finally {
      setRestoring(false);
    }
  };

  const handleCancel = () => {
    if (isNew) {
      navigate('/credentials');
      return;
    }
    if (credential) {
      populateForm(credential);
    }
    setSaveError(null);
    setConflicts(null);
    setEditing(false);
  };

  const handleGenerate = async (idx: number) => {
    try {
      const { value } = await api.generateValue();
      setFormPairs((prev) => prev.map((r, i) => (i === idx ? { ...r, value } : r)));
    } catch (err) {
      setSaveError((err as Error).message);
    }
  };

  const handleSave = async () => {
    setSaveError(null);
    setConflicts(null);

    const pairKeys = formPairs.map((p) => p.key);
    if (new Set(pairKeys).size !== pairKeys.length) {
      setSaveError('Credential pair keys must be unique.');
      return;
    }
    const metaKeys = formMetadata.map((m) => m.key);
    if (new Set(metaKeys).size !== metaKeys.length) {
      setSaveError('Metadata keys must be unique.');
      return;
    }

    const payload = {
      name: formName,
      enabled: formEnabled,
      documentation: formDocumentation,
      credential_pairs: Object.fromEntries(
        formPairs
          .filter((p) => p.key)
          .map((p) => [p.key, p.value]),
      ),
      metadata: Object.fromEntries(
        formMetadata
          .filter((m) => m.key)
          .map((m) => [m.key, m.value]),
      ),
      tags: [...new Set(formTags.filter(Boolean))],
    };

    setSaving(true);
    try {
      let saved: CredentialDetail;
      if (isNew) {
        saved = await api.createCredential(payload);
        if (!saved.id) {
          throw new Error('Credential was created, but no credential ID was returned.');
        }
        window.location.replace(`/credentials/${saved.id}`);
        return;
      } else if (id) {
        saved = await api.updateCredential(id, payload);
        setCredential(saved);
        populateForm(saved);
        setEditing(false);
      } else {
        throw new Error('Missing credential ID');
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
          onClick={() => navigate('/credentials')}
          sx={{ mb: 2 }}
        >
          Back to Credentials
        </Button>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  const canEdit = !isVersionView && (isNew ? permissions?.credentials?.create : credential?.permissions?.update);
  const daysTillRotation =
    credential?.next_rotation_date
      ? Math.round(
          (new Date(credential.next_rotation_date).getTime() - Date.now()) / 86400000,
        )
      : null;
  const restoreDisabled = versionNumber === latestRevision || !canRestore || restoring;
  const restoreTooltip = versionNumber === latestRevision
    ? 'This is already the current version.'
    : !canRestore
      ? 'You do not have permission to restore this credential.'
      : '';

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <Box>
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate(isVersionView ? `/credentials/${id}/history` : '/credentials')}
            sx={{ mb: 2 }}
          >
            {isVersionView ? 'Back to History' : 'Back to Credentials'}
          </Button>

          <Typography variant="h5" fontWeight={600}>
            {isNew ? 'New Credential' : credential?.name || id}
          </Typography>
        </Box>

        {!isNew && (
          <Stack direction="row" spacing={1} alignItems="flex-start" flexWrap="wrap">
            {isVersionView ? (
              <>
                <Button variant="outlined" onClick={() => navigate(`/credentials/${id}`)}>
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
                onClick={() => navigate(`/credentials/${id}/history`)}
              >
                History
              </Button>
            )}
          </Stack>
        )}
      </Box>

      {isVersionView && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Viewing credential version v{versionNumber}
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
                      Credential:{' '}
                      <Link component={RouterLink} to={`/credentials/${cid}`}>
                        {cid}
                      </Link>
                    </Typography>
                  ))}
                  {info.services?.map((sid) => (
                    <Typography key={sid} variant="body2" ml={2}>
                      Service:{' '}
                      <Link component={RouterLink} to={`/services/${sid}`}>
                        {sid}
                      </Link>
                    </Typography>
                  ))}
                </Box>
              ))}
              <Typography variant="body2" mt={1}>
                Please ensure credential pair keys are unique for mapped services, then try again.
              </Typography>
            </Box>
          )}
        </Alert>
      )}

      <Card elevation={1}>
        <CardContent sx={{ p: 3 }}>
          <Stack spacing={3}>
            {editing ? (
              <TextField
                label="Credential Name"
                size="small"
                fullWidth
                required
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
              />
            ) : (
              <ReadOnlyField label="Credential Name" value={credential?.name} />
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
                    label={credential?.enabled ? 'Enabled' : 'Disabled'}
                    size="small"
                    color={credential?.enabled ? 'success' : 'default'}
                    variant="outlined"
                  />
                </Box>
              )
            )}

            <Box>
              <Stack direction="row" alignItems="center" spacing={0.5} mb={1}>
                <SectionLabel>Credential Pairs</SectionLabel>
                <LockIcon sx={{ fontSize: '0.875rem', color: 'text.secondary', mb: '2px' }} />
                {!editing && (
                  <Tooltip
                    title={
                      showValues
                        ? 'Hide values'
                        : 'Show decrypted values (may affect rotation schedule)'
                    }
                  >
                    <IconButton size="small" onClick={handleToggleShow} sx={{ ml: 0.5 }}>
                      {showValues ? (
                        <VisibilityOffIcon fontSize="small" />
                      ) : (
                        <VisibilityIcon fontSize="small" />
                      )}
                    </IconButton>
                  </Tooltip>
                )}
              </Stack>
              <KeyValueTable
                rows={formPairs}
                onChange={setFormPairs}
                showValues={showValues || editing}
                editable={editing}
                onGenerate={handleGenerate}
                isCredentialPairs
              />
            </Box>

            <Box>
              <SectionLabel>Credential Metadata</SectionLabel>
              <KeyValueTable
                rows={formMetadata}
                onChange={setFormMetadata}
                showValues
                editable={editing}
              />
            </Box>

            {(editing || formTags.length > 0 || definedTags.length > 0) && (
              <Box>
                <SectionLabel>Tags</SectionLabel>
                {editing ? (
                  <Stack spacing={1}>
                    {formTags.map((tag, idx) => (
                      <Stack key={idx} direction="row" alignItems="center" spacing={1}>
                        <FormControl size="small" sx={{ minWidth: 200 }}>
                          <InputLabel>Tag</InputLabel>
                          <Select
                            label="Tag"
                            value={tag}
                            onChange={(event) =>
                              setFormTags((prev) =>
                                prev.map((t, i) => (i === idx ? (event.target.value as string) : t)),
                              )
                            }
                          >
                            {definedTags.map((value) => (
                              <MenuItem key={value} value={value}>
                                {value}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() =>
                            setFormTags((prev) => prev.filter((_, i) => i !== idx))
                          }
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Stack>
                    ))}
                    {definedTags.length > 0 && (
                      <Box>
                        <Button
                          size="small"
                          startIcon={<AddIcon />}
                          onClick={() => setFormTags((prev) => [...prev, ''])}
                        >
                          Add Tag
                        </Button>
                      </Box>
                    )}
                  </Stack>
                ) : (
                  <Stack direction="row" flexWrap="wrap" gap={0.5}>
                    {formTags.length ? (
                      formTags.map((tag) => <Chip key={tag} label={tag} size="small" />)
                    ) : (
                      <Typography color="text.secondary" variant="body2">
                        None
                      </Typography>
                    )}
                  </Stack>
                )}
              </Box>
            )}

            {!isNew && credential?.next_rotation_date && (
              <ReadOnlyField
                label="Next Rotation Date"
                value={`${credential.next_rotation_date}${
                  daysTillRotation !== null ? ` (${daysTillRotation} days)` : ''
                }`}
              />
            )}

            {editing ? (
              <TextField
                label="Rotation Documentation"
                size="small"
                fullWidth
                multiline
                minRows={3}
                value={formDocumentation}
                onChange={(e) => setFormDocumentation(e.target.value)}
                placeholder="Add documentation for how to rotate this credential. Add a link to a runbook if relevant."
              />
            ) : formDocumentation ? (
              <ReadOnlyField label="Rotation Documentation" value={formDocumentation} />
            ) : null}

            {!isNew && (
              <>
                <Divider />
                <Stack direction="row" flexWrap="wrap" gap={2}>
                  <ReadOnlyField
                    label="Credential ID"
                    value={credential?.id}
                    sx={{ flex: '2 1 220px' }}
                    valueSx={{
                      fontFamily: 'monospace',
                      fontSize: '0.8rem',
                      wordBreak: 'break-all',
                    }}
                  />
                  <ReadOnlyField
                    label="Revision"
                    value={credential?.revision?.toString() ?? '—'}
                    sx={{ flex: '0 1 100px' }}
                  />
                  <ReadOnlyField
                    label="Modified"
                    value={
                      credential?.modified_date
                        ? new Date(credential.modified_date).toLocaleString()
                        : '—'
                    }
                    sx={{ flex: '1 1 200px' }}
                  />
                  <ReadOnlyField
                    label="Modified By"
                    value={credential?.modified_by}
                    sx={{ flex: '1 1 180px' }}
                  />
                </Stack>

                {!isVersionView && credentialServices.length > 0 && (
                  <Box>
                    <SectionLabel>Services Using This Credential</SectionLabel>
                    <Stack spacing={0.5}>
                      {credentialServices.map((svc) => (
                        <Box key={svc.id}>
                          <Link component={RouterLink} to={`/services/${svc.id}`}>
                            {svc.id}
                          </Link>
                          {!svc.enabled && (
                            <Typography component="span" color="text.secondary" ml={1}>
                              (disabled)
                            </Typography>
                          )}
                        </Box>
                      ))}
                    </Stack>
                  </Box>
                )}
              </>
            )}

            <Typography variant="caption" color="text.secondary">
              Note: Only fields marked with{' '}
              <LockIcon sx={{ fontSize: 12, verticalAlign: 'middle' }} /> are encrypted at-rest.
            </Typography>
          </Stack>
        </CardContent>

        <CardActions sx={{ px: 3, pb: 3, pt: 0, gap: 1 }}>
          {!editing ? (
            canEdit ? (
              <Button
                variant="contained"
                onClick={handleEdit}
                sx={{
                  bgcolor: '#6bdfab',
                  color: '#424554',
                  '&:hover': { bgcolor: '#229B65', color: '#F4F5F5' },
                }}
              >
                Edit
              </Button>
            ) : (
              <Tooltip title="You do not have edit permission for this credential.">
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
