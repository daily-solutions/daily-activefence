# ActiveFence daily-python demo

This demo comes in two parts. The `python` directory contains the daily-python code, and the `moderator-client` directory contains a lightly modified version of the daily-react example app from [this repo](https://github.com/daily-demos/custom-video-daily-react-hooks).

To run the python code, edit `activefence.py` to add your own room and API key info, then run ngrok and the python script:

```
ngrok http -subdomain=yoursubdomain 8080
```

```
cd python
pip install daily-python requests boto3
python activefence.py
```

To run the moderator-client app:

```
cd moderator-client
npm install
npm start
```

You can directly join your room by opening `http://localhost:3000?roomurl=https://YOURDOMAIN.daily.co/YOURROOM`.
