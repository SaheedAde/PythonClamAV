import logging


def handle_error_response(code, message):
  logging.error(f'Error processing request: {message}')
  return f'{code}', {'message': message, 'status': 'error'}
