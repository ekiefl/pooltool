# Publishing a new pooltool release

These are instructions for how to make new pip-installable pooltool versions on PyPi.

## 1. House keeping

### Updating the logo

The logo must be updated for all major and minor versions (`MAJOR.MINOR.PATCH`).

* Rename `logo_small.png` to current version (e.g. `logo_v0p1.png`)
* Open `pooltool/logo/logo.blend` in Blender
* Select the relevant spheres in the "Scene Collection". For each, change the texture under "Surface".
* Under the "Render" tab, click "Render Image". Save the image as `logo.png`.
* Make a copy of `logo.png` that is 640 x 360. Call it `logo_small.png`
* To ensure the state of `logo.blend` is preserved, do not save your changes to `logo.blend`. And if you accidentally do, don't commit them.

## 2. Update the changelog

Move all entries from the `[Unreleased]` section in `CHANGELOG.md` into a new version heading with today's date, and add a fresh empty `[Unreleased]` section above it. Update the comparison links at the bottom of the file.

## 3. Update the version

Update the `version` field in `pyproject.toml` to the new release version. Commit the change.

```bash
RELEASE_VERSION=0.1.0
# Edit pyproject.toml: version = "0.1.0"
git add pyproject.toml
git commit -m "Bump version to ${RELEASE_VERSION}"
```

## 4. Create a git tag

Make sure you're on the main branch with no uncommitted changes.

```bash
git tag -a v${RELEASE_VERSION} -m "Release version ${RELEASE_VERSION}"
git push origin v${RELEASE_VERSION}
```

If you need to delete a tag you've created (or even pushed), use:

```bash
git tag -d <tagname> # Locally delete
git push origin :refs/tags/<tagname> # If you pushed it
```

## 5. Build the distribution

```bash
make build
```

Open the tar found in `dist/`. If you've added any non-Python files to the package since the last release, make sure they are either present or absent from the package (depending on the desired outcome).

## 6. Publish to the **test** PyPI repository

- Populate your `.env` using `.env.copy` as a template.

- Run `make build-and-test-publish`. If this fails due to timing out (slow upload speed that gets cut short), run `make build` and then skip ahead to trying out the installation locally.

- Create a fresh python environment to test the installation

```bash
uv venv --python 3.13 /tmp/pooltool-release-test
source /tmp/pooltool-release-test/bin/activate
```

- Install:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple --extra-index-url https://archive.panda3d.org/ pooltool-billiards==${RELEASE_VERSION} --force-reinstall
```

If test PyPi is timing out, you can instead consider testing the installation with

```bash
pip install dist/pooltool_billiards-${RELEASE_VERSION}.tar.gz --force-reinstall --extra-index-url https://archive.panda3d.org/
```

- Test it out. Make sure `which run-pooltool` leads to the test environment. Then see if the interactive interface can be loaded: `run-pooltool`. Additionally, check the path of `cd ~; python -c "import pooltool; print(pooltool.__file__)"; cd -`. It should be in site-packages of the test environment.

## 7. Publish to the **real** PyPI repository

- Go back to the dev environment.

- Run `make build-and-publish`

- Create a fresh test environment

```bash
rm -rf /tmp/pooltool-release-test
uv venv --python 3.13 /tmp/pooltool-release-test
source /tmp/pooltool-release-test/bin/activate
```

- Test installation: `pip install pooltool-billiards==${RELEASE_VERSION}` (you may need to wait for version to be live)

## 8. Make a release

- Make a release on github from the tag. Upload the `.whl` and `.tar.gz` found in `dist/`. For the release notes body, use:

```
See [CHANGELOG.md](https://github.com/ekiefl/pooltool/blob/main/CHANGELOG.md) for details.
```
