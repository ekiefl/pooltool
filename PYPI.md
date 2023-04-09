These are instructions for myself on how to make new pip-installable pooltool versions on PyPi.
Information comes from
https://betterscientificsoftware.github.io/python-for-hpc/tutorials/python-pypi-packaging/#creating-a-python-package

0. Little stuff: check that `requirements.txt` matches install_requires in `setup.py`. Make sure `pooltool.__init__.py` has version X.X.X. If you added data files, make sure they are included in the `MANIFEST.in`. Update `logo.png` if its not a sub-version (rename logo.png to previous version (e.g. v0p1.png) open Blender file, update textures, render at top, save as logo.png)

1. Change the version in `setup.py`. Rather than X.X.X, use X.X.X.dev0. This
   version is temporary until I'm positive that things are working properly.

2. In my development environment, run `python setup.py check`, then `python setup.py sdist`. This creates a tar.gz source distribution in the directory `dist/`

3. Time to upload this distribution to test.pypi. Run `twine upload --repository-url https://test.pypi.org/legacy/ dist/pooltool-billiards-X.X.X.dev0.tar.gz`. Username is ekiefl.

4. Create a fresh python environment to test the installation

```
conda deactivate
conda env remove --name asdf
conda create -y -n asdf python=3.8.10
conda activate asdf
```

5. Test the installation:
   `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple pooltool-billiards==X.X.X.dev0 --force-reinstall`.

6. Make sure `cd ~; which run_pooltool` leads to the asdf environment: `/Users/evan/anaconda3/envs/asdf/bin/run_pooltool`
   Then see if it works: `run_pooltool`

7. Change version to X.X.X in `setup.py`, then **back in the development environment** create dist: `python setup.py sdist`

8. Upload to pypi `twine upload dist/pooltool-billiards-X.X.tar.gz`

9. Create a new python environment

```
conda deactivate
conda env remove --name asdf
conda create -y -n asdf python=3.8.10
conda activate asdf
```

10. Test installation: `pip install pooltool-billiards==X.X.X` (you may need to wait for version to be live)

