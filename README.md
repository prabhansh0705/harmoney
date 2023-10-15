# Harmoney
In this project we are migrating the payment API from Node to Python

## Steps to clone this repo
```
git clone https://gitlab.centene.com/mpf/harmoney.git
cd harmoney
git remote add origin https://gitlab.centene.com/mpf/harmoney.git
git checkout develop
```

# Steps to setup virtualenv
```
python3 -m pip install virtualenv --user \
virtualenv env \
source env/bin/activate
```

# Packages used in repo
Django - Python Framework \
graphene-python - Graphene-Python is a library for building GraphQL APIs in Python easily, its main goal is to provide a simple but extendable API
For all list of packages, see requirements.txt


# Project layout
This project comprises of app named payment which has files like views, tests, models etc which wil be used to create the API.

# Useful links
https://graphene-python.org/
https://www.djangoproject.com/
https://gitlab.centene.com/mpf/harmoney