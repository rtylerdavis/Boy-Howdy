inih_cpp = dependency('INIReader')
libevdev = dependency('libevdev')
libpam = meson.get_compiler('cpp').find_library('pam')
threads = dependency('threads')

# Translations
subdir('po')

# Paths
paths_h = configure_file(
	input: 'paths.hh.in',
	output: 'paths.hh',
	configuration: pam_module_conf_data
)

# PAM modules must live in the system security directory (e.g. /usr/lib64/security),
# NOT under the meson install prefix (which defaults to /usr/local).
if get_option('pam_dir') != ''
    pamdir = get_option('pam_dir')
else
    # Try pkg-config first (Debian/Ubuntu ship pam.pc with a moduledir variable)
    pam_pkg = dependency('pam', method: 'pkg-config', required: false)
    pamdir = ''
    if pam_pkg.found()
        pamdir = pam_pkg.get_variable(pkgconfig: 'moduledir', default_value: '')
    endif
    if pamdir == ''
        # Fall back: use the system libdir under /usr, ignoring the meson prefix.
        # Fedora: /usr/lib64/security, Debian: /usr/lib/x86_64-linux-gnu/security
        pamdir = '/usr' / get_option('libdir') / 'security'
    endif
endif

shared_library(
	'pam_howdy',
	'main.cc',
	'enter_device.cc',
	dependencies: [
		libpam,
		inih_cpp,
		threads,
		libevdev,
	],
	link_depends: [
		paths_h,
	],
	install: true,
	install_dir: pamdir,
	install_tag: 'pam_module',
	name_prefix: ''
)
