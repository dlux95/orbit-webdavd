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

  ### DirectoryFilesystem
  The DirectoryFilesystem driver exposes a directory present on the local filesystem (or other filesystem which are mounted locally). Additional directories can be supplied which are allowed when resolving symlinks (DirectoryFilesystem driver forces resolved paths to be either in the basepath or in one of the supplied additional directories)  
  With Operators you can force the filesystem to act like a specific user or to act like the authenticated user (only makes sense with pam).  
  ### HomeFilesystem
  Like the DirectoryFilesystem but sets the basepath according to the homedirectory gained from the supplied Operator.

  ## 2. Virtual filesystem driver interface description
  TODO

  ## 3. Provided authenticator systems
  Currently implemented authenticator systems:
  * [DebugAuthenticator](#DebugAuthenticator)
  * [StaticAuthenticator](#StaticAuthenticator)
  * [PAMAuthenticator](#PAMAuthenticator)

  ### DebugAuthenticator
  The DebugAuthenticator successfully authenticates the user if the username is equal to the supplied password. It is primarily used to validate other parts of the daemon during development. __DO NOT USE IN PRODUCTION!__

  ### StaticAuthenticator
  The StaticAuthenticator validates supplied username and password with a static username/password map. This is sufficient for smaller installations where users don't need their own account in the machines user management.

  ### PAMAuthenticator
  The PAMAuthenticator validates supplied username and password with the help of PAM. It is used to authenticate against local system accounts. Because you can use PAM with credentials stored in LDAP or Kerberos this Authenticator is also viable if you use these to store credentials.

  ## 4. Authenticator interface description
  TODO

  ## 5. Provided operator systems
  TODO

  ## 6. Operator interface desciption
  TODO

  ## 7. Configuration examples
  TODO
    
  ## 8. Current WebDAV RFC compliance
  | WebDAV Feature                      | v0.1  		     | v0.2  		      |
  |-------------------------------------|:------------------:|:------------------:|
  | OPTIONS                             | :heavy_check_mark: | :heavy_check_mark: |
  | PROPFIND                            | :heavy_check_mark: | :heavy_check_mark: |
  | PROPFIND with Depth-Header          | :heavy_check_mark: | :heavy_check_mark: |
  | PROPFIND with XML-Props             |                    |
  | PROPPATCH                           | *1                 | *1                 |
  | MKCOL                               | :heavy_check_mark: | :heavy_check_mark: |
  | MKCOL with Body                     | *2                 | *2                 |
  | GET                                 | :heavy_check_mark: | :heavy_check_mark: |
  | HEAD                                | :heavy_check_mark: | :heavy_check_mark: |
  | DELETE                              | :heavy_check_mark: | :heavy_check_mark: |
  | PUT                                 | :heavy_check_mark: | :heavy_check_mark: |
  | COPY                                |         		     | :heavy_check_mark: |
  | COPY with Overwrite: T              |         		     |
  | MOVE                                |         		     | :heavy_check_mark: |
  | MOVE with Overwrite: T              |         		     |
  | LOCK                                | :heavy_check_mark: | :heavy_check_mark: |
  | UNLOCK                              | :heavy_check_mark: | :heavy_check_mark: |

  *1 Send a Dummy Response because dead properties are not supported yet  
  *2 RFC only defines that it can be used to create resources but no protocol specification 
