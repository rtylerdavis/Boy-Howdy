# Boy-Howdy

Windows Hello-style face authentication for Linux. Modernized fork of [boltgolt/howdy](https://github.com/boltgolt/howdy).

> **Work in Progress** — Boy-Howdy is an active modernization effort to bring Linux face unlock back to life on current distros. The upstream howdy project has not had a release since September 2020 and is broken on Fedora 41+, among other issues. Boy-Howdy aims to fix that.

## What is this?

Boy-Howdy uses your IR camera and facial recognition to authenticate via PAM — login, lock screen, sudo, su, etc. It replaces password prompts with your face, just like Windows Hello.

Key differences from upstream howdy:
- **No dlib dependency** — uses OpenCV's built-in DNN (YuNet + SFace) instead. No C++ compilation required.
- **Python 3.12+ only** — no Python 2 remnants, no deprecated APIs.
- **Security-first defaults** — conservative match thresholds, SHA256-verified model downloads.
- **Faster detection** — YuNet CNN is 3-10x faster than dlib's HOG detector.

## Status

This is a fresh fork, not a drop-in upgrade from howdy. Expect breaking changes. If you're coming from howdy, treat this as a new install.

### Done
- [x] Replaced dlib with OpenCV DNN (YuNet face detection + SFace face recognition)
- [x] Purged all Python 2 remnants and pam_python dependency
- [x] Fixed deprecated Python APIs (SourceFileLoader, invalid escape sequences, old threading)
- [x] Set minimum Python version to 3.12 with build-time enforcement
- [x] Fixed ambiguous `/usr/bin/python` default to `/usr/bin/python3`
- [x] Updated model download script with SHA256 checksum verification
- [x] Modernized string formatting across codebase

### To Do
- [ ] Fix Python path discovery in PAM context (PAM strips environment variables)
- [ ] Fix PAM module install path mismatch (`/usr/local/lib64/` vs `/usr/lib64/`)
- [ ] Add authselect support for Fedora PAM management
- [ ] Ship SELinux policy module for camera access during auth
- [ ] Create RPM spec file for Fedora packaging
- [ ] Add proper Python packaging (pyproject.toml)
- [ ] Fix face model file permissions (644 → 600)
- [ ] Fix PAM return codes (PAM_IGNORE vs PAM_SUCCESS)
- [ ] Handle stale v2.x PAM entries that can lock users out
- [ ] Intel IPU6 / libcamera camera support
- [ ] IR emitter detection and management

## Credits

Forked from [boltgolt/howdy](https://github.com/boltgolt/howdy) (MIT License). Original project by [boltgolt](https://github.com/boltgolt) and contributors.

Face detection powered by [YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) and face recognition by [SFace](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface), both from the [OpenCV Zoo](https://github.com/opencv/opencv_zoo).
