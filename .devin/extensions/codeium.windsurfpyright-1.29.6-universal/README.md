<h1>Devin Pyright </h1>

Devin Pyright provides language server features, including type-checking and semantic highlighting, for Python in Devin. It is a fork of basedpyright, which is a fork of pyright.

This extension is only supported within Devin.

Modifications to basedpyright include:

-   Disabling the refactoring code during file renames.
-   Reducing the default strictness of the type checking to better match PyLance.
-   Disabling inlay hints by default to match PyLance, and because they interact with autocomplete.

Devin Pyright uses config settings from pyrightconfig.json, or [tool.windsurfpyright] in your pyproject.toml.

While we recommend Devin Pyright, [basedpyright](https://open-vsx.org/extension/detachhead/basedpyright) or [pyright](https://open-vsx.org/extension/ms-pyright/pyright) are also functional alternatives.

Our thanks go to the original authors for pyright and basedpyright. The documentation for basedpyright is included below.

---

<h1><img src="https://docs.basedpyright.com/latest/img/readme_logo.png"> basedpyright</h1>

<!-- --8<-- [start:header] -->

[![pypi](https://img.shields.io/pypi/dm/basedpyright?logo=pypi&color=3775A9)](https://pypi.org/project/basedpyright/)
[![visual studio marketplace](https://img.shields.io/visual-studio-marketplace/d/detachhead.basedpyright?logo=visualstudiocode&color=007ACC)](https://marketplace.visualstudio.com/items?itemName=detachhead.basedpyright)
[![open VSX](https://img.shields.io/open-vsx/dt/detachhead/basedpyright?logo=vscodium&color=2F80ED)](https://open-vsx.org/extension/detachhead/basedpyright)
[![sublime text](https://img.shields.io/packagecontrol/dt/LSP-basedpyright?logo=sublimetext&color=FF9800)](https://packagecontrol.io/packages/LSP-basedpyright)
[![homebrew](https://img.shields.io/homebrew/installs/dm/basedpyright?logo=homebrew&color=fbb040)](https://formulae.brew.sh/formula/basedpyright)
[![Discord](https://img.shields.io/discord/948915247073349673?logo=discord&color=5865F2)](https://discord.gg/7y9upqPrk2)
[![basedpyright - checked](https://img.shields.io/badge/basedpyright-checked-42b983)](https://docs.basedpyright.com)

Basedpyright is a fork of [pyright](https://github.com/microsoft/pyright) with various type checking improvements, pylance features and more.

<!-- --8<-- [end:header] -->

See [the documentation](https://detachhead.github.io/basedpyright) for information about why this fork exists, and a comprehensive list of features and improvements we've made to pyright.
