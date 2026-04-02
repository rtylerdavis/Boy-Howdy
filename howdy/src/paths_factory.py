from pathlib import PurePath
import paths

models = [
    "face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx",
]


def model_data_dir_path() -> str:
    return str(paths.model_data_dir)


def face_detector_path() -> str:
    return str(paths.model_data_dir / models[0])


def face_recognizer_path() -> str:
    return str(paths.model_data_dir / models[1])


def user_model_path(user: str) -> str:
    return str(paths.user_models_dir / f"{user}.dat")


def config_file_path() -> str:
    return str(paths.config_dir / "config.ini")


def snapshots_dir_path() -> PurePath:
    return paths.log_path / "snapshots"


def snapshot_path(snapshot: str) -> str:
    return str(snapshots_dir_path() / snapshot)


def user_models_dir_path() -> PurePath:
    return paths.user_models_dir


def logo_path() -> str:
    return str(paths.data_dir / "logo.png")
