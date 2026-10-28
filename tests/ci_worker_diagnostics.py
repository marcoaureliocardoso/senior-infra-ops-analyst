"""Closed audit-worker failure protocol. Never retain received command content."""
import json

PREFIX = b'CI_ROOT_FAILURE '
PHASES = frozenset('''ROOT_SCOPE ROOT_MANIFEST ROOT_DIRECTORIES ROOT_CACHE
AUDIT_RUNTIME_LOAD AUDIT_RUNTIME_VERIFY AUDIT_REQUEST AUDIT_JOURNAL_OPEN
AUDIT_JOURNAL_SPAWN AUDIT_JOURNAL_WAIT AUDIT_MATCH TRANSPORT'''.split())
ERRORS = frozenset('''UNKNOWN_ERROR OS_ERROR CI_ROOT_SCOPE_REJECTED
CI_ROOT_DIRECTORY_UNSAFE CI_ROOT_RECORD_UNSAFE CI_ROOT_OWNERSHIP_UNPROVEN
CI_AUDIT_SCOPE_REJECTED CI_ROOT_COMMAND_FAILED CI_ROOT_COMMAND_TIMEOUT
CI_ROOT_COMMAND_OUTPUT_LIMIT CI_ROOT_TRANSPORT_FAILED CI_ROOT_PROTOCOL_INVALID
RUNTIME_SPEC_INVALID RUNTIME_DIRECTORY_UNSAFE RUNTIME_BINARY_UNSAFE
RUNTIME_BINARY_CHANGED RUNTIME_RECEIPT_INVALID RUNTIME_IDENTITY_CHANGED
RUNTIME_RECEIPT_CHANGED RUNTIME_VERIFICATION_FAILED RUNTIME_VERSION_MISMATCH'''.split())
KEYS = frozenset({'phase', 'error', 'workerReturnCode', 'commandReturnCode'})


def return_code(value):
    return value is None or type(value) is int and -128 <= value <= 255


def validate_failure(value):
    if (type(value) is not dict or set(value) != KEYS
            or type(value['phase']) is not str or value['phase'] not in PHASES
            or type(value['error']) is not str or value['error'] not in ERRORS
            or not return_code(value['workerReturnCode']) or not return_code(value['commandReturnCode'])):
        raise ValueError('CI_ROOT_PROTOCOL_INVALID')
    return value


def encode_failure(trace, error):
    code = 'OS_ERROR' if isinstance(error, OSError) else 'UNKNOWN_ERROR'
    if (type(error) is ValueError and len(error.args) == 1
            and type(error.args[0]) is str and error.args[0] in ERRORS):
        code = error.args[0]
    value = validate_failure(dict(phase=trace['phase'], error=code, workerReturnCode=1,
                                  commandReturnCode=trace.get('commandReturnCode')))
    return PREFIX.decode('ascii') + json.dumps(value, separators=(',', ':'), sort_keys=True)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('CI_ROOT_PROTOCOL_INVALID')
        result[key] = value
    return result


def decode_failure(payload, worker_rc):
    fallback = dict(phase='TRANSPORT', error='CI_ROOT_TRANSPORT_FAILED',
                    workerReturnCode=worker_rc if return_code(worker_rc) else None, commandReturnCode=None)
    if type(payload) is not bytes or not payload.startswith(PREFIX):
        return fallback
    fallback['error'] = 'CI_ROOT_PROTOCOL_INVALID'
    if worker_rc != 1 or type(worker_rc) is not int or len(payload) > 1024: return fallback
    try:
        value = validate_failure(json.loads(payload[len(PREFIX):], object_pairs_hook=_unique))
        if value['phase'] == 'TRANSPORT' or value['workerReturnCode'] != 1: return fallback
        return value
    except (ValueError, UnicodeError, RecursionError):
        return fallback


def failure_detail(error):
    if (type(error) is ValueError and len(error.args) == 2
            and type(error.args[0]) is str and error.args[0] == 'CI_ROOT_WORKER_FAILED'):
        try: return validate_failure(error.args[1])
        except ValueError: pass
    return None
