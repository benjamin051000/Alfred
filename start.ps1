# Run docker image (connect config.ini (read-only) as a volume)
docker run -itv ${PWD}/config.ini:/Alfred/config.ini:ro alfred
