# Managing secrets and mappings

Confidant is simple; it has two concepts: secrets and the mappings of those
secrets to groups. Both secrets and their mappings to groups are revisioned
and no revision is ever deleted. Confidant has two views: the resources view
and the history view.

## Using the resources view

### Creating secrets

![interface create](images/interface-create.png)

In the left panel of the resources view is the list of secrets and groups.
Above that is a filter, and next to the filter is a plus. Clicking on that plus
gives you the option to create a secret or to create a service.

Click on create secret. This will bring up a new secret resource in the
right panel.

Secrets have human readable names, which can be renamed, and a
set of secret pairs. Credential pairs are key/value pairs, where the key is
alphanumeric and the value can be anything. Credential pairs are the secrets
and are encrypted at-rest. The rest of the metadata is stored along with the secret
and is un-encrypted, so the friendly name should not contain anything sensitive.

![interface new secret](images/interface-new-secret.png)

Secrets can have more than a single secret pair; however, it's
important to note that keys must be unique in a secret, and when mapping
secrets to a service, the keys must be unique across all secrets in
the mapped service. This is to avoid confusion on the service's end, where two
conflicting keys would force the service to choose which key is valid.

### Mapping secrets to groups

![interface new service](images/interface-new-service.png)

In the same way you created a new secret, do the same thing, but now click
on create service. This will bring up a new service resourse in the right
panel.

Groups in Confidant use a user-defined group ID. Choose the identifier you
want to use for secret mappings and create the service with that value.

### Finding secrets and groups in the sidebar

![interface filter](images/interface-filter.png)

Once you have enough secrets and groups, it can be difficult to find them
in the sidebar. To make this easier, the sidebar has a filter at the top
that'll let you selectively display secrets and groups.

![interface filter with regex](images/interface-filter-with-regex.png)

By default this filter will match any word in the user-defined name of
secrets and groups, but it's also possible to use a regex filter instead.

## Using the history view

![interface history](images/interface-history.png)

The history view can be used to explore changes in secrets or groups. The
left panel of the history view shows a list of changes, sorted by date.
Clicking on any revision in the left panel will bring up that revision in the
right panel. From there, you can inspect the selected revision and revert to
it if needed.
