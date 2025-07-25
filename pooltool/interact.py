"""An endpoint for classes that enable interaction"""

from pooltool.ani.animate import Game, ShotViewer

_shot_viewer: ShotViewer | None = None


def show(*args, **kwargs):
    """Opens the interactive interface for one or more shots.

    Important:
        For instructions on how to use the interactive interface, see :doc:`The
        Interface </getting_started/interface>`.

    Args:
        shot_or_shots:
            The shot or collection of shots to visualize. This can be a single
            :class:`pooltool.system.System` object or a
            :class:`pooltool.system.MultiSystem` object containing
            multiple systems.

            Note:
                If a multisystem is passed, the systems can be scrolled through by
                pressing *n* (next) and *p* (previous). When using ``pt.show()``,
                press *Enter* to toggle parallel visualization mode where all systems
                play simultaneously with reduced opacity except the active one. In
                parallel mode, use *n* and *p* to change which system has full opacity.
                Note that parallel visualization is only available in ``pt.show()``
                and not when playing the game through ``run-pooltool``.
        title:
            The title to display in the visualization. Defaults to an empty string.
        camera_state:
            The initial camera state that the visualization is rendered with.

    Example:

        This example visualizes a single shot.

        >>> import pooltool as pt
        >>> system = pt.System.example()

        Make sure the shot is simulated, otherwise it will make for a boring
        visualization:

        >>> pt.simulate(system, inplace=True)

        Now visualize the shot:

        >>> pt.show(system)

        (Press *escape* to exit the interface and continue script execution)
    """
    global _shot_viewer

    if _shot_viewer is None:
        _shot_viewer = ShotViewer()

    _shot_viewer.show(*args, **kwargs)


__all__ = [
    "Game",
    "show",
]
