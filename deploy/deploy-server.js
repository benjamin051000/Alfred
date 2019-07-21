let express = require('express');
let childP = require('child_process');
let app = express();


let githubUsername = 'benjamin051000';

app.post('/webhooks/github', (request, response) => {

    if(branch.indexOf('master') >= 0 && request.body.sender.login === githubUsername) {
        //Update the server
        childP.exec('./update.sh', (err, stdout, stderr) => {
        if(err) {
            console.err(err);
            //Send an error!
            return response.send(500);
        }
        //Send a success
        res.send(200);
    });
    }
});
