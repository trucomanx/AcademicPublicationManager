# academic-publication-manager

Simple academic publication manager GUI.

## Testar program

```bash
cd src
python3 -m academic_publication_manager.program
```

## Upload to PYPI

```bash
pip install --upgrade pkginfo twine packaging

cd src
python -m build
twine upload dist/*
```

## Install from PYPI

The homepage in pipy is https://pypi.org/project/academic-publication-manager/

```bash
pip install --upgrade academic-publication-manager
```

Using:

```bash
academic-publication-manager
```

## Install from source
Installing `academic-publication-manager` program

```bash
git clone https://github.com/trucomanx/AcademicPublicationManager.git
cd AcademicPublicationManager
pip install -r requirements.txt
cd src
python3 setup.py sdist
pip install dist/academic_publication_manager-*.tar.gz
```
Using:

```bash
academic-publication-manager
```

## Uninstall

```bash
pip uninstall academic_publication_manager
```
