import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Button,
  TextField,
  Card,
  CardContent,
  CardActions,
  CircularProgress,
  Alert,
  Divider,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Checkbox,
  IconButton,
  Tooltip,
  FormControlLabel,
  FormGroup,
  Link,
  Stack,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import LockIcon from '@mui/icons-material/Lock';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import HistoryIcon from '@mui/icons-material/History';
import RestoreIcon from '@mui/icons-material/Restore';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import KeyValueTable, { KeyValueRow } from '../components/KeyValueTable';
import CenteredSpinner from '../components/CenteredSpinner';
import { api } from '../api';
import { useAppContext } from '../contexts/AppContext';
import {
  CreateSecretPayload,
  SecretDetail,
  SecretGroupsResponse,
} from '../types/api';
import {
  secretDetailPath,
  secretHistoryPath,
  secretVersionPath,
  validateSecretId,
} from '../utils/resourceIds';
import { parseSecretRouteRemainder } from '../utils/secretRouteParams';

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

type SecretDetailParams = { '*': string };

export default function SecretDetailPage() {
  const params = useParams<SecretDetailParams>();
  const { id, version } = parseSecretRouteRemainder(params['*']);
  const navigate = useNavigate();
  const { clientConfig } = useAppContext();
  const isNew = !id;
  const versionNumber = version;
  const isVersionView = versionNumber !== null && !Number.isNaN(versionNumber);
  const permissions = clientConfig?.generated?.permissions;
  const maintenanceMode = clientConfig?.generated?.maintenance_mode ?? false;

  const [secret, setSecret] = useState<SecretDetail | null>(null);
  const [secretGroups, setSecretGroups] = useState<
    SecretGroupsResponse['groups']
  >([]);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(isNew);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [showValues, setShowValues] = useState(false);
  const [decrypted, setDecrypted] = useState(false);
  const [latestRevision, setLatestRevision] = useState<number | null>(null);
  const [canRestore, setCanRestore] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [restoreDialogOpen, setRestoreDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [versionRevisions, setVersionRevisions] = useState<number[]>([]);
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [generateTargetIdx, setGenerateTargetIdx] = useState<number | null>(null);
  const [generateLength, setGenerateLength] = useState('32');
  const [generateComplexity, setGenerateComplexity] = useState({
    lowercase: true,
    uppercase: true,
    digits: true,
    symbols: true,
  });
  const [generateError, setGenerateError] = useState<string | null>(null);

  const [formName, setFormName] = useState('');
  const [formId, setFormId] = useState('');
  const [formPairs, setFormPairs] = useState<KeyValueRow[]>([{ key: '', value: '' }]);
  const [formMetadata, setFormMetadata] = useState<KeyValueRow[]>([]);
  const [formDocumentation, setFormDocumentation] = useState('');

  const populateForm = useCallback((cred: SecretDetail) => {
    setFormName(cred.name ?? '');
    setFormId(cred.id ?? '');
    const pairs = Object.entries(cred.secret_pairs ?? {}).map(([key, value]) => ({
      key,
      value,
    }));
    if (pairs.length) {
      setFormPairs(pairs);
    } else if ((cred.secret_keys ?? []).length) {
      setFormPairs(cred.secret_keys.map((key) => ({ key, value: '' })));
    } else {
      setFormPairs([{ key: '', value: '' }]);
    }
    setFormMetadata(
      Object.entries(cred.metadata ?? {}).map(([key, value]) => ({ key, value })),
    );
    setFormDocumentation(cred.documentation ?? '');
  }, []);

  useEffect(() => {
    if (isNew) {
      setLoading(false);
      return;
    }

    setShowValues(false);
    setDecrypted(false);
    setLatestRevision(null);
    setCanRestore(false);
    setVersionRevisions([]);
    setLoading(true);
    setError(null);

    if (isVersionView && id && versionNumber !== null) {
      Promise.all([
        api.getSecretVersion(id, versionNumber),
        api.getSecret(id),
        api.getSecretVersions(id),
      ])
        .then(([cred, current, history]) => {
          setSecret(cred);
          populateForm(cred);
          setSecretGroups([]);
          setLatestRevision(current.revision);
          setCanRestore(
            current.permissions?.revert ?? current.permissions?.update ?? false,
          );
          setVersionRevisions(
            [...(history.versions ?? [])]
              .map((item) => item.revision)
              .sort((a, b) => a - b),
          );
        })
        .catch((err: Error) => setError(err.message))
        .finally(() => setLoading(false));
      return;
    }

    Promise.all([api.getSecret(id), api.getSecretGroups(id)])
      .then(([cred, svcData]) => {
        setSecret(cred);
        populateForm(cred);
        setSecretGroups(svcData.groups ?? []);
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
    if (!decrypted && id) {
      try {
        const full = isVersionView && versionNumber !== null
          ? await api.decryptSecretVersion(id, versionNumber)
          : await api.decryptSecret(id);
        setSecret(full);
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
        const full = await api.decryptSecret(id);
        setSecret(full);
        populateForm(full);
        setDecrypted(true);
      } catch (err) {
        setError((err as Error).message);
        return;
      }
    }
    setSaveError(null);
    setEditing(true);
  };

  const handleRestoreVersion = async () => {
    if (!id || versionNumber === null) {
      return;
    }

    setSaveError(null);
    setRestoring(true);
    try {
      const restored = await api.restoreSecretVersion(id, versionNumber);
      navigate(secretDetailPath(restored.id));
    } catch (err) {
      setSaveError((err as Error).message);
    } finally {
      setRestoring(false);
    }
  };

  const handleCancel = () => {
    if (isNew) {
      navigate('/secrets');
      return;
    }
    if (secret) {
      populateForm(secret);
    }
    setSaveError(null);
    setEditing(false);
  };

  const handleDelete = async () => {
    if (!id) {
      return;
    }

    setSaveError(null);
    setDeleting(true);
    try {
      await api.deleteSecret(id);
      navigate('/secrets');
    } catch (err) {
      setSaveError((err as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  const handleGenerate = async (idx: number) => {
    setGenerateTargetIdx(idx);
    setGenerateLength('32');
    setGenerateComplexity({
      lowercase: true,
      uppercase: true,
      digits: true,
      symbols: true,
    });
    setGenerateError(null);
    setGenerateDialogOpen(true);
  };

  const handleRunGenerate = async () => {
    if (generateTargetIdx === null) {
      return;
    }

    const length = Number(generateLength);
    if (!Number.isInteger(length) || length < 1) {
      setGenerateError('Length must be a positive integer.');
      return;
    }

    const complexity: string[] = Object.entries(generateComplexity)
      .filter(([, enabled]) => enabled)
      .map(([name]) => name);
    if (!complexity.length) {
      setGenerateError('Select at least one character class.');
      return;
    }

    try {
      const { value } = await api.generateValue({ length, complexity });
      setFormPairs((prev) => prev.map((r, i) => (i === generateTargetIdx ? { ...r, value } : r)));
      setGenerateError(null);
      setGenerateDialogOpen(false);
    } catch (err) {
      setGenerateError((err as Error).message);
    }
  };

  const handleSave = async () => {
    setSaveError(null);

    const pairKeys = formPairs.filter((p) => p.key).map((p) => p.key);
    const normalizedPairKeys = pairKeys.map((key) => key.toLocaleLowerCase());
    if (new Set(normalizedPairKeys).size !== normalizedPairKeys.length) {
      setSaveError('Secret pair keys must be unique ignoring case.');
      return;
    }
    const metaKeys = formMetadata.map((m) => m.key);
    if (new Set(metaKeys).size !== metaKeys.length) {
      setSaveError('Metadata keys must be unique.');
      return;
    }
    if (isNew) {
      const idError = validateSecretId(formId);
      if (idError) {
        setSaveError(idError);
        return;
      }
    }

    const payload: CreateSecretPayload = {
      id: formId,
      name: formName,
      documentation: formDocumentation,
      secret_pairs: Object.fromEntries(
        formPairs
          .filter((p) => p.key)
          .map((p) => [p.key, p.value]),
      ),
      metadata: Object.fromEntries(
        formMetadata
          .filter((m) => m.key)
          .map((m) => [m.key, m.value]),
      ),
    };

    setSaving(true);
    try {
      let saved: SecretDetail;
      if (isNew) {
        saved = await api.createSecret(payload);
        if (!saved.id) {
          throw new Error('Secret was created, but no secret ID was returned.');
        }
        window.location.replace(secretDetailPath(saved.id));
        return;
      } else if (id) {
        saved = await api.updateSecret(id, payload);
        setSecret(saved);
        populateForm(saved);
        setEditing(false);
      } else {
        throw new Error('Missing secret ID');
      }
    } catch (err: unknown) {
      setSaveError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <CenteredSpinner minHeight={320} />;
  }

  if (error) {
    return (
      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate('/secrets')}
          sx={{ mb: 2 }}
        >
          Back to Secrets
        </Button>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  const canEdit = !maintenanceMode
    && !isVersionView
    && (isNew ? permissions?.secrets?.create : secret?.permissions?.update);
  const canDelete = !maintenanceMode && !isVersionView && !isNew && secret?.permissions?.delete;
  const canDecrypt = !isNew && !!secret?.permissions?.decrypt;
  const currentVersionIdx = versionNumber !== null
    ? versionRevisions.indexOf(versionNumber)
    : -1;
  const prevVersion = currentVersionIdx > 0 ? versionRevisions[currentVersionIdx - 1] : null;
  const nextVersion = currentVersionIdx !== -1 && currentVersionIdx < versionRevisions.length - 1
    ? versionRevisions[currentVersionIdx + 1]
    : null;
  const restoreDisabled = (
    maintenanceMode
    || versionNumber === latestRevision
    || !canRestore
    || restoring
  );
  const restoreTooltip = versionNumber === latestRevision
    ? 'This is already the current version.'
    : maintenanceMode
      ? 'Maintenance mode is enabled.'
    : !canRestore
      ? 'You do not have permission to restore this secret.'
      : '';

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <Box>
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate(
              isVersionView ? secretHistoryPath(id!) : '/secrets',
            )}
            sx={{ mb: 2 }}
          >
            {isVersionView ? 'Back to History' : 'Back to Secrets'}
          </Button>

          <Typography variant="h5" fontWeight={600}>
            {isNew ? 'New Secret' : secret?.name || id}
          </Typography>
        </Box>

        {!isNew && (
          <Stack direction="row" spacing={1} alignItems="flex-start" flexWrap="wrap">
            {isVersionView ? (
              <>
                <Tooltip title={prevVersion === null ? 'No older version' : ''}>
                  <span>
                    <Button
                      variant="outlined"
                      startIcon={<NavigateBeforeIcon />}
                      disabled={prevVersion === null}
                      onClick={() => {
                        if (prevVersion !== null) {
                          navigate(secretVersionPath(id!, prevVersion));
                        }
                      }}
                    >
                      {prevVersion !== null ? `v${prevVersion}` : 'Older'}
                    </Button>
                  </span>
                </Tooltip>
                <Tooltip title={nextVersion === null ? 'No newer version' : ''}>
                  <span>
                    <Button
                      variant="outlined"
                      endIcon={<NavigateNextIcon />}
                      disabled={nextVersion === null}
                      onClick={() => {
                        if (nextVersion !== null) {
                          navigate(secretVersionPath(id!, nextVersion));
                        }
                      }}
                    >
                      {nextVersion !== null ? `v${nextVersion}` : 'Newer'}
                    </Button>
                  </span>
                </Tooltip>
                <Tooltip title={restoreTooltip}>
                  <span>
                    <Button
                      variant="contained"
                      startIcon={<RestoreIcon />}
                      sx={{
                        bgcolor: '#6bdfab',
                        color: '#424554',
                        '&:hover': { bgcolor: '#229B65', color: '#F4F5F5' },
                      }}
                      onClick={() => setRestoreDialogOpen(true)}
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
                onClick={() => navigate(secretHistoryPath(id!))}
              >
                History
              </Button>
            )}
          </Stack>
        )}
      </Box>

      {isVersionView && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Viewing secret version v{versionNumber}
          {latestRevision === versionNumber ? ' (current)' : ''}
        </Alert>
      )}

      <Dialog open={restoreDialogOpen} onClose={() => !restoring && setRestoreDialogOpen(false)}>
        <DialogTitle>Restore this version?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This will restore secret version v{versionNumber} as the current version.
            The current value will be replaced, and a new version will be created.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRestoreDialogOpen(false)} disabled={restoring}>
            Cancel
          </Button>
          <Button
            variant="contained"
            sx={{
              bgcolor: '#6bdfab',
              color: '#424554',
              '&:hover': { bgcolor: '#229B65', color: '#F4F5F5' },
            }}
            startIcon={restoring ? <CircularProgress size={16} color="inherit" /> : <RestoreIcon />}
            onClick={async () => {
              await handleRestoreVersion();
              setRestoreDialogOpen(false);
            }}
            disabled={restoreDisabled || restoring}
          >
            {restoring ? 'Restoring…' : 'Restore'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={deleteDialogOpen} onClose={() => !deleting && setDeleteDialogOpen(false)}>
        <DialogTitle>Archive and delete this secret?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This removes the secret from active use and archives its current
            record and version history with the same secret ID. The secret
            cannot be deleted while any group still references it.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={deleting}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            startIcon={deleting ? <CircularProgress size={16} color="inherit" /> : <DeleteIcon />}
            onClick={async () => {
              await handleDelete();
              setDeleteDialogOpen(false);
            }}
            disabled={deleting}
          >
            {deleting ? 'Deleting…' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>

        <Dialog
        open={generateDialogOpen}
        onClose={() => {
          setGenerateDialogOpen(false);
          setGenerateTargetIdx(null);
          setGenerateError(null);
        }}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Generate Random Value</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField
              label="Length"
              type="number"
              size="small"
              value={generateLength}
              onChange={(event) => setGenerateLength(event.target.value)}
              inputProps={{ min: 1, max: 1024, step: 1 }}
              helperText="Length must be between 1 and 1024."
            />
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Character classes
              </Typography>
              <FormGroup>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={generateComplexity.lowercase}
                      onChange={(event) =>
                        setGenerateComplexity((prev) => ({
                          ...prev,
                          lowercase: event.target.checked,
                        }))
                      }
                    />
                  }
                  label="Lowercase letters"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={generateComplexity.uppercase}
                      onChange={(event) =>
                        setGenerateComplexity((prev) => ({
                          ...prev,
                          uppercase: event.target.checked,
                        }))
                      }
                    />
                  }
                  label="Uppercase letters"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={generateComplexity.digits}
                      onChange={(event) =>
                        setGenerateComplexity((prev) => ({
                          ...prev,
                          digits: event.target.checked,
                        }))
                      }
                    />
                  }
                  label="Digits"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={generateComplexity.symbols}
                      onChange={(event) =>
                        setGenerateComplexity((prev) => ({
                          ...prev,
                          symbols: event.target.checked,
                        }))
                      }
                    />
                  }
                  label="Symbols"
                />
              </FormGroup>
            </Box>
            <Typography variant="caption" color="text.secondary">
              The generated value will include at least one character from each
              selected class.
            </Typography>
            {generateError && <Alert severity="error">{generateError}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setGenerateDialogOpen(false);
              setGenerateTargetIdx(null);
              setGenerateError(null);
            }}
          >
            Cancel
          </Button>
          <Button variant="contained" onClick={handleRunGenerate}>
            Generate
          </Button>
        </DialogActions>
      </Dialog>

      {saveError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {saveError}
        </Alert>
      )}

      <Card elevation={1}>
        <CardContent sx={{ p: 3 }}>
          <Stack spacing={3}>
            {editing && isNew ? (
              <TextField
                label="Secret ID"
                size="small"
                fullWidth
                required
                value={formId}
                onChange={(e) => setFormId(e.target.value)}
                helperText={
                  'Use letters, numbers, and /_+=.@-. Max 512 chars; no trailing /.'
                }
              />
            ) : null}

            {editing ? (
              <TextField
                label="Secret Name"
                size="small"
                fullWidth
                required
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
              />
            ) : (
              <ReadOnlyField label="Secret Name" value={secret?.name} />
            )}

            <Box>
              <Stack direction="row" alignItems="center" spacing={0.5} mb={1}>
                <SectionLabel>Secret Pairs</SectionLabel>
                <LockIcon sx={{ fontSize: '0.875rem', color: 'text.secondary', mb: '2px' }} />
                {!editing && canDecrypt && (
                  <Tooltip
                    title={canDecrypt
                      ? (showValues
                        ? 'Hide values'
                        : isVersionView
                          ? 'Decrypt version values'
                          : 'Decrypt values')
                      : 'You do not have permission to decrypt this secret.'}
                  >
                    <span>
                      <IconButton
                        size="small"
                        onClick={handleToggleShow}
                        sx={{ ml: 0.5 }}
                        disabled={!canDecrypt}
                      >
                        {showValues ? (
                          <VisibilityOffIcon fontSize="small" />
                        ) : (
                          <VisibilityIcon fontSize="small" />
                        )}
                      </IconButton>
                    </span>
                  </Tooltip>
                )}
              </Stack>
              <KeyValueTable
                rows={formPairs}
                onChange={setFormPairs}
                showValues={showValues || editing}
                editable={editing}
                onGenerate={handleGenerate}
                isSecretPairs
              />
            </Box>

            <Box>
              <SectionLabel>Secret Metadata</SectionLabel>
              <KeyValueTable
                rows={formMetadata}
                onChange={setFormMetadata}
                showValues
                editable={editing}
              />
            </Box>

            {editing ? (
              <TextField
                label="Documentation"
                size="small"
                fullWidth
                multiline
                minRows={3}
                value={formDocumentation}
                onChange={(e) => setFormDocumentation(e.target.value)}
                placeholder="Add documentation for this secret. Add a link to a runbook if relevant."
              />
            ) : formDocumentation ? (
              <ReadOnlyField label="Documentation" value={formDocumentation} />
            ) : null}

            {!isNew && (
              <>
                <Divider />
                <Stack direction="row" flexWrap="wrap" gap={2}>
                  <ReadOnlyField
                    label="Secret ID"
                    value={secret?.id}
                    sx={{ flex: '2 1 220px' }}
                    valueSx={{
                      fontFamily: 'monospace',
                      fontSize: '0.8rem',
                      wordBreak: 'break-all',
                    }}
                  />
                  <ReadOnlyField
                    label="Revision"
                    value={secret?.revision?.toString() ?? '—'}
                    sx={{ flex: '0 1 100px' }}
                  />
                  <ReadOnlyField
                    label="Modified"
                    value={
                      secret?.modified_date
                        ? new Date(secret.modified_date).toLocaleString()
                        : '—'
                    }
                    sx={{ flex: '1 1 200px' }}
                  />
                  <ReadOnlyField
                    label="Modified By"
                    value={secret?.modified_by}
                    sx={{ flex: '1 1 180px' }}
                  />
                </Stack>

                {!isVersionView && secretGroups.length > 0 && (
                  <Box>
                    <SectionLabel>Groups Using This Secret</SectionLabel>
                    <Stack spacing={0.5}>
                      {secretGroups.map((svc) => (
                        <Box key={svc.id}>
                          <Link component={RouterLink} to={`/groups/${svc.id}`}>
                            {svc.id}
                          </Link>
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
          {!isVersionView && (!editing ? (
            <>
              {canEdit ? (
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
                <Tooltip title="You do not have edit permission for this secret.">
                  <span>
                    <Button variant="outlined" disabled>Edit</Button>
                  </span>
                </Tooltip>
              )}
              {canDelete ? (
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<DeleteIcon />}
                  onClick={() => setDeleteDialogOpen(true)}
                >
                  Delete
                </Button>
              ) : (
                <Tooltip title="You do not have delete permission for this secret.">
                  <span>
                    <Button
                      variant="outlined"
                      color="error"
                      startIcon={<DeleteIcon />}
                      disabled
                    >
                      Delete
                    </Button>
                  </span>
                </Tooltip>
              )}
            </>
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
          ))}
        </CardActions>
      </Card>
    </Box>
  );
}
