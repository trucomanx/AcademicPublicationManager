# {PROGRAM_NAME}

{SUMMARY}

## Testar program

```bash
cd src
python3 -m {MODULE_NAME}.program
```

## Upload to PYPI

```bash
pip install --upgrade pkginfo twine packaging

cd src
python -m build
twine upload dist/*
```

## Install from PYPI

The homepage in pipy is https://pypi.org/project/{PROGRAM_NAME}/

```bash
pip install --upgrade {PROGRAM_NAME}
```

Using:

```bash
{PROGRAM_NAME}
```

## Install from source
Installing `{PROGRAM_NAME}` program

```bash
git clone https://github.com/trucomanx/{REPOSITORY_NAME}.git
cd {REPOSITORY_NAME}
pip install -r requirements.txt
cd src
python3 setup.py sdist
pip install dist/{MODULE_NAME}-*.tar.gz
```
Using:

```bash
{PROGRAM_NAME}
```

## Uninstall

```bash
pip uninstall {MODULE_NAME}
```
