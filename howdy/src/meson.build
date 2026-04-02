if meson.is_subproject()
project('howdy', 'cpp', license: 'MIT', version: 'beta', meson_version: '>= 0.64.0')
endif


datadir = get_option('prefix') / get_option('datadir') / 'howdy'
py_conf = configuration_data(paths_dict)
py_conf.set('data_dir', datadir)

py = import('python').find_installation(paths_dict.get('python_path'))
py.dependency()

if py.language_version().version_compare('< 3.12')
    error('Boy-Howdy requires Python >= 3.12, found ' + py.language_version())
endif

py_paths = configure_file(
    input: 'paths.py.in',
    output: 'paths.py',
    configuration: py_conf,
)

py_sources = [
    'cli/__init__.py',
    'cli/add.py',
    'cli/clear.py',
    'cli/config.py',
    'cli/disable.py',
    'cli/list.py',
    'cli/remove.py',
    'cli/set.py',
    'cli/snap.py',
    'cli/test.py',
    'cli.py',
    'compare.py',
    'i18n.py',
    'paths_factory.py',
    'recorders/__init__.py',
    'recorders/ffmpeg_reader.py',
    'recorders/pyv4l2_reader.py',
    'recorders/v4l2.py',
    'recorders/video_capture.py',
    'rubberstamps/__init__.py',
    'rubberstamps/hotkey.py',
    'rubberstamps/nod.py',
    'snapshot.py',
    py_paths,
]

# Include PAM module
if get_option('install_in_site_packages')
    pysourcesinstalldir = join_paths(py.get_install_dir(), 'howdy')
else  
    pysourcesinstalldir = get_option('py_sources_dir') != '' ? get_option('py_sources_dir') / 'howdy' : join_paths(get_option('prefix'), get_option('libdir'), 'howdy')
endif

pam_module_conf_data = configuration_data(paths_dict)
pam_module_conf_data.set('compare_script_path', join_paths(pysourcesinstalldir, 'compare.py'))
pam_module_conf_data.set('config_file_path', config_path)
subdir('pam')
if get_option('install_pam_config')
    # pamdir is inherited from the pam subproject
    pam_config = configure_file(
        input: 'pam-config/howdy.in',
        output: 'pam-config',
        configuration: {'pamdir': pamdir}
    )
    install_data(
        pam_config,
        install_dir: get_option('prefix') / get_option('datadir') / 'pam-configs',
        install_mode: 'rwxr-xr-x',
        install_tag: 'pam',
        rename: 'howdy',
    )
endif

if get_option('install_in_site_packages')
    py.install_sources(
        py_sources,
        subdir: 'howdy',
        preserve_path: true,
        install_tag: 'py_sources',
    )
else
    install_data(
        py_sources,
        preserve_path: true,
        install_dir: pysourcesinstalldir,
        install_mode: 'r--r--r--',
        install_tag: 'py_sources',
    )
endif

install_data('logo.png', install_tag: 'meta')
autocomplete = configure_file(
    input: 'autocomplete/howdy.in',
    output: 'autocomplete',
    configuration: configuration_data({ 'config_path': config_path })
)
install_data(
    autocomplete,
    install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'bash-completion', 'completions'),
    install_mode: 'rwxr--r--',
    install_tag: 'bash_completion',
    rename: 'howdy',
)

fs = import('fs')
if not fs.exists(config_path)
    install_data('config.ini', install_dir: confdir, install_mode: 'rwxr--r--', install_tag: 'config')
endif

install_data('model-data/install.sh', install_dir: modeldatadir, install_mode: 'rwxr-xr-x')

install_man('../howdy.1')

cli_path = join_paths(pysourcesinstalldir, 'cli.py')
conf_data = configuration_data({ 'script_path': cli_path, 'python_path': py.full_path() })

bin_name = 'howdy'
bin = configure_file(
    input: 'bin/howdy.in',
    output: bin_name,
    configuration: conf_data
)
install_data(
  bin,
  install_mode: 'rwxr-xr-x',
  install_dir: get_option('bindir'),
  install_tag: 'bin',
)
