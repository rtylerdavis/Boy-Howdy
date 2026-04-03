%global selinux_policyver %(rpm -q --qf "%%{version}" selinux-policy 2>/dev/null || echo 0.0.0)

Name:           boy-howdy
Version:        4.0.0
Release:        1%{?dist}
Summary:        Linux face authentication (Windows Hello style)
License:        MIT
URL:            https://github.com/rtylerdavis/Boy-Howdy
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildRequires:  meson >= 0.64.0
BuildRequires:  gcc-c++
BuildRequires:  pam-devel
BuildRequires:  inih-devel
BuildRequires:  libevdev-devel
BuildRequires:  python3-devel >= 3.12
BuildRequires:  gettext
BuildRequires:  checkpolicy
BuildRequires:  selinux-policy-devel

Requires:       python3 >= 3.12
Requires:       python3-opencv
Requires:       python3-numpy
Requires:       pam
Requires:       %{name}-selinux = %{version}-%{release}

%description
Boy-Howdy is a Linux face authentication system that integrates with PAM
to provide Windows Hello-style face unlock for login, sudo, and other
authentication prompts. Uses OpenCV DNN (YuNet + SFace) for fast, accurate
face detection and recognition with zero extra dependencies beyond OpenCV.

Fork of boltgolt/howdy, modernized for Python 3.12+, Fedora, and current
Linux distributions.

# ---- SELinux subpackage ----
%package selinux
Summary:        SELinux policy for Boy-Howdy face authentication
BuildArch:      noarch
Requires:       selinux-policy >= %{selinux_policyver}
Requires(post): policycoreutils
Requires(postun): policycoreutils

%description selinux
SELinux policy module for Boy-Howdy. Grants display managers (GDM/SDDM)
and console login the permissions needed to access camera and uinput
devices for face authentication.

# ---- GTK subpackage ----
%package gtk
Summary:        GTK authentication UI for Boy-Howdy
Requires:       %{name} = %{version}-%{release}
Requires:       python3-gobject
Requires:       gtk3

%description gtk
Optional GTK-based authentication overlay UI for Boy-Howdy. Shows a visual
indicator during face authentication at the login screen.

%prep
%autosetup -n Boy-Howdy-%{version}

%build
# Build the main project
%meson \
    -Dpam_dir=%{_libdir}/security \
    -Dconfig_dir=%{_sysconfdir}/howdy \
    -Dmodel_data_dir=%{_datadir}/boy-howdy/models \
    -Duser_models_dir=%{_sysconfdir}/howdy/models \
    -Dpy_sources_dir=%{_libdir} \
    -Dpython_path=%{python3} \
    -Dwith_polkit=true
%meson_build

# Build SELinux policy
cd fedora
make -f Makefile.selinux
cd ..

%install
%meson_install

# Install SELinux policy
install -d %{buildroot}%{_datadir}/selinux/packages
install -m 644 fedora/boy-howdy.pp %{buildroot}%{_datadir}/selinux/packages/

# Install authselect helper script and upgrade checker
install -d %{buildroot}%{_sbindir}
install -m 755 fedora/howdy-authselect %{buildroot}%{_sbindir}/
install -m 755 fedora/howdy-upgrade-check %{buildroot}%{_sbindir}/

# Install model download script
install -d %{buildroot}%{_datadir}/boy-howdy/models
install -m 755 howdy/src/model-data/install.sh %{buildroot}%{_datadir}/boy-howdy/models/

# Create directories for user face models and logs
install -d -m 711 %{buildroot}%{_sysconfdir}/howdy/models
install -d %{buildroot}%{_localstatedir}/log/howdy

%post selinux
semodule -i %{_datadir}/selinux/packages/boy-howdy.pp 2>/dev/null || :

%postun selinux
if [ $1 -eq 0 ]; then
    semodule -r boy-howdy 2>/dev/null || :
fi

%pretrans -p <lua>
-- Run upgrade check to clean stale v2.x PAM entries before install.
-- Uses lua because pretrans can't depend on package scriptlets.
os.execute("/usr/sbin/howdy-upgrade-check --fix 2>/dev/null || true")

%post
echo ""
echo "=== Boy-Howdy installed ==="
echo ""
echo "Next steps:"
echo "  1. Download face models:  cd %{_datadir}/boy-howdy/models && sudo ./install.sh"
echo "  2. Enable in PAM:         sudo howdy-authselect enable"
echo "  3. Enroll your face:      sudo howdy add"
echo "  4. Test it:               sudo howdy test"
echo ""

%preun
if [ $1 -eq 0 ]; then
    # On full removal, disable authselect integration if active
    if command -v howdy-authselect &>/dev/null; then
        howdy-authselect disable 2>/dev/null || :
    fi
fi

%files
%license LICENSE
%doc README.md howdy-modernization-changes.md
%{_bindir}/howdy
%{_libdir}/security/pam_howdy.so
%{_libdir}/howdy/
%dir %{_sysconfdir}/howdy
%config(noreplace) %{_sysconfdir}/howdy/config.ini
%dir %attr(711,root,root) %{_sysconfdir}/howdy/models
%{_datadir}/boy-howdy/
%{_datadir}/bash-completion/completions/howdy
%{_sbindir}/howdy-authselect
%{_sbindir}/howdy-upgrade-check
%{_mandir}/man1/howdy.1*
%dir %{_localstatedir}/log/howdy

%files selinux
%{_datadir}/selinux/packages/boy-howdy.pp

%files gtk
%{_bindir}/howdy-gtk
%{_libdir}/howdy-gtk/
%{_datadir}/howdy-gtk/
%{_datadir}/polkit-1/actions/com.github.boltgolt.howdy-gtk.policy

%changelog
* Wed Apr 02 2026 Tyler Davis <tyler@rtylerdavis.us> - 4.0.0-1
- Initial Boy-Howdy package (fork of howdy)
- Replaced dlib with OpenCV DNN (YuNet + SFace) — zero new deps
- Python 3.12+ minimum, all Python 2 remnants removed
- Fixed PAM module Python path discovery and install path
- Added SELinux policy module for camera/uinput access
- Added authselect integration script
- Secured face model file permissions (600)
