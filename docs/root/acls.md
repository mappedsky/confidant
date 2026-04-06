# Access Controls (ACLs)

## Design

The design for managing fine-grained ACLs in confidant is relatively simple. Hookpoints are called whenever a resource type will be accessed by an end-user; these hookpoints look like:

```python
check = acl_module_check(
    resource_type='secret',
    action='metadata',
    resource_id=id,
)
if not check:
    ...
```

Some hookpoints include extra information, via kwargs:

```python
check = acl_module_check(
    resource_type='group',
    action='update',
    resource_id=id,
    kwargs={
        'secret_ids': combined_cred_ids,
    },
)
if not check:
    ...
```

These hookpoints all call back to the same function, which by default is:

```python
def default_acl(*args, **kwargs):
    """ Default ACLs for confidant: always return true for users, but enforce
    ACLs for groups, restricting access to:
    * resource_type: service
      actions: metadata, get
    """
    resource_type = kwargs.get('resource_type')
    action = kwargs.get('action')
    resource_id = kwargs.get('resource_id')
    # Some ACL checks also pass extra args in via kwargs, which we would
    # access via:
    #    resource_kwargs = kwargs.get('kwargs')
    if authnz.user_is_user_type('user'):
        return True
    elif authnz.user_is_user_type('service'):
        if resource_type == 'service' and action in ['metadata', 'get']:
            # Does the resource ID match the authenticated username?
            if authnz.user_is_service(resource_id):
                return True
        # We currently only allow groups to access service get/metadata
        return False
    else:
        # This should never happen, but paranoia wins out
        return False
```

This function is defined by the `ACL_MODULE` setting, which by default is `confidant.authnz.rbac:default_acl`. The format is `python.path.to.module:function_in_module`. You can use this to implement an ACL approach that integrates with your own enviroment, or adjusts confidant's behavior to your needs.

When implementing a new ACL module, remember that there are two principal types: `user` and `service`. Confidant now reads that distinction directly from JWT claims provided by the IdP, so your ACL logic must handle both types explicitly. Additionally, you should likely default your return to `False`, unless you're intentionally broadening access.

## ACL Hookpoints

The following hookpoints are currently available:

### Secrets

#### List secrets

```python
acl_module_check(resource_type='secret', action='list')
```

This check controls access to lists of secret metadata.

#### Get secret metadata

```python
acl_module_check(
    resource_type='secret',
    action='metadata',
    resource_id=id,
)
```

This check controls access to specific secret metadata, which does not include secret pairs. Fine-grained controls can be applied using the provided `resource_id`.

#### Get secret

```python
acl_module_check(
    resource_type='secret',
    action='read',
    resource_id=id,
)
```

This check controls access to specific secrets without triggering rotation alerting side effects. This is intended for service reads that fetch secret pairs. Fine-grained controls can be applied using the provided `resource_id`.

#### Get secret with alert

```python
acl_module_check(
    resource_type='secret',
    action='read_with_alert',
    resource_id=id,
)
```

This check controls access to specific secrets and allows the read path to update `last_decrypted_date`, which can affect required rotation timing. This is intended for human users that fetch secret pairs.

#### Create secret

```python
acl_module_check(
    resource_type='secret',
    action='create',
)
```

This check controls create access to secrets. This is a global permission, so no fine-grained ID is provided.

#### Update secret

```python
acl_module_check(
    resource_type='secret',
    action='update',
    resource_id=id,
)
```

This check controls update access to specific secrets. Fine-grained controls can be applied using the provided `resource_id`. Note that if you're controlling access to this, you probably also want to control access to [Revert secret](#revert-secret).

#### Revert secret

```python
acl_module_check(
    resource_type='secret',
    action='revert',
    resource_id=id,
)
```

This check controls revert access to specific secrets. Fine-grained controls can be applied using the provided `resource_id`. Note that if you're controlling access to this, you probably also want to control access to [Update secret](#update-secret).

This action does not require access to view or edit secret pairs, so it can be used to allow folks to rollback changes to resources without access to view/edit them.

#### Delete secret

```python
acl_module_check(
    resource_type='secret',
    action='delete',
    resource_id=id,
)
```

This check controls delete access to specific secrets. Deletes archive the
secret and all of its versions under the same secret ID, then remove the
active record from the primary secret partitions. Fine-grained controls can be
applied using the provided `resource_id`.

### Groups

#### List groups

```python
acl_module_check(resource_type='group', action='list')
```

This check controls access to lists of service metadata.

#### Get service metadata

```python
acl_module_check(
    resource_type='group',
    action='metadata',
    resource_id=id,
)
```

This check controls access to specific service metadata. Service reads no longer expand mapped secrets; secret payloads are fetched from the secret endpoints instead. Fine-grained controls can be applied using the provided `resource_id`.

#### Get service

```python
acl_module_check(
    resource_type='group',
    action='get',
    resource_id=id,
)
```

This check controls access to specific service data. Service reads no longer expand mapped secrets; secret payloads are fetched from the secret endpoints instead. Fine-grained controls can be applied using the provided `resource_id`.

#### Get secret via mapped service

Credential read endpoints also allow access when the authenticated service is mapped to the requested secret:

```python
acl_module_check(
    resource_type='secret',
    action='read',
    resource_id=id,
)
```

The default ACL module continues to handle human users. Credential routes add a service-mapping authorization check before returning secret metadata or pairs. Mapped service reads use `read`; interactive user reads use `read_with_alert`.

#### Create service

```python
acl_module_check(
    resource_type='group',
    action='create',
    resource_id=id,
)
```

This check controls create access to specific groups. Fine-grained controls can be applied using the provided `resource_id`.

#### Update service

```python
acl_module_check(
    resource_type='group',
    action='update',
    resource_id=id,
)
```

This check controls update access to specific groups. Fine-grained controls can be applied using the provided `resource_id`. Note that if you're controlling access to this, you probably also want to control access to [Revert service](#revert-service).

#### Revert service

```python
acl_module_check(
    resource_type='group',
    action='revert',
    resource_id=id,
)
```

This check controls revert access to specific groups. Fine-grained controls can be applied using the provided `resource_id`. Note that if you're controlling access to this, you probably also want to control access to [Update service](#update-service).

This action does not require access to view or update groups, so it can be used to allow folks to rollback changes to resources without access to view/update them.

#### Delete service

```python
acl_module_check(
    resource_type='group',
    action='delete',
    resource_id=id,
)
```

This check controls delete access to specific groups. Deletes archive the
group and all of its versions under the same group ID, then remove the active
record from the primary group partitions. Fine-grained controls can be applied
using the provided `resource_id`.
