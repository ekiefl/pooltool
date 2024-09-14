# Publishing a new pooltool release

These are instructions for how to make new pip-installable pooltool versions on PyPi.

## 1. House keeping

- Update `logo.png` if its not a sub-version (rename logo_small.png to previous version (e.g. logo_v0p1.png) open Blender file, update textures, render at top, save as logo.png). Then make a copy of logo.png that is 640 x 360 called logo_small.png.

## 2. Create a git tag

Versioning is handled dynamically based on git tags. So to make a new release, you first make a new git tag. Make sure you're on the main branch with no uncommitted changes.

```bash
RELEASE_VERSION=0.1.0
git tag -a v${RELEASE_VERSION} -m "Release version ${RELEASE_VERSION}"
git push origin v${RELEASE_VERSION}
```

If you need to delete a tag you've created (or even pushed), use:

```bash
git tag -d <tagname> # Locally delete
git push origin :refs/tags/<tagname> # If you pushed it
```

## 3. Build the distribution

```bash
make build
```

You should see something like this:

```bash
Building pooltool-billiards (0.1.0)
  - Building sdist
  - Built pooltool_billiards-0.1.0.tar.gz
  - Building wheel
  - Built pooltool_billiards-0.1.0-py3-none-any.whl
```

If there are additional metadata attached to the version (_e.g._ `0.3.4a2.dev1+eb17e9c.dirty`), then your tag isn't up to date.

Open the tar found in `dist/`. If you've added any non-Python files to the package since the last release, make sure they are either present or absent from the package (depending on the desired outcome).

Also open `pooltool/__init__.py` and make sure the `__version__` variable was populated with something other than the placeholder, `0.0.0`.

## 4. Publish to the **test** PyPI repository

- Populate your `.env` using `.env.copy` as a template.

- Run `make build-and-test-publish`. If this fails due to timing out (slow upload speed that gets cut short), run `make build` and then skip ahead to trying out the installation locally.

- Create a fresh python environment to test the installation

```
source ~/.bashrc
conda deactivate
conda env remove --name asdf
conda create -y -n asdf python=3.12.4
PYTHONPATH=""
conda activate asdf
```

- Install:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple --extra-index-url https://archive.panda3d.org/ pooltool-billiards==${RELEASE_VERSION} --force-reinstall
```

If test PyPi is timing out, you can instead consider testing the installation with 

```bash
pip install dist/pooltool_billiards-${RELEASE_VERSION}.tar.gz --force-reinstall --extra-index-url https://archive.panda3d.org/
```

- Test it out. Make sure `which run-pooltool` leads to the asdf environment: `/Users/evan/anaconda3/envs/asdf/bin/run_pooltool`. Then see if the interactive interface can be loaded: `run-pooltool`. Additionally, check the path of `cd ~; python -c "import pooltool; print(pooltool.__file__)"; cd -`. It should be in site-packages of asdf environment.

## 5. Publish to the **real** PyPI repository

- Go back to the dev environment.

- Run `make build-and-publish`

- Create a new python environment

```
source ~/.bashrc
conda deactivate
conda env remove --name asdf
conda create -y -n asdf python=3.12.4
PYTHONPATH=""
conda activate asdf
cd ~
```

- Test installation: `pip install pooltool-billiards==${RELEASE_VERSION}` (you may need to wait for version to be live)

## 6. Make a release

- Make a release on github from the tag. Upload the `.whl` and `.tar.gz` found in `dist/`.
