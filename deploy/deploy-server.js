let express = require('express');
let childP = require('child_process');
let app = express();


let githubUsername = 'benjamin051000';

app.use(express.json());

app.listen(3000, ()=>{});

app.post('/webhooks/github', (request, response) => {

    let sender = request.body.sender.login;
    let branch = request.body.ref;
    console.log(sender);
    console.log(branch);

    if(branch.indexOf('master') >= 0 && sender.login === githubUsername) {
        //Update the server
        console.log('Attempting to execute update.sh...');
        childP.exec('./update.sh', (err, stdout, stderr) => {
            if(err) {
                console.error(err);
                //Send an error!
                return response.sendStatus(500);
            }
            else {
                console.log('Executed update.sh successfully.');
            }
        });
    }
    //Send a success
    response.sendStatus(200);
    console.log('Sent response successfully.');
});
