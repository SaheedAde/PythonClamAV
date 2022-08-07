import os
import clamd
import logging
import datetime

from io import BytesIO
from flask import Flask, request
from google.cloud import storage
from google.cloud.storage import Blob
from scanner_utils import handle_error_response

app = Flask(__name__)

BUCKET_NAME = 'BUCKET_NAME'

STORAGE_CLIENT = storage.Client()
MAX_FILE_SIZE = 500000000
BUCKET_CONFIG = {
    'buckets': [{
        'unscanned': BUCKET_NAME,
        'clean': 'clean_bucket_name', # to be created
        'quarantined': 'quarantined_bucket_name' # to be created
    }],
}

def copy_processed_file(filename, is_clean, config):
    dest_path = ''
    success = True
    try:
        src_bucket = STORAGE_CLIENT.get_bucket(config['unscanned'])
        dest_bucket_name = config['clean'] if is_clean else config['quarantined']
        dest_bucket = STORAGE_CLIENT.get_bucket(dest_bucket_name)

        src_file = src_bucket.blob(filename)
        dest_file = src_bucket.copy_blob(src_file, dest_bucket, dest_path)
    except Exception as e:
        msg = f'Copying {filename} to {dest_bucket_name} Error'
        success = False
        logging.error(msg)

    return success


@app.route("/")
def hello_world():
    name = os.environ.get("NAME", "World")
    return "Hello {}!".format(name)


@app.route("/scan_file", methods=['POST'])
def scanner():
    data = request.get_json(force=True)
    kind = data.get('kind')
    name = data.get('name') # example.txt
    bucket = data.get('bucket')
    size = data.get('size')
    if kind != 'storage#object':
        return handle_error_response(403, f'{kind} is not a GCS Storage Object')
    if not name:
        return handle_error_response(403, f'file name not specified')
    if not bucket:
        return handle_error_response(403, f'bucket name not specified')
    if size is None:
        return handle_error_response(403, f'size not specified')
    if type(size) != int:
        return handle_error_response(403, f'size not specified')
    if size > MAX_FILE_SIZE:
        msg = f'file gs://{bucket}/{name} too large for scanning at {size} bytes'
        return handle_error_response(403, msg)

    config = [c for c in BUCKET_CONFIG['buckets'] if c['unscanned'] == bucket]
    if not config:
        msg = f'Bucket name - {bucket} not in config'
        return handle_error_response(404, msg)

    config = config[0]
    try:
        cd = clamd.ClamdUnixSocket()
        logging.info(f'Server responded with message: {cd.ping()}')
    except Exception as e:
        logging.error('Server is not active')
        return handle_error_response(500, 'Server is not active')

    clamd_version = cd.version()
    logging.info(
        f'Scan request for gs://{bucket}/{name}, \
        ({size} bytes) scanning with clam {clamd_version}'
    )

    bucket_obj = STORAGE_CLIENT.bucket(bucket)
    stats = Blob(bucket=bucket_obj, name=name).exists(STORAGE_CLIENT)

    if not stats:
        msg = f'File: gs://{bucket}/{name} does not exist'
        return handle_error_response(404, msg)

    file = BytesIO()
    file_blob = bucket_obj.blob(name)
    file_blob.download_to_file(file)

    start_time = datetime.datetime.now()
    successful = True
    try:
        scan_result = cd.instream(file)
    except Exception as e:
        successful = False
    finally:
        # Ensure stream is destroyed in all situations to prevent any
        # resource leak
        file.close()
        if not successful:
            msg = f'Error while scanning File: gs://{bucket}/{name}: {e}'
            logging.error(msg)
            return handle_error_response(500, msg)

    scan_duration = datetime.datetime.now() - start_time
    if scan_result['stream'][0] not in ['FOUND', 'OK']:
        msg = f'Error while processing File: gs://{bucket}/{name} \
                ({size}) bytes in {scan_duration} ms'
        logging.info(scan_result['stream'][0])
        logging.error(msg)
        return handle_error_response(500, msg)

    file_is_clean = scan_result['stream'][0] == 'OK'
    scan_msg = 'CLEAN' if file_is_clean else 'INFECTED'
    msg = f'Scan status for gs://{bucket}/{name}: {scan_msg} \
            ({size} bytes in {scan_duration} ms)'
    logging.info(msg)
    copy_status = copy_processed_file(name, file_is_clean, config)

    # Respond to API client.
    return '200', {
        'status': scan_msg,
        'clam_version': clamd_version,
        'copy_status': copy_status
    }
