# Python CLAMAV

This is a Flask Malware scanner for Google Cloud Storage.
The project is configured to run on GCP cloud run.

## Installation

Use [docker-compose](https://docs.docker.com/compose/) to install and start.

```bash
$ docker-compose build
$ docker-compose up
```

## Usage

```bash
$ curl -d '{"kind": "storage#object", "name":"example.txt", "bucket":"BUCKET_NAME","size": int<file_size> }' -H "Content-Type: application/json" -X POST http://localhost:5000/scan_file
```

If Malware is found in the file, the file would be moved to a quarantine bucket.
If the file is clean, the file would be moved to a clean bucket.
Modify the code to specify the quarantine and clean bucketa.