FROM python:3.9-slim

WORKDIR /app

# install dependencies
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt --extra-index-url https://www.piwheels.org/simple
RUN rm requirements.txt

# source code
COPY main.py main.py

CMD [ "python3", "main.py" ]
