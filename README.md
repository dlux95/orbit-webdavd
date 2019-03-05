# OrbitOS WebDAV Daemon
## What is orbit-webdavd?
  The OrbitOS WebDAV Daemon provides a WebDAV interface for different virtual Filesystems. These Filesystem can either be real local Filesystems, Mounted Filesystems via fstab (including NFSv3) or other sources for which a orbit-webdavd filesystem driver exist (like MySQL, Redis, MongoDB, ...).

  Different authenticator plugins allow for different authentication methods (PAM, Ldap, static Mapping, ...). Credential outcomes are cached for performance reasons.

  Operators provide a way to act differently depending on user and context. These can be defined on a per virtual filesystem basis.

## Topics
  1. [Provided virtual filesystem drivers](#1-Provided-virtual-filesystem-drivers)
  2. [Virtual filesystem driver interface description](#2-Virtual-filesystem-driver-interface-description)
  3. [Provided authenticator systems](#3-Provided-authenticator-systems)
  4. [Authenticator interface description](#4-Authenticator-interface-description)
  5. [Provided operator systems](#5-Provided-operator-systems)
  6. [Operator interface description](#6-Operator-interface-description)
  7. [Configuration examples](#7-Configuration-examples)
  8. [Current WebDAV RFC compliance](#8-Current-WebDAV-RFC-compliance)

  ## 1. Provided virtual filesystem drivers
  Currently implemented virtual filesystem drivers:
  * [DirectoryFilesystem](#DirectoryFilesystem)
  * [HomeFilesystem](#HomeFilesystem)

  ## DirectoryFilesystem
  The DirectoryFilesystem driver exposes a directory present on the local filesystem (or other filesystem which are mounted locally). Additional directories can be supplied which are allowed when resolving symlinks (DirectoryFilesystem driver forces resolved paths to be either in the basepath or in one of the supplied additional directories)

  With Operators you can force the filesystem to act like a specific user or to act like the authenticated user (only makes sense with pam).

  ## HomeFilesystem
  Like the DirectoryFilesystem but sets the basepath according to the homedirectory gained from the supplied Operator.
    
    
  ## 8. Current WebDAV RFC compliance
  | WebDAV Feature          |   v0.1  |
  |-------------------------|:-------:|
  | OPTIONS                 | &#9745; |
  | GET                     | &#9745; |
  | PROPFIND                | &#9745; |
  | PUT                     | &#9745; |
  | MKCOL                   | &#9745; |
  | COPY                    |         |
  | MOVE                    |         |
  | DELETE                  | &#9745; |
  | LOCK                    | &#9745; |
  | UNLOCK                  | &#9745; |
