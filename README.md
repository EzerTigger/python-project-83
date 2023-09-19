### Hexlet tests and linter status:
[![Actions Status](https://github.com/EzerTigger/python-project-83/workflows/hexlet-check/badge.svg)](https://github.com/EzerTigger/python-project-83/actions)

[site here](https://page-analyzer-0bho.onrender.com)

## Getting Started

#### Clone the current repository via command:
```git clone https://github.com/EzerTigger/python-project-83```

***

## Requirements
* python >= 3.10
* Poetry >= 1.5.1
***

## Required packages
* Flask ^2.3.2
* Python-dotenv  ^1.0.1
* to avoid psycopg problems with different OS, install psycopg2-binary ^2.9.4
* Every other packages are shown inside pyproject.toml

***

#### Check your pip version with the following command:
```python -m pip --version```

#### Make sure that pip is always up-to-date. If not, use the following:
```python -m pip install --upgrade pip```

#### Next install poetry on your OS. (the link is below)
[Poetry installation](https://python-poetry.org/docs/)
##### don't forget to init poetry packages with command ```poetry init```

### We will be also working with postgreSQL, so make sure that you have installed it on your OS

*** 

## Makefile 
#### For every project should be configured a Makefile to initiate the project without requiring manual commands
#### Current project starts after typing ```make setup```
#### Inside our ```make setup``` we have 2 commands hidden:
* ``` make install```, which makes poetry install packages from pyproject.toml
* ```make lock```, which locks poetry packages inside poetry.lock
***

#### After configuration, you should use ```make dev``` to start your flask app