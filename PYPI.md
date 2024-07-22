# Publishing pooltool

These are instructions for how to make new pip-installable pooltool versions on PyPi.

## 1. House keeping

- Make sure `pooltool.__init__.py` has version X.X.X.

- If you added data files since the last release, make sure they have been added to the `pyproject.toml.

- Update `logo.png` if its not a sub-version (rename logo_small.png to previous version (e.g. logo_v0p1.png) open Blender file, update textures, render at top, save as logo.png). Then make a copy of logo.png that is 640 x 360 called logo_small.png.

- Change the version in `pyproject.toml`. Rather than X.X.X, use X.X.X.dev0. This version is temporary until you're positive that things are working properly.

## 2. Build the distribution

```bash
poetry build
```

You can find it at `dist/pooltool-0.3.3+dev.tar.gz` (along with the wheel (`.whl`))

## 3. Publish to the **test** PyPI repository

- Populate your `.env` using `.env.copy` as a template.

- Run `make test-publish`. If this fails due to timing out (slow upload speed that gets cut short), skip ahead to trying out the installation locally.

- Create a fresh python environment to test the installation

```
source ~/.bashrc
conda deactivate
conda env remove --name asdf
conda create -y -n asdf python=3.8.10
PYTHONPATH=""
conda activate asdf
```

- Install:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple pooltool-billiards==X.X.X.dev0 --force-reinstall
```

If test PyPi is timing out, you can instead consider testing the installation with 

```bash
pip install dist/pooltool-billiards-X.X.X.dev0.tar.gz --force-reinstall
```

- Test it out. Make sure `which run-pooltool` leads to the asdf environment: `/Users/evan/anaconda3/envs/asdf/bin/run_pooltool`. Then see if it works: `run-pooltool`. Additionally, check the path of `cd ~; python -c "import pooltool; print(pooltool.__file__)"; cd -`. It should be in site-packages of asdf environment.

## 4. Rebuild with correct version tag

- Change version to X.X.X in `pyproject.toml`, then **back in the development environment** create the dist:

```bash
poetry build
```

## 5. Publish to the **real** PyPI repository

- Run `make publish`

- Create a new python environment

```
source ~/.bashrc
conda deactivate
conda env remove --name asdf
conda create -y -n asdf python=3.8.10
PYTHONPATH=""
conda activate asdf
cd ~
```

- Test installation: `pip install pooltool-billiards==X.X.X` (you may need to wait for version to be live)

- Push changes to main.

## 6. Make a release

- Make a release on github. Run `python setup.py sdist bdist_wheel` **back in the development environment** and upload the `.whl` and `.tar.gz` found in `dist/`

## 7. Update version tag with +dev

- **After** the release is made, in `pooltool/__init__.py` set the version to X.X.X+dev. Commit and push.
