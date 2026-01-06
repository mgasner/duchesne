---
title: ty
---

# ty

Strawberry comes with support for [ty](https://docs.astral.sh/ty/), an extremely
fast Python type checker written in Rust by Astral (the makers of uv and Ruff).

This guide will explain how to configure ty to work with Strawberry.

## Install ty

The first thing we need to do is to install [ty](https://docs.astral.sh/ty/).
You can install it using pip, uv, or other package managers:

```bash
# Using uv (recommended)
uv tool install ty

# Using pip
pip install ty

# Using pipx
pipx install ty
```

Once the tool is installed, we need to configure it. To do so we need to create
a `ty.toml` file in the root of our project or add a `[tool.ty]` section to your
`pyproject.toml`:

```toml
# ty.toml
[environment]
python-version = "3.10"
```

Or in `pyproject.toml`:

```toml
[tool.ty]
[tool.ty.environment]
python-version = "3.10"
```

Once you have configured the settings, you can run `ty check` and you should be
getting type checking errors.

```bash
ty check .
```
