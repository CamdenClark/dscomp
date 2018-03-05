To get started, install and start mysqld, then run

```
virtualenv venv -p python3
source venv/bin/activate
pip install -r requirements.0.txt
pip install -r requirements.1.txt

export FLASK_APP=dscomp
export FLASK_DEBUG = true
flask initdb
flask run
```

I might have gotten a couple things wrong up there, I'm doing this from memory.

But basically, install and start msyqld, use python 3, install the dependencies, add those environment variables, then initialize the database, and run flask.
