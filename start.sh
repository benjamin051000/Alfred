# Run docker image (connect config.ini (read-only) as a volume)
# TODO if this fails, just copy and paste into Bash shell.
docker run -v ${PWD}/config.ini:/Alfred/config.ini:ro -it alfred
