FROM python:3.13.0-alpine

RUN apk add --no-cache \
    curl \
    postgresql

# Install packages
RUN python -m pip install --upgrade pip
RUN python -m pip install \
    Django \
    "psycopg[binary]" \
    django-debug-toolbar \
    python-dotenv \
    requests \
    pyjwt \
    logging \
    pyotp \
    djangorestframework \
    markdown \
    django-filter \
    drf-spectacular \
    python-socketio \
    gunicorn \
    "python-socketio[client]" \
    numpy \
    neat-python


# Move Script File
COPY ./run_server.sh /server/run_server.sh
RUN chmod +x /server/run_server.sh

# Move Server File
# COPY . /server

# Execute Script
WORKDIR /server
ENTRYPOINT ["sh", "./run_server.sh"]
