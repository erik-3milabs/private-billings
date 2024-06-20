# Docker

## Build
To build the application as a Docker, navigate to the root of this package and execute the following command
```sh
sudo docker build -t private-billing -f docker/DockerFile .
```

## Run
To run a container, execute
```sh
sudo docker run -p <port>:<port> <variables> private-billing
```
where `<port>` should be replaced with the port at which the server is accessible and `<variables>` should be replaced with the appropriate environment variables.
For details on which variables should be used, look at the [docker-compose file](docker-compose.yml).

## Compose
To launch the network described in the compose file, execute
```sh
sudo docker compose -f docker/docker-compose.yml up
```

## Trigger
You can use `trigger.py` to trigger the billing network.
Copy it to the top-level folder, and execute
```sh
python3 trigger <cycle-id>
```
with `<cycle-id>` replaced by the id of the cycle for which you want to compute the bills.
