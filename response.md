# Response to reviewers (take one)

Thanks again for your reviews @sebastianotronto and @eliotwrobson.

## Common themes

Reading through everything, there are a couple of major themes that I'm picking up on that I want to address at a high level. Those things are versioning, ease of installation, and lack of obvious research application. 

### (1) Versioning

Thanks both of you for pointing out that pooltool doesn't work on Python 3.12. The culprit was the dependency `pprofile`, which is used in a couple of places in `sandbox/`. I think it's a great package, but until https://github.com/vpelletier/pprofile/pull/51 is merged, I'm forced to drop it as a dependency. Any profiling code has been removed, rather than replaced with something else ¯\_(ツ)_/¯.

Package dependencies are now defined by poetry. I did some manual dependency version testing and settled on the following dependencies:

```
[tool.poetry.dependencies]
python = ">=3.9,<3.13"
panda3d = [
  {platform = "darwin", version=">=1.10.13,<1.11"},
  {platform = "linux", version = "1.11.0.dev3444", allow-prereleases = true, source = "panda3d-archive"},
  {platform = "win32", version = "1.11.0.dev3444", allow-prereleases = true, source = "panda3d-archive"},
]
panda3d-gltf = ">=1.2.0"
panda3d-simplepbr = ">=0.12.0"
numpy = ">=1.26.0"  # Lower bound for 3.12 (https://github.com/numpy/numpy/releases/tag/v1.26.0)
numba = ">=0.59.0"  # # Lower bound for 3.12 (https://numba.readthedocs.io/en/latest/user/installing.html#version-support-information)
scipy = ">=1.12.0"  # Required for numba. Lower bound for 3.12 is officially 1.11, but in practice seems to be 1.12 on MacOS
attrs = ">=21.3.0"
cattrs = ">=22.1.0"
msgpack = ">=1.0.0"  # cattrs structuring fails with msgpack<1
msgpack-numpy = ">=0.4.8"
pyyaml = ">=5.2"
click = ">=8.0.0"
Pillow = ">=6.2.0"
h5py = ">=3.10"
```


The lower bounds were determined judiciously, where I tried to pick the oldest versions that were compatible with Python 3.12. This maximizes the target space for dependency resolution so as to maximize the odds that pooltool can share the same python environment with other packages, rather than being relegated as a standalone application. At the same time, I didn't create any dependency branching based on Python version (e.g. if Python <3.9, use Numpy <1.26).

Speaking of which, numpy 1.26.0 is the lower bound for 3.12, but it drops support for 3.8. I've followed suit and dropped support for 3.8, which makes pooltool's Python range >=3.9,<3.13.

To test over this version range, I am now running pooltool's test suite in a matrix of builds, where I test 3.9 and 3.12 for Linux, MacOS, and Windows. With this test matrix now in place, testing for 3.13 and beyond will be easy-peasy.

The development version has correspondingly experienced a _massive_ bump from 3.8.10 to 3.12.4. No more living in the past!

All the changes mentioned can be found in https://github.com/ekiefl/pooltool/pull/124 and https://github.com/ekiefl/pooltool/pull/125.

### (2) Ease of installation

Installation got mentioned quite a few times, which obviously isn't a great sign. For me, the main takeaways from reading your comments were that installation (1) doesn't work on 3.12, (2) perhaps messy/long, and (3) somewhat hard to find.

As mentioned, pooltool now works on 3.12. There also now exists improved signage in the [installation instructions](https://pooltool.readthedocs.io/en/latest/getting_started/install.html#installation) and in the README.md that clarify which Python versions pooltool supports.

The pip installation instructions previously had an unconventional additional step (for Linux and Windows), requiring uninstallation of panda3d 1.10.x and reinstallation of 1.11.x--a prerelease. For context, this is required due to this mouse-related feature being absent in Windows and Linux: https://github.com/panda3d/panda3d/issues/928. Thanks to poetry, this messiness is now handled with the following dependency specification:

```
panda3d = [
  {platform = "darwin", version=">=1.10.13,<1.11"},
  {platform = "linux", version = "1.11.0.dev3444", allow-prereleases = true, source = "panda3d-archive"},
  {platform = "win32", version = "1.11.0.dev3444", allow-prereleases = true, source = "panda3d-archive"},
]
```

The result is now that what used to be this:

```
# Windows and Linux
pip install pooltool-billiards
pip uninstall panda3d -y
pip install --pre --extra-index-url https://archive.panda3d.org/ panda3d

# MacOS
pip install pooltool-billiards
```

Is now this:

```
# Windows and Linux
pip install pooltool-billiards --extra-index-url https://archive.panda3d.org/

# MacOS
pip install pooltool-billiards
```

Once 1.11 is released, the `--extra-index-url` can be removed altogether :)

The developer instructions have also been improved and shortened thanks to this and thanks to poetry.

### (3) Lack of obvious research application

It seems that pooltool has not been presented in a way that exemplifies its use in research. First of all, it would be very helpful to hear what both of you have to say about this, since this wasn't expanded upon in either of your comments, I'm currently just inferring this based on the unchecked box related to whether pooltool satisfies JOSS's definition of having an obvious research application.

So further elaboration would be very helpful. But in the meantime, I would like to bring to light several things that in my opinion justify not only pooltool's potential to be applied in research, but also its already demonstrated application within research.

If you haven't already read it, I think the [JOSS draft paper](https://github.com/ekiefl/pooltool/blob/main/paper.md) does a great job of describing billiards-related research and how billiards simulation plays a central role in this multidisciplinary field. (By the way, there exists a GitHub action that renders this paper, so if you want to view it rendered, you can download the artifact from [this run](https://github.com/ekiefl/pooltool/actions/runs/10233601953)). Anyways, here are some relevant excerpts that help define the research landscape of billiards:

Excerpt 1:

> Billiards, a broad classification for games like pool and snooker, supports a robust, multidisciplinary research and engineering community that investigates topics in physics, game theory, computer vision, robotics, and cue sports analytics. Central to these pursuits is the need for accurate simulation.

Excerpt 2:

> Billiards simulation serves as the foundation for a wide array of research topics that collectively encompass billiards-related studies. Specifically, the application of game theory to develop AI billiards players has led to simulations becoming critical environments for the training of autonomous agents [@Smith2007-jq; @Archibald2010-av; @Fragkiadaki2015-oh; @Archibald2016-sd; @Silva2018-cm; @Chen2019-dk; @Tung2019-zu]. Meanwhile, billiards-playing robot research, which relies on simulations to predict the outcome of potential actions, has progressed significantly in the last 30 years and serves as a benchmark for broader advancements within sports robotics [@Sang1994-jv; @Alian2004-zs; @Greenspan2008-wg; @Nierhoff2012-st; @Mathavan2016-ck; @Bhagat2018-bx]. Billiards simulations also enrich computer vision (CV) capabilities, facilitating precise ball trajectory tracking and enhancing shot reconstruction for player analysis and training (for a review, see @Rodriguez-Lozano2023-hq). Additionally, through augmented reality (AR) and broadcast overlays, simulations have the potential to extend their impact by offering shot prediction and strategy formulation in contexts such as personal training apps and TV broadcasting, creating a more immersive understanding of the game.

Since billiards-related research is niche, I can understand how pooltool's application to research may not be obvious, however I think the "Statement of Need" section explains things by explaining the current shortcomings of the research landscape:

> Unfortunately, the current billiards simulation software landscape reveals a stark contrast between the realistic physics seen in some commercially-produced games (i.e., *Shooterspool* and *VirtualPool4*) and the limited functionality of open-source projects. Commercial products have little, if any, utility in research contexts due to closed source code and a lack of open APIs. Conversely, available open source tools lack realism, usability, and adaptability for generic research needs. The most widely cited simulator in research studies, *FastFiz*[^1], is unpackaged, unmaintained, provides no modularity for custom geometries nor for physical models, offers restrictive 2D visualizations, outputs minimal simulation results with no built-in capabilities for introspection, and was custom built for hosting the Association for the Advancement of Artificial Intelligence (AAAI) Computational Pool Tournament from 2005-2008 [@Archibald2010-av]. Another option, *Billiards*[^2], offers a visually appealing 3D game experience, realistic physics, and supports customization via Lua scripting. However, as a standalone application, it lacks interoperability with commonly used systems and tools in research. Written in Lua, an uncommon language in the scientific community, it has limited appeal in research settings. The lack of Windows support is another drawback. *FooBilliard++*[^3] is a 3D game with realistic physics, yet is not a general purpose billiards simulator, instead focusing on game experience and aesthetics. Other offerings suffer from drawbacks already mentioned.
> 
> The lack of suitable software for billiards simulation in research contexts forces researchers to develop case-specific simulators that meet their research requirements but fall short of serving the broader community as general purpose simulators. This fragments the research collective, renders cross-study results difficult or impossible to compare, and leads to wasted effort spent reinventing the wheel. `pooltool` fills this niche by providing a billiards simulation platform designed for speed, flexibility, and extensibility in mind.

Pooltool was created specifically to fill in this gap in research tools.

But perhaps more importantly, I would like to point out the ways in which pooltool has already been applied in research:

1. Researchers at the Shanghai AI Laboratory have developed pool-playing AI agents using pooltool as the simulation environment. Pooltool has been incorporated as a formal dependency in their popular MCTS-based RL project, [LightZero](https://github.com/opendilab/LightZero). In the words of one of their main developers:

    > The pooltool simulation environment [...] holds great potential as a research benchmark in the field of reinforcement learning. It not only offers scientific value but also encompasses an element of fun. We believe integrating it as a long-term expandable benchmark environment will significantly contribute to the advancement of our research endeavors

    (https://github.com/opendilab/LightZero/discussions/182#discussioncomment-8403618)

2. Researchers at the University of Edinburgh are using pooltool to test the physical reasoning capabilities of large language models (LLMs). The precedent for this research is described by them in [SimLM](https://arxiv.org/abs/2312.14215), and a small teaser of their work using pooltool is described [here](https://seanmemery.github.io/).

3. A student at Oxford University, Alistair White-Horne, created a "Real-Time Pool and Snooker Assistant" using pooltool as the underlying visualization and simulation module. Their thesis can be found [here](https://drive.google.com/file/d/1-pUT87cGoxx8DyMNVIMUoU6f-rVrz4IR/view?usp=sharing)

One thing that could highlight pooltool as a research tool could be turning some analyses in `sandbox/` into proper vignettes that are hosted on the documentation. For example, the contributor @zhaodong-wang added a quantiative verification of the "30-degree rule", a practical rule for determining ball directions post-collision: https://github.com/ekiefl/pooltool/pull/119. This could be a two birds one stone effort, since @eliotwrobson rightfully noticed a lack of vignettes. How does that sound?

Also, perhaps a section could also be added to the README.md called "Projects using pooltool" or something like that, since referencing ways in which pooltool is being used in research environments is both proof of and advertisement for pooltool's applicability to research.

## The checklist

With those three large topics out of the way, here is the checklist section of my response.

Since the checklist is the same for both of you, I'm going to respond to each unchecked box and tag one or both of you depending on whether you had checked the box. In the next sections I'll address each of your individual comments.

> * [ ]  **Vignette(s)** demonstrating major functionality that runs successfully locally.

@eliotwrobson, I haven't done it yet, but I'm going to add a couple of vignettes to the documentation, since currently there is really just the ["Hello World" vignette](https://pooltool.readthedocs.io/en/latest/getting_started/script.html).

> * [ ]  **Examples** for all user-facing functions.

How should we proceed @cmarmo? @sebastianotronto is right that not every user-facing function contains an example. But as they've pointed out, that's because the API is very granular: "_As I noted above, not all functions have examples, but considering how fine-grained the API is I do not think it would be necessary_".

The vast majority of the codebase is exposed in the API, so if we take the term "user-facing functions" to mean those in the API, this requirement would entail an enormous amount of work. In my opinion, the effort would extend beyond what I assume to be the intent of this checkbox: to ensure users have resources to learn by example. For what it's worth, I think the documentation in its current state satisfies this very important requirement (example-based documentation is something I care a lot about).

> * [ ]  **Metadata** including author(s), author e-mail(s), a url, and any other relevant metadata e.g., in a `pyproject.toml` file or elsewhere.

@sebastianotronto, @eliotwrobson: Added in https://github.com/ekiefl/pooltool/pull/124. Can be seen here: https://github.com/ekiefl/pooltool/blob/3b76a311166dba32bd34771fe2ab82b6e3fbf71e/pyproject.toml#L19-L37

> * [ ]  Badges for:
>   
>   * [ ]  Continuous integration and test coverage,
>   * [x]  Docs building (if you have a documentation website),
>   * [ ]  A [repostatus.org](https://www.repostatus.org/) badge,
>   * [ ]  Python versions supported,
>   * [ ]  Current package version (on PyPI / Conda).

@sebastianotronto, @eliotwrobson: Added in https://github.com/ekiefl/pooltool/pull/127. Can be seen here: https://github.com/ekiefl/pooltool

> * [ ]  Package installation instructions

@sebastianotronto, @eliotwrobson: I read you guys loud and clear, the installation instructions definitely need more visibility. But I would prefer that they are not duplicated in both the README.md and the documentation (https://pooltool.readthedocs.io/en/latest/getting_started/install.html). This increases maintenace burden by violating single-source-of-truth. To achieve what I _hope_ is the best of both worlds, I've added an explicit `# Installation` section to the README that links to the installation page in https://github.com/ekiefl/pooltool/pull/127. In particular, this commit: https://github.com/ekiefl/pooltool/commit/79085c3cca317818a4e16718e79a8260e51125c6

> * [ ]  Any additional setup required to use the package (authentication tokens, etc.)

@sebastianotronto, @eliotwrobson: With the adoption of poetry, I hope there now exists no additional setup that needs documenting (I say that with my fingers crossed).

> * [ ]  Descriptive links to all vignettes. If the package is small, there may only be a need for one vignette which could be placed in the README.md file.
>   
>   * [ ]  Brief demonstration of package usage (as it makes sense - links to vignettes could also suffice here if package description is clear)

@sebastianotronto, @eliotwrobson: Once vignettes are added to the documentation, I will link them somewhere in the README.md

> * [ ]  If applicable, how the package compares to other similar packages and/or how it relates to other packages in the scientific ecosystem.

@sebastianotronto, here is a paragraph from the JOSS `paper.md` draft that situates pooltool with respective to similar software:

"_Unfortunately, the current billiards simulation software landscape reveals a stark contrast between the realistic physics seen in some commercially-produced games (i.e., *Shooterspool* and *VirtualPool4*) and the limited functionality of open-source projects. Commercial products have little, if any, utility in research contexts due to closed source code and a lack of open APIs. Conversely, available open source tools lack realism, usability, and adaptability for generic research needs. The most widely cited simulator in research studies, *FastFiz*[^1], is unpackaged, unmaintained, provides no modularity for custom geometries nor for physical models, offers restrictive 2D visualizations, outputs minimal simulation results with no built-in capabilities for introspection, and was custom built for hosting the Association for the Advancement of Artificial Intelligence (AAAI) Computational Pool Tournament from 2005-2008 [@Archibald2010-av]. Another option, *Billiards*[^2], offers a visually appealing 3D game experience, realistic physics, and supports customization via Lua scripting. However, as a standalone application, it lacks interoperability with commonly used systems and tools in research. Written in Lua, an uncommon language in the scientific community, it has limited appeal in research settings. The lack of Windows support is another drawback. *FooBilliard++*[^3] is a 3D game with realistic physics, yet is not a general purpose billiards simulator, instead focusing on game experience and aesthetics. Other offerings suffer from drawbacks already mentioned._"

Do you think I should try and synthesize some of this info into the README, or do you think it's fine to let sleeping dogs rest?

> * [ ]  Citation information

@sebastianotronto: Added in https://github.com/ekiefl/pooltool/pull/127 (https://github.com/ekiefl/pooltool/commit/11e9efd5ad8de371f729c32e52ef5c50bdbf73f7).

> * [ ]  The package is easy to install

@eliotwrobson, I think the instructions (both from source and with pip) are simpler and easier to find now!

> * [ ]  **Packaging guidelines**: The package conforms to the pyOpenSci [packaging guidelines](https://www.pyopensci.org/python-package-guide).
>   A few notable highlights to look at:
>   
>   * [ ]  Package supports modern versions of Python and not [End of life versions](https://endoflife.date/python).
>   * [x]  Code format is standard throughout package and follows PEP 8 guidelines (CI tests for linting pass)

@sebastianotronto, @eliotwrobson: I think things are now much more compliant. PRs https://github.com/ekiefl/pooltool/pull/124, https://github.com/ekiefl/pooltool/pull/125, https://github.com/ekiefl/pooltool/pull/127, https://github.com/ekiefl/pooltool/pull/128, and https://github.com/ekiefl/pooltool/pull/129 have transformed pooltool into a package that, at least from what I can tell, complies with the package guidelines set forth by pyOpenSci. There are (at least) two exceptions though: pooltool has no [developer guide](https://www.pyopensci.org/python-package-guide/documentation/repository-files/development-guide.html) (described as ideal to have) and no conda package (which I am keen to add, but currently is blocked by this grayskull issue: https://github.com/conda/grayskull/issues/463).

> * [ ]  The package has an **obvious research application** according to JOSS's definition in their [submission requirements](http://joss.theoj.org/about#submission_requirements).
> 
> _Note:_ Be sure to check this carefully, as JOSS's submission requirements and scope differ from pyOpenSci's in terms of what types of packages are accepted.
>
> The package contains a `paper.md` matching [JOSS's requirements](http://joss.theoj.org/about#paper_structure) with:
> 
> * [ ]  **A short summary** describing the high-level functionality of the software
> * [ ]  **Authors:** A list of authors with their affiliations
> * [ ]  **A statement of need** clearly stating problems the software is designed to solve and its target audience.
> * [ ]  **References:** With DOIs for all those that have one (e.g. papers, datasets, software).

@sebastianotronto, @eliotwrobson: I gave my spiel about this above in "Common themes".

## Comments by @sebastianotronto

## Comments by @eliotwrobson

## My TODOs

I wanted to get my response out before I had necessarily addressed all the issues, just to keep things out in the open. I think getting it out early could prove especially useful for getting feedback on my plan, just to make sure I'm not barking up the wrong tree. So I've made this to-do list, which I welcome anyone to make suggestions to.

- [ ] Implement a compiling/loading numba cache step so initial shot doesn't take forever
- [ ] Improve the formatting of documentation
- [ ] Investigate whether I can _easily_ change documentation format to single-page
- [ ] Move test modules to tests/
- [ ] Deep dive on @sebastianotronto's idea for event caching
- [ ] Add numba types
- [ ] Add some research-oriented vignettes
