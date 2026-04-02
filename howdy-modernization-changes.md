# Boy-Howdy Modernization Changes

Tracking all changes made to modernize the fork from boltgolt/howdy.

---

## Modernization Todo List

### Critical
- [x] **Kill Python 2 / pam_python dependency** — 3.0.0 beta on master already uses C++ PAM module. Verified no Python 2 remnants remain.
- [x] **Solve the dlib problem** — Replaced dlib entirely with OpenCV DNN (YuNet + SFace). Zero new dependencies.
- [x] **Fix Python path discovery in PAM context** — PAM module now builds a minimal environment (`PYTHONPATH`, `PATH`) and passes it to the Python subprocess via `posix_spawnp`.
- [x] **Fix PAM module install path** — Auto-detects system PAM directory via pkg-config, falls back to `/usr/<libdir>/security` (ignoring meson prefix).

### Fedora-Specific
- [x] **Add authselect support** — `howdy-authselect` script with enable/disable/status. Creates custom profile based on user's current one.
- [x] **Ship an SELinux policy module** — Type enforcement policy granting `xdm_t`/`login_t` access to `v4l_device_t` and `uinput_device_t`.
- [x] **Create an RPM spec file** — Full spec with SELinux subpackage, GTK subpackage, proper deps and scriptlets.
- [x] **Python 3.13/3.14 compatibility** — Fixed deprecated `datetime.utcnow()`, invalid escape sequences, deprecated `SourceFileLoader.load_module()`.

### Code Quality / Modernization
- [x] **Add proper Python packaging** — `pyproject.toml` with metadata, deps, and Python version constraint. Meson remains the build system.
- [x] **Fix security issues (model permissions)** — Face model files now written with 0600, models dir with 0700.
- [x] **Fix PAM return code (#661)** — `howdy_error` returns `PAM_IGNORE` instead of `PAM_AUTH_ERR`; `pam_sm_setcred` returns `PAM_SUCCESS`.
- [x] **Clean up build system** — Fixed `python_path` default, added Python >= 3.12 check, removed dead dlib fetch code.
- [x] **Safe upgrade path from v2.x (#1091)** — `howdy-upgrade-check` script detects/fixes stale pam_python.so entries, old dlib files, dead symlinks. Runs in RPM %pretrans.

### Nice-to-Have / Future
- [ ] **Intel IPU6 / libcamera support** — Many modern Intel laptops use MIPI cameras that don't work with V4L2/OpenCV.
- [ ] **IR emitter management** — Integrate or detect `linux-enable-ir-emitter`.
- [ ] **Triage upstream issues** — Cherry-pick useful fixes from the 320 open issues.

---

## Python 3.12+ Modernization (2026-04-01)

Minimum Python version set to **3.12** (covers Ubuntu 24.04 LTS, Fedora 41+, Arch).

### 1. Replaced deprecated `SourceFileLoader.load_module()`
**File:** `howdy/src/rubberstamps/__init__.py`
- `SourceFileLoader.load_module()` has been deprecated since Python 3.4 and is slated for removal
- Replaced with modern `importlib.util.spec_from_file_location()` / `module_from_spec()` / `exec_module()` API

### 2. Fixed invalid regex escape sequence
**File:** `howdy/src/rubberstamps/__init__.py`
- Regex pattern string contained `\w` and `\.` in a non-raw string
- Python 3.12+ treats invalid escape sequences as errors
- Added `r""` raw string prefix

### 3. Replaced `_thread` with `threading` module
**File:** `howdy/src/compare.py`
- `_thread` is a low-level internal module not intended for direct use
- Replaced `thread.allocate_lock()` with `threading.Lock()`
- Replaced `thread.start_new_thread()` with `threading.Thread().start()`

### 4. Converted `%` string formatting to `.format()`
**Files:** `howdy/src/compare.py`, `howdy/src/cli/add.py`, `howdy/src/cli/test.py`
- Replaced all old-style `%` formatting with `.format()` calls
- Used `.format()` instead of f-strings for `_()` i18n-wrapped strings so gettext can still extract translation literals

### 5. Fixed `python_path` default
**File:** `meson.options`
- Changed default from `/usr/bin/python` (ambiguous, may not exist or point to Python 2) to `/usr/bin/python3`

### 6. Added Python version check in build system
**File:** `howdy/src/meson.build`
- Added build-time check that errors out if Python < 3.12 is detected

---

## dlib → OpenCV DNN Migration (2026-04-01)

Replaced dlib (C++ library requiring compilation from source, not packaged for Fedora) with OpenCV's built-in DNN face detection and recognition. **Zero new dependencies** — OpenCV was already required.

### Why this matters
- dlib is not available as a package in Fedora repos (`python3-dlib` doesn't exist)
- Building dlib from source requires CMake, C++ compiler, BLAS, and takes 10+ minutes
- dlib breaks frequently with new Python versions
- OpenCV DNN is faster (YuNet: ~1.6ms vs dlib HOG: 5-20ms for detection)
- Equal or better accuracy (SFace: 99.40% vs dlib: 99.38% on LFW)

### Models
| Old (dlib) | New (OpenCV DNN) | Size |
|---|---|---|
| `shape_predictor_5_face_landmarks.dat` | Built into YuNet detection output | — |
| `mmod_human_face_detector.dat` | `face_detection_yunet_2023mar.onnx` | 227 KB |
| `dlib_face_recognition_resnet_model_v1.dat` | `face_recognition_sface_2021dec.onnx` | 37 MB |

### API changes
| Operation | Old (dlib) | New (OpenCV DNN) |
|---|---|---|
| Face detection | `dlib.get_frontal_face_detector()` / `dlib.cnn_face_detection_model_v1()` | `cv2.FaceDetectorYN.create()` |
| Landmark prediction | `dlib.shape_predictor()` — separate call | Included in YuNet detection output (5 landmarks per face) |
| Face encoding | `dlib.face_recognition_model_v1().compute_face_descriptor()` | `cv2.FaceRecognizerSF.feature(alignCrop(frame, face))` |
| Face matching | `np.linalg.norm()` L2 distance, threshold 0.35 | `cv2.FaceRecognizerSF.match()` cosine similarity, threshold 0.40 |

### Config changes
- **Removed:** `use_cnn` — YuNet is CNN-based by default (no separate HOG/CNN toggle needed)
- **Changed:** `certainty` — now cosine similarity (0.0-1.0, higher = more strict). Default 0.40 (secure). Old scale was 1-10 divided by 10 as L2 distance.
- **Added:** `detection_threshold` — minimum YuNet detection confidence (default 0.9)

### Files changed
| File | Change |
|---|---|
| `howdy/src/compare.py` | Complete rewrite — dlib → cv2.FaceDetectorYN + cv2.FaceRecognizerSF |
| `howdy/src/cli/add.py` | Complete rewrite — dlib → OpenCV DNN for face enrollment |
| `howdy/src/cli/test.py` | Complete rewrite — dlib → OpenCV DNN for test preview |
| `howdy/src/rubberstamps/nod.py` | Updated to use YuNet landmark output format instead of dlib pose_predictor |
| `howdy/src/rubberstamps/__init__.py` | Removed `pose_predictor` from opencv dict passed to stamps |
| `howdy/src/paths_factory.py` | Replaced dlib model paths with YuNet/SFace ONNX paths |
| `howdy/src/paths.py.in` | `dlib_data_dir` → `model_data_dir` |
| `howdy/src/config.ini` | Updated config for new engine, removed `use_cnn`, added `detection_threshold` |
| `howdy/src/model-data/install.sh` | New download script for YuNet + SFace ONNX models (with SHA256 verification) |
| `howdy-gtk/src/paths.py.in` | `dlib_data_dir` → `model_data_dir` |
| `howdy-gtk/src/paths_factory.py` | `dlib_data_dir_path()` → `model_data_dir_path()` |
| `howdy-gtk/src/onboarding.py` | Updated model file checks and download paths |
| `meson.build` | `dlibdatadir` → `modeldatadir`, version bumped to 4.0.0 |
| `meson.options` | `dlib_data_dir` → `model_data_dir` |
| `howdy/src/meson.build` | Updated model data install paths, removed old dlib fetch code |

### Breaking changes
- **Face models must be re-enrolled** — SFace embeddings are incompatible with dlib embeddings. Users must run `howdy add` after upgrading.
- **Config format changed** — `certainty` value scale is different (cosine similarity vs L2 distance). Old config values will not work correctly.
- **`use_cnn` removed** — YuNet is always CNN-based. The config option is ignored.

### Security improvements
- Download script verifies SHA256 checksums on model files
- Default certainty threshold (0.40) is conservative — prioritizes security
- Detection threshold (0.9) reduces false detections

---

## PAM Module Fixes (2026-04-02)

### 1. Fixed Python path discovery in PAM context
**Files:** `howdy/src/pam/main.cc`, `howdy/src/pam/paths.hh.in`, `howdy/src/meson.build`

PAM modules run with a heavily stripped environment. The C++ PAM module was passing `nullptr` as the environment to `posix_spawnp`, giving the Python subprocess an empty environment — no `PATH`, no `PYTHONPATH`, nothing. Python couldn't find howdy's own modules or system site-packages.

**Fix:** The PAM module now constructs a minimal environment at runtime:
- `PYTHONPATH` — set to the compiled-in howdy Python sources install directory (e.g. `/usr/lib64/howdy`), so Python can find `compare.py`'s sibling modules (`paths_factory`, `snapshot`, `recorders`, etc.)
- `PATH` — set to `/usr/local/bin:/usr/bin:/bin` so subprocess calls (e.g. `howdy-gtk`) can find executables

A new `PYTHON_SOURCES_DIR` constant is compiled into `paths.hh` from `pysourcesinstalldir` in the meson build.

### 2. Fixed PAM module install path
**File:** `howdy/src/pam/meson.build`

The PAM module was installing to `<prefix>/<libdir>/security/` which with meson's default prefix gives `/usr/local/lib64/security/`. PAM only looks in the system directory (`/usr/lib64/security/` on Fedora, `/usr/lib/x86_64-linux-gnu/security/` on Debian).

**Fix:** Three-tier detection:
1. Explicit `pam_dir` option — if set, use it (no change)
2. pkg-config — query `pam.pc` for `moduledir` variable (works on Debian/Ubuntu where `libpam0g-dev` ships the file)
3. Fallback — `/usr/<libdir>/security/`, using the system libdir but hardcoding `/usr` instead of the meson prefix, since PAM modules must always go in the system security directory

---

## Fedora Integration + Security (2026-04-02)

### 1. Authselect support
**File:** `fedora/howdy-authselect`

Bash script with `enable`/`disable`/`status` subcommands:
- `enable` — Gets the current authselect profile and features, creates a custom profile (`custom/boy-howdy`) based on it, injects `auth sufficient pam_howdy.so` before `pam_unix.so` in system-auth/password-auth/fingerprint-auth, activates with all existing features. Saves original profile for revert.
- `disable` — Reverts to the saved original profile and features, removes the custom profile directory.
- `status` — Shows whether the boy-howdy profile is active and if pam_howdy.so is present.

Works with any base profile (local, sssd, winbind) and preserves all existing features (with-fingerprint, with-faillock, etc.).

### 2. SELinux policy module
**Files:** `fedora/boy-howdy.te`, `fedora/boy-howdy.fc`, `fedora/boy-howdy.if`, `fedora/Makefile.selinux`

Type enforcement policy allowing:
- `xdm_t` (GDM/SDDM) → `v4l_device_t` (camera): `open read write ioctl getattr`
- `login_t` (console) → `v4l_device_t` (camera): same
- `xdm_t` → `uinput_device_t` (enter workaround): same
- `login_t` → `uinput_device_t` (enter workaround): same

No custom file contexts needed — howdy files use standard system types (`lib_t`, `etc_t`).

Built with `selinux-policy-devel` Makefile or directly via `checkmodule`/`semodule_package`. Installed via `semodule -i`.

### 3. RPM spec file
**File:** `fedora/boy-howdy.spec`

Three packages:
- `boy-howdy` — Core: PAM module, Python sources, CLI, config, model download script, authselect script
- `boy-howdy-selinux` — SELinux policy module (noarch), auto-installed/removed via scriptlets
- `boy-howdy-gtk` — Optional GTK auth overlay UI

Key meson options set in the spec:
- `-Dpam_dir=%{_libdir}/security` — explicit for safety
- `-Dpy_sources_dir=%{_libdir}` — installs Python to `/usr/lib64/howdy/`
- `-Dwith_polkit=true` — enables the polkit policy for howdy-gtk

### 4. Face model file permissions (security fix)
**File:** `howdy/src/cli/add.py`

- Model files now written with `os.open(..., 0o600)` instead of default `open()` (which used umask, typically 644)
- Models directory created with `os.makedirs(..., mode=0o700)`
- Face encodings are biometric data and should only be readable by root

### 5. PAM return code fix (#661)
**File:** `howdy/src/pam/main.cc`

Two changes to PAM return codes:

1. **`howdy_error` → `PAM_IGNORE` instead of `PAM_AUTH_ERR`**
   - When face auth fails (timeout, dark image, etc.), the module now returns `PAM_IGNORE` ("pretend I wasn't here") instead of `PAM_AUTH_ERR`
   - With `sufficient` config: both codes continue the stack, so no behavior change
   - With `required`/`requisite` config: `PAM_IGNORE` won't block login, while `PAM_AUTH_ERR` would
   - Face auth failure should never prevent password authentication

2. **`pam_sm_setcred` → `PAM_SUCCESS` instead of `PAM_IGNORE`**
   - Standard practice for PAM modules that don't manage credentials
   - Some applications expect `setcred` to return `PAM_SUCCESS` after a successful `authenticate`
   - `PAM_IGNORE` from `setcred` could cause inconsistent behavior

### 6. Safe upgrade path from v2.x (#1091)
**File:** `fedora/howdy-upgrade-check`

Standalone script (also called from RPM `%pretrans`) that detects and cleans up stale howdy v2.x artifacts:

1. **Stale PAM entries** — Scans `/etc/pam.d/` and authselect configs for `pam_python.so.*howdy` lines. Comments them out with `--fix` rather than deleting (reversible).
2. **Old installation directory** — Removes `/lib/security/howdy/` and variants from v2.x manual installs.
3. **Old dlib model files** — Removes `shape_predictor_*.dat`, `mmod_human_face_detector.dat`, etc.
4. **Stale face models** — Detects user models with dlib-format encodings (incompatible with SFace) and warns about re-enrollment.
5. **Dead symlinks** — Removes `/usr/local/bin/howdy` if it points to the old v2.x location.

Dry run by default; `--fix` flag applies changes. Wired into RPM spec as `%pretrans` lua scriptlet.

### 7. Python packaging metadata
**File:** `pyproject.toml`

Declares project metadata, Python version constraint (`>=3.12`), and runtime dependencies (`numpy`, `opencv-python>=4.5.4`). Optional GTK dependencies in `[project.optional-dependencies]`.

Meson remains the build system — this file is for tooling (dependabot, IDE support, etc.), not pip installation.
