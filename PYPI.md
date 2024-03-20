These are instructions for myself on how to make new pip-installable pooltool versions on PyPi.
Information comes from
https://betterscientificsoftware.github.io/python-for-hpc/tutorials/python-pypi-packaging/#creating-a-python-package

0. Little stuff: check that `requirements.txt` matches install_requires in `setup.py`. Make sure `pooltool.__init__.py` has version X.X.X. If you added data files, make sure they are included in the `MANIFEST.in`. Update `logo.png` if its not a sub-version (rename logo_small.png to previous version (e.g. logo_v0p1.png) open Blender file, update textures, render at top, save as logo.png). Then make a copy of logo.png that is 640 x 360 called logo_small.png.

1. Change the version in `setup.py`. Rather than X.X.X, use X.X.X.dev0. This
   version is temporary until I'm positive that things are working properly.

2. In my development environment, run `python setup.py check`, then `python setup.py sdist`. This creates a tar.gz source distribution in the directory `dist/`

3. Time to upload this distribution to test.pypi. Run `twine upload --repository-url https://test.pypi.org/legacy/ dist/pooltool-billiards-X.X.X.dev0.tar.gz`. Username is __token__ and password is the API token in your keychain under "TestPyPi pooltool".

4. Create a fresh python environment to test the installation

```
source ~/.bashrc
conda deactivate
conda env remove --name asdf
conda create -y -n asdf python=3.8.10
PYTHONPATH=""
conda activate asdf
```

5. Test the installation:
   `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple pooltool-billiards==X.X.X.dev0 --force-reinstall`.

6. Make sure `cd ~; which run_pooltool` leads to the asdf environment: `/Users/evan/anaconda3/envs/asdf/bin/run_pooltool`
   Then see if it works: `run_pooltool`. Additionally, check path of `python -c "import pooltool; print(pooltool.__file__)"`. It should be in site-packages of asdf environment.

7. Change version to X.X.X in `setup.py`, then **back in the development environment** create dist: `python setup.py sdist`

8. Upload to pypi `twine upload dist/pooltool-billiards-X.X.X.tar.gz`. Username is __token__ and password is the API token in your keychain under "PyPi pooltool".

9. Create a new python environment

```
source ~/.bashrc
conda deactivate
conda env remove --name asdf
conda create -y -n asdf python=3.8.10
PYTHONPATH=""
conda activate asdf
cd ~
```

10. Test installation: `pip install pooltool-billiards==X.X.X` (you may need to wait for version to be live)

11. Make a release on github. Run `python setup.py sdist bdist_wheel` **back in the development environment** and upload the `.whl` and `.tar.gz` found in `dist/`
