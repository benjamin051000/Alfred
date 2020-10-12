# Alfred
A Discord bot written via the python discord wrapper discord-py.

To use, first `pip install -r requirements.txt` to install necessary packages.

Then, simply run one of the start scripts!

Alternatively, you can build and run the provided Dockerfile with `docker build -t alfred . && docker run -it alfred`.

To automate deployment of updates to the server, use a github webhook. In `deploy-server.js`, edit your username and branch to push events to. Then `npm init` to get all required packages and run `pm2 start deploy-server.js` to start the server. When a commit is pushed to remote on the branch specified in the server file, it will automatically kill the python process, pull from remote, and restart seamlessly.
