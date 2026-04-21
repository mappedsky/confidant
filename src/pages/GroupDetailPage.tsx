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
  IconButton,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  Link,
  Stack,
  Checkbox,
  ListItemText,
  OutlinedInput,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableContainer,
  TableRow,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import HistoryIcon from '@mui/icons-material/History';
import RestoreIcon from '@mui/icons-material/Restore';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import { api } from '../api';
import { useAppContext } from '../contexts/AppContext';
import CenteredSpinner from '../components/CenteredSpinner';
import {
  GroupWritePayload,
  SecretSummary,
  GroupDetail,
} from '../types/api';
import {
  secretDetailPath,
  secretPolicyHasGlob,
  validateSecretPolicyPath,
  validateGroupId,
} from '../utils/resourceIds';

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

const POLICY_ACTIONS = [
  'list',
  'create',
  'metadata',
  'decrypt',
  'update',
  'delete',
  'revert',
] as const;

interface GroupPolicyRow {
  secretId: string;
  permissions: string[];
}

type GroupDetailParams = { id?: string; version?: string };

export default function GroupDetailPage() {
  const { id, version } = useParams<GroupDetailParams>();
  const navigate = useNavigate();
  const { clientConfig } = useAppContext();
  const isNew = !id;
  const versionNumber = version ? Number(version) : null;
  const isVersionView = versionNumber !== null && !Number.isNaN(versionNumber);
  const permissions = clientConfig?.generated?.permissions;
  const maintenanceMode = clientConfig?.generated?.maintenance_mode ?? false;

  const [group, setGroup] = useState<GroupDetail | null>(null);
  const [allSecrets, setAllSecrets] = useState<SecretSummary[]>([]);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(isNew);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [latestRevision, setLatestRevision] = useState<number | null>(null);
  const [canRestore, setCanRestore] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [restoreDialogOpen, setRestoreDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [versionRevisions, setVersionRevisions] = useState<number[]>([]);

  const [formId, setFormId] = useState('');
  const [formPolicies, setFormPolicies] = useState<GroupPolicyRow[]>([]);

  const populateForm = useCallback((svc: GroupDetail) => {
    setFormId(svc.id ?? '');
    setFormPolicies(
      Object.entries(svc.policies ?? {}).map(([secretId, permissions]) => ({
        secretId,
        permissions: [...permissions],
      })),
    );
  }, []);

  useEffect(() => {
    api.getSecrets()
      .then((data) => setAllSecrets(data.secrets ?? []))
      .catch(() => {});

    if (isNew) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    setLatestRevision(null);
    setCanRestore(false);
    setVersionRevisions([]);

    if (isVersionView && id && versionNumber !== null) {
      Promise.all([
        api.getGroupVersion(id, versionNumber),
        api.getGroup(id),
        api.getGroupVersions(id),
      ])
        .then(([svc, current, history]) => {
          setGroup(svc);
          populateForm(svc);
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

    api.getGroup(id)
      .then((svc) => {
        setGroup(svc);
        populateForm(svc);
        setLatestRevision(svc.revision);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id, isNew, isVersionView, populateForm, versionNumber]);

  const handleAddPolicy = () => {
    setFormPolicies((prev) => [...prev, { secretId: '', permissions: [] }]);
  };

  const handleRemovePolicy = (idx: number) => {
    setFormPolicies((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSecretChange = (idx: number, secretId: string) => {
    setFormPolicies((prev) =>
      prev.map((policy, i) =>
        i === idx
          ? {
              ...policy,
              secretId,
            }
          : policy,
      ),
    );
  };

  const handlePermissionsChange = (idx: number, permissions: string[]) => {
    setFormPolicies((prev) =>
      prev.map((policy, i) =>
        i === idx
          ? {
              ...policy,
              permissions,
            }
          : policy,
      ),
    );
  };

  const handleSave = async () => {
    setSaveError(null);

    const idError = validateGroupId(formId);
    if (idError) {
      setSaveError(idError);
      return;
    }

    const secretIds = formPolicies.map((policy) => policy.secretId).filter(Boolean);
    if (new Set(secretIds).size !== secretIds.length) {
      setSaveError('Each policy must reference a unique secret.');
      return;
    }
    if (formPolicies.some((policy) => !policy.secretId)) {
      setSaveError('Each policy row must select a secret.');
      return;
    }
    for (const policy of formPolicies) {
      const policyError = validateSecretPolicyPath(policy.secretId);
      if (policyError) {
        setSaveError(policyError);
        return;
      }
    }
    if (formPolicies.some((policy) => policy.permissions.length === 0)) {
      setSaveError('Each policy row must include at least one permission.');
      return;
    }

    if (isNew) {
      try {
        await api.getGroup(formId);
        setSaveError(`Group with id ${formId} already exists.`);
        return;
      } catch (err) {
        const error = err as { status?: number };
        if (error.status !== 404) {
          setSaveError('Failed to check if group already exists.');
          return;
        }
      }
    }

    const payload: GroupWritePayload = {
      id: formId,
      policies: Object.fromEntries(
        formPolicies.map((policy) => [
          policy.secretId,
          [...new Set(policy.permissions)],
        ]),
      ),
    };

    setSaving(true);
    try {
      let saved: GroupDetail;
      if (isNew) {
        saved = await api.createGroup(formId, payload);
        if (!saved.id) {
          throw new Error('Group was created, but no group ID was returned.');
        }
        window.location.replace(`/groups/${saved.id}`);
        return;
      } else if (id) {
        saved = await api.updateGroup(id, payload);
        setGroup(saved);
        populateForm(saved);
        setEditing(false);
      } else {
        throw new Error('Missing group ID');
      }
    } catch (err: unknown) {
      setSaveError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (isNew) {
      navigate('/groups');
      return;
    }
    if (group) {
      populateForm(group);
    }
    setSaveError(null);
    setEditing(false);
  };

  const handleRestoreVersion = async () => {
    if (!id || versionNumber === null) {
      return;
    }

    setSaveError(null);
    setRestoring(true);
    try {
      const restored = await api.restoreGroupVersion(id, versionNumber);
      navigate(`/groups/${restored.id}`);
    } catch (err) {
      setSaveError((err as Error).message);
    } finally {
      setRestoring(false);
    }
  };

  const handleDelete = async () => {
    if (!id) {
      return;
    }

    setSaveError(null);
    setDeleting(true);
    try {
      await api.deleteGroup(id);
      navigate('/groups');
    } catch (err) {
      setSaveError((err as Error).message);
    } finally {
      setDeleting(false);
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
          onClick={() => navigate('/groups')}
          sx={{ mb: 2 }}
        >
          Back to Groups
        </Button>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  const canEdit = !maintenanceMode && !isVersionView && (isNew
    ? permissions?.groups?.create
    : group?.permissions?.update);
  const canDelete = !maintenanceMode && !isVersionView && !isNew && group?.permissions?.delete;
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
      ? 'You do not have permission to restore this group.'
      : '';

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <Box>
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate(isVersionView ? `/groups/${id}/history` : '/groups')}
            sx={{ mb: 2 }}
          >
            {isVersionView ? 'Back to History' : 'Back to Groups'}
          </Button>

          <Typography variant="h5" fontWeight={600}>
            {isNew ? 'New Group' : group?.id || id}
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
                      onClick={() => navigate(`/groups/${id}/versions/${prevVersion}`)}
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
                      onClick={() => navigate(`/groups/${id}/versions/${nextVersion}`)}
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
                onClick={() => navigate(`/groups/${id}/history`)}
              >
                History
              </Button>
            )}
          </Stack>
        )}
      </Box>

      {isVersionView && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Viewing group version v{versionNumber}
          {latestRevision === versionNumber ? ' (current)' : ''}
        </Alert>
      )}

      <Dialog open={restoreDialogOpen} onClose={() => !restoring && setRestoreDialogOpen(false)}>
        <DialogTitle>Restore this version?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This will restore group version v{versionNumber} as the current version.
            The current group configuration will be replaced, and a new version will be created.
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
        <DialogTitle>Archive and delete this group?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This removes the group from active use and archives its current
            record and version history with the same group ID.
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

      {saveError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {saveError}
        </Alert>
      )}

      <Card elevation={1}>
        <CardContent sx={{ p: 3 }}>
          <Stack spacing={3}>
            {isNew ? (
              <TextField
                label="Group ID"
                size="small"
                required
                value={formId}
                onChange={(event) => setFormId(event.target.value)}
                placeholder="Enter a group ID"
                helperText="Use letters, numbers, and _+=.@-. Max 512 chars."
              />
            ) : (
              <ReadOnlyField label="Group ID" value={group?.id} valueSx={{ fontFamily: 'monospace' }} />
            )}

            <Box>
              <SectionLabel>Policies</SectionLabel>
              <TableContainer
                component={Paper}
                variant="outlined"
                sx={{ borderColor: 'divider', borderRadius: 1, overflowX: 'auto' }}
              >
                <Table size="small" sx={{ minWidth: 640 }}>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600, width: editing ? '34%' : '28%' }}>Secret</TableCell>
                      <TableCell sx={{ fontWeight: 600, width: '28%' }}>Secret ID</TableCell>
                      <TableCell sx={{ fontWeight: 600, width: editing ? '30%' : '36%' }}>Permissions</TableCell>
                      {editing && <TableCell sx={{ fontWeight: 600, width: 60 }} />}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {formPolicies.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={editing ? 4 : 3} sx={{ color: 'text.secondary', fontStyle: 'italic' }}>
                          No policies configured.
                        </TableCell>
                      </TableRow>
                    ) : (
                      formPolicies.map((policy, idx) => {
                        const secret = allSecrets.find(
                          (item) => item.id === policy.secretId,
                        );
                        return (
                        <TableRow key={idx}>
                          <TableCell>
                            {editing ? (
                              <TextField
                                size="small"
                                fullWidth
                                value={policy.secretId}
                                onChange={(event) =>
                                  handleSecretChange(idx, event.target.value)
                                }
                                placeholder="secret-id or glob like apps/*"
                              />
                            ) : (
                              <Box>
                                {secretPolicyHasGlob(policy.secretId) ? (
                                  <Typography variant="body2">
                                    {policy.secretId}
                                  </Typography>
                                ) : (
                                  <Link
                                    component={RouterLink}
                                    to={secretDetailPath(policy.secretId)}
                                  >
                                    {secret?.name || policy.secretId}
                                  </Link>
                                )}
                              </Box>
                            )}
                          </TableCell>
                          <TableCell>
                            <Typography color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                              {policy.secretId || '—'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            {editing ? (
                              <FormControl size="small" fullWidth>
                                <Select
                                  multiple
                                  value={policy.permissions}
                                  onChange={(event) =>
                                    handlePermissionsChange(
                                      idx,
                                      event.target.value as string[],
                                    )
                                  }
                                  input={<OutlinedInput />}
                                  renderValue={(selected) =>
                                    (selected as string[]).join(', ') || 'Select permissions'
                                  }
                                >
                                  {POLICY_ACTIONS.map((action) => (
                                    <MenuItem key={action} value={action}>
                                      <Checkbox
                                        checked={policy.permissions.includes(action)}
                                      />
                                      <ListItemText primary={action} />
                                    </MenuItem>
                                  ))}
                                </Select>
                              </FormControl>
                            ) : (
                              <Typography color="text.secondary">
                                {policy.permissions.join(', ') || '—'}
                              </Typography>
                            )}
                          </TableCell>
                          {editing && (
                            <TableCell>
                              <IconButton
                                size="small"
                                color="error"
                                onClick={() => handleRemovePolicy(idx)}
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </TableCell>
                          )}
                        </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
              {editing && (
                <Button
                  size="small"
                  startIcon={<AddIcon />}
                  onClick={handleAddPolicy}
                  sx={{ mt: 1 }}
                >
                  Add policy
                </Button>
              )}
              {editing && allSecrets.length > 0 && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                  Existing secrets can be referenced directly, or use a glob
                  like `apps/*`. Use `*` for global list/create access.
                </Typography>
              )}
            </Box>

            {!isNew && (
              <>
                <Divider />
                <Stack direction="row" flexWrap="wrap" gap={2}>
                  <ReadOnlyField
                    label="Revision"
                    value={group?.revision?.toString() ?? '—'}
                    sx={{ flex: '0 1 100px' }}
                  />
                  <ReadOnlyField
                    label="Modified"
                    value={
                      group?.modified_date
                        ? new Date(group.modified_date).toLocaleString()
                        : '—'
                    }
                    sx={{ flex: '1 1 200px' }}
                  />
                  <ReadOnlyField
                    label="Modified By"
                    value={group?.modified_by}
                    sx={{ flex: '1 1 180px' }}
                  />
                </Stack>
              </>
            )}
          </Stack>
        </CardContent>

        <CardActions sx={{ px: 3, pb: 3, pt: 0, gap: 1 }}>
          {!isVersionView && (!editing ? (
            <>
              {canEdit ? (
                <Button
                  variant="contained"
                  onClick={() => {
                    setSaveError(null);
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
                <Tooltip title="You do not have edit permission for this group.">
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
                <Tooltip title="You do not have delete permission for this group.">
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
