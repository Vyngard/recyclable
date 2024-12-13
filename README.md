# recyclable

This is a webapp for managing the beverage containers and images used for ML.  It supports the following activities:
- Scanning the container's barcode, collecting information about that container, and capturing images of that
  container.  All of this data is stored in the DB.
- Importing the existing container data that is currently stored in AWS S3.
- Extracting container data from the DB and creating folders in Sagemaker for use in training the ML models.

See Jira story [OML-85](https://olyns.atlassian.net/browse/OML-85) for the current To Do list.

## How To: Setup for local development

- Install postgres on your laptop
- Create a user and database with:

```
$ psql postgres
postgres=# CREATE ROLE db_user WITH LOGIN PASSWORD 'f4K20jJb#5';
postgres=# ALTER USER db_user WITH LOGIN SUPERUSER;
postgres=# ALTER USER db_user WITH CREATEDB;
postgres=# \q
$ dropdb recyclable
$ createdb recyclable
```
- Configure python virtual environment 
```
$ brew install pyenv
$ brew install pyenv-virtualenv
$ pyenv install 3.11.6
$ pyenv virtualenv 3.11.6 recyclable
```
- Activate virtual environment
```
$ pyenv activate recyclable
(recyclable)$ 
```
- Install requirements
```
# from this directory, do
(recyclable)$ pip install -r requirements.txt
```
- Setup Django
```
# from this directory, do
(recyclable)$ export PYTHONPATH=`pwd`
(recyclable)$ export DJANGO_SETTINGS_MODULE='recyclable_proj.settings'
(recyclable)$ django-admin showmigrations
(recyclable)$ django-admin makemigrations recyclable
(recyclable)$ django-admin migrate
(recyclable)$ django-admin createsuperuser
```

Go into `recyclable_proj/settings.py` and get the `SECRET_KEY` from Tad

- Setup AWS credentials
  - Get AWS credentials for the "management" account (276851901635) from Tad.
  - Ask Tad to give you read and write access to the S3 bucket olyns-recyclable.
  - Either make sure that that profile is the default profile in your ~/.aws/credentials file,
    or set the environment variable AWS_PROFILE to the name of that profile.


## How To: Do basic operations

- Run unit tests with: `$ django-admin test`
- Start the server with: `$ django-admin runserver`

## How To: Run the imaging webapp

- Start the server, then point your browser to `http://127.0.0.1:8000/recyclable`
- You may need to log in with the superuser that you created above.
- See the containers and image data that you created with the admin app. (See below.)
- See the image jpegs with `$ ls -lt /tmp | head`



## How To: Run the admin app

- Start the server, if it's not already running. (See above)
- Point your browser to `http://127.0.0.1:8000/admin/`
- Log in with the superuser that you created above.

## How To: Create a fresh DB

```
$ dropdb recyclable
$ rm recyclable/migrations/0*.py
$ createdb recyclable
$ django-admin makemigrations recyclable
$ django-admin migrate
```

## POC

### How To: Clear the tables prior to reloading data into the db

```
$ psql recyclable
# delete from recyclable_image
# delete from recyclable_container
# \q
```

### How To: Load some initial data from the S3 bucket.

- cd to olyns-sandbox/container_image_database.
- Run the aws_script.py script to create the postgres database called demo.
- Export the data from that database to two csv files: containers.csv & images.csv, with:

```
$ psql demo
# COPY (SELECT * FROM container) to '/tmp/container.csv' WITH CSV HEADER;
# COPY (SELECT * FROM image) to '/tmp/image.csv' WITH CSV HEADER;
```

- cd to recyclable directory, then do

```
$ django-admin shell
>>> import recyclable.models
>>> recyclable.models.load_models_from_csv('/tmp')
```
