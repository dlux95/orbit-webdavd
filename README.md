# OrbitOS WebDAV Daemon
## What is orbit-webdavd?
The OrbitOS WebDAV Daemon provides a WebDAV interface for different virtual Filesystems. These Filesystem can either be real local Filesystems, Mounted Filesystems via fstab (including NFSv3) or other sources for which a orbit-webdavd filesystem driver exist (like MySQL, Redis, MongoDB, ...).

Different authenticator plugins allow for different authentication methods (PAM, Ldap, static Mapping, ...). Credential outcomes are cached for performance reasons.

Operators provide a way to act differently depending on user and context. These can be defined on a per virtual filesystem basis.

## Topics
  1. Provided virtual filesystem drivers
  2. Virtual filesystem driver interface description
  3. Provided authenticator systems
  4. Authenticator interface description
  5. Provided operator systems
  6. Operator interface description
  7. Configuration examples
  8. Current WebDAV RFC compliance
