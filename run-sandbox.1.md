% sandbox-manager(1) Version 1.0.0 | sandbox-manager Usage Guide
% catcraft (*https://github.com/CatCraftYT*)

# NAME
**sandbox-manager** - A python script to manage bubblewrap (bwrap) sandboxes using YAML configuration files.

# SYNOPSIS
sandbox [**-h**] [**\--flatten**] [**\--blocking**] [**\--run** *EXECUTABLE*] [**\--search-in** *DIR*] *filename*

# DESCRIPTION
To use the `sandbox` command, provide a valid configuration file as the `filename` argument. sandbox-manager will search for configuration files in the following places, in the following order:

1. In the directories specified in each instance of the *--search-in* command-line option.

2. In the directories specified in the **SANDBOX_CONFIG_DIRS** environment variable, with each directory seperated by colons.

3. In the **default_configs** directory.

# OPTIONS
**filename**  
The name of the configuration file to run, without the file extension.

**--help -h**  
Show a help message and exit.

**--flatten -f**  
Parse the given configuration file and its dependencies, print out a new configuration file with the dependencies integrated, then exit. Useful for determining exactly what a program will be given access to.

**--blocking -b**  
If set, the script will wait for the sandbox process to terminate before terminating itself. Useful when running a shell so that it runs in the foreground.

**--run** *EXECUTABLE*  
A program to run instead of the one specified in the given config file. Useful for running a shell in the sandboxed application's environment.

**--search-in** *DIR* **-s** *DIR*  
A directory to search for config files in. Can be specified multiple times.

# CONFIGURATION
Configuration files are defined using the YAML format. They require exactly one **run** key (if used as the *filename* argument), but a **name** key is also strongly recommended. Any values of a given configuration option will be passed to a shell, so it is important that only trusted configuration files are used (and inherited).

The valid configuration options are:

## **name**: *string*
Defines the name of the application. Copied (with whitespace removed) to the `appName` environment variable when running bubblewrap. For a version with whitespace included, use the `appNameWspace` variable. If `name` is not specified, the sandbox will run, but a warning will be printed to the console.

## **run**: *executable*
Defines the application to run. Since it is passed to a shell, it can be called in any way normally possible from a shell (i.e. as a path or executable name).

## **inherit**: *list*
Takes a list of sandbox names to inherit. Inherited sandboxes have their **preprocess** and **permission** categories merged with the parent sandbox's respective categories. Inheritance is performed recursively, so inherited sandboxes can also have their own inheritances, but it is possible to get into infinite loops, so use inheritance carefully. The **run** configuration option will not be inherited, and a warning will be printed to the console if an inherited sandbox contains it.

## **preprocess**
Used to perform some operation before running the sandbox. Currently, only the **mkdir** option exists.

**mkdir**: *directory*  
Create a new directory at *directory*. Also creates parent directories if they don't already exist.

## **permissions**
Defines permissions for the sandbox. Unless otherwise specified, each option under these categories contains a list of the specified type (e.g. a list of paths). It contains the following options:

**filesystem**  
Defines filesystem permissions. Can contain the following options:

> **bind**: *path*  
> Allows (binds) a file or directory in the sandbox, with both read and write access for applications within it.

> **bind-to**: *path1* *path2*  
> Allows (binds) a file or directory *path1* in the sandbox with read and write access, but places it at the location *path2* within the sandbox.

> **ro-bind**: *path*  
> Allows (binds) a file or directory in the sandbox as read-only.

> **ro-bind-to**: *path1* *path2*  
> Allows (binds) a file or directory *path1* in the sandbox as read-only, but places it at the location *path2* within the sandbox.

> **bind-devices**: *path*  
> Allows (binds) a device file, or a directory containing device files, into the sandbox. Can be used on non-device files, but this option is required for device files to work properly in the sandbox.

> **bind-devices-to**: *path1* *path2*  
> Allows (binds) a device file or directory containing device files *path1*, but places it at the location *path2* within the sandbox.

> **link**: *path1* *path2*  
> Creates a symlink in the sandbox, redirecting read/writes at *path2* to *path1*.

> **new-dev**: *path*  
> Creates a new device filesystem at *path* containing */dev/null*, */dev/zero*, */dev/urandom* and other commonly needed device files.

> **new-tmpfs**: *path*  
> Creates a new tmpfs (temporary filesystem) at *path*.

> **new-proc**: *path*  
> Creates a procfs containing all running processes. If **share-pid** is not set, this will only contain processes running within the sandbox.

> **create-files**: *path*: *data*  
> Creates a file in the sandbox at *path*, containing the string *data*. This option should contain key-value pairs of the form "*path*: *data*".

Every option containing **bind** can be appended with the '**-opt**' suffix, indicating that bubblewrap should silently fail if the file or directory doesn't exist.

**namespaces**  
Defines namespace permissions (e.g. user namespaces). This option is a list of namespaces to share.

> **share-user**  
> Shares the user namespace. Enabling this allows applications to use the user configurations of the host system (i.e. a new user can't be created with an already existing uid).

> **share-ipc**  
> Shares the ipc namespace. Enabling this allows sandboxed applications to communicate with other (unsandboxed) applications on the system.

> **share-pid**  
> Shares the pid namespace. Enabling this allows sandboxed applications to view and interact with other (unsandboxed) processes on the system. Note that sandboxed applications can still see other applications within the sandbox, even without this option.

> **share-network**  
> Shares the network namespace. Enabling this allows applications to access the network.

> **share-hostname**  
> Shares the uts namespace. Enabling this allows applications to change the system's hostname for all processes (assuming they have permission to do so). Note that even without this option, the system's hostname is shared with the sandboxed application.

> **share-cgroup**  
> Shares the cgroup namespace.

**environment**  
Defines environment variables passed to (or created in) the sandbox.

> **copyenv** *env*  
> Copies the environment variable *env* into the sandbox.

> **setenv** *env* *value*  
> Sets the environment variable *env* to *value* in the sandbox.

**dbus**  
Defines access to D-Bus services. Uses *xdg-dbus-proxy* to filter queries.

> **see** *service*  
> Allows an application to see D-Bus service *service* on the bus (i.e. get its name and ID), but not communicate with it.

> **talk** *service*  
> Allows an application to send method calls and recieve signals from the service.

> **own** *service*  
> Allows an application to own the name of the service.

