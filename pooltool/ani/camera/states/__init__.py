from pathlib import Path

from pooltool.ani.camera._camera import CameraState

camera_states = {
    path.stem: CameraState.from_json(path)
    for path in Path(__file__).parent.glob("*.json")
}
