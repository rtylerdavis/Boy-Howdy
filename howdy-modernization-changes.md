# Boy-Howdy Modernization Changes

Tracking all changes made to modernize the fork from boltgolt/howdy.

---

## Modernization Todo List

### Critical
- [x] **Kill Python 2 / pam_python dependency** — 3.0.0 beta on master already uses C++ PAM module. Verified no Python 2 remnants remain.
- [x] **Solve the dlib problem** — Replaced dlib entirely with OpenCV DNN (YuNet + SFace). Zero new dependencies.
- [ ] **Fix Python path discovery in PAM context** — PAM strips env vars; `compare.py` can't find Python modules. Need to set `PYTHONPATH` from the C++ PAM module or compile paths in at build time.
- [ ] **Fix PAM module install path** — Builds to `/usr/local/lib64/security/` but PAM looks in `/usr/lib64/security/`. Needs meson option or auto-detection.

### Fedora-Specific
- [ ] **Add authselect support** — Ship a custom authselect profile or installer that creates one.
- [ ] **Ship an SELinux policy module** — Camera access blocked by SELinux at GDM/SDDM login. Need a proper `.te` policy file.
- [ ] **Create an RPM spec file** — No official spec exists. Proper spec with deps, paths, and SELinux policy.
- [x] **Python 3.13/3.14 compatibility** — Fixed deprecated `datetime.utcnow()`, invalid escape sequences, deprecated `SourceFileLoader.load_module()`.

### Code Quality / Modernization
- [ ] **Add proper Python packaging** — No `pyproject.toml` or `setup.cfg`. Python code is raw files copied by meson.
- [ ] **Fix security issues** — Face model file permissions (644 → 600), PAM module should return `PAM_IGNORE` not `PAM_SUCCESS` (#661).
- [x] **Clean up build system** — Fixed `python_path` default, added Python >= 3.12 check, removed dead dlib fetch code.
- [ ] **Safe upgrade path from v2.x** — Stale PAM entries referencing old `pam_python.so` can lock users out (#1091).

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
